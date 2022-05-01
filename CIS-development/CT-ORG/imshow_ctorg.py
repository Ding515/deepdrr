# -*- coding: utf-8 -*-
"""
Created on Mon Apr  4 23:00:04 2022

@author: Ding
"""

import nibabel as nib
import numpy as np
#nii_file = nib.load('E:\\R3\\result\\temp_nnunet_mask\\98-Pediatric-CT-SEG-B1B6F67A.nii.gz')
nii_file = nib.load('E:\\R3\\result\\labels.nii')
data = nii_file.get_fdata()

x,y,z = np.where(data==5)
data1=np.zeros((data.shape[0],data.shape[1],data.shape[2]))
data1[x,y,z]=1
new_image = nib.Nifti1Image(data1, np.eye(4)) 
nib.save(new_image, 'E:\\R3\\result\\labels_5.nii') 
#label = list(np.unique(data))


