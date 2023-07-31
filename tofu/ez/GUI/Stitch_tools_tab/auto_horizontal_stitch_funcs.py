import os
import tifffile
from collections import defaultdict
import numpy as np
import multiprocessing as mp
from functools import partial
from scipy.stats import gmean
import math
import yaml
import sys
from tofu.ez.util import get_dims
from tofu.ez.find_axis_cmd_gen import find_axis_std, move_axis_images
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
            'use_common_flats2': True if len(self.parameters['flats2_dir']) > 0 else False,
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

        # For each zview we compute the axis of rotation
        print("--> Finding Axis of Rotation for each Z-View")
        self.compute_centers()
        print("\n ==> Found the following z-views and their corresponding axis of rotation <==")

        # Check the axis values and adjust for any outliers
        # If difference between two subsequent zdirs is > 3 then just change it to be 1 greater than previous
        self.correct_outliers()
        print("--> ct_axis_dict after correction: ")
        print(self.ct_axis_dict)

        # Find the greatest axis value for use in determining overall cropping amount when stitching
        # self.find_greatest_axis_value()
        # print("Greatest axis value: " + str(self.greatest_axis_value))
        

        
        overlap = 0
        if self.parameters['enable_half_acquisition_axis']:
            ax_range_list = self.parameters['search_half_acquisition_axis'].split(",")
            range_min = ax_range_list[0]
            range_max = ax_range_list[1]
            step = ax_range_list[2]
            
            overlap_parameters = {
                '360overlap_input_dir': self.parameters["input_dir"], #TODO Support multiple view folders
                '360overlap_temp_dir': os.path.join(self.parameters["temp_dir"], "tmp-360axis-search"),
                '360overlap_output_dir': os.path.join(self.parameters["output_dir"], "ezufo-360axis-search"),
                '360overlap_row': self.parameters['search_slice'],
                '360overlap_lower_limit': range_min,
                '360overlap_upper_limit': range_max,
                '360overlap_increment': step,
                '360overlap_doRR': self.parameters['enable_ring_removal']
            }
            
            overlap = find_overlap(overlap_parameters, self.fdt_settings)
            print("Pixel Overlap:", overlap)
        
        # Output the input parameters and axis values to the log file
        self.write_to_log_file()

        # For each ct-dir and z-view we want to stitch all the images using the values in ct_axis_dict
        if not self.parameters['dry_run']:
            print("\n--> Stitching Images...")
            self.stitch_images()
            print("--> Finished Stitching")
            
    def stitch_images(self):
        for i, (ctdir, ax) in enumerate(self.ct_axis_dict.items()):
            print("================================================================")
            print(" -> Working On: " + str(ctdir))
            #cra = float(self.greatest_axis_value) - float(ax)   #TODO Replace with 360-axis-search result
            cra = 0
            print(f"    axis position {ax}, margin to crop {cra} pixels")
            stitch_folder = "stitched"
            stack_folder = ctdir[len(self.lvl0):]
            if len(stack_folder) > 0 and (stack_folder[0] == '/' or stack_folder[0] == "\\"):
                stack_folder = stack_folder[1:]   # Remove absolute path character
                
            main_360_mp_depth1(ctdir,
                    os.path.join(self.parameters['output_dir'], stitch_folder, stack_folder),
                    ax, cra)

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
        
    def compute_centers(self):
        """
        Computes the rotational axis for each image in half-acquisition mode by minimizing STD of a slice
        """

        for i, ctset in enumerate(self.ct_dirs):          
            search_slice = int(self.parameters['search_slice'])
            nviews, wh, multipage = get_dims(os.path.join(ctset[0], self.fdt_settings['tomo']))
            
            # Obtain the largest patch size
            patch_size = 0
            if(wh[0] > wh[1]):
                patch_size = wh[0]
            else:
                patch_size = wh[1]
            print("WH:", wh)
            
            # Find center of rotation axis of each stack
            axis_folder = 'axis-search'
            os.system('rm -rf {}'.format(os.path.join(self.parameters['temp_dir'], axis_folder)))
            ax = find_axis_std(
                ctset,
                self.parameters['temp_dir'],
                self.parameters['search_rotational_axis'],
                search_slice,
                patch_size,
                False,
                nviews, wh
            )
            
            # Move axis for each stack to an output axis folder            
            move_axis_images(                        
                ctset[0][len(self.lvl0):],
                os.path.join(self.parameters['temp_dir'], axis_folder),
                os.path.join(self.parameters['output_dir'], axis_folder),
                self.parameters['search_rotational_axis'])
            self.ct_axis_dict[ctset[0]] = ax

    def get_filtered_filenames(self, path, exts=['.tif', '.edf']):
        result = []

        try:
            for ext in exts:
                result += [os.path.join(path, f) for f in os.listdir(path) if f.endswith(ext)]
        except OSError:
            return []

        return sorted(result)

    def compute_rotation_axis(self, first_projection, last_projection):
        """
        Compute the tomographic rotation axis based on cross-correlation technique.
        *first_projection* is the projection at 0 deg, *last_projection* is the projection
        at 180 deg.
        """
        from scipy.signal import fftconvolve
        width = first_projection.shape[1]
        first_projection = first_projection - first_projection.mean()
        last_projection = last_projection - last_projection.mean()

        # The rotation by 180 deg flips the image horizontally, in order
        # to do cross-correlation by convolution we must also flip it
        # vertically, so the image is transposed and we can apply convolution
        # which will act as cross-correlation
        convolved = fftconvolve(first_projection, last_projection[::-1, :], mode='same')
        center = np.unravel_index(convolved.argmax(), convolved.shape)[1]

        return (width / 2.0 + center) / 2

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
            file_handle.write("Flats Directory: " + self.parameters['flats_dir'] + "\n")
            file_handle.write("Darks Directory: " + self.parameters['darks_dir'] + "\n")
            file_handle.write("Search Rotational Axis:" + str(self.parameters['search_rotational_axis']) + "\n")

            # Print z-directory and corresponding axis value
            file_handle.write("\n======================== Axis Values ========================\n")
            for key in self.ct_axis_dict:
                key_value_str = str(key) + " : " + str(self.ct_axis_dict[key])
                print(key_value_str)
                file_handle.write(key_value_str + '\n')

            file_handle.write("\nGreatest axis value: " + str(self.greatest_axis_value))
        except FileNotFoundError:
            print("Error: Could not write log file")

    def correct_outliers(self):
        """
        This function looks at each CTDir containing Z00-Z0N
        If the axis values for successive zviews are greater than 3 (an outlier)
        Then we correct this by tying the outlier to the previous Z-View axis plus one
        self.ct_axis_dict is updated with corrected axis values
        """
        sorted_by_ctdir_dict = defaultdict(dict)
        for key in self.ct_axis_dict:
            path_key, zdir = os.path.split(str(key))
            axis_value = self.ct_axis_dict[key]
            sorted_by_ctdir_dict[path_key][zdir] = axis_value

        for dir_key in sorted_by_ctdir_dict:
            z_dir_list = list(sorted_by_ctdir_dict[dir_key].values())

            # Need to account for the case where the first z-view is an outlier
            min_value = min(z_dir_list)
            if z_dir_list[0] > min_value + 2:
                z_dir_list[0] = min_value

            # Compare the difference of successive pairwise axis values
            # If the difference is greater than 3 then set the second pair value to be 1 more than the first pair value
            for index in range(len(z_dir_list) - 1):
                first_value = z_dir_list[index]
                second_value = z_dir_list[index + 1]
                difference = abs(second_value - first_value)
                if difference > 3:
                    # Set second value to be one more than first
                    z_dir_list[index + 1] = z_dir_list[index] + 1

            # Assigns the values in z_dir_list back to the ct_dir_dict
            index = 0
            for zdir in sorted_by_ctdir_dict[dir_key]:
                corrected_axis_value = z_dir_list[index]
                sorted_by_ctdir_dict[dir_key][zdir] = corrected_axis_value
                index += 1

        # Assigns the corrected values back to self.ct_axis_dict
        for path_key in sorted_by_ctdir_dict:
            for z_key in sorted_by_ctdir_dict[path_key]:
                path_string = os.path.join(str(path_key), str(z_key))
                self.ct_axis_dict[path_string] = sorted_by_ctdir_dict[path_key][z_key]

    def find_greatest_axis_value(self):
        """
        Looks through all axis values and determines the greatest value
        """
        axis_list = list(self.ct_axis_dict.values())
        self.greatest_axis_value = max(axis_list)

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
        print("Flats Directory: " + self.parameters['flats_dir'])
        print("Darks Directory: " + self.parameters['darks_dir'])
        print("Search Rotational Axis:", str(self.parameters['search_rotational_axis']))
        print("============================================================")
