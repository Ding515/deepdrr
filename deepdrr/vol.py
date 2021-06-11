"""Volume class for CT volume.

"""

from __future__ import annotations
from typing import Union, Tuple, Literal, List, Optional, Dict

import logging
import numpy as np
from pathlib import Path
import nibabel as nib
from pydicom.filereader import dcmread
import nrrd

from . import load_dicom
from . import geo
from . import utils

pv, pv_available = utils.try_import_pyvista()
vtk, nps, vtk_available = utils.try_import_vtk()


logger = logging.getLogger(__name__)


class Volume(object):
    data: np.ndarray
    materials: Dict[str, np.ndarray]
    anatomical_from_ijk: geo.FrameTransform
    world_from_anatomical: geo.FrameTransform

    def __init__(
        self,
        data: np.ndarray,
        materials: Dict[str, np.ndarray],
        anatomical_from_ijk: geo.FrameTransform,
        world_from_anatomical: Optional[geo.FrameTransform] = None,
    ) -> None:
        """A deepdrr Volume object with materials segmentation and orientation in world-space.

        The recommended way to create a Volume is to load from a NifTi file using the `Volume.from_nifti(path)` class method.

        Args:
            data (np.ndarray): the density data (a 3D array)
            materials (Dict[str, np.ndarray]): material segmentation of the volume, mapping material name to binary segmentation.
            anatomical_from_ijk (geo.FrameTransform): transformation from IJK space to anatomical (RAS or LPS).
            world_from_anatomical (Optional[geo.FrameTransform], optional): transformation from the anatomical space to world coordinates. If None, assumes identity. Defaults to None.
        """
        self.data = np.array(data).astype(np.float32)
        self.materials = self._format_materials(materials)
        self.anatomical_from_ijk = geo.frame_transform(anatomical_from_ijk)
        self.world_from_anatomical = (
            geo.FrameTransform.identity(3)
            if world_from_anatomical is None
            else geo.frame_transform(world_from_anatomical)
        )

    @classmethod
    def from_parameters(
        cls,
        data: np.ndarray,
        materials: Dict[str, np.ndarray],
        origin: geo.Point3D,
        spacing: Optional[geo.Vector3D] = [1, 1, 1],
        anatomical_coordinate_system: Optional[Literal["LPS", "RAS", "none"]] = None,
        world_from_anatomical: Optional[geo.FrameTransform] = None,
    ):
        """Create a volume object with a segmentation of the materials, with its own anatomical coordinate space, from parameters.

        Note that the anatomical coordinate system is not the world coordinate system (which is cartesian).
        
        Suggested anatomical coordinate space units is millimeters.
        A helpful introduction to the geometry is can be found [here](https://www.slicer.org/wiki/Coordinate_systems).

        Args:
            volume (np.ndarray): the volume density data.
            materials (dict[str, np.ndarray]): mapping from material names to binary segmentation of that material.
            origin (Point3D): Location of the volume's origin in the anatomical coordinate system.
            spacing (Tuple[float, float, float], optional): Spacing of the volume in the anatomical coordinate system. Defaults to (1, 1, 1).
            anatomical_coordinate_system (Literal['LPS', 'RAS', 'none']): anatomical coordinate system convention. Defaults to 'none'.
            world_from_anatomical (FrameTransform, optional): Optional transformation from anatomical to world coordinates. 
                If None, then identity is used. Defaults to None.
        """
        origin = geo.point(origin)
        spacing = geo.vector(spacing)

        assert spacing.dim == 3

        # define anatomical_from_ijk FrameTransform
        if (
            anatomical_coordinate_system is None
            or anatomical_coordinate_system == "none"
        ):
            anatomical_from_ijk = geo.FrameTransform.from_scaling(
                scaling=spacing, translation=origin
            )
        elif anatomical_coordinate_system == "LPS":
            # IJKtoLPS = LPS_from_IJK
            rotation = [
                [spacing[0], 0, 0],
                [0, 0, spacing[2]],
                [0, -spacing[1], 0],
            ]
            anatomical_from_ijk = geo.FrameTransform.from_rt(
                rotation=rotation, translation=origin
            )
        else:
            raise NotImplementedError(
                "conversion from RAS (not hard, look at LPS example)"
            )

        return cls(
            data=data,
            materials=materials,
            anatomical_from_ijk=anatomical_from_ijk,
            world_from_anatomical=world_from_anatomical,
        )

    @classmethod
    def from_hu(
        cls,
        hu_values: np.ndarray,
        origin: geo.Point3D,
        use_thresholding: bool = True,
        spacing: Optional[geo.Vector3D] = (1, 1, 1),
        anatomical_coordinate_system: Optional[Literal["LPS", "RAS", "none"]] = None,
        world_from_anatomical: Optional[geo.FrameTransform] = None,
    ) -> None:
        data = cls._convert_hounsfield_to_density(hu_values)
        materials = cls._segment_materials(hu_values, use_thresholding=use_thresholding)

        return cls.from_parameters(
            data,
            materials,
            origin=origin,
            spacing=spacing,
            anatomical_coordinate_system=anatomical_coordinate_system,
            world_from_anatomical=world_from_anatomical,
        )

    @staticmethod
    def _get_cache_path(
        use_thresholding: bool = True,
        cache_dir: Optional[Path] = None,
        prefix: str = "",
    ) -> Optional[Path]:
        return (
            None
            if cache_dir is None
            else Path(cache_dir)
            / "{}materials{}.npz".format(
                prefix, "_with_thresholding" if use_thresholding else ""
            )
        )

    @staticmethod
    def _convert_hounsfield_to_density(hu_values: np.ndarray):
        return load_dicom.conv_hu_to_density(hu_values)

    @staticmethod
    def _segment_materials(
        hu_values: np.ndarray, use_thresholding: bool = True,
    ) -> Dict[str, np.ndarray]:
        """Segment the materials.

        Meant for internal use, particularly to be overriden by volumes with different materials.

        Args:
            hu_values (np.ndarray): volume data in Hounsfield Units.
            use_thretholding (bool, optional): whether to segment with thresholding (true) or a DNN. Defaults to True.

        Returns:
            Dict[str, np.ndarray]: materials segmentation.
        """
        if use_thresholding:
            return load_dicom.conv_hu_to_materials_thresholding(hu_values)
        else:
            return load_dicom.conv_hu_to_materials(hu_values)

    @classmethod
    def segment_materials(
        cls,
        hu_values: np.ndarray,
        use_thresholding: bool = True,
        use_cached: bool = True,
        cache_dir: Optional[Path] = None,
        prefix: str = "",
    ) -> Dict[str, np.ndarray]:
        """Segment the materials in a volume, potentially caching.

       

        Args:
            hu_values (np.ndarray): volume data in Hounsfield Units.
            use_thretholding (bool, optional): whether to segment with thresholding (true) or a DNN. Defaults to True.
            use_cached (bool, optional): use the cached segmentation, if it exists. Defaults to True.
            cache_dir (Optional[Path], optional): where to look for the segmentation cache. If None, no caching performed. Defaults to None.
            prefix (str, optional): Optional prefix to prepend to the cache names. Defaults to ''.

        Returns:
            Dict[str, np.ndarray]: materials segmentation.
        """

        materials_path = cls._get_cache_path(
            use_thresholding=use_thresholding, cache_dir=cache_dir, prefix=prefix
        )

        if materials_path is not None and materials_path.exists() and use_cached:
            logger.info(f"using cached materials segmentation at {materials_path}")
            materials = dict(np.load(materials_path))
        else:
            logger.info(f"segmenting materials in volume")
            materials = cls._segment_materials(
                hu_values, use_thresholding=use_thresholding
            )

            if materials_path is not None:
                np.savez(materials_path, **materials)

        return materials

    @classmethod
    def from_nifti(
        cls,
        path: Path,
        world_from_anatomical: Optional[geo.FrameTransform] = None,
        use_thresholding: bool = True,
        use_cached: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """Load a volume from NiFti file.

        Args:
            path (Path): path to the .nii.gz file.
            use_thresholding (bool, optional): segment the materials using thresholding (faster but less accurate). Defaults to True.
            world_from_anatomical (Optional[geo.FrameTransform], optional): position the volume in world space. If None, uses identity. Defaults to None.
            use_cached (bool, optional): [description]. Use a cached segmentation if available. Defaults to True.
            cache_dir (Optional[Path], optional): Where to load/save the cached segmentation. If None, use the parent dir of `path`. Defaults to None.

        Returns:
            [type]: [description]
        """
        path = Path(path)

        if cache_dir is None:
            cache_dir = path.parent

        logger.info(f"loading NiFti volume from {path}")
        img = nib.load(path)
        if img.header.get_xyzt_units() != ("mm", "sec"):
            logger.warning(f"got NifTi units: {img.header.get_xyzt_units()}")

        anatomical_from_ijk = geo.FrameTransform(img.affine)
        hu_values = img.get_fdata()

        data = cls._convert_hounsfield_to_density(hu_values)
        materials = cls.segment_materials(
            hu_values,
            use_thresholding=use_thresholding,
            use_cached=use_cached,
            cache_dir=cache_dir,
        )

        return cls(data, materials, anatomical_from_ijk, world_from_anatomical,)

    @classmethod
    def from_dicom(
        cls,
        path: Path,
        use_thresholding: bool = True,
        world_from_anatomical: Optional[geo.FrameTransform] = None,
        use_cached: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """
        load a volume from a dicom file and compute the anatomical_from_ijk transform from metadata
        https://www.slicer.org/wiki/Coordinate_systems
        Args:
            path: path-like to a multi-frame dicom file. (Currently only Multi-Frame from Siemens supported)
            use_thresholding (bool, optional): segment the materials using thresholding (faster but less accurate). Defaults to True.
            world_from_anatomical (Optional[geo.FrameTransform], optional): position the volume in world space. If None, uses identity. Defaults to None.
            use_cached (bool, optional): [description]. Use a cached segmentation if available. Defaults to True.
            cache_dir (Optional[Path], optional): Where to load/save the cached segmentation. If None, use the parent dir of `path`. Defaults to None.

        Returns:
            Volume: an instance of a deepdrr volume
        """
        path = Path(path)
        stem = path.name.split(".")[0]

        if cache_dir is None:
            cache_dir = path.parent

        # Multi-frame dicoms store all slices of a volume in one file.
        # they must specify the necessary dicom tags under
        # https://dicom.innolitics.com/ciods/enhanced-ct-image/enhanced-ct-image-multi-frame-functional-groups
        assert (
            path.is_file()
        ), "Currently only multi-frame dicoms are supported. Path must refer to a file."
        logger.info(f"loading Dicom volume from {path}")

        # reading the dicom dataset object
        ds = dcmread(path)

        # slice specific tags
        frames = ds.PerFrameFunctionalGroupsSequence
        num_slices = len(frames)
        first_slice_position = np.array(
            frames[0].PlanePositionSequence[0].ImagePositionPatient
        )
        last_slice_position = np.array(
            frames[-1].PlanePositionSequence[0].ImagePositionPatient
        )

        # volume specific tags
        shared = ds.SharedFunctionalGroupsSequence[0]
        RC = (
            np.array(shared.PlaneOrientationSequence[0].ImageOrientationPatient)
            .reshape(2, 3)
            .T
        )
        PixelSpacing = np.array(shared.PixelMeasuresSequence[0].PixelSpacing)
        SliceThickness = np.array(shared.PixelMeasuresSequence[0].SliceThickness)
        offset = shared.PixelValueTransformationSequence[0].RescaleIntercept
        scale = shared.PixelValueTransformationSequence[0].RescaleSlope

        # make user aware that this is only tested on windows
        if ds.Manufacturer != "SIEMENS":
            logger.warning(
                "Multi-frame loading has only been tested on Siemens Enhanced CT DICOMs."
                "Please verify everything works as expected."
            )

        # read the 'raw' data array
        raw_data = ds.pixel_array.astype(np.float32)
        hu_values = raw_data * scale + offset

        """
        EXPLANATION - indexing conventions

        According to dicom (C.7.6.3.1.4 - Pixel Data) slices are of shape (Rows, Columns) 
        => must be (j, i) indexed if we define i == horizontal and j == vertical.
        => we want to conform to the (i, j, k) layout and therefore move the axis of the data array
        """

        # convert data to our indexing convention (k, j, i) -> (j, i, k)
        hu_values = hu_values.transpose((2, 1, 0)).copy()

        # transform the volume in HU to densities
        data = load_dicom.conv_hu_to_density(hu_values)

        # obtain materials analogous to nifti
        if use_thresholding:
            materials_path = cache_dir / f"{stem}_materials_thresholding.npz"
            if use_cached and materials_path.exists():
                logger.info(f"found materials segmentation at {materials_path}.")
                materials = dict(np.load(materials_path))
            else:
                logger.info(f"segmenting materials in volume")
                materials = load_dicom.conv_hu_to_materials_thresholding(hu_values)
                np.savez(materials_path, **materials)
        else:
            materials_path = cache_dir / f"{stem}_materials.npz"
            if use_cached and materials_path.exists():
                logger.info(f"found materials segmentation at {materials_path}.")
                materials = dict(np.load(materials_path))
            else:
                logger.info(f"segmenting materials in volume")
                materials = load_dicom.conv_hu_to_materials(hu_values)
                np.savez(materials_path, **materials)

        """
        EXPLANATION - 3d affine transform
        
        DICOM does not offer a 3d transform to locate the voxel data in world space for historic reasons.
        However we can construct it from some related DICOM tags. See this resource for more information:
        https://nipy.org/nibabel/dicom/dicom_orientation.html
        
        Note, that we do not modify the affine transform to account for the differences in indexing, but 
        instead modified the data in memory to be in (i, j, k) order.
        """
        # construct column for index k
        k = np.array(
            (last_slice_position - first_slice_position) / (num_slices - 1)
        ).reshape(3, 1)

        # check if the calculated increment matches the SliceThickness (allow .1 millimeters deviations)
        assert np.allclose(np.abs(k[2]), SliceThickness, atol=0.1, rtol=0)

        # apply scaling to mm
        RC_scaled = RC * PixelSpacing

        # construct rotation matrix from three columns for (i, j, k)
        rot = np.hstack((RC_scaled, k))

        # construct affine matrix
        affine = np.zeros((4, 4))
        affine[:3, :3] = rot  # rotation and scaling
        affine[:3, 3] = first_slice_position  # translation
        affine[3, 3] = 1  # homogenous component

        # log affine matrix in debug mode
        logger.debug(f"manually constructed affine matrix: \n{affine}")
        logger.debug(
            f"volume_center_xyz : {np.mean([affine @ np.array([*data.shape, 1]), affine @ [0, 0, 0, 1]], axis=0)}"
        )

        # cast to FrameTransform
        lps_from_ijk = geo.FrameTransform(affine)

        # constructing the volume
        return cls(data, materials, lps_from_ijk, world_from_anatomical,)

    def to_dicom(self, path: str):
        """Write the volume to a DICOM file.

        Args:
            path (str): the path to the file.
        """
        path = Path(path)

        raise NotImplementedError("save volume to dicom file")

    @classmethod
    def from_nrrd(
        cls, 
        path: str, 
        world_from_anatomical: Optional[geo.FrameTransform] = None, 
        use_thresholding: bool = True,
        use_cached: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """Load a volume from a nrrd file.

        Args:
            path (str): path to the file.
            use_thresholding (bool, optional): segment the materials using thresholding (faster but less accurate). Defaults to True.
            world_from_anatomical (Optional[geo.FrameTransform], optional): position the volume in world space. If None, uses identity. Defaults to None.
            use_cached (bool, optional): Use a cached segmentation if available. Defaults to True.
            cache_dir (Optional[Path], optional): Where to load/save the cached segmentation. If None, use the parent dir of `path`. Defaults to None.

        Returns:
            Volume: A volume formed from the NRRD.
        """
        hu_values, header = nrrd.read(path)
        ijk_from_anatomical = np.concatenate(
            [
                header['space directions'],
                header['space origin'].reshape(-1, 1),
            ],
            axis=1,
        )
        ijk_from_anatomical = np.concatenate([ijk_from_anatomical, [[0, 0, 0, 1]]], axis=0)
        anatomical_from_ijk = np.linalg.inv(ijk_from_anatomical)
        data = cls._convert_hounsfield_to_density(hu_values)
        materials = cls.segment_materials(
            hu_values,
            use_thresholding=use_thresholding,
            use_cached=use_cached,
            cache_dir=cache_dir,
        )

        return cls(data, materials, anatomical_from_ijk, world_from_anatomical)

    @property
    def origin(self) -> geo.Point3D:
        """The origin of the volume in anatomical space."""
        return geo.point(self.anatomical_from_ijk.t)

    @property
    def origin_in_world(self) -> geo.Point3D:
        """The origin of the volume in world space."""
        return geo.point(self.world_from_ijk.t)

    @property
    def center_in_world(self) -> geo.Point3D:
        """The center of the volume in world coorindates. Useful for debugging."""
        return self.world_from_ijk @ geo.point(np.array(self.shape) / 2)

    @property
    def spacing(self) -> geo.Vector3D:
        """The spacing of the voxels."""
        return geo.vector(np.abs(np.array(self.anatomical_from_ijk.R)).max(axis=0))

    def _format_materials(self, materials: Dict[str, np.ndarray],) -> np.ndarray:
        """Standardize the input material segmentation."""
        for mat in materials:
            materials[mat] = np.array(materials[mat]).astype(np.float32)

        return materials

    @property
    def shape(self) -> Tuple[int, int, int]:
        return self.data.shape

    @property
    def world_from_ijk(self) -> geo.FrameTransform:
        return self.world_from_anatomical @ self.anatomical_from_ijk

    @property
    def ijk_from_world(self) -> geo.FrameTransform:
        return self.world_from_ijk.inv

    def __array__(self) -> np.ndarray:
        return self.data

    def translate_center_to(self, x: geo.Point3D) -> None:
        """Translate the volume so that its center is located at world-space point x.

        Only changes the translation elements of the world_from_anatomical transform. Preserves the current rotation of the 

        Args:
            x (geo.Point3D): the world-space point.

        """

        # TODO(killeen): fix this. It doesn't use x.
        x = geo.point(x)
        center_anatomical = self.anatomical_from_ijk @ geo.point(
            np.array(self.shape) / 2
        )
        self.world_from_anatomical = geo.FrameTransform.from_rt(
            self.world_from_anatomical.R
        ) @ geo.FrameTransform.from_origin(center_anatomical)

    def __contains__(self, x: geo.Point3D) -> bool:
        """Determine whether the point x is inside the volume.

        Args:
            x (geo.Point3D): world-space point.

        """
        x_ijk = self.ijk_from_world @ geo.point(x)
        return np.all(0 <= np.array(x_ijk) <= np.array(self.shape) - 1)

    def _make_surface(self, material: str = "bone"):
        """Make a surface for the boolean segmentation"""
        assert vtk_available and pv_available
        assert (
            material in self.materials
        ), f'"{material}" not in {self.materials.keys()}'

        segmentation = self.materials[material]
        R = self.anatomical_from_ijk.R
        t = self.anatomical_from_ijk.t

        vol = vtk.vtkStructuredPoints()
        vol.SetDimensions(
            segmentation.shape[0], segmentation.shape[1], segmentation.shape[2]
        )
        vol.SetOrigin(
            -np.sign(R[0, 0]) * t[0], np.sign(R[1, 1]) * t[1], np.sign(R[2, 2]) * t[2],
        )
        vol.SetSpacing(
            -abs(R[0, 0]), abs(R[1, 1]), abs(R[2, 2]),
        )

        segmentation = segmentation.astype(np.uint8)
        scalars = nps.numpy_to_vtk(segmentation.ravel(order="F"), deep=True)
        vol.GetPointData().SetScalars(scalars)

        logger.debug("isolating bone surface for visualization...")
        dmc = vtk.vtkDiscreteMarchingCubes()
        dmc.SetInputData(vol)
        dmc.GenerateValues(1, 1, 1)
        dmc.ComputeGradientsOff()
        dmc.ComputeNormalsOff()
        dmc.Update()

        surface = pv.wrap(dmc.GetOutput())
        if surface.is_all_triangles():
            surface.triangulate(inplace=True)

        surface.decimate_pro(
            0.01,
            feature_angle=60,
            splitting=False,
            preserve_topology=True,
            inplace=True,
        )
        surface.smooth(
            n_iter=30,
            relaxation_factor=0.25,
            feature_angle=70,
            boundary_smoothing=False,
            inplace=True,
        )
        surface.compute_normals(inplace=True)

        return surface

    def get_surface(
        self,
        material: str = "bone",
        cache_dir: Optional[Path] = None,
        use_cached: bool = True,
    ):
        cache_path = (
            None if cache_dir is None else Path(cache_dir) / f"{material}_mesh.vtp"
        )
        if use_cached and cache_path is not None and cache_path.exists():
            logger.info(f"reading cached {material} mesh from {cache_path}")
            surface = pv.read(cache_path)
        else:
            logger.info(f"meshing {material} segmentation...")
            surface = self._make_surface(material)
            if cache_path is not None:
                if not cache_dir.exists():
                    cache_dir.mkdir()
                logger.info(f"caching {material} surface to {cache_path}.")
                surface.save(cache_path)
        return surface

    def get_mesh_in_world(
        self,
        full: bool = False,
        cache_dir: Optional[Path] = None,
        use_cached: bool = True,
    ) -> pv.PolyData:
        """Get a pyvista mesh of the outline in world-space.

        Args:
            full (bool): Whether to render the full volume or just a wireframe. Defaults to False.
            cache_dir (Optional[Path], optional): a location to cache the bone surface.
            use_cached (bool): If False, don't use the cached bone surface but re-create it (expensive). Defaults to True.

        Returns:
            pv.PolyData: pyvista mesh.
        """

        assert (
            pv_available
        ), f"PyVista not available for obtaining Volume mesh. Try: `pip install pyvista`"

        x, y, z = np.array(self.shape) - 1
        points = [
            [0, 0, 0],
            [0, 0, z],
            [0, y, 0],
            [0, y, z],
            [x, 0, 0],
            [x, 0, z],
            [x, y, 0],
            [x, y, z],
        ]

        points = [list(self.world_from_ijk @ geo.point(p)) for p in points]
        mesh = pv.Line(points[0], points[1])
        mesh += pv.Line(points[0], points[2])
        mesh += pv.Line(points[3], points[1])
        mesh += pv.Line(points[3], points[2])
        mesh += pv.Line(points[4], points[5])
        mesh += pv.Line(points[4], points[6])
        mesh += pv.Line(points[7], points[5])
        mesh += pv.Line(points[7], points[6])
        mesh += pv.Line(points[0], points[4])
        mesh += pv.Line(points[1], points[5])
        mesh += pv.Line(points[2], points[6])
        mesh += pv.Line(points[3], points[7])

        if full:
            logger.debug(f"getting full surface mesh for volume")
            material_mesh = self.get_surface(
                material="bone", cache_dir=cache_dir, use_cached=use_cached
            )
            material_mesh.transform(geo.get_data(self.world_from_anatomical))
            mesh += material_mesh

        return mesh


class MetalVolume(Volume):
    """Same as a volume, but with a different segmentation for the materials.

    """

    @staticmethod
    def _convert_hounsfield_to_density(hu_values: np.ndarray):
        # TODO: verify
        return 30 * hu_values

    @staticmethod
    def _segment_materials(
        hu_values: np.ndarray, use_thresholding: bool = True
    ) -> Dict[str, np.ndarray]:
        if not use_thresholding:
            raise NotImplementedError

        return dict(
            air=(hu_values == 0), bone=(hu_values > 0), titanium=(hu_values > 0),
        )
