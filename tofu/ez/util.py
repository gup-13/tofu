"""
Created on Apr 20, 2020

@author: gasilos
"""
import os
import tifffile
import yaml
import numpy as np
from tofu.util import get_filenames, get_first_filename, get_image_shape, read_image

import tofu.ez.params as parameters
from tofu.ez.params import EZVARS
from tofu.config import SECTIONS

def get_dims(pth):
    # get number of projections and projections dimensions
    first_proj = get_first_filename(pth)
    multipage = False
    try:
        shape = get_image_shape(first_proj)
    except:
        raise ValueError("Failed to determine size and number of projections in {}".format(pth))
    if len(shape) == 2:  # single page input
        return len(get_filenames(pth)), [shape[-2], shape[-1]], multipage
    elif len(shape) == 3:  # multipage input
        nviews = 0
        for i in get_filenames(pth):
            nviews += get_image_shape(i)[0]
        multipage = True
        return nviews, [shape[-2], shape[-1]], multipage
    return -6, [-6, -6]


def bad_vert_ROI(multipage, path2proj, y, height):
    if multipage:
        with tifffile.TiffFile(get_filenames(path2proj)[0]) as tif:
            proj = tif.pages[0].asarray().astype(float)
    else:
        proj = read_image(get_filenames(path2proj)[0]).astype(float)
    y_region = slice(y, min(y + height, proj.shape[0]), 1)
    proj = proj[y_region, :]
    if proj.shape[0] == 0:
        return True
    else:
        return False


def make_copy_of_flat(flatdir, flat_copy_name, dryrun):
    first_flat_file = get_first_filename(flatdir)
    try:
        shape = get_image_shape(first_flat_file)
    except:
        raise ValueError("Failed to determine size and number of flats in {}".format(flatdir))
    cmd = ""
    if len(shape) == 2:
        last_flat_file = get_filenames(flatdir)[-1]
        cmd = "cp {} {}".format(last_flat_file, flat_copy_name)
    else:
        flat = read_image(get_filenames(flatdir)[-1])[-1]
        if dryrun:
            cmd = 'echo Will save a copy of flat into "{}"'.format(flat_copy_name)
        else:
            tifffile.imwrite(flat_copy_name, flat)

    # something isn't right in this logic? It used to work but then
    # stopped to create a copy of flat correctly. Going to point to all flats simply
    return cmd


def clean_tmp_dirs(tmpdir, fdt_names):
    tmp_pattern = ["proj", "sino", "mask", "flat", "dark", "radi"]
    tmp_pattern += fdt_names
    # clean directories in tmpdir if their names match pattern
    if os.path.exists(tmpdir):
        for filename in os.listdir(tmpdir):
            if filename[:4] in tmp_pattern:
                os.system("rm -rf {}".format(os.path.join(tmpdir, filename)))


def enquote(string, escape=False):
    addition = '\\"' if escape else '"'

    return addition + string + addition


def save_params(args, ctsetname, ax, nviews, WH):
    if not EZVARS['inout']['dryrun']['value'] and not os.path.exists(EZVARS['inout']['output-dir']['value']):
        os.makedirs(EZVARS['inout']['output-dir']['value'])
    tmp = os.path.join(EZVARS['inout']['output-dir']['value'], ctsetname)
    if not EZVARS['inout']['dryrun']['value'] and not os.path.exists(tmp):
        os.makedirs(tmp)
    if not EZVARS['inout']['dryrun']['value'] and EZVARS['inout']['save-params']['value']:
        # Dump the params .yaml file
        try:
            yaml_output_filepath = os.path.join(tmp, "parameters.yaml")
            yaml_output = open(yaml_output_filepath, "w")
            yaml.dump(parameters.params, yaml_output)
        except FileNotFoundError:
            print("Something went wrong when exporting the .yaml parameters file")

        # Dump the reco.params output file
        fname = os.path.join(tmp, 'reco.params')
        f = open(fname, 'w')
        f.write('*** General ***\n')
        f.write('Input directory {}\n'.format(EZVARS['inout']['input-dir']['value']))
        if ctsetname == '':
            ctsetname = '.'
        f.write('CT set {}\n'.format(ctsetname))
        if EZVARS['COR']['search-method']['value'] == 1 or EZVARS['COR']['search-method']['value'] == 2:
            f.write('Center of rotation {} (auto estimate)\n'.format(ax))
        else:
            f.write('Center of rotation {} (user defined)\n'.format(ax))
        f.write('Dimensions of projections {} x {} (height x width)\n'.format(WH[0], WH[1]))
        f.write('Number of projections {}\n'.format(nviews))
        f.write('*** Preprocessing ***\n')
        tmp = 'None'
        if EZVARS['inout']['preprocess']['value']:
            tmp = EZVARS['inout']['preprocess-command']['value']
        f.write('  '+tmp+'\n')
        f.write('*** Image filters ***\n')
        if EZVARS['filters']['rm_spots']['value']:
            f.write(' Remove large spots enabled\n')
            f.write('  threshold {}\n'.format(SECTIONS['find-large-spots']['spot-threshold']['value']))
            f.write('  sigma {}\n'.format(SECTIONS['find-large-spots']['gauss-sigma']['value']))
        else:
            f.write('  Remove large spots disabled\n')
        if SECTIONS['retrieve-phase']['enable-phase']['value']:
            f.write(' Phase retrieval enabled\n')
            f.write('  energy {} keV\n'.format(SECTIONS['retrieve-phase']['energy']['value']))
            f.write('  pixel size {:0.1f} um\n'.format(SECTIONS['retrieve-phase']['pixel-size']['value'] * 1e6))
            f.write('  sample-detector distance {} m\n'.format(SECTIONS['retrieve-phase']['propagation-distance']['value'][0]))
            f.write('  delta/beta ratio {:0.0f}\n'.format(10 ** SECTIONS['retrieve-phase']['regularization-rate']['value']))
        else:
            f.write('  Phase retrieval disabled\n')
        f.write('*** Ring removal ***\n')
        if EZVARS['RR']['enable']['value']:
            if EZVARS['RR']['use-ufo']['value']:
                tmp = '2D'
                if EZVARS['RR']['ufo-2d']['value']:
                    tmp = '1D'
                f.write('  RR with ufo {} stripes filter\n'.format(tmp))
                f.write(f'   sigma horizontal {EZVARS["RR"]["sx"]["value"]}')
                f.write(f'   sigma vertical {EZVARS["RR"]["sy"]["value"]}')
            else:
                if EZVARS['RR']['spy-rm-wide']['value']:
                    tmp = '  RR with ufo sarepy remove wide filter, '
                    tmp += 'window {}, SNR {}\n'.format(
                        EZVARS['RR']['spy-wide-window']['value'],
                        EZVARS['RR']['spy-wide-SNR']['value'])
                    f.write(tmp)
                f.write('  '
                        'RR with ufo sarepy sorting filter, window {}\n'.
                        format(EZVARS['RR']['spy-narrow-window']['value'])
                        )
        else:
            f.write('RR disabled\n')
        f.write('*** Region of interest ***\n')
        if EZVARS['inout']['input_ROI']['value']:
            f.write('Vertical ROI defined\n')
            f.write('  first row {}\n'.format(SECTIONS['reading']['y']['value']))
            f.write('  height {}\n'.format(SECTIONS['reading']['height']['value']))
            f.write('  reconstruct every {}th row\n'.format(SECTIONS['reading']['y-step']['value']))
        else:
            f.write('Vertical ROI: all rows\n')
        if EZVARS['inout']['output-ROI']['value']:
            f.write('ROI in slice plane defined\n')
            f.write('  x {}\n'.format(EZVARS['inout']['output-x']['value']))
            f.write('  width {}\n'.format(EZVARS['inout']['output-width']['value']))
            f.write('  y {}\n'.format(EZVARS['inout']['output-y']['value']))
            f.write('  height {}\n'.format(EZVARS['inout']['output-height']['value']))
        else:
            f.write('ROI in slice plane not defined\n')
        f.write('*** Reconstructed values ***\n')
        if EZVARS['inout']['clip_hist']['value']:
            f.write('  {} bit\n'.format(SECTIONS['general']['output-bitdepth']['value']))
            f.write('  Min value in 32-bit histogram {}\n'.format(SECTIONS['general']['output-minimum']['value']))
            f.write('  Max value in 32-bit histogram {}\n'.format(SECTIONS['general']['output-maximum']['value']))
        else:
            f.write('  32bit, histogram untouched\n')
        f.write('*** Optional reco parameters ***\n')
        if SECTIONS['general-reconstruction']['volume-angle-z']['value'][0] > 0:
            f.write('  Rotate volume by: {:0.3f} deg\n'.format(SECTIONS['general-reconstruction']['volume-angle-z']['value'][0]))
        f.close()
