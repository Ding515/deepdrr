# -*- coding: utf-8 -*-
"""
Created on Mon Apr 18 09:40:25 2022

@author: Ding
"""

import nibabel as nib
import numpy as np

original_data_path = 'E:\\R3\\result\\result_combination\\THIN_BONE_TORSO_STANDARD_TORSO_Thorax_81918_19.nii.gz'
data_struct = nib.load(original_data_path)
original_data = data_struct.get_fdata()
existing_mask_path = 'E:\\R3\\result\\result_combination\\fusion_result_withoutvnet.nii.gz'
mask_struct = nib.load(existing_mask_path)
mask_data = mask_struct.get_fdata()
mask_data = mask_data.astype(np.int8)


mean = -630.1
std = 479.7

mask_data[(mask_data==0) * ((original_data-mean)/std<(-500-mean)/std)] = 1
mask_data[(mask_data==0) * ((original_data-mean)/std>=(-500-mean)/std)] = 3

fusion_mask_struct = nib.Nifti1Image(mask_data,np.eye(4))
nib.save(fusion_mask_struct,'E:\\R3\\result\\result_combination\\fusion_result_threshold.nii.gz')
single_mask = np.zeros(mask_data.shape,dtype = np.int8)
single_mask [mask_data==7] =1
single_mask_struct = nib.Nifti1Image(single_mask,np.eye(4))
nib.save(single_mask_struct,'E:\\R3\\result\\result_combination\\fusion_result_threshold_kidney.nii.gz')
