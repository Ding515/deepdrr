import os

def runinf_nnUNet(idir,odir,TaskType):
    nii_directory = os.environ.get('nnUNet_raw_data_base') + '/nnUNet_raw_data/' + idir + '/'
    os.system('nnUNet_predict -i ' + nii_directory + 'imagesTs/ -o ' + odir +
              '/nnU_OUTPUT_Task' + str(TaskType) + '_' + idir + ' -t ' + str(TaskType) + ' -m 3d_fullres')


if __name__ == "__main__":
    TaskType = 17  # Liver:3, Lung:6, Pancreas:7, Spleen:9, multi-atlas abdominal organs:17
    input = '0430compressed'
    output = '/home/sean/torso_mid_result/nnunet_mask'
    runinf_nnUNet(input,output,TaskType)

