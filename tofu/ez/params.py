# This file is used to share params as a global variable
import yaml
import os
from collections import OrderedDict
from tofu.util import restrict_value

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

# (!) DEPRECATED - This mapping can be used to convert old yaml settings to new ones
# Mapping table: [param name, dictionary name, key1, key2] -> dictionary[key1][key2]

MAP_TABLE = [
    # Format: [param name, dict name, key1 in dict, key2 in dict[key1]]
    # i.e. param name <-> dict[key1][key2]
    # PATHS
    ['main_config_input_dir','ezvars','inout','input-dir'],
    ['main_config_temp_dir','ezvars','inout','tmp-dir'],
    ['main_config_output_dir','ezvars','inout','output-dir'],
    ['main_config_darks_dir_name','ezvars', 'inout', 'darks-dir'],
    ['main_config_flats_dir_name','ezvars', 'inout', 'flats-dir'],
    ['main_config_tomo_dir_name','ezvars', 'inout', 'tomo-dir'],
    ['main_config_flats2_dir_name','ezvars', 'inout', 'flats2-dir'],
    ['main_config_save_multipage_tiff','ezvars','inout','bigtiff-output'],
    
    # center of rotation parameters 
    ['main_cor_axis_search_method','ezvars','COR','search-method'],
    ['main_cor_axis_search_interval','ezvars','COR','search-interval'],
    ['main_cor_search_row_start','ezvars','COR','search-row'],
    ['main_cor_recon_patch_size','ezvars','COR','patch-size'],
    ['main_cor_axis_column','ezvars','COR','user-defined-ax'],
    ['main_cor_axis_increment_step','ezvars','COR','user-defined-dax'],
    
    #ring removal
    ['main_filters_remove_spots','ezvars','filters','rm_spots'],
    ['main_filters_remove_spots_threshold','sections','find-large-spots','spot-threshold'],
    ['main_filters_remove_spots_blur_sigma','sections','find-large-spots','gauss-sigma'],
    ['main_filters_ring_removal','ezvars','RR','enable-RR'],
    ['main_filters_ring_removal_ufo_lpf','ezvars','RR','use-ufo'],
    ['main_filters_ring_removal_ufo_lpf_1d_or_2d','ezvars','RR','ufo-2d'],
    ['main_filters_ring_removal_ufo_lpf_sigma_horizontal','ezvars','RR','sx'],
    ['main_filters_ring_removal_ufo_lpf_sigma_vertical','ezvars','RR','sy'],
    ['main_filters_ring_removal_sarepy_window_size','ezvars','RR','spy-narrow-window'],
    ['main_filters_ring_removal_sarepy_wide','ezvars','RR','spy-rm-wide'],
    ['main_filters_ring_removal_sarepy_window','ezvars','RR','spy-wide-window'],
    ['main_filters_ring_removal_sarepy_SNR','ezvars','RR','spy-wide-SNR'],
    
    # phase retrieval
    ['main_pr_phase_retrieval','sections','retrieve-phase','enable-phase'],
    ['main_pr_photon_energy','sections','retrieve-phase','energy'],
    ['main_pr_pixel_size','sections','retrieve-phase','pixel-size'],
    ['main_pr_detector_distance','sections','retrieve-phase','propagation-distance'],
    ['main_pr_delta_beta_ratio','sections','retrieve-phase','regularization-rate'],
    
    # Crop vertically
    ['main_region_select_rows','ezvars','inout','input_ROI'],
    ['main_region_first_row','sections','reading','y'],
    ['main_region_number_rows','sections','reading','height'],
    ['main_region_nth_row','sections','reading','y-step'],
    
    # conv to 8 bit ##
    ['main_region_clip_histogram','ezvars','inout','clip_hist'],
    ['main_region_bit_depth','sections','general','output-bitdepth'],
    ['main_region_histogram_min','sections','general','output-minimum'],
    ['main_region_histogram_max','sections','general','output-maximum'],
    
    ## Processing attributes
    ['main_config_preprocess','ezvars','inout','preprocess'],
    ['main_config_preprocess_command','ezvars','inout','preprocess-command'],
    
    ## ROI in slice
    ['main_region_rotate_volume_clock','sections','general-reconstruction','volume-angle-z'],
    ['main_region_crop_slices','ezvars','inout','output-ROI'],
    ['main_region_crop_x','ezvars','inout','output-x'],
    ['main_region_crop_width','ezvars','inout','output-width'],
    ['main_region_crop_y','ezvars','inout','output-y'],
    ['main_region_crop_height','ezvars','inout','output-height'],
    
    ## misc settings
    ['main_config_dry_run','ezvars','inout','dryrun'],
    ['main_config_save_params','ezvars','inout','save-params'],
    ['main_config_keep_temp','ezvars','inout','keep-tmp'],
    
    ## sinFFC settings
    ['advanced_ffc_sinFFC','ezvars','flat-correction','smart-ffc'],
    ['advanced_ffc_method','ezvars','flat-correction','smart-ffc-method'],
    ['advanced_ffc_eigen_pco_reps','ezvars','flat-correction','eigen-pco-reps'],
    ['advanced_ffc_eigen_pco_downsample','ezvars','flat-correction','eigen-pco-downsample'],
    ['advanced_ffc_downsample','ezvars','flat-correction','downsample'],

    
    ## Settings for using file/darks across multiple experiments
    ['main_config_open_viewer','ezvars','inout','open-viewer'],
    ['main_config_common_flats_darks','ezvars','inout','shared-flatsdarks'],
    ['main_config_darks_path','ezvars','inout','path2-shared-darks'],
    ['main_config_flats_path','ezvars','inout','path2-shared-flats'],
    ['main_config_flats2_checkbox','ezvars','inout','shared-flats-after'],
    ['main_config_flats2_path','ezvars','inout','path2-shared-flats2'],
    
    ## NLMDN Settings
    ['advanced_nlmdn_apply_after_reco','ezvars','nlmdn','do-after-reco'],
    ['advanced_nlmdn_input_dir','ezvars','nlmdn','input-dir'],
    ['advanced_nlmdn_input_is_file','ezvars','nlmdn','input-is-1file'],
    ['advanced_nlmdn_output_dir','ezvars','nlmdn','output_pattern'],
    ['advanced_nlmdn_save_bigtiff','ezvars','nlmdn','bigtiff_output'],
    ['advanced_nlmdn_sim_search_radius','ezvars','nlmdn','search-radius'],
    ['advanced_nlmdn_patch_radius','ezvars','nlmdn','patch-radius'],
    ['advanced_nlmdn_smoothing_control','ezvars','nlmdn','h'],
    ['advanced_nlmdn_noise_std','ezvars','nlmdn','sigma'],
    ['advanced_nlmdn_window','ezvars','nlmdn','window'],
    ['advanced_nlmdn_fast','ezvars','nlmdn','fast'],
    ['advanced_nlmdn_estimate_sigma','ezvars','nlmdn','estimate-sigma'],
    ['advanced_nlmdn_dry_run','ezvars','nlmdn','dryrun'],
    
    ## Advanced Settings
    ['advanced_advtofu_lamino_angle','sections','cone-beam-weight','axis-angle-x'],
    ['advanced_adv_tofu_z_axis_rotation','sections','general-reconstruction','overall-angle'],
    ['advanced_advtofu_center_position_z','sections','cone-beam-weight','center-position-z'],
    ['advanced_advtofu_y_axis_rotation','sections','general-reconstruction','axis-angle-y'],
    ['advanced_advtofu_aux_ffc_dark_scale','sections','flat-correction','dark-scale'],
    ['advanced_advtofu_aux_ffc_flat_scale','sections','flat-correction','flat-scale'],
    ['advanced_advtofu_extended_settings','ezvars','advanced','more-reco-params'],
    
    ['advanced_advtofu_aux_ffc_dark_scale','ezvars','flat-correction','dark-scale'],
    ['advanced_advtofu_aux_ffc_flat_scale','ezvars','flat-correction','flat-scale'],
            
    ## Optimizations
    ['advanced_optimize_verbose_console','sections','general','verbose'],
    ['advanced_optimize_slice_mem_coeff','sections','general-reconstruction','slice-memory-coeff'],
    ['advanced_optimize_slices_per_device','sections','general-reconstruction','slices-per-device'],
    #['advanced_optimize_num_gpus','sections','general-reconstruction','num-gpu-threads'], #Replaced by data-splitting-policy
    
    #Others
    ['parameters_type', 'ezvars', 'advanced', 'parameter-type']
]

EZVARS = OrderedDict()

EZVARS['inout'] = {
    'input-dir': {
        'ezdefault': os.path.join(os.path.expanduser('~'),""), 
        'type': str, 
        'help': "TODO"},
    'output-dir': {
        'ezdefault': os.path.join(os.path.expanduser('~'),"rec"), 
        'type': str, 
        'help': "TODO"},
    'tmp-dir' : {
        'ezdefault': os.path.join(os.path.expanduser('~'),"tmp-ezufo"),
        'type': str, 
        'help': "TODO"},
    'darks-dir': {
        'ezdefault': "darks",
        'type': str, 
        'help': "TODO"},
    'flats-dir': {
        'ezdefault': "flats",
        'type': str, 
        'help': "TODO"},
    'tomo-dir': {
        'ezdefault': "tomo",
        'type': str, 
        'help': "TODO"},
    'flats2-dir': {
        'ezdefault': "flats2",
        'type': str, 
        'help': "TODO"},
    'bigtiff-output': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'input_ROI': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'clip_hist': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'preprocess': {
        'ezdefault': False, 
        'type': bool, 
        'help': "TODO"},
    'preprocess-command': {
        'ezdefault': "remove-outliers size=3 threshold=500 sign=1", 
        'type': str, 
        'help': "TODO"},
    'output-ROI': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'output-x': {
        'ezdefault': 0,
        'type': restrict_value((0,None),dtype=int), 
        'help': "Crop slices: x"},
    'output-width': {
        'ezdefault': 0,
        'type': restrict_value((0,None),dtype=int), 
        'help': "Crop slices: width"},
    'output-y': {
        'ezdefault': 0,
        'type': restrict_value((0,None),dtype=int), 
        'help': "Crop slices: y"},
    'output-height': {
        'ezdefault': 0,
        'type': restrict_value((0,None),dtype=int), 
        'help': "Crop slices: height"},
    'dryrun': {
        'ezdefault': False, 
        'type': bool, 
        'help': "TODO"},
    'save-params': {
        'ezdefault': True, 
        'type': bool, 
        'help': "TODO"},
    'keep-tmp': {
        'ezdefault': False, 
        'type': bool, 
        'help': "TODO"},
    'open-viewer': {
        'ezdefault': False, 
        'type': bool, 
        'help': "TODO"},
    'shared-flatsdarks': {
        'ezdefault': False, 
        'type': bool, 
        'help': "TODO"},
    'path2-shared-darks': {
        'ezdefault': "Absolute path to darks", 
        'type': str, 
        'help': "TODO"},
    'path2-shared-flats': {
        'ezdefault': "Absolute path to flats", 
        'type': str, 
        'help': "TODO"},
    'shared-flats-after': {
        'ezdefault': False, 
        'type': bool, 
        'help': "TODO"},
    'path2-shared-flats2': {
        'ezdefault': "Absolute path to flats2", 
        'type': str, 
        'help': "TODO"},
    'shared-df-used': {
        'ezdefault': False,
        'type': bool,
        'help': "Internal variable; must be set to True once "
                "shared flats/darks were used in the recontruction pipeline"},
}

EZVARS['COR'] = {
    'search-method': {
        'ezdefault': 1,
        'type': int, 
        'help': "TODO"},
    'search-interval': {
        'ezdefault': "1010,1030,0.5",
        'type': str, 
        'help': "TODO"},
    'patch-size': {
        'ezdefault': 256,
        'type': restrict_value((0,None),dtype=int), 
        'help': "Size of reconstructed patch [pixel]"},
    'search-row': {
        'ezdefault': 100,
        'type': restrict_value((0,None), dtype=int), 
        'help': "Search in slice from row number"},
    'user-defined-ax': {
        'ezdefault': 0.0,
        'type': restrict_value((0,None),dtype=float), 
        'help': "Axis is in column No [pixel]"},
    'user-defined-dax': {
        'ezdefault': 0.0,
        'type': float, 
        'help': "TODO"},
}

EZVARS['filters'] = {
    'rm_spots': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO-G"},
    'spot-threshold': {
        'ezdefault': 1000,
        'type': restrict_value((0,None), dtype=float),
        'help': "TODO-G"}
}

EZVARS['RR'] = {
    'enable-RR': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO-G"},
    'use-ufo': {
        'ezdefault': True,
        'type': bool, 
        'help': "TODO-G"},
    'ufo-2d': {
        'ezdefault': False, 
        'type': bool, 
        'help': "TODO"},
    'sx': {
        'ezdefault': 3,
        'type': restrict_value((0,None),dtype=int), 
        'help': "ufo ring-removal sigma horizontal (try 3..31)"},
    'sy': {
        'ezdefault': 1,
        'type': restrict_value((0,None),dtype=int), 
        'help': "ufo ring-removal sigma vertical (try 1..5)"},
    'spy-narrow-window': {
        'ezdefault': 21,
        'type': restrict_value((0,None),dtype=int), 
        'help': "window size"},
    'spy-rm-wide': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'spy-wide-window': {
        'ezdefault': 91, 
        'type': restrict_value((0,None),dtype=int), 
        'help': "wind"},
    'spy-wide-SNR': {
        'ezdefault': 3, 
        'type': restrict_value((0,None),dtype=int), 
        'help': "SNR"},
}

EZVARS['flat-correction'] = {
    'smart-ffc': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'smart-ffc-method': {
        'ezdefault': "eigen",
        'type': str, 
        'help': "TODO"},
    'eigen-pco-reps': {
        'ezdefault': 4,
        'type': restrict_value((0,None),dtype=int), 
        'help': "Flat Field Correction: Eigen PCO Repetitions"},
    'eigen-pco-downsample': {
        'ezdefault': 2,
        'type': restrict_value((0,None),dtype=int), 
        'help': "Flat Field Correction: Eigen PCO Downsample"},
    'downsample': {
        'ezdefault': 4,
        'type': restrict_value((0,None),dtype=int), 
        'help': "Flat Field Correction: Downsample"},
    'dark-scale': {
        'ezdefault': 1.0,
        'type': float, 
        'help': "Scaling dark"}, #(?) has the same name in SECTION
    'flat-scale': {
        'ezdefault': 1.0,
        'type': float, 
        'help': "Scaling falt"}, #(?) has the same name in SECTION
}

#TODO ADD CHECKING NLMDN SETTINGS
EZVARS['nlmdn'] = {
    'do-after-reco': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'input-dir': {
        'ezdefault': os.getcwd(),
        'type': str, 
        'help': "TODO"},
    'input-is-1file': {
        'ezdefault': False, 
        'type': bool, 
        'help': "TODO"},
    'output_pattern': {
        'ezdefault': os.getcwd() + '-nlmfilt',
        'type': str, 
        'help': "TODO"},
    'bigtiff_output': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'search-radius': {
        'ezdefault': 10,
        'type': int, 
        'help': "TODO"},
    'patch-radius': {
        'ezdefault': 3,
        'type': int, 
        'help': "TODO"},
    'h': {
        'ezdefault': 0.0,
        'type': float, 
        'help': "TODO"},
    'sigma': {
        'ezdefault': 0.0,
        'type': float, 
        'help': "TODO"},
    'window': {
        'ezdefault': 0.0,
        'type': float, 
        'help': "TODO"},
    'fast': {
        'ezdefault': True,
        'type': bool, 
        'help': "TODO"},
    'estimate-sigma': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'dryrun': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
}


EZVARS['advanced'] = {
    'more-reco-params': {
        'ezdefault': False,
        'type': bool, 
        'help': "TODO"},
    'parameter-type': {
        'ezdefault': "", 
        'type': str, 
        'help': "TODO"},
    'enable-optimization': {
        'ezdefault': False,
        'type': bool,
        'help': "TODO"
    }   
}