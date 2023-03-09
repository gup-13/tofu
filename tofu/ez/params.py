# This file is used to share params as a global variable
import yaml
from collections import OrderedDict
from tofu.util import restrict_value

import os #EZVARS[inout][tmp-dir]

#TODO Make good structure to store parameters
# similar to tofu? and
# use tofu's structure for existing reco params
# test comment

params = {}

PARAMS = OrderedDict()
PARAMS['ezmview'] = {
    'num_sets': {
        'default': None,
        'type': float,
        'help': "Axis position"},
    'indir': {
        'default': False,
        'help': "Reconstruct without writing data",
        'action': 'store_true'}}


def save_parameters(params, file_path):
    file_out = open(file_path, 'w')
    yaml.dump(params, file_out)
    print("Parameters file saved at: " + str(file_path))


#######

# Mapping table: [param name, dictionary name, key1, key2] -> dictionary[key1][key2]
# Note: The ordering of parameters should match the ordering of parameters in ".yaml" parameter file

MAP_TABLE = [
    # Format: [param name, dict name, key1 in dict, key2 in dict[key1]]
    # i.e. param name <-> dict[key1][key2]
    # PATHS
    ['main_config_input_dir','ezvars','inout','input-dir'],          # EZVARS['inout']['input-dir'] str
    ['main_config_temp_dir','ezvars','inout','tmp-dir'],             # EZVARS['inout']['tmp-dir']  str
    ['main_config_output_dir','ezvars','inout','output-dir'],        # EZVARS['inout']['output-dir'] str
    ['main_config_darks_dir_name','ezvars', 'inout', 'darks-dir'],        # None str (EZVARS['inout']['darks-dir])
    ['main_config_flats_dir_name','ezvars', 'inout', 'flats-dir'],        # None str (EZVARS['inout']['flats-dir])
    ['main_config_tomo_dir_name','ezvars', 'inout', 'tomo-dir'],         # None str (EZVARS['inout']['tomo-dir])
    ['main_config_flats2_dir_name','ezvars', 'inout', 'flats2-dir'],       # None str (EZVARS['inout']['flats2-dir])
    ['main_config_save_multipage_tiff','ezvars','inout','bigtiff-output'],   # EZVARS['inout']['bigtiff-output'] str
    
    # center of rotation parameters 
    ['main_cor_axis_search_method','ezvars','COR','search-method'],           # EZVARS['COR']['search-method'] int
    ['main_cor_axis_search_interval','ezvars','COR','search-interval'],       # EZVARS['COR']['search-interval'] str
    ['main_cor_search_row_start','ezvars','COR','search-row'],                # EZVARS['COR']['search-row'] int
    ['main_cor_recon_patch_size','ezvars','COR','patch-size'],                # EZVARS['COR']['patch-size'] int
    ['main_cor_axis_column','ezvars','COR','user-defined-ax'],                # EZVARS['COR']['user-defined-ax'] float
    ['main_cor_axis_increment_step','ezvars','COR','user-defined-dax'],       # EZVARS['COR']['user-defined-dax'] float
    
    #ring removal
    ['main_filters_remove_spots','ezvars','filters','rm_spots'],                                # EZVARS['filters']['rm_spots'] bool
    ['main_filters_remove_spots_threshold','sections','find-large-spots','spot-threshold'],     # SECTIONS['find-large-spots']['spot-threshold'] int -> float
    ['main_filters_remove_spots_blur_sigma','sections','find-large-spots','gauss-sigma'],       # SECTIONS['find-large-spots']['gauss-sigma'] int -> float
    ['main_filters_ring_removal','ezvars','RR','enable'],                                       # EZVARS['RR']['enable'] bool
    ['main_filters_ring_removal_ufo_lpf','ezvars','RR','use-ufo'],                              # EZVARS['RR']['use-ufo'] bool
    ['main_filters_ring_removal_ufo_lpf_1d_or_2d','ezvars','RR','ufo-2d'],                      # EZVARS['RR']['ufo-2d'] bool
    ['main_filters_ring_removal_ufo_lpf_sigma_horizontal','ezvars','RR','sx'],                  #EZVARS['RR']['sx'] int
    ['main_filters_ring_removal_ufo_lpf_sigma_vertical','ezvars','RR','sy'],                    #EZVARS['RR']['sy'] int 
    ['main_filters_ring_removal_sarepy_window_size','ezvars','RR','spy-narrow-window'],         #EZVARS['RR']['spy-narrow-window'] int
    ['main_filters_ring_removal_sarepy_wide','ezvars','RR','spy-rm-wide'],                      #EZVARS['RR']['spy-rm-wide'] bool
    ['main_filters_ring_removal_sarepy_window','ezvars','RR','spy-wide-window'],                #EZVARS['RR']['spy-wide-window'] int
    ['main_filters_ring_removal_sarepy_SNR','ezvars','RR','spy-wide-SNR'],                      #EZVARS['RR']['spy-wide-SNR'] int
    
    # phase retrieval
    ['main_pr_phase_retrieval','sections','retrieve-phase','enable'],                   #SECTIONS['retrieve-phase']['enable'] bool -> (N/A)
    ['main_pr_photon_energy','sections','retrieve-phase','energy'],                     #SECTIONS['retrieve-phase']['energy'] int -> float
    ['main_pr_pixel_size','sections','retrieve-phase','pixel-size'],                    #SECTIONS['retrieve-phase']['pixel-size'] float -> float
    ['main_pr_detector_distance','sections','retrieve-phase','propagation-distance'],   #SECTIONS['retrieve-phase']['propagation-distance'] float ->'tupleize()'
    ['main_pr_delta_beta_ratio','sections','retrieve-phase','regularization-rate'],     #SECTIONS['retrieve-phase']['regularization-rate'] float (apply log10 to input)->float
    
    # Crop vertically
    ['main_region_select_rows','ezvars','inout','input_ROI'],           #EZVARS['inout']['input_ROI'] bool
    ['main_region_first_row','sections','reading','y'],                 #SECTIONS['reading']['y'] int -> int [0,inf]
    ['main_region_number_rows','sections','reading','height'],          #SECTIONS['reading']['height'] int -> int [0,inf]
    ['main_region_nth_row','sections','reading','y-step'],              #SECTIONS['reading']['y-step'] int -> int [0,inf]
    
    # conv to 8 bit ##
    ['main_region_clip_histogram','ezvars','inout','clip_hist'],        #EZVARS['inout']['clip_hist'] bool
    ['main_region_bit_depth','sections','general','output-bitdepth'],   #SECTIONS['general']['output-bitdepth'] int -> int [0,inf]
    ['main_region_histogram_min','sections','general','output-minimum'],#SECTIONS['general']['output-minimum'] float -> float
    ['main_region_histogram_max','sections','general','output-maximum'],#SECTIONS['general']['output-maximum'] float -> float
    
    ## Processing attributes
    ['main_config_preprocess','ezvars','inout','preprocess'],                   #EZVARS['inout']['preprocess'] bool
    ['main_config_preprocess_command','ezvars','inout','preprocess-command'],   #EZVARS['inout']['preprocess-command'] str
    
    ## ROI in slice
    ['main_region_rotate_volume_clock','sections','general-reconstruction','volume-angle-z'],   #SECTIONS['general-reconstruction']['volume-angle-z'] float -> tupleize(dtype=list) (str?)
    ['main_region_crop_slices','ezvars','inout','output-ROI'],                                  #EZVARS['inout']['output-ROI'] bool
    ['main_region_crop_x','ezvars','inout','output-x'],                                         #EZVARS['inout']['output-x'] int
    ['main_region_crop_width','ezvars','inout','output-width'],                                 #EZVARS['inout']['output-width'] int
    ['main_region_crop_y','ezvars','inout','output-y'],                                         #EZVARS['inout']['output-y'] int
    ['main_region_crop_height','ezvars','inout','output-height'],                               #EZVARS['inout']['output-height'] int
    
    ## misc settings
    ['main_config_dry_run','ezvars','inout','dryrun'],               #EZVARS['inout']['dryrun'] bool
    ['main_config_save_params','ezvars','inout','save-params'],      #EZVARS['inout']['save-params'] bool
    ['main_config_keep_temp','ezvars','inout','keep-tmp'],           #EZVARS['inout']['keep-tmp'] bool
    
    ## sinFFC settings
    ['advanced_ffc_sinFFC','ezvars','flat-correction','smart-ffc'],                         #EZVARS['flat-correction']['smart-ffc'] bool
    ['advanced_ffc_method','ezvars','flat-correction','smart-ffc-method'],                  #EZVARS['flat-correction']['smart-ffc-method'] str
    ['advanced_ffc_eigen_pco_reps','ezvars','flat-correction','eigen-pco-reps'],            #EZVARS['flat-correction']['eigen-pco-reps'] int
    ['advanced_ffc_eigen_pco_downsample','ezvars','flat-correction','eigen-pco-downsample'],#EZVARS['flat-correction']['eigen-pco-downsample']int
    ['advanced_ffc_downsample','ezvars','flat-correction','downsample'],                    #EZVARS['flat-correction']['downsample'] int

    
    ## Settings for using file/darks across multiple experiments
    ['main_config_open_viewer','ezvars','inout','open-viewer'],                 #None bool (EZVARS['inout']['open-viewer'])
    ['main_config_common_flats_darks','ezvars','inout','shared-flatsdarks'],    #EZVARS['inout']['shared-flatsdarks'] bool
    ['main_config_darks_path','ezvars','inout','path2-shared-darks'],           #EZVARS['inout']['path2-shared-darks'] str
    ['main_config_flats_path','ezvars','inout','path2-shared-flats'],           #EZVARS['inout']['path2-shared-flats'] str
    ['main_config_flats2_checkbox','ezvars','inout','shared-flats-after'],      #EZVARS['inout']['shared-flats-after'] bool
    ['main_config_flats2_path','ezvars','inout','path2-shared-flats-after'],    #EZVARS['inout']['path2-shared-flats-after'] str
    
    ## NLMDN Settings
    ['advanced_nlmdn_apply_after_reco','ezvars','nlmdn','do-after-reco'],       #EZVARS['nlmdn']['do-after-reco'] bool
    ['advanced_nlmdn_input_dir','ezvars','nlmdn','input-dir'],                  #EZVARS['nlmdn']['input-dir'] str
    ['advanced_nlmdn_input_is_file','ezvars','nlmdn','input-is-1file'],         #EZVARS['nlmdn']['input-is-1file'] bool
    ['advanced_nlmdn_output_dir','ezvars','nlmdn','output_pattern'],            #EZVARS['nlmdn']['output_pattern'] str
    ['advanced_nlmdn_save_bigtiff','ezvars','nlmdn','bigtiff_output'],          #EZVARS['nlmdn']['bigtiff_output'] bool
    ['advanced_nlmdn_sim_search_radius','ezvars','nlmdn','search-radius'],      #EZVARS['nlmdn']['search-radius'] str
    ['advanced_nlmdn_patch_radius','ezvars','nlmdn','patch-radius'],            #EZVARS['nlmdn']['patch-radius'] str
    ['advanced_nlmdn_smoothing_control','ezvars','nlmdn','h'],                  #EZVARS['nlmdn']['h'] str
    ['advanced_nlmdn_noise_std','ezvars','nlmdn','sigma'],                      #EZVARS['nlmdn']['sigma'] str
    ['advanced_nlmdn_window','ezvars','nlmdn','window'],                        #EZVARS['nlmdn']['window'] str
    ['advanced_nlmdn_fast','ezvars','nlmdn','fast'],                            #EZVARS['nlmdn']['fast'] bool
    ['advanced_nlmdn_estimate_sigma','ezvars','nlmdn','estimate-sigma'],        #EZVARS['nlmdn']['estimate-sigma'] bool
    ['advanced_nlmdn_dry_run','ezvars','nlmdn','dryrun'],                       #EZVARS['nlmdn']['dryrun'] bool
    
    ## Advanced Settings
    ['advanced_advtofu_lamino_angle','sections','cone-beam-weight','axis-angle-x'],           #SECTIONS['general-reconstruction']['axis-angle-x'] str -> tupleize(dtype=list) (str?)
    ['advanced_adv_tofu_z_axis_rotation','sections','general-reconstruction','overall-angle'],      #SECTIONS['general-reconstruction']['overall-angle'] str -> (N/A) (in 'z-parameter'?) 
    ['advanced_advtofu_center_position_z','sections','cone-beam-weight','center-position-z'], #SECTIONS['general-reconstruction']['center-position-z'] str -> (N/A) (in 'z-parameter'?)
    ['advanced_advtofu_y_axis_rotation','sections','general-reconstruction','axis-angle-y'],        #SECTIONS['general-reconstruction']['axis-angle-y'] str -> tupleize(dtype=list) (str?)
    ['advanced_advtofu_aux_ffc_dark_scale','sections','flat-correction','dark-scale'],              #SECTIONS['flat-correction']['dark-scale'] str -> float
    ['advanced_advtofu_aux_ffc_flat_scale','sections','flat-correction','flat-scale'],              #SECTIONS['flat-correction']['flat-scale'] str -> float
    ['advanced_advtofu_extended_settings','ezvars','advanced','more-reco-params'],                  #EZVARS['advanced']['more-reco-params'] bool
    
    ['advanced_advtofu_aux_ffc_dark_scale','ezvars','flat-correction','dark-scale'], #(?) Same as SECTION?
    ['advanced_advtofu_aux_ffc_flat_scale','ezvars','flat-correction','flat-scale'], #(?) Same as SECTION?
            
    ## Optimizations
    ['advanced_optimize_verbose_console','sections','general','verbose'],                           #SECTIONS['general']['verbose'] bool -> None (bool)
    ['advanced_optimize_slice_mem_coeff','sections','general-reconstruction','slice-memory-coeff'], #SECTIONS['general-reconstruction']['slice-memory-coeff'] str -> None(float) [0.01, 0.95]
    ['advanced_optimize_slices_per_device','sections','general-reconstruction','data-splitting-policy'],     #SECTIONS['general-reconstruction']['data-splitting-policy'] str -> str
    ['advanced_optimize_num_gpus','sections','general-reconstruction','num-gpu-threads'],# '#SECTIONS['general-reconstruction']['num-gpu-threads'] (??) str -> int[1,inf]
    
    #Others
    ['parameters_type', 'ezvars', 'advanced', 'parameter-type']
]

EZVARS = OrderedDict()

EZVARS['inout'] = {
    'input-dir': {
        'default': "", 
        'type': str, 
        'help': "TODO"},
    'output-dir': {
        'default': "", 
        'type': str, 
        'help': "TODO"},
    'tmp-dir' : {
        'default': os.path.join(os.path.expanduser('~'),"tmp-ezufo"), #G
        'type': str, 
        'help': "TODO-updated Default"},
    'darks-dir': {
        'default': "darks", #G
        'type': str, 
        'help': "TODO-updated Default"},
    'flats-dir': {
        'default': "flats", #G
        'type': str, 
        'help': "TODO-updated Default"},
    'tomo-dir': {
        'default': "tomo", #G
        'type': str, 
        'help': "TODOç"},
    'flats2-dir': {
        'default': "flats2", #G
        'type': str, 
        'help': "TODO-updated Default"},
    'bigtiff-output': {
        'default': False, #G 
        'type': bool, 
        'help': "TODO"},
    'input_ROI': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
    'clip_hist': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
    'preprocess': {
        'default': False, 
        'type': bool, 
        'help': "TODO-updated Default"},
    'preprocess-command': {
        'default': "remove-outliers size=3 threshold=500 sign=1", 
        'type': str, 
        'help': "TODO-updated Default"},
    'output-ROI': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
    'output-x': {
        'default': 0, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "Crop slices: x"},
    'output-width': {
        'default': 0, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "Crop slices: width"},
    'output-y': {
        'default': 0, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "Crop slices: y"},
    'output-height': {
        'default': 0, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "Crop slices: height"},
    'dryrun': {
        'default': False, 
        'type': bool, 
        'help': "TODO-updated Default"},
    'save-params': {
        'default': True, 
        'type': bool, 
        'help': "TODO-updated Default"},
    'keep-tmp': {
        'default': False, 
        'type': bool, 
        'help': "TODO-updated Default"},
    'open-viewer': {
        'default': False, 
        'type': bool, 
        'help': "TODO-updated Default"},
    'shared-flatsdarks': {
        'default': False, 
        'type': bool, 
        'help': "TODO-updated Default"},
    'path2-shared-darks': {
        'default': "Absolute path to darks", 
        'type': str, 
        'help': "TODO-updated Default"},
    'path2-shared-flats': {
        'default': "Absolute path to flats", 
        'type': str, 
        'help': "TODO"},
    'shared-flats-after': {
        'default': False, 
        'type': bool, 
        'help': "TODO-updated Default"},
    'path2-shared-flats-after': {
        'default': "Absolute path to flats2", 
        'type': str, 
        'help': "TODO-updated Default"},
}

EZVARS['COR'] = {
    'search-method': {
        'default': 1, #G
        'type': int, 
        'help': "TODO"},
    'search-interval': {
        'default': "1010,1030,0.5", #G
        'type': str, 
        'help': "TODO"},
    'patch-size': {
        'default': 256, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "Size of reconstructed patch [pixel]"},
    'search-row': {
        'default': 100, #G
        'type': restrict_value((0,None), dtype=int), 
        'help': "Search in slice from row number"},
    'user-defined-ax': {
        'default': 0.0, #G
        'type': restrict_value((0,None),dtype=float), 
        'help': "Axis is in column No [pixel]"},
    'user-defined-dax': {
        'default': 0.0, #G
        'type': float, 
        'help': "TODO"},
}

EZVARS['filters'] = {'rm_spots': {
        'default': False, #G
        'type': bool, 
        'help': "TODO-G"}}

EZVARS['RR'] = {
    'enable': {
        'default': False, #G
        'type': bool, 
        'help': "TODO-G"},
    'use-ufo': {
        'default': True, #G
        'type': bool, 
        'help': "TODO-G"},
    'ufo-2d': {
        'default': False, #G 
        'type': bool, 
        'help': "TODO"},
    'sx': {
        'default': 0, 
        'type': restrict_value((0,None),dtype=int), 
        'help': "ufo ring-removal sigma horizontal"},
    'sy': {
        'default': 0, 
        'type': restrict_value((0,None),dtype=int), 
        'help': "ufo ring-removal sigma vertical"},
    'spy-narrow-window': {
        'default': 21, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "window size"},
    'spy-rm-wide': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
    'spy-wide-window': {
        'default': 91, #G 
        'type': restrict_value((0,None),dtype=int), 
        'help': "wind"},
    'spy-wide-SNR': {
        'default': 3, #G 
        'type': restrict_value((0,None),dtype=int), 
        'help': "SNR"},
}

#TODO ADD CHECKING NLMDN SETTINGS
#TODO ADD CHECKING FOR ADVANCED SETTINGS
EZVARS['flat-correction'] = {
    'smart-ffc': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
    'smart-ffc-method': {
        'default': "eigen", #G
        'type': str, 
        'help': "TODO"},
    'eigen-pco-reps': {
        'default': 4, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "Flat Field Correction: Eigen PCO Repetitions"},
    'eigen-pco-downsample': {
        'default': 2, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "Flat Field Correction: Eigen PCO Downsample"},
    'downsample': {
        'default': 4, #G
        'type': restrict_value((0,None),dtype=int), 
        'help': "Flat Field Correction: Downsample"},
    'dark-scale': {
        'default': 1.0, #G
        'type': float, 
        'help': "Scaling dark"}, #(?) has the same name in SECTION
    'flat-scale': {
        'default': 1.0, #G
        'type': float, 
        'help': "Scaling falt"}, #(?) has the same name in SECTION
}

EZVARS['nlmdn'] = {
    'do-after-reco': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
    'input-dir': {
        'default': os.getcwd(), #G
        'type': str, 
        'help': "TODO"},
    'input-is-1file': {
        'default': False, 
        'type': bool, 
        'help': "TODO"},
    'output_pattern': {
        'default': os.getcwd() + '-nlmfilt', #G
        'type': str, 
        'help': "TODO"},
    'bigtiff_output': {
        'default': False, #G
        'type': bool, 
        'help': "TODO-updated Default"},
    'search-radius': {
        'default': 10, #G
        'type': int, 
        'help': "TODO"},
    'patch-radius': {
        'default': "3", #G
        'type': int, 
        'help': "TODO"},
    'h': {
        'default': 0.0, #G
        'type': float, 
        'help': "TODO"},
    'sigma': {
        'default': 0.0, #G
        'type': float, 
        'help': "TODO"},
    'window': {
        'default': 0.0, #G
        'type': float, 
        'help': "TODO"},
    'fast': {
        'default': True, #G
        'type': bool, 
        'help': "TODO"},
    'estimate-sigma': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
    'dryrun': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
}


EZVARS['advanced'] = {
    'more-reco-params': {
        'default': False, #G
        'type': bool, 
        'help': "TODO"},
    'parameter-type': {
        'default': "", 
        'type': str, 
        'help': "TODO"}
}

EZVARS['find-large-spots'] = {
    'gauss-sigma': {
        'default': 0.0,
        'type': restrict_value((0,None), dtype=float),
        'help': "Gaussian sigma for removing low frequencies (filter will be 1 - gauss window)"},
    'spot-threshold': {
        'default': 0.0,
        'type': restrict_value((0,None), dtype=float),
        'help': "Pixels with grey value larger than this are considered as spots"},
}

EZVARS['retrieve-phase'] = {
    'enable': {
        'default': False, #G
        'type': bool,
        'help': "Enable phase retrieval"},
    'energy': {
        'default': 20, #G
        'type': restrict_value((0,None),dtype=float),
        'help': "Photon energy [keV]"},
    'pixel-size': {
        'default': 3.6, #G
        'type': restrict_value((0,None),dtype=float),
        'help': "Pixel size [micron]"},
    'propagation-distance': {
        'default': "0.1", #G
        'type': restrict_tupleize((0,None)),
        'help': ("Sample <-> detector distance (if one value, then use the same for x and y "
                 "direction, otherwise first specifies x and second y direction) [m]")},
    'regularization-rate': {
        'default': 200, #G - (!) - mismatch from help. Orignally 2. 
        'type': restrict_value((0,None),dtype=float),
        'help': "Regularization rate (typical values between [2, 3])"}
}

EZVARS['reading'] = {
    'y': {
        'default': 100, #G
        'type': restrict_value((0, None), dtype=int),
        'help': 'Vertical coordinate from where to start reading the input image'},
    'height': {
        'default': 200, #G
        'type': restrict_value((0, None), dtype=int),
        'help': "Number of rows which will be read (ROI height)"},
    'y-step': {
        'default': 20, #G
        'type': restrict_value((0, None), dtype=int),
        'help': "Read every \"step\" row from the input"}    
}

EZVARS['general'] = {
    'verbose': {
        'default': False, #G
        'help': 'Verbose output',
        'action': 'store_true'},
    'output-bitdepth': {
        'default': 8, #G - original: 32
        'type': restrict_value((0, None), dtype=int),
        'help': "Bit depth of output, either 8, 16 or 32",
        'metavar': 'BITDEPTH'},
    'output-minimum': {
        'default': 0.0, #G
        'type': float,
        'help': "Minimum value that maps to zero",
        'metavar': 'MIN'},
    'output-maximum': {
        'default': 0.0, #G
        'type': float,
        'help': "Maximum input value that maps to largest output value",
        'metavar': 'MAX'},
    
}

EZVARS['general-reconstruction'] = {
    'center-position-z': {
        'default': 0, #G
        'type': float,
        'help': "Z rotation axis position on a projection [pixels]"},
    'axis-angle-x': {   
        'default': 30, #G
        'type': float,
        'help': "Rotation axis rotation around the x axis"
                "(laminographic angle, 0 = tomography) [deg]"},
    'volume-angle-z': {
        'default': 0.0, #G
        'type': float,
        'help': "Volume rotation around the z axis (vertical) [deg]"},
    'overall-angle': {
        'default': 360, #G
        'type': float,
        'help': "The total angle over which projections were taken in degrees"},
    'axis-angle-y': {
        'default': 0, #G
        'type': float,
        'help': "Rotation axis rotation around the y axis (along beam direction) [deg]"},
    'slice-memory-coeff': {
        'default': 0.7, #G - original: 0.8
        'type': restrict_value((0.01, 0.95)),
        'help': "Portion of the GPU memory used for slices (from 0.01 to 0.9) [fraction]. "
                "The total amount of consumed memory will be larger depending on the "
                "complexity of the graph. In case of OpenCL memory allocation errors, "
                "try reducing this value."},
    'num-gpu-threads': {
        'default': 1, #G
        'type': restrict_value((1, None), dtype=int),
        'help': "Number of parallel reconstruction threads on one GPU"},
    'slices-per-device': {
        'default': 0,
        'type': restrict_value((0, None), dtype=int),
        'help': "Number of slices computed by one computing device"},
    'data-splitting-policy': {
        'default': 'one', #G
        'type': str,
        'help': "'one': one GPU should process as many slices as possible,\n"
                "'many': slices should be spread across as many GPUs as possible",
        'choices': ['one', 'many']}
}