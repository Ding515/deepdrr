# -*- coding: utf-8 -*-
"""
Created on Fri Apr 29 04:13:28 2022

@author: Ding
"""

import os
import shutil
loaded_path = '/srv/data1/killeen/datasets/VertFluoro/torso_volumes'
upload_path ='/home/sean/torso_mid_result/data'
file_name_prefix = 'STANDARD_TORSO_Thorax_'
file_name_surfix = '.nii.gz'
exclude_surfix = 'seg'

case_list = os.listdir(loaded_path)

for case_name in case_list:
    
    file_list = os.listdir(os.path.join(loaded_path,case_name))
    
    for file_name in file_list:
        
        if file_name_prefix in file_name and file_name_surfix in file_name and exclude_surfix not in file_name:
            
            current_file_path = os.path.join(loaded_path,case_name,file_name)
            
            uploaded_file_path = os.path.join(upload_path,case_name+'.nii.gz')
            
            shutil.copyfile(current_file_path,uploaded_file_path)
            
            
            
            