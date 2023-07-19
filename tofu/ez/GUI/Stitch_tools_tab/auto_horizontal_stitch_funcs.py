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
from tofu.ez.main import get_CTdirs_list

class AutoHorizontalStitchFunctions:
    def __init__(self, parameters):
        self.lvl0 = os.path.abspath(parameters["input_dir"])
        self.ct_dirs = []
        self.ct_axis_dict = {}
        self.parameters = parameters
        self.greatest_axis_value = 0

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
        self.find_ct_dirs()

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
        self.find_greatest_axis_value()
        print("Greatest axis value: " + str(self.greatest_axis_value))

        # Output the input parameters and axis values to the log file
        self.write_to_log_file()

        # For each ct-dir and z-view we want to stitch all the images using the values in ct_axis_dict
        if not self.parameters['dry_run']:
            print("\n--> Stitching Images...")
            self.find_and_stitch_images()
            print("--> Finished Stitching")

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

    def find_ct_dirs(self):
        """
        Walks directories rooted at "Input Directory" location
        Appends their absolute path to ct-dir if they contain a directory with same name as "tomo" entry in GUI
        """
        for root, dirs, files in os.walk(self.lvl0):
            for name in dirs:
                if name == "tomo":
                    self.ct_dirs.append(root)
        self.ct_dirs = sorted(list(set(self.ct_dirs)))
        
    def compute_centers(self):
        """
        Computes the rotational axis for each image in half-acquisition mode by minimizing STD of a slice
        """
        W, lvl0 = get_CTdirs_list(self.parameters['input_dir']) # using EZVARS tomo, flats, flats2, and dark dir
        for i, ctset in enumerate(W):          
            search_row = 100 #TODO add a GUI box
            nviews, wh, multipage = get_dims(os.path.join(ctset[0], "tomo"))
            patch_size = wh[0] # should be width of the image? -> is the image guaranteed to be a square?
            axis_folder = 'axis-search'
            os.system('rm -rf {}'.format(os.path.join(self.parameters['temp_dir'], axis_folder)))
            ax = find_axis_std(
                ctset,
                self.parameters['temp_dir'],
                self.parameters['search_interval'],
                search_row,
                patch_size,
                False,
                nviews, wh
            )
                        
            move_axis_images(                        
                ctset[0][len(lvl0):],
                os.path.join(self.parameters['temp_dir'], axis_folder),
                os.path.join(self.parameters['output_dir'], axis_folder),
                self.parameters['search_interval'])
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
            file_handle.write("Search Interval:" + str(self.parameters['search_interval']) + "\n")
            file_handle.write("Sample on right: " + str(self.parameters['sample_on_right']) + "\n")

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

    def find_and_stitch_images(self):
        index = range(len(self.ct_dirs))
        pool = mp.Pool(processes=mp.cpu_count())
        exec_func = partial(self.find_and_stitch_parallel_proc)
        # TODO : Try using pool.map or pool.imap_unordered and compare times
        # Try imap_unordered() as see if it is faster - with chunksize len(self.ct_dir) / mp.cpu_count()
        # pool.imap_unordered(exec_func, index, int(len(self.ct_dirs) / mp.cpu_count()))
        pool.map(exec_func, index)

    def find_and_stitch_parallel_proc(self, index):
        z_dir_path = self.ct_dirs[index]
        # Get list of image names in the directory
        try:
            # Want to maintain directory structure for output so we subtract the output-path from z_dir_path
            # Then we append this to the output_dir path
            diff_path = os.path.relpath(z_dir_path, self.parameters['input_dir'])
            out_path = os.path.join(self.parameters['output_dir'], diff_path)
            rotation_axis = self.ct_axis_dict[z_dir_path]

            # If using common flats/darks across all zdirs
            # then use common flats/darks directories as source of images to stitch and save to output zdirs
            if self.parameters['common_flats_darks'] is True:
                self.stitch_180_pairs(rotation_axis, z_dir_path, out_path, "tomo")
                flats_parent_path, garbage = os.path.split(self.parameters['flats_dir'])
                self.stitch_180_pairs(rotation_axis, flats_parent_path, out_path, "flats")
                darks_parent_path, garbage = os.path.split(self.parameters['darks_dir'])
                self.stitch_180_pairs(rotation_axis, darks_parent_path, out_path, "darks")
            # If using local flats/darks to each zdir then use those as source for stitching
            elif self.parameters['common_flats_darks'] is False:
                self.stitch_180_pairs(rotation_axis, z_dir_path, out_path, "tomo")
                # Need to account for case where flats, darks, flats2 don't exist
                if os.path.isdir(os.path.join(z_dir_path, "flats")):
                    self.stitch_180_pairs(rotation_axis, z_dir_path, out_path, "flats")
                if os.path.isdir(os.path.join(z_dir_path, "darks")):
                    self.stitch_180_pairs(rotation_axis, z_dir_path, out_path, "darks")
                if os.path.isdir(os.path.join(z_dir_path, "flats2")):
                    self.stitch_180_pairs(rotation_axis, z_dir_path, out_path, "flats2")

            print("--> " + str(z_dir_path))
            print("Axis of rotation: " + str(rotation_axis))

        except NotADirectoryError as e:
            print("Skipped - Not a Directory: " + e.filename)

    def stitch_180_pairs(self, rotation_axis, in_path, out_path, type_str):
        """
        Finds images in tomo, flats, darks, flats2 directories corresponding to 180 degree pairs
        The first image is stitched with the middle image and so on by using the index and midpoint
        :param rotation_axis: axis of rotation for z-directory
        :param in_path: absolute path to z-directory
        :param out_path: absolute path to output directory
        :param type_str: Type of subdirectory - e.g. "tomo", "flats", "darks", "flats2"
        """
        os.makedirs(os.path.join(out_path, type_str), mode=0o777)
        image_list = sorted(os.listdir(os.path.join(in_path, type_str)))
        midpoint = int(len(image_list) / 2)
        for index in range(midpoint):
            first_path = os.path.join(in_path, type_str, image_list[index])
            second_path = os.path.join(in_path, type_str, image_list[midpoint + index])
            output_image_path = os.path.join(out_path, type_str, type_str + "_stitched_{:>04}.tif".format(index))
            crop_amount = abs(self.greatest_axis_value - round(rotation_axis))
            self.open_images_stitch_write(rotation_axis, crop_amount, first_path, second_path, output_image_path)

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
        print("Search Interval:", str(self.parameters['search_interval']))
        print("Sample on right: " + str(self.parameters['sample_on_right']))
        print("============================================================")

    """****** BORROWED FUNCTIONS ******"""

    def read_image(self, file_name, flip_image):
        """
        Reads in a tiff image from disk at location specified by file_name, returns a numpy array
        :param file_name: Str - path to file
        :param flip_image: Bool - Whether image is to be flipped horizontally or not
        :return: A numpy array of type float
        """
        with tifffile.TiffFile(file_name) as tif:
            image = tif.pages[0].asarray(out='memmap')
        if flip_image is True:
            image = np.fliplr(image)
        return image

    def open_images_stitch_write(self, ax, crop, first_image_path, second_image_path, out_fmt):
        if self.parameters['sample_on_right'] is False:
            # Read each image into a numpy array - We flip the second image
            first = self.read_image(first_image_path, flip_image=False)
            second = self.read_image(second_image_path, flip_image=True)
        if self.parameters['sample_on_right'] is True:
            # We pass index and formats as argument - We flip the first image before stitching
            first = self.read_image(first_image_path, flip_image=True)
            second = self.read_image(second_image_path, flip_image=False)

        stitched = self.stitch(first, second, ax, crop)
        tifffile.imwrite(out_fmt, stitched)

    def stitch(self, first, second, axis, crop):
        h, w = first.shape
        if axis > w / 2:
            dx = int(2 * (w - axis) + 0.5)
        else:
            dx = int(2 * axis + 0.5)
            tmp = np.copy(first)
            first = second
            second = tmp
        result = np.empty((h, 2 * w - dx), dtype=first.dtype)
        ramp = np.linspace(0, 1, dx)

        # Mean values of the overlapping regions must match, which corrects flat-field inconsistency
        # between the two projections
        # We clip the values in second so that there are no saturated pixel overflow problems
        k = np.mean(first[:, w - dx:]) / np.mean(second[:, :dx])
        second = np.clip(second * k, np.iinfo(np.uint16).min, np.iinfo(np.uint16).max).astype(np.uint16)

        result[:, :w - dx] = first[:, :w - dx]
        result[:, w - dx:w] = first[:, w - dx:] * (1 - ramp) + second[:, :dx] * ramp
        result[:, w:] = second[:, dx:]

        return result[:, slice(int(crop), int(2 * (w - axis) - crop), 1)]

    def col_round(self, x):
        frac = x - math.floor(x)
        if frac < 0.5: return math.floor(x)
        return math.ceil(x)
