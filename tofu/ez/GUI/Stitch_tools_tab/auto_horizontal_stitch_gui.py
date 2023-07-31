import os
import logging
import shutil
import yaml

from PyQt5.QtWidgets import QPushButton, QLabel, QLineEdit, QGridLayout, QFileDialog, QCheckBox,\
                            QMessageBox, QGroupBox
from tofu.ez.GUI.Stitch_tools_tab.auto_horizontal_stitch_funcs import AutoHorizontalStitchFunctions
from tofu.util import get_tuple_validator, get_int_validator

class AutoHorizontalStitchGUI(QGroupBox):
    def __init__(self):
        super().__init__()
        self.setTitle('Auto Horizontal Stitch')

        #logger = logging.getLogger()
        #logger.setLevel(logging.DEBUG)

        self.parameters = {'parameters_type': 'auto_horizontal_stitch'}
        self.auto_horizontal_stitch_funcs = None

        self.input_button = QPushButton("Select Input Path")
        self.input_button.clicked.connect(self.input_button_pressed)
        self.input_entry = QLineEdit()
        self.input_entry.textChanged.connect(self.set_input_entry)
        
        self.temp_button = QPushButton("Select Temp Path")
        self.temp_button.clicked.connect(self.temp_button_pressed)
        self.temp_entry = QLineEdit()
        self.temp_entry.textChanged.connect(self.set_temp_entry)

        self.output_button = QPushButton("Select Output Path")
        self.output_button.clicked.connect(self.output_button_pressed)
        self.output_entry = QLineEdit()
        self.output_entry.textChanged.connect(self.set_output_entry)

        self.flats_darks_group = QGroupBox("Use Common Set of Flats and Darks")
        self.flats_darks_group.clicked.connect(self.set_flats_darks_group)

        self.darks_button = QPushButton("Select Darks Path")
        self.darks_button.clicked.connect(self.darks_button_pressed)
        self.darks_entry = QLineEdit()
        self.darks_entry.textChanged.connect(self.set_darks_entry)
        
        self.flats_button = QPushButton("Select Flats Path")
        self.flats_button.clicked.connect(self.flats_button_pressed)
        self.flats_entry = QLineEdit()
        self.flats_entry.textChanged.connect(self.set_flats_entry)
        
        self.flats2_button = QPushButton("Select Flats2 Path")
        self.flats2_button.clicked.connect(self.flats2_button_pressed)
        self.flats2_entry = QLineEdit()
        self.flats2_entry.textChanged.connect(self.set_flats2_entry)
        
        self.search_half_acquisition_axis_label = QLabel("Search half-acquisition axis in\n[start, stop, step] interval")
        self.search_half_acquisition_axis_entry = QLineEdit()
        self.search_half_acquisition_axis_entry.setValidator(get_tuple_validator())
        self.search_half_acquisition_axis_entry.textChanged.connect(self.set_search_half_acquisition_axis_entry)
        
        self.enable_ring_removal_checkbox = QCheckBox("Enable ring removal")
        self.enable_ring_removal_checkbox.stateChanged.connect(self.set_enable_ring_removal_checkbox)
        
        self.enable_half_acquisition_checkbox = QCheckBox("Enable half-acquisition axis search")
        self.enable_half_acquisition_checkbox.stateChanged.connect(self.set_enable_half_acquisition_axis_checkbox)

        self.search_rotational_axis_label = QLabel("Search rotation axis in\n[start, stop, step] interval")
        self.search_rotational_axis_entry = QLineEdit()
        self.search_rotational_axis_entry.setValidator(get_tuple_validator())
        self.search_rotational_axis_entry.textChanged.connect(self.set_search_rotational_axis_entry)
        
        self.search_slice_label = QLabel("Search in Slice Number")
        self.search_slice_entry = QLineEdit()
        self.search_slice_entry.setValidator(get_int_validator())
        self.search_slice_entry.textChanged.connect(self.set_search_slice_entry)

        self.save_params_button = QPushButton("Save parameters")
        self.save_params_button.clicked.connect(self.save_params_button_clicked)

        self.import_params_button = QPushButton("Import parameters")
        self.import_params_button.clicked.connect(self.import_params_button_clicked)

        self.help_button = QPushButton("Help")
        self.help_button.clicked.connect(self.help_button_pressed)

        self.delete_temp_button = QPushButton("Delete Output Directory")
        self.delete_temp_button.clicked.connect(self.delete_button_pressed)

        self.stitch_button = QPushButton("Stitch")
        self.stitch_button.clicked.connect(self.stitch_button_pressed)

        self.dry_run_checkbox = QCheckBox("Dry Run")
        self.dry_run_checkbox.stateChanged.connect(self.set_dry_run_checkbox)

        self.set_layout()

        self.init_values()
        self.show()

    def set_layout(self):
        self.setMaximumSize(800, 500)

        layout = QGridLayout()
        layout.addWidget(self.input_button, 0, 0, 1, 1)
        layout.addWidget(self.input_entry, 0, 1, 1, 3)
        layout.addWidget(self.temp_button, 1, 0, 1, 1)
        layout.addWidget(self.temp_entry, 1, 1, 1, 3)
        layout.addWidget(self.output_button, 2, 0, 1, 1)
        layout.addWidget(self.output_entry, 2, 1, 1, 3)

        self.flats_darks_group.setCheckable(True)
        self.flats_darks_group.setChecked(False)
        flats_darks_layout = QGridLayout()
        flats_darks_layout.addWidget(self.darks_button, 0, 0, 1, 1)
        flats_darks_layout.addWidget(self.darks_entry, 0, 1, 1, 2)
        flats_darks_layout.addWidget(self.flats_button, 1, 0, 1, 1)
        flats_darks_layout.addWidget(self.flats_entry, 1, 1, 1, 2)
        flats_darks_layout.addWidget(self.flats2_button, 2, 0, 1, 1)
        flats_darks_layout.addWidget(self.flats2_entry, 2, 1, 1, 2)
        self.flats_darks_group.setLayout(flats_darks_layout)
        layout.addWidget(self.flats_darks_group, 3, 0, 1, 5)
        
        layout.addWidget(self.search_half_acquisition_axis_label, 4, 0)
        layout.addWidget(self.search_half_acquisition_axis_entry, 4, 1)
        layout.addWidget(self.enable_ring_removal_checkbox, 4, 2)
        layout.addWidget(self.enable_half_acquisition_checkbox, 4, 3)

        layout.addWidget(self.search_rotational_axis_label, 5, 0)
        layout.addWidget(self.search_rotational_axis_entry, 5, 1)
        layout.addWidget(self.search_slice_label, 5, 2)
        layout.addWidget(self.search_slice_entry, 5, 3)

        layout.addWidget(self.save_params_button, 6, 0, 1, 2)
        layout.addWidget(self.help_button, 6, 2, 1, 1)
        layout.addWidget(self.import_params_button, 6, 3, 1, 1)

        layout.addWidget(self.stitch_button, 7, 0, 1, 2)
        layout.addWidget(self.dry_run_checkbox, 7, 2, 1, 1)
        layout.addWidget(self.delete_temp_button, 7, 3, 1, 1)
        self.setLayout(layout)

    def init_values(self):
        self.input_entry.setText("...enter input directory")
        self.temp_entry.setText("...enter temp directory")
        self.output_entry.setText("...enter output directory")
        self.parameters['common_flats_darks'] = False
        self.darks_entry.setText("...enter darks directory")
        self.parameters['darks_dir'] = ""
        self.flats_entry.setText("...enter flats directory")
        self.parameters['flats_dir'] = ""
        self.flats2_entry.setText("...enter flats2 directory")
        self.parameters['flats2_dir'] = ""
        self.search_half_acquisition_axis_entry.setText("100,200,1")
        self.parameters['search_half_acquisition_axis'] = "100,200,1"
        self.enable_ring_removal_checkbox.setChecked(False)
        self.parameters['enable_ring_removal'] = False
        self.enable_half_acquisition_checkbox.setChecked(True)
        self.parameters['enable_half_acquisition_axis'] = True
        self.search_rotational_axis_entry.setText("1010,1030,0.5")
        self.parameters['search_rotational_axis'] = "1010,1030,0.5"
        self.search_slice_entry.setText("100")
        self.parameters['search_slice'] = "100"
        self.dry_run_checkbox.setChecked(False)
        self.parameters['dry_run'] = False

    def update_parameters(self, new_parameters):
        logging.debug("Update parameters")
        # Update parameters dictionary (which is passed to auto_stitch_funcs)
        self.parameters = new_parameters
        # Update displayed parameters for GUI
        self.input_entry.setText(self.parameters['input_dir'])
        self.temp_entry.setText(self.parameters['temp_dir'])
        self.output_entry.setText(self.parameters['output_dir'])
        self.flats_darks_group.setChecked(bool(self.parameters['common_flats_darks']))
        self.darks_entry.setText(self.parameters['darks_dir'])
        self.flats_entry.setText(self.parameters['flats_dir'])
        self.flats_entry.setText(self.parameters['flats2_dir'])
        self.search_half_acqusition_axis_entry.setText(self.parameters['search_half_acqusition_axis'])
        self.enable_ring_removal_checkbox.setChecked(bool(self.parameters['enable_ring_removal']))
        self.enable_half_acquisition_checkbox.setChecked(bool(self.parameters['enable_half_acqusition_axis']))
        self.search_rotational_axis_entry.setText(self.parameters['search_rotational_axis'])
        self.search_slice_entry.setText(self.parameters['search_slice'])
        self.dry_run_checkbox.setChecked(bool(self.parameters['dry_run']))

    def input_button_pressed(self):
        logging.debug("Input Button Pressed")
        dir_explore = QFileDialog(self)
        input_dir = dir_explore.getExistingDirectory()
        self.input_entry.setText(input_dir)
        self.parameters['input_dir'] = input_dir

    def set_input_entry(self):
        logging.debug("Input Entry: " + str(self.input_entry.text()))
        self.parameters['input_dir'] = str(self.input_entry.text())    
    
    def temp_button_pressed(self):
        logging.debug("Temp Button Pressed")
        dir_explore = QFileDialog(self)
        temp_dir = dir_explore.getExistingDirectory()
        self.temp_entry.setText(temp_dir)
        self.parameters['temp_dir'] = temp_dir
            
    def set_temp_entry(self):
        logging.debug("Temp Entry: " + str(self.temp_entry.text()))
        self.parameters['temp_dir'] = str(self.temp_entry.text())

    def output_button_pressed(self):
        logging.debug("Output Button Pressed")
        dir_explore = QFileDialog(self)
        output_dir = dir_explore.getExistingDirectory()
        self.output_entry.setText(output_dir)
        self.parameters['output_dir'] = output_dir

    def set_output_entry(self):
        logging.debug("Output Entry: " + str(self.output_entry.text()))
        self.parameters['output_dir'] = str(self.output_entry.text())

    def set_flats_darks_group(self):
        logging.debug("Use Common Flats/Darks: " + str(self.flats_darks_group.isChecked()))
        if self.parameters['common_flats_darks'] is True:
            self.parameters['common_flats_darks'] = False
        else:
            self.parameters['common_flats_darks'] = True

    def darks_button_pressed(self):
        logging.debug("Darks Button Pressed")
        dir_explore = QFileDialog(self)
        darks_dir = dir_explore.getExistingDirectory()
        self.darks_entry.setText(darks_dir)
        self.parameters['darks_dir'] = darks_dir

    def set_darks_entry(self):
        logging.debug("Darks Entry: " + str(self.darks_entry.text()))
        self.parameters['darks_dir'] = str(self.darks_entry.text())
        
    def flats_button_pressed(self):
        logging.debug("Flats Button Pressed")
        dir_explore = QFileDialog(self)
        flats_dir = dir_explore.getExistingDirectory()
        self.flats_entry.setText(flats_dir)
        self.parameters['flats_dir'] = flats_dir

    def set_flats_entry(self):
        logging.debug("Flats Entry: " + str(self.flats_entry.text()))
        self.parameters['flats_dir'] = str(self.flats_entry.text())
        
    def flats2_button_pressed(self):
        logging.debug("Flats2 Button Pressed")
        dir_explore = QFileDialog(self)
        flats2_dir = dir_explore.getExistingDirectory()
        self.flats2_entry.setText(flats2_dir)
        self.parameters['flats2_dir'] = flats2_dir

    def set_flats2_entry(self):
        logging.debug("Flats2 Entry: " + str(self.flats2_entry.text()))
        self.parameters['flats2_dir'] = str(self.flats2_entry.text())
            
    def set_search_half_acquisition_axis_entry(self):
        logging.debug("Search Half-Acquisition Axis: " + str(self.search_half_acquisition_axis_entry.text()))
        self.parameters['search_half_acquisition_axis'] = str(self.search_half_acquisition_axis_entry.text())
        
    def set_enable_ring_removal_checkbox(self):
        logging.debug("Enable ring removal Checkbox: " + str(self.enable_ring_removal_checkbox.isChecked()))
        self.parameters['enable_ring_removal'] = self.enable_ring_removal_checkbox.isChecked()
    
    def set_enable_half_acquisition_axis_checkbox(self):
        logging.debug("Enable half-acqusition Checkbox: " + str(self.enable_half_acquisition_checkbox.isChecked()))
        self.parameters['enable_half_acquisition_axis'] = self.enable_half_acquisition_checkbox.isChecked()
        self.search_half_acquisition_axis_entry.setEnabled(self.parameters['enable_half_acquisition_axis'])
        self.enable_ring_removal_checkbox.setEnabled(self.parameters['enable_half_acquisition_axis'])

    def set_search_rotational_axis_entry(self):
        logging.debug("Search Rotational Axis: " + str(self.search_rotational_axis_entry.text()))
        self.parameters['search_rotational_axis'] = str(self.search_rotational_axis_entry.text())
        
    def set_search_slice_entry(self):
        logging.debug("Search Slice: " + str(self.search_slice_entry.text()))
        self.parameters['search_slice'] = self.search_slice_entry.text()

    def save_params_button_clicked(self):
        logging.debug("Save params button clicked")
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

    def import_params_button_clicked(self):
        logging.debug("Import params button clicked")
        dir_explore = QFileDialog(self)
        params_file_path = dir_explore.getOpenFileName(filter="*.yaml")
        try:
            file_in = open(params_file_path[0], 'r')
            new_parameters = yaml.load(file_in, Loader=yaml.FullLoader)
            self.update_parameters(new_parameters)
            print("Parameters file loaded from: " + str(params_file_path[0]))
        except FileNotFoundError:
            print("You need to select a valid input file")

    def help_button_pressed(self):
        logging.debug("Help Button Pressed")
        h = "Auto-Stitch is used to automatically find the axis of rotation" \
            " in order to stitch pairs of images gathered in half-acquisition mode.\n\n"
        h += "The input directory must contain at least one directory named 'tomo' containing .tiff image files.\n\n"
        h += "The output directory, containing the stitched images," \
             " maintains the structure of the directory tree rooted at the input directory.\n\n"
        h += "If the experiment uses one set of flats/darks the" \
             " 'Use Common Set of Flats and Darks' checkbox must be selected." \
             " These will then be copied and stitched according to the axis of rotation of each z-view.\n\n"
        h += "If each z-view contains its own set of flats/darks then" \
             " auto_stitch will automatically use these for flat-field correction and stitching.\n\n"
        h += "Parameters can be saved to and loaded from .yaml files of the user's choice.\n\n"
        h += "If the dry run button is selected the program will find the axis values without stitching the images.\n\n"
        QMessageBox.information(self, "Help", h)

    def delete_button_pressed(self):
        logging.debug("Delete Output Directory Button Pressed")
        delete_dialog = QMessageBox.question(self, 'Quit', 'Are you sure you want to delete the output directory?',
                                             QMessageBox.Yes | QMessageBox.No)
        if delete_dialog == QMessageBox.Yes:
            try:
                print("Deleting: " + self.parameters['output_dir'] + " ...")
                shutil.rmtree(self.parameters['output_dir'])
                print("Deleted directory: " + self.parameters['output_dir'])
            except FileNotFoundError:
                print("Directory does not exist: " + self.parameters['output_dir'])

    def stitch_button_pressed(self):
        logging.debug("Stitch Button Pressed")
        self.auto_horizontal_stitch_funcs = AutoHorizontalStitchFunctions(self.parameters)
        self.auto_horizontal_stitch_funcs.run_horizontal_auto_stitch()

    def set_dry_run_checkbox(self):
        logging.debug("Dry Run Checkbox: " + str(self.dry_run_checkbox.isChecked()))
        self.parameters['dry_run'] = self.dry_run_checkbox.isChecked()

'''
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AutoHorizontalStitchGUI()
    sys.exit(app.exec_())
'''
