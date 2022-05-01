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

### Segmentation pipeline using CT-ORG Net
This is the CT-ORG segmentation part based on NMDID dataset, two stages for segmentation:

```./CT-ORG/torso_sample_collecting.py``` for specific data collection in general torso dataset

```./CT-ORG/org_mask_batch.py``` for CT-ORG Net segmentation.

### Merging
Currently the mering part utilizes masks from nnUNet and CT-ORG Net.
We assume the data is stored in the following format:

```bash
  --original_data
  --CT-ORG mask
  --nnUNet mask
  --Merging result
```
Merging part requires the masks collected from CT-ORG and nnUNet and the original data. For each voxel, a label will be assigned based on previous segmentation result or CT values(into air or general soft tissue categories). And the merging masks will be stored in merging result folder. All of these four directories are required as input for this program.

Output types for current merging mask is:
```
usion_dict = {1:'air',2:'bone', 3:'soft tissue',4:'liver',5:'bladder',6:'lung',7:'kidney',8:'spleen',
               9:'gallbladder',10:'esophagus',11:'stomach'}
```
This is an one-channel mask specific for DeepDRR input.

### Use the new segmentation method to simulate X-Ray image

The `use_nnunet` module contains the following utilities: (this module is not in the current directory. it is merged with DeepDRR package.)

`.read_mask(dir, LabelType)`: Read an existing segmentation mask with the corresponding label format of `LabelType`. Assign corresponding material property according to this mask when performing projection.

`.nnu_segmentation(input, TaskType)`: For the input CT image, automatically generate the corresponding mask using one of the pretrained model of nnU-Net (the choose of pretrained model is controlled by `TaskType`), and perform projection using the generated mask.

