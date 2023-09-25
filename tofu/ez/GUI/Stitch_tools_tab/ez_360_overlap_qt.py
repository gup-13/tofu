from PyQt5.QtWidgets import (
    QGroupBox,
    QPushButton,
    QCheckBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QGridLayout,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import pyqtSignal
import logging
from shutil import rmtree
import yaml
import os
from tofu.ez.Helpers.find_360_overlap import find_overlap, map_sharpness_type_to_name
import tofu.ez.params as params
from tofu.ez.params import EZVARS
from tofu.util import get_int_validator, get_tuple_validator

#TODO Make all stitching tools compatible with the bigtiffs


LOG = logging.getLogger(__name__)

class Overlap360Group(QGroupBox):
    get_fdt_names_on_stitch_pressed = pyqtSignal()
    get_RR_params_on_start_pressed = pyqtSignal()
    
    def __init__(self):
        super().__init__()

        self.setTitle("360-AXIS-SEARCH")
        self.setToolTip("Stitches and reconstructs one slice with different axis of rotation positions for half-acqusition mode data set(s)")
        self.setStyleSheet('QGroupBox {color: Orange;}')

        self.input_dir_button = QPushButton("Select input directory")
        self.input_dir_button.clicked.connect(self.input_button_pressed)
        self.input_dir_entry = QLineEdit()
        self.input_dir_entry.editingFinished.connect(self.set_input_entry)

        self.temp_dir_button = QPushButton("Select temp directory")
        self.temp_dir_button.clicked.connect(self.temp_button_pressed)
        self.temp_dir_entry = QLineEdit()
        self.temp_dir_entry.editingFinished.connect(self.set_temp_entry)

        self.output_dir_button = QPushButton("Select output directory")
        self.output_dir_button.clicked.connect(self.output_button_pressed)
        self.output_dir_entry = QLineEdit()
        self.output_dir_entry.editingFinished.connect(self.set_output_entry)

        self.pixel_row_label = QLabel("Row to be reconstructed")
        self.pixel_row_entry = QLineEdit()
        self.pixel_row_entry.setValidator(get_int_validator())
        self.pixel_row_entry.editingFinished.connect(self.set_pixel_row)

        self.min_label = QLabel("Lower limit of stitch/axis search range")
        self.min_entry = QLineEdit()
        self.min_entry.setValidator(get_int_validator())
        self.min_entry.editingFinished.connect(self.set_lower_limit)

        self.max_label = QLabel("Upper limit of stitch/axis search range")
        self.max_entry = QLineEdit()
        self.max_entry.setValidator(get_int_validator())
        self.max_entry.editingFinished.connect(self.set_upper_limit)

        self.step_label = QLabel("Value by which to increment through search range")
        self.step_entry = QLineEdit()
        self.step_entry.setValidator(get_int_validator())
        self.step_entry.editingFinished.connect(self.set_increment)
        
        self.patch_size_label = QLabel("Image patch size")
        self.patch_size_entry = QLineEdit()
        self.patch_size_entry.setValidator(get_int_validator())
        self.patch_size_entry.editingFinished.connect(self.set_patch_size)

        self.RR_checkbox = QCheckBox("Apply ring removal")
        self.RR_checkbox.stateChanged.connect(self.set_RR_checkbox)
        
        self.detrend_checkbox = QCheckBox("Apply detrend")
        self.detrend_checkbox.stateChanged.connect(self.set_detrend_checkbox)
        
        self.sharpness_type_label = QLabel("Sharpness evaluation Type")
        self.sharpness_type_entry = QComboBox()
        for key in map_sharpness_type_to_name:
            self.sharpness_type_entry.addItem(map_sharpness_type_to_name[key])
        self.sharpness_type_entry.currentIndexChanged.connect(self.set_sharpness_type)
        
        self.help_button = QPushButton("Help")
        self.help_button.clicked.connect(self.help_button_pressed)

        self.find_overlap_button = QPushButton("Generate slices")
        self.find_overlap_button.clicked.connect(self.overlap_button_pressed)
        self.find_overlap_button.setStyleSheet("color:royalblue;font-weight:bold")

        self.import_parameters_button = QPushButton("Import Parameters from File")
        self.import_parameters_button.clicked.connect(self.import_parameters_button_pressed)

        self.save_parameters_button = QPushButton("Save Parameters to File")
        self.save_parameters_button.clicked.connect(self.save_parameters_button_pressed)

        self.setCheckable(True)
        self.set_layout()
        self.clicked.connect(self.update_size)
    
    def update_size(self):
        if self.isChecked():
            self.setMaximumSize(10000, 500) # Expanded
        else:
            self.setMaximumSize(10000, 20) # Collapsed

    def set_layout(self):
        self.update_size()
        
        layout = QGridLayout()
        layout.addWidget(self.input_dir_button, 0, 0, 1, 2)
        layout.addWidget(self.input_dir_entry, 1, 0, 1, 2)
        layout.addWidget(self.output_dir_button, 2, 0, 1, 2)
        layout.addWidget(self.output_dir_entry, 3, 0, 1, 2)
        layout.addWidget(self.temp_dir_button, 4, 0, 1, 2)
        layout.addWidget(self.temp_dir_entry, 5, 0, 1, 2)
        layout.addWidget(self.pixel_row_label, 6, 0)
        layout.addWidget(self.pixel_row_entry, 6, 1)
        layout.addWidget(self.min_label, 7, 0)
        layout.addWidget(self.min_entry, 7, 1)
        layout.addWidget(self.max_label, 8, 0)
        layout.addWidget(self.max_entry, 8, 1)
        layout.addWidget(self.step_label, 9, 0)
        layout.addWidget(self.step_entry, 9, 1)
        layout.addWidget(self.patch_size_label, 10, 0)
        layout.addWidget(self.patch_size_entry, 10, 1)
        layout.addWidget(self.sharpness_type_label, 11, 0)
        layout.addWidget(self.sharpness_type_entry, 11, 1)
        layout.addWidget(self.RR_checkbox, 12, 0)
        layout.addWidget(self.detrend_checkbox, 12, 1)
        layout.addWidget(self.help_button, 13, 0)
        layout.addWidget(self.find_overlap_button, 13, 1)
        layout.addWidget(self.import_parameters_button, 14, 0)
        layout.addWidget(self.save_parameters_button, 14, 1)
        self.setLayout(layout)

    def init_values(self):
        self.parameters = {'parameters_type': '360_overlap'}
        self.parameters['360overlap_input_dir'] = os.path.expanduser('~')  #EZVARS['360-olap-search']['indir']
        self.input_dir_entry.setText(self.parameters['360overlap_input_dir'])
        self.parameters['360overlap_output_dir'] = os.path.join(    #EZVARS['360-olap-search']['outdir']
                        os.path.expanduser('~'), "ezufo-360axis-search")
        self.output_dir_entry.setText(self.parameters['360overlap_output_dir'])
        self.parameters['360overlap_temp_dir'] = os.path.join(   #EZVARS['360-olap-search']['tmpdir']
                        os.path.expanduser('~'), "tmp-360axis-search")
        self.temp_dir_entry.setText(self.parameters['360overlap_temp_dir'])
        self.parameters['360overlap_row'] = 200       #EZVARS['360-olap-search']['y']
        self.pixel_row_entry.setText(str(self.parameters['360overlap_row']))
        self.parameters['360overlap_lower_limit'] = 100   #EZVARS['360-olap-search']['column_first']
        self.min_entry.setText(str(self.parameters['360overlap_lower_limit']))
        self.parameters['360overlap_upper_limit'] = 200   #EZVARS['360-olap-search']['column_last']
        self.max_entry.setText(str(self.parameters['360overlap_upper_limit']))
        self.parameters['360overlap_increment'] = 1    #EZVARS['360-olap-search']['column_step']
        self.step_entry.setText(str(self.parameters['360overlap_increment']))
        self.parameters['360overlap_patch_size'] = 0    #full size
        self.patch_size_entry.setText(str(self.parameters['360overlap_patch_size']))
        self.parameters['360overlap_sharpness_type'] = "msag"
        self.update_sharpness_type_entry()
        self.parameters['360overlap_doRR'] = False  # replace with #EZVARS['360-olap-search']['remove-rings']
        self.RR_checkbox.setChecked(bool(self.parameters['360overlap_doRR']))
        self.parameters['360overlap_detrend'] = False
        self.detrend_checkbox.setChecked(bool(self.parameters['360overlap_detrend']))

    def update_parameters(self, new_parameters):
        LOG.debug("Update parameters")
        if new_parameters['parameters_type'] != '360_overlap':
            print("Error: Invalid parameter file type: " + str(new_parameters['parameters_type']))
            return -1
        # Update parameters dictionary (which is passed to auto_stitch_funcs)
        for key in new_parameters:
            self.parameters[key] = new_parameters[key]
        
        # Update displayed parameters for GUI
        self.input_dir_entry.setText(self.parameters['360overlap_input_dir'])
        self.temp_dir_entry.setText(self.parameters['360overlap_temp_dir'])
        self.output_dir_entry.setText(self.parameters['360overlap_output_dir'])
        self.pixel_row_entry.setText(str(self.parameters['360overlap_row']))
        self.min_entry.setText(str(self.parameters['360overlap_lower_limit']))
        self.max_entry.setText(str(self.parameters['360overlap_upper_limit']))
        self.step_entry.setText(str(self.parameters['360overlap_increment']))
        self.patch_size_entry.setText(str(self.parameters['360overlap_patch_size']))
        self.update_sharpness_type_entry()
        self.RR_checkbox.setChecked(bool(self.parameters['360overlap_doRR']))
        self.detrend_checkbox.setChecked(bool(self.parameters['360overlap_detrend']))

    def input_button_pressed(self):
        LOG.debug("Select input button pressed")
        dir_explore = QFileDialog(self)
        dir = dir_explore.getExistingDirectory()
        if dir:
            self.parameters['360overlap_input_dir'] = dir
            self.input_dir_entry.setText(self.parameters['360overlap_input_dir'])

    def set_input_entry(self):
        LOG.debug("Input: " + str(self.input_dir_entry.text()))
        self.parameters['360overlap_input_dir'] = str(self.input_dir_entry.text())

    def temp_button_pressed(self):
        LOG.debug("Select temp button pressed")
        dir_explore = QFileDialog(self)
        dir = dir_explore.getExistingDirectory()
        if dir:
            self.parameters['360overlap_temp_dir'] = dir
            self.temp_dir_entry.setText(self.parameters['360overlap_temp_dir'])

    def set_temp_entry(self):
        LOG.debug("Temp: " + str(self.temp_dir_entry.text()))
        self.parameters['360overlap_temp_dir'] = str(self.temp_dir_entry.text())

    def output_button_pressed(self):
        LOG.debug("Select output button pressed")
        dir_explore = QFileDialog(self)
        dir = dir_explore.getExistingDirectory()
        if dir:
            self.parameters['360overlap_output_dir'] = dir
            self.output_dir_entry.setText(self.parameters['360overlap_output_dir'])

    def set_output_entry(self):
        LOG.debug("Output: " + str(self.output_dir_entry.text()))
        self.parameters['360overlap_output_dir'] = str(self.output_dir_entry.text())

    def set_pixel_row(self):
        LOG.debug("Pixel row: " + str(self.pixel_row_entry.text()))
        self.parameters['360overlap_row'] = int(self.pixel_row_entry.text())

    def set_lower_limit(self):
        LOG.debug("Lower limit: " + str(self.min_entry.text()))
        self.parameters['360overlap_lower_limit'] = int(self.min_entry.text())

    def set_upper_limit(self):
        LOG.debug("Upper limit: " + str(self.max_entry.text()))
        self.parameters['360overlap_upper_limit'] = int(self.max_entry.text())

    def set_increment(self):
        LOG.debug("Value of increment: " + str(self.step_entry.text()))
        self.parameters['360overlap_increment'] = int(self.step_entry.text())
        
    def set_patch_size(self):
        LOG.debug("Image Patch Size: " + str(self.patch_size_entry.text()))
        self.parameters['360overlap_patch_size'] = int(self.patch_size_entry.text())
        
    def set_sharpness_type(self):
        LOG.debug("Sharpness evaluation type: " + str(self.sharpness_type_entry.currentText()))
        if(self.sharpness_type_entry.currentText() == "Gradient"):
            self.parameters['360overlap_sharpness_type'] = "msag"
        elif(self.sharpness_type_entry.currentText() == "Standard Deviation"):
            self.parameters['360overlap_sharpness_type'] = "mstd"
        else:
            self.parameters['360overlap_sharpness_type'] = "invalid"
            
    def update_sharpness_type_entry(self):
        LOG.debug("Apply sharpness evaluation type: " + str(self.sharpness_type_entry.currentText()))
        combobox_index = 0 
        for key in map_sharpness_type_to_name:
            if map_sharpness_type_to_name[key] == self.parameters['360overlap_sharpness_type']:
                self.sharpness_type_entry.setCurrentIndex(combobox_index)
            
            combobox_index = combobox_index + 1
        
    def set_RR_checkbox(self):
        LOG.debug("Apply ring removal: " + str(self.RR_checkbox.isChecked()))
        self.parameters['360overlap_doRR'] = bool(self.RR_checkbox.isChecked())
    
    def set_detrend_checkbox(self):
        LOG.debug("Apply detrend: " + str(self.detrend_checkbox.isChecked()))
        self.parameters['360overlap_detrend'] = bool(self.detrend_checkbox.isChecked())

    def overlap_button_pressed(self):
        LOG.debug("Find overlap button pressed")
        self.get_fdt_names_on_stitch_pressed.emit()
        self.get_RR_params_on_start_pressed.emit()
        if os.path.exists(self.parameters['360overlap_output_dir']) and \
                    len(os.listdir(self.parameters['360overlap_output_dir'])) > 0:
            qm = QMessageBox()
            rep = qm.question(self, '', "Output directory exists and not empty. Can I delete it to continue?",
                              qm.Yes | qm.No)
            if rep == qm.Yes:
                try:
                    rmtree(self.parameters['360overlap_output_dir'])
                except:
                    QMessageBox.information(self, "Problem", "Cannot delete existing output dir")
                    return
            else:
                return
        if os.path.exists(self.parameters['360overlap_temp_dir']) and \
                len(os.listdir(self.parameters['360overlap_temp_dir'])) > 0:
            qm = QMessageBox()
            rep = qm.question(self, '', "Temporary dir exist and not empty. Can I delete it to continue?", qm.Yes | qm.No)
            if rep == qm.Yes:
                try:
                    rmtree(self.parameters['360overlap_temp_dir'])
                except:
                    QMessageBox.information(self, "Problem", "Cannot delete existing tmp dir")
                    return
            else:
                return
        if not os.path.exists(self.parameters['360overlap_temp_dir']):
            os.makedirs(self.parameters['360overlap_temp_dir'])
        if not os.path.exists(self.parameters['360overlap_output_dir']):
            os.makedirs(self.parameters['360overlap_output_dir'])
        
        fdt_settings = {
            'darks': EZVARS['inout']['darks-dir']['value'],
            'flats': EZVARS['inout']['flats-dir']['value'],
            'tomo': EZVARS['inout']['tomo-dir']['value'],
            'flats2': EZVARS['inout']['flats2-dir']['value'],
            'common_darks': EZVARS['inout']['path2-shared-darks']['value'],
            'common_flats': EZVARS['inout']['path2-shared-flats']['value'],
            'common_flats2': EZVARS['inout']['path2-shared-flats2']['value'],
            'use_common_flats2': True,
            'use_shared_flatsdarks': EZVARS['inout']['shared-flatsdarks']['value']
        }
            
        overlaps, points_list = find_overlap(self.parameters, fdt_settings)
        for i in range(0, len(overlaps)):
            LOG.debug("For view index %d with overlap %d, the calculations are: %s", i, overlaps[i], points_list[i])
        if os.path.exists(self.parameters['360overlap_output_dir']):
            params_file_path = os.path.join(self.parameters['360overlap_output_dir'], '360_overlap_params.yaml')
            params.save_parameters(self.parameters, params_file_path)


    def help_button_pressed(self):
        LOG.debug("Help button pressed")
        h = "This script takes as input a CT scan that has been collected in 'half-acquisition' mode"
        h += " and produces a series of reconstructed slices, each of which are generated by cropping and"
        h += " concatenating opposing projections together over a range of 'overlap' values (i.e. the pixel column"
        h += " at which the images are cropped and concatenated)."
        h += " The objective is to review this series of images to determine the pixel column at which the axis of rotation"
        h += " is located (much like the axis search function commonly used in reconstruction software)."
        QMessageBox.information(self, "Help", h)

    def import_parameters_button_pressed(self):
        LOG.debug("Import params button clicked")
        dir_explore = QFileDialog(self)
        params_file_path = dir_explore.getOpenFileName(filter="*.yaml")
        try:
            file_in = open(params_file_path[0], 'r')
            new_parameters = yaml.load(file_in, Loader=yaml.FullLoader)
            if self.update_parameters(new_parameters) == 0:
                print("Parameters file loaded from: " + str(params_file_path[0]))
        except FileNotFoundError:
            print("You need to select a valid input file")

    def save_parameters_button_pressed(self):
        LOG.debug("Save params button clicked")
        dir_explore = QFileDialog(self)
        params_file_path = dir_explore.getSaveFileName(filter="*.yaml")
        garbage, file_name = os.path.split(params_file_path[0])
        file_extension = os.path.splitext(file_name)
        # If the user doesn't enter the .yaml extension then append it to filepath
        if file_extension[-1] == "":
            file_path = params_file_path[0] + ".yaml"
        else:
            file_path = params_file_path[0]
        try:
            file_out = open(file_path, 'w')
            yaml.dump(self.parameters, file_out)
            print("Parameters file saved at: " + str(file_path))
        except FileNotFoundError:
            print("You need to select a directory and use a valid file name")

