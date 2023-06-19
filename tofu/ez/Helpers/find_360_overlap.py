"""
This script takes as input a CT scan that has been collected in "half-acquisition" mode
and produces a series of reconstructed slices, each of which are generated by cropping and
concatenating opposing projections together over a range of "overlap" values (i.e. the pixel column
at which the images are cropped and concatenated).
The objective is to review this series of images to determine the pixel column at which the axis of rotation
is located (much like the axis search function commonly used in reconstruction software).
"""

import os
import numpy as np
import tifffile

from tofu.ez.image_read_write import TiffSequenceReader
from tofu.ez.params import EZVARS
from tofu.ez.Helpers.stitch_funcs import findCTdirs, stitch_float32_output
from tofu.util import get_filenames, get_image_shape
from tofu.ez.ufo_cmd_gen import get_filter2d_sinos_cmd
from tofu.ez.find_axis_cmd_gen import evaluate_images_simp



def extract_row(dir_name, row):
    tsr = TiffSequenceReader(dir_name)
    tmp = tsr.read(0)
    (N, M) = tmp.shape
    if (row < 0) or (row > N):
        row = N//2
    num_images = tsr.num_images
    if num_images % 2 == 1:
        print(f"odd number of images ({num_images}) in {dir_name}, "
              f"discarding the last one before stitching pairs")
        num_images-=1
    A = np.empty((num_images, M), dtype=np.uint16)
    for i in range(num_images):
        A[i, :] = tsr.read(i)[row, :]
    tsr.close()
    return A

def find_overlap(parameters):
    print("Finding CTDirs...")
    ctdirs, lvl0 = findCTdirs(parameters['360overlap_input_dir'],
                              EZVARS['inout']['tomo-dir']['value'])
    print(ctdirs)

    dirdark = EZVARS['inout']['darks-dir']['value']
    dirflats = EZVARS['inout']['flats-dir']['value']
    dirflats2 = EZVARS['inout']['flats2-dir']['value']
    if EZVARS['inout']['shared-flatsdarks']['value']:
        dirdark = EZVARS['inout']['path2-shared-darks']['value']
        dirflats = EZVARS['inout']['path2-shared-flats']['value']
        dirflats2 = EZVARS['inout']['path2-shared-flats2']['value']
    # concatenate images with various overlap and generate sinograms
    for ctset in ctdirs:
        print("Working on ctset:" + str(ctset))
        index_dir = os.path.basename(os.path.normpath(ctset))
        # loading:
        try:
            row_flat = np.mean(extract_row(
                os.path.join(ctset, dirflats), parameters['360overlap_row']))
        except:
            print(f"Problem loading flats in {ctset}")
            continue
        try:
            row_dark = np.mean(extract_row(
                os.path.join(ctset, dirdark), parameters['360overlap_row']))
        except:
            print(f"Problem loading darks in {ctset}")
            continue
        try:
            row_tomo = extract_row(
                os.path.join(ctset, EZVARS['inout']['tomo-dir']['value']),
                                   parameters['360overlap_row'])
        except:
            print(f"Problem loading projections from "
                  f"{os.path.join(ctset, EZVARS['inout']['tomo-dir']['value'])}")
            continue
        row_flat2 = None
        tmpstr = os.path.join(ctset, dirflats2)
        if os.path.exists(tmpstr):
            try:
                row_flat2 = np.mean(extract_row(tmpstr, parameters['360overlap_row']))
            except:
                print(f"Problem loading flats2 in {ctset}")

        (num_proj, M) = row_tomo.shape

        print('Flat-field correction...')
        # Flat-correction
        tmp_flat = np.tile(row_flat, (num_proj, 1))
        if row_flat2 is not None:
            tmp_flat2 = np.tile(row_flat2, (num_proj, 1))
            ramp = np.linspace(0, 1, num_proj)
            ramp = np.transpose(np.tile(ramp, (M, 1)))
            tmp_flat = tmp_flat * (1-ramp) + tmp_flat2 * ramp
            del ramp, tmp_flat2

        tmp_dark = np.tile(row_dark, (num_proj, 1))
        tomo_ffc = -np.log((row_tomo - tmp_dark)/np.float32(tmp_flat - tmp_dark))
        del row_tomo, row_dark, row_flat, tmp_flat, tmp_dark
        np.nan_to_num(tomo_ffc, copy=False, nan=0.0, posinf=0.0, neginf=0.0)

        # create interpolated sinogram of flats on the
        # same row as we use for the projections, then flat/dark correction
        print('Creating stitched sinograms...')

        sin_tmp_dir = os.path.join(parameters['360overlap_temp_dir'], index_dir, 'sinos')
        print(sin_tmp_dir)
        os.makedirs(sin_tmp_dir)
        for axis in range(parameters['360overlap_lower_limit'],
                          parameters['360overlap_upper_limit']+parameters['360overlap_increment'],
                          parameters['360overlap_increment']):
            cro = parameters['360overlap_upper_limit'] - axis
            if axis > M // 2:
                cro = axis - parameters['360overlap_lower_limit']
            A = stitch_float32_output(
                tomo_ffc[: num_proj//2, :], tomo_ffc[num_proj//2:, ::-1], axis, cro)
            print(A.shape[1])
            tifffile.imwrite(os.path.join(
                sin_tmp_dir, 'sin-axis-' + str(axis).zfill(4) + '.tif'), A.astype(np.float32))

            # perform reconstructions for each sinogram and save to output folder

        print('Reconstructing slices...')
        #reco_axis = M-parameters['360overlap_upper_limit'] # equivalently half-width
        sin_width = get_image_shape(get_filenames(sin_tmp_dir)[0])[-1]
        sin_height = get_image_shape(get_filenames(sin_tmp_dir)[0])[-2]

        if parameters['360overlap_doRR']:
            print("Applying ring removal filter")
            tmpdir = os.path.join(parameters['360overlap_temp_dir'], index_dir)
            rrcmd = get_filter2d_sinos_cmd(tmpdir,
                                   EZVARS['RR']['sx']['value'],
                                   EZVARS['RR']['sy']['value'],
                                   sin_height, sin_width)
            print(rrcmd)
            os.system(rrcmd)
            sin_tmp_dir = os.path.join(parameters['360overlap_temp_dir'], index_dir, 'sinos-filt')

        outname = os.path.join(os.path.join(
            parameters['360overlap_output_dir'], f"{index_dir}-sli.tif"))

        cmd = f'tofu tomo --axis {sin_width//2} --sinograms {sin_tmp_dir}'
        cmd +=' --output ' + os.path.join(outname)
        print(cmd)
        os.system(cmd)

        points, maximum = evaluate_images_simp(outname, "msag")
        print(f"Estimated overlap:" 
            f"{parameters['360overlap_lower_limit'] + parameters['360overlap_increment'] * maximum}")

        print("Finished processing: " + str(index_dir))
        print("********************DONE********************")

    #shutil.rmtree(parameters['360overlap_temp_dir'])
    print("Finished processing: " + str(parameters['360overlap_input_dir']))

