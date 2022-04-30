## Latest Development of CISII Project

New Features: 1. Segmentation pipeline using nnU-Net and CT-ORG; 2. New module named `use_nnunet` for assigning materials; 3. Codes for downstream nodule insertion and detection task.

### Segmentation pipeline using nnU-Net

To infer by nnU-Net pretrained models on NMDID dataset, these two utilities can be used:
```bash
nnunet/dataprep.py
nnunet/infer_nnUNet.py
```
The first one prepares CT images into the format suitable for nnU-Net. `type` can be adjusted for different type of input image (NIFTI, DICOM, single or batch).

The second one performs inference using pretrained models of nnU-Net. User can use `TaskType` to choose the paticular pretrained model.

### Use the new segmentation method to simulate X-Ray image

The `use_nnunet` module contains the following utilities: (this module is not in the current directory. it is merged with DeepDRR package.)

`.read_mask(dir, LabelType)`: Read an existing segmentation mask with the corresponding label format of `LabelType`. Assign corresponding material property according to this mask when performing projection.

`.nnu_segmentation(input, TaskType)`: For the input CT image, automatically generate the corresponding mask using one of the pretrained model of nnU-Net (the choose of pretrained model is controlled by `TaskType`), and perform projection using the generated mask.

