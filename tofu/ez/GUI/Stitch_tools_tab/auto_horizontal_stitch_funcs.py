import os
import numpy as np
import yaml
from tofu.ez.Helpers.stitch_funcs import main_360_mp_depth1
from tofu.ez.main import get_CTdirs_list
from tofu.ez.Helpers.find_360_overlap import find_overlap

class AutoHorizontalStitchFunctions:
    def __init__(self, parameters):
        self.lvl0 = os.path.abspath(parameters["input_dir"])
        self.ct_dirs = []
        self.ct_axis_dict = {}
        self.parameters = parameters
        self.greatest_axis_value = 0
        self.fdt_settings = {
            'darks': "darks",
            'flats':"flats",
            'tomo':"tomo",
            'flats2':"flats2",
            'common_darks': self.parameters['darks_dir'],
            'common_flats': self.parameters['flats_dir'],
            'common_flats2': self.parameters['flats2_dir'],
            'use_common_flats2': True if len(str(self.parameters['flats2_dir'])) > 0 else False,
            'use_shared_flatsdarks': self.parameters['common_flats_darks']
        }

    def run_horizontal_auto_stitch(self):
        """
        Main function that calls all other functions
        """
        # Write parameters to .yaml file - quit if something goes wrong
        if self.write_yaml_params() == -1:
            return -1

        self.print_parameters()

        # Check input directory and find structure
        print("--> Finding CT Directories")
        self.ct_dirs, self.lvl0 = get_CTdirs_list(self.parameters['input_dir'], self.fdt_settings)
        if len(self.ct_dirs) == 0:
            print("Error: Could not find any input CT directories")
            print("-> Ensure that the directory you selected contains subdirectories named 'tomo'")
            return -1
        
        ax_range_list = self.parameters['search_half_acquisition_axis'].split(",")
        range_min = int(ax_range_list[0])
        range_max = int(ax_range_list[1])
        step = int(ax_range_list[2])
        
        overlap_parameters = {
            '360overlap_input_dir': self.parameters['input_dir'],
            '360overlap_temp_dir': self.parameters["temp_dir"],
            '360overlap_output_dir': os.path.join(self.parameters["output_dir"], "360axis-search"),
            '360overlap_row': self.parameters['search_slice'],
            '360overlap_lower_limit': range_min,
            '360overlap_upper_limit': range_max,
            '360overlap_increment': step,
            '360overlap_patch_size': self.parameters['patch_size'],
            '360overlap_doRR': self.parameters['enable_ring_removal'],
            'parameters_type': '360_overlap'
        }
        
        overlaps, _ = find_overlap(overlap_parameters, self.fdt_settings)
        
        if(len(overlaps) != len(self.ct_dirs)):
            print("Error: Could not find overlaps in one of the ct directories")
            return -1
        
        for i, ctset in enumerate(self.ct_dirs):          
            # Assign axis to a ct directory
            self.ct_axis_dict[ctset[0]] = overlaps[i]

        # Find the greatest axis value for use in determining overall cropping amount when stitching
        self.find_greatest_axis_value()
        
        # Output the input parameters and axis values to the log file
        self.write_to_log_file()

        # For each ct-dir and z-view we want to stitch all the images using the values in ct_axis_dict
        if not self.parameters['dry_run']:
            print("\n--> Stitching Images...")
            self.stitch_images()
            print("--> Finished Stitching")
            
    def stitch_images(self):
        for i, (ctdir, axis) in enumerate(self.ct_axis_dict.items()):
            print("================================================================")
            print(" -> Working On: " + str(ctdir))
            crop_pixels = self.greatest_axis_value - axis
            # TODO Address images flipping
            
            print(f"    horizontal acquisition axis position {axis}, margin to crop {crop_pixels} pixels")
            stitch_folder = "stitched"
            stack_folder = ctdir[len(self.lvl0):]
            if len(stack_folder) > 0 and (stack_folder[0] == '/' or stack_folder[0] == "\\"):
                stack_folder = stack_folder[1:]   # Remove absolute path character
                
            main_360_mp_depth1(ctdir,
                    os.path.join(self.parameters['output_dir'], stitch_folder, stack_folder),
                    axis, crop_pixels)

    def write_yaml_params(self):
        try:
            # Create the output directory root and save the parameters.yaml file
            os.makedirs(self.parameters['output_dir'], mode=0o777)
            file_path = os.path.join(self.parameters['output_dir'], 'auto_vertical_stitch_parameters.yaml')
            file_out = open(file_path, 'w')
            yaml.dump(self.parameters, file_out)
            print("Parameters file saved at: " + str(file_path))
            return 0
        except FileExistsError:
            print("--> Output Directory Exists - Delete Before Proceeding")
            return -1
    
    def find_greatest_axis_value(self):
        """
        Looks through all axis values and determines the greatest value
        """
        axis_list = list(self.ct_axis_dict.values())
        self.greatest_axis_value = max(axis_list)

    def write_to_log_file(self):
        '''
        Creates a log file with extension .info at the root of the output_dir tree structure
        Log file contains directory path and axis value
        '''
        if not os.path.isdir(self.parameters['output_dir']):
            os.makedirs(self.parameters['output_dir'], mode=0o777)
        file_path = os.path.join(self.parameters['output_dir'], 'axis_values.info')
        print("Axis values log file stored at: " + file_path)
        try:
            file_handle = open(file_path, 'w')
            # Print input parameters
            file_handle.write("======================== Parameters ========================" + "\n")
            file_handle.write("Input Directory: " + self.parameters['input_dir'] + "\n")
            file_handle.write("Output Directory: " + self.parameters['output_dir'] + "\n")
            file_handle.write("Using common set of flats and darks: " + str(self.parameters['common_flats_darks']) + "\n")
            file_handle.write("Darks Directory: " + self.parameters['darks_dir'] + "\n")
            file_handle.write("Flats Directory: " + self.parameters['flats_dir'] + "\n")
            file_handle.write("Flats2 Directory: " + self.parameters['flats2_dir'] + "\n")
            file_handle.write("Search Axis:" + str(self.parameters['search_half_acquisition_axis']) + "\n")

            # Print z-directory and corresponding axis value
            file_handle.write("\n======================== Axis Values ========================\n")
            for key in self.ct_axis_dict:
                key_value_str = str(key) + " : " + str(self.ct_axis_dict[key])
                print(key_value_str)
                file_handle.write(key_value_str + '\n')

            file_handle.write("\nGreatest axis value: " + str(self.greatest_axis_value))
        except FileNotFoundError:
            print("Error: Could not write log file")
            
    def print_parameters(self):
        """
        Prints parameter values with line formatting
        """
        print()
        print("**************************** Running Auto Horizontal Stitch ****************************")
        print("======================== Parameters ========================")
        print("Input Directory: " + self.parameters['input_dir'])
        print("Output Directory: " + self.parameters['output_dir'])
        print("Using common set of flats and darks: " + str(self.parameters['common_flats_darks']))
        print("Darks Directory: " + self.parameters['darks_dir'])
        print("Flats Directory: " + self.parameters['flats_dir'])
        print("Flats2 Directory: " + self.parameters['flats2_dir'])
        print("Search Axis:", str(self.parameters['search_half_acquisition_axis']))
        print("============================================================")
