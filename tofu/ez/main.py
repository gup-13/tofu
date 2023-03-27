"""
Created on Apr 5, 2018
@author: sergei gasilov
"""

import logging
import os
import warnings
warnings.filterwarnings("ignore")
import time

from tofu.ez.ctdir_walker import WalkCTdirs
from tofu.ez.tofu_cmd_gen import tofu_cmds
from tofu.ez.ufo_cmd_gen import ufo_cmds
from tofu.ez.find_axis_cmd_gen import findCOR_cmds
from tofu.ez.util import *
from tofu.ez.image_read_write import TiffSequenceReader
from tifffile import imwrite
from tofu.ez.params import EZVARS
from tofu.config import SECTIONS

LOG = logging.getLogger(__name__)


def get_CTdirs_list(inpath, fdt_names, args):
    """
    Determines whether directories containing CT data are valid.
    Returns list of subdirectories with valid CT data
    :param inpath: Path to the CT directory containing subdirectories with flats/darks/tomo (and flats2 if used)
    :param fdt_names: Names of the directories which store flats/darks/tomo (and flats2 if used)
    :param args: Arguments from the GUI
    :return: W.ctsets: List of "good" CTSets and W.lvl0: Path to root of CT sets
    """
    # Constructor call to create WalkCTDirs object
    W = WalkCTdirs(inpath, fdt_names, args)
    # Find any directories containing "tomo" directory
    W.findCTdirs()
    # If "Use common flats/darks across multiple experiments" is enabled
    if EZVARS['inout']['shared-flatsdarks']['value']:
        logging.debug("Use common darks/flats")
        logging.debug("Path to darks: " + str(EZVARS['inout']['path2-shared-darks']['value']))
        logging.debug("Path to flats: " + str(EZVARS['inout']['path2-shared-flats']['value']))
        logging.debug("Path to flats2: " + str(EZVARS['inout']['path2-shared-flats-after']['value']))
        logging.debug("Use flats2: " + str(EZVARS['inout']['shared-flats-after']['value']))
        # Determine whether paths to common flats/darks/flats2 exist
        if not W.checkCommonFDT():
            print("Invalid path to common flats/darks")
            return W.ctsets, W.lvl0
        else:
            LOG.debug("Paths to common flats/darks exist")
            # Check whether directories contain only .tif files
            if not W.checkCommonFDTFiles():
                return W.ctsets, W.lvl0
            else:
                # Sort good bad sets
                W.SortBadGoodSets()
                return W.ctsets, W.lvl0
    # If "Use common flats/darks across multiple experiments" is not enabled
    else:
        LOG.debug("Use flats/darks in same directory as tomo")
        # Check if common flats/darks/flats2 are type 3 or 4
        W.checkCTdirs()
        # Need to check if common flats/darks contain only .tif files
        W.checkCTfiles()
        W.SortBadGoodSets()
        return W.ctsets, W.lvl0


def frmt_ufo_cmds(cmds, ctset, out_pattern, ax, args, Tofu, Ufo, FindCOR, nviews, WH):
    """formats list of processing commands for a CT set"""
    # two helper variables to mark that PR/FFC has been done at some step
    swiFFC = True  # FFC is always required required
    swiPR = SECTIONS['retrieve-phase']['enable-phase']['value']  # PR is an optional operation

    ####### PREPROCESSING #########
    Ufo.common_fd_used = False
    Tofu.common_fd_used = False
    if EZVARS['filters']['rm_spots']['value']:
        # copy one flat to tmpdir now as path might change if preprocess is enabled
        tsr = TiffSequenceReader(os.path.join(ctset[0],
                                              EZVARS['inout']['flats-dir']['value']))
        flat1 = tsr.read(tsr.num_images - 1)  # taking the last flat
        tsr.close()
        flat1_file = os.path.join(EZVARS['inout']['tmp-dir']['value'], "flat1.tif")
        imwrite(flat1_file, flat1)
    if EZVARS['inout']['preprocess']['value']:
        cmds.append('echo " - Applying filter(s) to images "')
        cmds_prepro = Ufo.get_pre_cmd(ctset, EZVARS['inout']['preprocess-command']['value'],
                                      EZVARS['inout']['tmp-dir']['value'], args)
        cmds.extend(cmds_prepro)
        # reset location of input data
        ctset = (EZVARS['inout']['tmp-dir']['value'], ctset[1])
        Ufo.common_fd_used = True
        Tofu.common_fd_used = True
    ###################################################
    if EZVARS['filters']['rm_spots']['value']:  # generate commands to remove sci. spots from projections
        cmds.append('echo " - Flat-correcting and removing large spots"')
        cmds_inpaint = Ufo.get_inp_cmd(ctset, EZVARS['inout']['tmp-dir']['value'], args, WH[0], nviews)
        # reset location of input data
        ctset = (EZVARS['inout']['tmp-dir']['value'], ctset[1])
        Ufo.common_fd_used = True
        Tofu.common_fd_used = True
        cmds.extend(cmds_inpaint)
        swiFFC = False  # no need to do FFC anymore

    ######## PHASE-RETRIEVAL #######
    # Do PR separately if sinograms must be generate or if vertical ROI is defined
    if SECTIONS['retrieve-phase']['enable-phase']['value'] and EZVARS['RR']['enable']['value']:  # or (SECTIONS['retrieve-phase']['enable-phase']['value'] and EZVARS['inout']['input_ROI']['value']):
        if swiFFC:  # we still need need flat correction #Inpaint No
            cmds.append('echo " - Phase retrieval with flat-correction"')
            if EZVARS['flat-correction']['smart-ffc']['value']:
                cmds.append(Tofu.get_pr_sinFFC_cmd(ctset, args, nviews, WH[0]))
                cmds.append(Tofu.get_pr_tofu_cmd_sinFFC(ctset, args, nviews, WH))
            elif not EZVARS['flat-correction']['smart-ffc']['value']:
                cmds.append(Tofu.get_pr_tofu_cmd(ctset, args, nviews, WH[0]))
            Tofu.common_fd_used = True
        else:  # Inpaint Yes
            cmds.append('echo " - Phase retrieval from flat-corrected projections"')
            cmds.extend(Ufo.get_pr_ufo_cmd(args, nviews, WH))
        swiPR = False  # no need to do PR anymore
        swiFFC = False  # no need to do FFC anymore

    # if args.PR and args.vcrop: # have to reset location of input data
    #    ctset = (args.tmpdir, ctset[1])

    ################# RING REMOVAL #######################
    if EZVARS['RR']['enable']['value']:
        # Generate sinograms first
        if swiFFC:  # we still need to do flat-field correction
            if EZVARS['flat-correction']['smart-ffc']['value']:
                # Create flat corrected images using sinFFC
                cmds.append(Tofu.get_sinFFC_cmd(ctset, args, nviews, WH[0]))
                # Feed the flat corrected images to sino gram generation
                cmds.append(Tofu.get_sinos_noffc_cmd(ctset[0], EZVARS['inout']['tmp-dir']['value'], args, nviews, WH))
            elif not EZVARS['flat-correction']['smart-ffc']['value']:
                cmds.append('echo " - Make sinograms with flat-correction"')
                cmds.append(Tofu.get_sinos_ffc_cmd(ctset, EZVARS['inout']['tmp-dir']['value'], args, nviews, WH))
        else:  # we do not need flat-field correction
            cmds.append('echo " - Make sinograms without flat-correction"')
            cmds.append(Tofu.get_sinos_noffc_cmd(ctset[0], EZVARS['inout']['tmp-dir']['value'], args, nviews, WH))
        swiFFC = False
        # Filter sinograms
        if EZVARS['RR']['use-ufo']['value']:
            if EZVARS['RR']['ufo-2d']['value']:
                cmds.append('echo " - Ring removal - ufo 1d stripes filter"')
                cmds.append(Ufo.get_filter1d_sinos_cmd(EZVARS['inout']['tmp-dir']['value'],
                            EZVARS['RR']['sx']['value'], nviews))
            else:
                cmds.append('echo " - Ring removal - ufo 2d stripes filter"')
                cmds.append(Ufo.get_filter2d_sinos_cmd(EZVARS['inout']['tmp-dir']['value'], \
                            EZVARS['RR']['sx']['value'],
                            EZVARS['RR']['sy']['value'],
                                                       nviews, WH[1]))
        else:
            cmds.append('echo " - Ring removal - sarepy filter(s)"')
            # note - calling an external program, not an ufo-kit script
            tmp = os.path.dirname(os.path.abspath(__file__))
            path_to_filt = os.path.join(tmp, "RR_external.py")
            if os.path.isfile(path_to_filt):
                tmp = os.path.join(EZVARS['inout']['tmp-dir']['value'], "sinos")
                cmdtmp = 'python {} --sinos {} --mws {} --mws2 {} --snr {} --sort_only {}' \
                    .format(path_to_filt, tmp,
                            EZVARS['RR']['spy-narrow-window']['value'],
                            EZVARS['RR']['spy-wide-window']['value'],
                            EZVARS['RR']['spy-wide-SNR']['value'],
                            int(not EZVARS['RR']['spy-rm-wide']['value']))
                cmds.append(cmdtmp)
            else:
                cmds.append('echo "Omitting RR because file with filter does not exist"')
        if not EZVARS['inout']['keep-tmp']['value']:
            cmds.append("rm -rf {}".format(os.path.join(EZVARS['inout']['tmp-dir']['value'], "sinos")))
        # Convert filtered sinograms back to projections
        cmds.append('echo " - Generating proj from filtered sinograms"')
        cmds.append(Tofu.get_sinos2proj_cmd(args, WH[0]))
        # reset location of input data
        ctset = (EZVARS['inout']['tmp-dir']['value'], ctset[1])

    # Finally - call to tofu reco
    cmds.append('echo " - CT with axis {}; ffc:{}, PR:{}"'.format(ax, swiFFC, swiPR))
    if EZVARS['flat-correction']['smart-ffc']['value'] and swiFFC:
        cmds.append(Tofu.get_sinFFC_cmd(ctset, args, nviews, WH[0]))
        cmds.append(
            Tofu.get_reco_cmd_sinFFC(ctset, out_pattern, ax, args, nviews, WH, swiFFC, swiPR)
        )
    else:  # If not using sinFFC
        cmds.append(Tofu.get_reco_cmd(ctset, out_pattern, ax, args, nviews, WH, swiFFC, swiPR))

    return nviews, WH


def fmt_nlmdn_ufo_cmd(inpath: str, outpath: str, args):  ### TODO call one function from nlmdn module!!
    """
    :param inp: Path to input directory before NLMDN applied
    :param out: Path to output directory after NLMDN applied
    :param args: List of args
    :return:
    """
    cmd = 'ufo-launch read path={}'.format(inpath)
    cmd += ' ! non-local-means patch-radius={}'.format(EZVARS['nlmdn']['patch-radius']['value'])
    cmd += ' search-radius={}'.format(EZVARS['nlmdn']['search-radius']['value'])
    cmd += ' h={}'.format(EZVARS['nlmdn']['h']['value'])
    cmd += ' sigma={}'.format(EZVARS['nlmdn']['sigma']['value'])
    cmd += ' window={}'.format(EZVARS['nlmdn']['window']['value'])
    cmd += ' fast={}'.format(EZVARS['nlmdn']['fast']['value'])
    cmd += ' estimate-sigma={}'.format(EZVARS['nlmdn']['estimate-sigma']['value'])
    cmd += ' ! write filename={}'.format(enquote(outpath))
    if not EZVARS['nlmdn']['bigtiff_output']['value']:
        cmd += " bytes-per-file=0 tiff-bigtiff=False"
    if EZVARS['inout']['clip_hist']['value']:
        cmd += f" bits={SECTIONS['general']['output-bitdepth']['value']} rescale=False"
    return cmd

def execute_reconstruction(args, fdt_names):
    # array with the list of commands
    cmds = []
    # clean temporary directory or create if it doesn't exist
    if not os.path.exists(EZVARS['inout']['tmp-dir']['value']):
        os.makedirs(EZVARS['inout']['tmp-dir']['value'])
    # else:
    #    clean_tmp_dirs(EZVARS['inout']['tmp-dir']['value'], fdt_names)

    if EZVARS['inout']['clip_hist']['value']:
        if SECTIONS['general']['output-minimum']['value'] > SECTIONS['general']['output-maximum']['value']:
            raise ValueError('hmin must be smaller than hmax to convert to 8bit without contrast inversion')

    # get list of all good CT directories to be reconstructed

    print('*********** Analyzing input directory ************')
    W, lvl0 = get_CTdirs_list(EZVARS['inout']['input-dir']['value'], fdt_names, args)
    # W is an array of tuples (path, type)
    # get list of already reconstructed sets
    recd_sets = findSlicesDirs(EZVARS['inout']['output-dir']['value'])
    # initialize command generators
    FindCOR = findCOR_cmds(fdt_names)
    Tofu = tofu_cmds(fdt_names)
    Ufo = ufo_cmds(fdt_names)
    # populate list of reconstruction commands
    print("*********** AXIS INFO ************")
    for i, ctset in enumerate(W):
        # ctset is a tuple containing a path and a type (3 or 4)
        if not already_recd(ctset[0], lvl0, recd_sets):
            # determine initial number of projections and their shape
            path2proj = os.path.join(ctset[0], fdt_names[2])
            nviews, WH, multipage = get_dims(path2proj)
            # If EZVARS['COR']['search-method']['value'] == 4 then bypass axis search and use image midpoint
            if EZVARS['COR']['search-method']['value'] != 4:
                if (EZVARS['inout']['input_ROI']['value'] and bad_vert_ROI(multipage, path2proj,
                                SECTIONS['reading']['y']['value'], SECTIONS['reading']['height']['value'])):
                    print('{}\t{}'.format('CTset:', ctset[0]))
                    print('{:>30}\t{}'.format('Axis:', 'na'))
                    print('Vertical ROI does not contain any rows.')
                    print("{:>30}\t{}, dimensions: {}".format("Number of projections:", nviews, WH))
                    continue
                # Find axis of rotation using auto: correlate first/last projections
                if EZVARS['COR']['search-method']['value'] == 1:
                    ax = FindCOR.find_axis_corr(ctset,
                                    EZVARS['inout']['input_ROI']['value'],
                                    SECTIONS['reading']['y']['value'],
                                    SECTIONS['reading']['height']['value'], multipage, args)
                # Find axis of rotation using auto: minimize STD of a slice
                elif EZVARS['COR']['search-method']['value'] == 2:
                    cmds.append("echo \"Cleaning axis-search in tmp directory\"")
                    os.system('rm -rf {}'.format(os.path.join(EZVARS['inout']['tmp-dir']['value'], 'axis-search')))
                    ax = FindCOR.find_axis_std(ctset,
                                               EZVARS['inout']['tmp-dir']['value'],
                                               EZVARS['COR']['search-interval']['value'],
                                               EZVARS['COR']['patch-size']['value'],
                                               EZVARS['COR']['search-row']['value'],
                                               nviews, args, WH)
                else:
                    ax = EZVARS['COR']['user-defined-ax']['value'] + i * EZVARS['COR']['user-defined-dax']['value']
            # If EZVARS['COR']['search-method']['value'] == 4 then bypass axis search and use image midpoint
            elif EZVARS['COR']['search-method']['value'] == 4:
                ax = FindCOR.find_axis_image_midpoint(ctset, multipage, WH)
                print("Bypassing axis search and using image midpoint: {}".format(ax))

            setid = ctset[0][len(lvl0) + 1:]
            out_pattern = os.path.join(EZVARS['inout']['output-dir']['value'], setid, 'sli/sli')
            cmds.append('echo ">>>>> PROCESSING {}"'.format(setid))
            # rm files in temporary directory first of all to
            # format paths correctly and to avoid problems
            # when reconstructing ct sets with variable number of rows or projections
            cmds.append('echo "Cleaning temporary directory"'.format(setid))
            clean_tmp_dirs(EZVARS['inout']['tmp-dir']['value'], fdt_names)
            # call function which formats commands for this data set
            nviews, WH = frmt_ufo_cmds(cmds, ctset, out_pattern, \
                                       ax, args, Tofu, Ufo, FindCOR, nviews, WH)
            save_params(args, setid, ax, nviews, WH)
            print('{}\t{}'.format('CTset:', ctset[0]))
            print('{:>30}\t{}'.format('Axis:', ax))
            print("{:>30}\t{}, dimensions: {}".format("Number of projections:", nviews, WH))
            # tmp = "Number of projections: {}, dimensions: {}".format(nviews, WH)
            # cmds.append("echo \"{}\"".format(tmp))
            if EZVARS['nlmdn']['do-after-reco']['value']:
                logging.debug("Using Non-Local Means Denoising")
                head, tail = os.path.split(out_pattern)
                slidir = os.path.dirname(os.path.join(head, 'sli'))
                nlmdn_output = os.path.join(slidir+"-nlmdn", "sli-nlmdn-%04i.tif")
                cmds.append(fmt_nlmdn_ufo_cmd(slidir, nlmdn_output, args))
        else:
            print("{} has been already reconstructed".format(ctset[0]))
    # execute commands = start reconstruction
    start = time.time()
    print("*********** PROCESSING ************")
    for cmd in cmds:
        if not EZVARS['inout']['dryrun']['value']:
            os.system(cmd)
        else:
            print(cmd)
    if not EZVARS['inout']['keep-tmp']['value']:
        clean_tmp_dirs(EZVARS['inout']['tmp-dir']['value'], fdt_names)

    print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print("*** Done. Total processing time {} sec.".format(int(time.time() - start)))
    print("*** Waiting for the next job...........")


def already_recd(ctset, indir, recd_sets):
    x = False
    if ctset[len(indir) + 1 :] in recd_sets:
        x = True
    return x


def findSlicesDirs(lvl0):
    recd_sets = []
    for root, dirs, files in os.walk(lvl0):
        for name in dirs:
            if name == "sli":
                recd_sets.append(root[len(lvl0) + 1 :])
    return recd_sets
