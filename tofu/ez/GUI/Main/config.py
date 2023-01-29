import os
import logging
from functools import partial

import numpy as np
from shutil import rmtree

from PyQt5.QtWidgets import (
    QMessageBox,
    QFileDialog,
    QCheckBox,
    QPushButton,
    QGridLayout,
    QLabel,
    QGroupBox,
    QLineEdit,
)
from PyQt5.QtCore import QCoreApplication, QTimer, pyqtSignal, Qt, QRegExp
from PyQt5.QtGui import QRegExpValidator
from tofu.ez.main import execute_reconstruction, clean_tmp_dirs
from tofu.ez.yaml_in_out import Yaml_IO
from tofu.ez.GUI.message_dialog import warning_message

import tofu.ez.params as parameters
from tofu.config import SECTIONS
from tofu.ez.params import EZVARS, MAP_TABLE


#TODO Get rid of the old args structure and store all parameters
# like tofu does
# try input validator like that
# reg_ex = QRegExp("[0-9]+.?[0-9]{,2}")
# input_validator = QRegExpValidator(reg_ex, self.inc_axis_entry)
# self.inc_axis_entry.setValidator(input_validator)

LOG = logging.getLogger(__name__)


class ConfigGroup(QGroupBox):
    """
    Setup and configuration settings
    """

    # Used to send signal to ezufo_launcher when settings are imported https://stackoverflow.com/questions/2970312/pyqt4-qtcore-pyqtsignal-object-has-no-attribute-connect
    signal_update_vals_from_params = pyqtSignal(dict)
    # Used to send signal when reconstruction is done
    signal_reco_done = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.setTitle("Input/output and misc settings")
        self.setStyleSheet("QGroupBox {color: purple;}")

        self.yaml_io = Yaml_IO()

        # Select input directory
        self.input_dir_select = QPushButton("Select input directory (or paste abs. path)")
        self.input_dir_select.setStyleSheet("background-color:lightgrey; font: 12pt;")

        self.input_dir_entry = QLineEdit()
        self.input_dir_entry.editingFinished.connect(self.set_input_dir)
        self.input_dir_select.pressed.connect(self.select_input_dir)

        # Save .params checkbox
        self.save_params_checkbox = QCheckBox("Save args in .params file")
        self.save_params_checkbox.stateChanged.connect(self.set_save_args)

        # Select output directory
        self.output_dir_select = QPushButton()
        self.output_dir_select.setText("Select output directory (or paste abs. path)")
        self.output_dir_select.setStyleSheet("background-color:lightgrey; font: 12pt;")

        self.output_dir_entry = QLineEdit()
        self.output_dir_entry.editingFinished.connect(self.set_output_dir)
        self.output_dir_select.pressed.connect(self.select_output_dir)

        # Save in separate files or in one huge tiff file
        self.bigtiff_checkbox = QCheckBox()
        self.bigtiff_checkbox.setText("Save slices in multipage tiffs")
        self.bigtiff_checkbox.setToolTip(
            "Will save images in bigtiff containers. \n"
            "Note that some temporary data is always saved in bigtiffs.\n"
            "Use bio-formats importer plugin for imagej or fiji to open the bigtiffs."
        )
        self.bigtiff_checkbox.stateChanged.connect(self.set_big_tiff)

        # Crop in the reconstruction plane
        self.preproc_checkbox = QCheckBox()
        self.preproc_checkbox.setText("Preprocess with a generic ufo-launch pipeline, f.i.")
        self.preproc_checkbox.setToolTip(
            "Selected ufo filters will be applied to each "
            "image before reconstruction begins. \n"
            'To print the list of filters use "ufo-query -l" command. \n'
            'Parameters of each filter can be seen with "ufo-query -p filtername".'
        )
        self.preproc_checkbox.stateChanged.connect(self.set_preproc)

        self.preproc_entry = QLineEdit()
        self.preproc_entry.editingFinished.connect(self.set_preproc_entry)

        # Names of directories with flats/darks/projections frames
        self.e_DIRTYP = ["darks", "flats", "tomo", "flats2"]
        self.dir_name_label = QLabel()
        self.dir_name_label.setText("Name of flats/darks/tomo subdirectories in each CT data set")
        self.darks_entry = QLineEdit()
        self.darks_entry.editingFinished.connect(self.set_darks)
        self.flats_entry = QLineEdit()
        self.flats_entry.editingFinished.connect(self.set_flats)
        self.tomo_entry = QLineEdit()
        self.tomo_entry.editingFinished.connect(self.set_tomo)
        self.flats2_entry = QLineEdit()
        self.flats2_entry.editingFinished.connect(self.set_flats2)

        # Select flats/darks/flats2 for use in multiple reconstructions
        self.use_common_flats_darks_checkbox = QCheckBox()
        self.use_common_flats_darks_checkbox.setText(
            "Use common flats/darks across multiple experiments"
        )
        self.use_common_flats_darks_checkbox.stateChanged.connect(self.set_flats_darks_checkbox)

        self.select_darks_button = QPushButton("Select path to darks (or paste abs. path)")
        self.select_darks_button.setToolTip("Background detector noise")
        self.select_darks_button.clicked.connect(self.select_darks_button_pressed)

        self.select_flats_button = QPushButton("Select path to flats (or paste abs. path)")
        self.select_flats_button.setToolTip("Images without sample in the beam")
        self.select_flats_button.clicked.connect(self.select_flats_button_pressed)

        self.select_flats2_button = QPushButton("Select path to flats2 (or paste abs. path)")
        self.select_flats2_button.setToolTip(
            "If selected, it will be assumed that flats were \n"
            "acquired before projections while flats2 after \n"
            "and interpolation will be used to compute intensity of flat image \n"
            "for each projection between flats and flats2"
        )
        self.select_flats2_button.clicked.connect(self.select_flats2_button_pressed)

        self.darks_absolute_entry = QLineEdit()
        self.darks_absolute_entry.setText("Absolute path to darks")
        self.darks_absolute_entry.editingFinished.connect(self.set_common_darks)

        self.flats_absolute_entry = QLineEdit()
        self.flats_absolute_entry.setText("Absolute path to flats")
        self.flats_absolute_entry.editingFinished.connect(self.set_common_flats)

        self.use_flats2_checkbox = QCheckBox("Use common flats2")
        self.use_flats2_checkbox.clicked.connect(self.set_use_flats2)

        self.flats2_absolute_entry = QLineEdit()
        self.flats2_absolute_entry.editingFinished.connect(self.set_common_flats2)
        self.flats2_absolute_entry.setText("Absolute path to flats2")

        # Select temporary directory
        self.temp_dir_select = QPushButton()
        self.temp_dir_select.setText("Select temporary directory (or paste abs. path)")
        self.temp_dir_select.setToolTip(
            "Temporary data will be saved there.\n"
            "note that the size of temporary data can exceed 300 GB in some cases."
        )
        self.temp_dir_select.pressed.connect(self.select_temp_dir)
        self.temp_dir_select.setStyleSheet("background-color:lightgrey; font: 12pt;")
        self.temp_dir_entry = QLineEdit()
        self.temp_dir_entry.editingFinished.connect(self.set_temp_dir)

        # Keep temp data selection
        self.keep_tmp_data_checkbox = QCheckBox()
        self.keep_tmp_data_checkbox.setText("Keep all temp data till the end of reconstruction")
        self.keep_tmp_data_checkbox.setToolTip(
            "Useful option to inspect how images change at each step"
        )
        self.keep_tmp_data_checkbox.stateChanged.connect(self.set_keep_tmp_data)

        # IMPORT SETTINGS FROM FILE
        self.open_settings_file = QPushButton()
        self.open_settings_file.setText("Import parameters from file")
        self.open_settings_file.setStyleSheet("background-color:lightgrey; font: 12pt;")
        self.open_settings_file.pressed.connect(self.import_settings_button_pressed)

        # EXPORT SETTINGS TO FILE
        self.save_settings_file = QPushButton()
        self.save_settings_file.setText("Export parameters to file")
        self.save_settings_file.setStyleSheet("background-color:lightgrey; font: 12pt;")
        self.save_settings_file.pressed.connect(self.export_settings_button_pressed)

        # QUIT
        self.quit_button = QPushButton()
        self.quit_button.setText("Quit")
        self.quit_button.setStyleSheet("background-color:lightgrey; font: 13pt; font-weight: bold;")
        self.quit_button.clicked.connect(self.quit_button_pressed)

        # HELP
        self.help_button = QPushButton()
        self.help_button.setText("Help")
        self.help_button.setStyleSheet("background-color:lightgrey; font: 13pt; font-weight: bold")
        self.help_button.clicked.connect(self.help_button_pressed)

        # DELETE
        self.delete_reco_dir_button = QPushButton()
        self.delete_reco_dir_button.setText("Delete reco dir")
        self.delete_reco_dir_button.setStyleSheet(
            "background-color:lightgrey; font: 13pt; font-weight: bold"
        )
        self.delete_reco_dir_button.clicked.connect(self.delete_button_pressed)

        # DRY RUN
        self.dry_run_button = QPushButton()
        self.dry_run_button.setText("Dry run")
        self.dry_run_button.setStyleSheet(
            "background-color:lightgrey; font: 13pt; font-weight: bold"
        )
        self.dry_run_button.clicked.connect(self.dryrun_button_pressed)

        # RECONSTRUCT
        self.reco_button = QPushButton()
        self.reco_button.setText("Reconstruct")
        self.reco_button.setStyleSheet(
            "background-color:lightgrey;color:royalblue; font: 14pt; font-weight: bold;"
        )
        self.reco_button.clicked.connect(self.reco_button_pressed)

        # OPEN IMAGE AFTER RECONSTRUCT
        self.open_image_after_reco_checkbox = QCheckBox()
        self.open_image_after_reco_checkbox.setText(
            "Load images and open viewer after reconstruction"
        )
        self.open_image_after_reco_checkbox.clicked.connect(self.set_open_image_after_reco)

        self.set_layout()

    def set_layout(self):
        """
        Sets the layout of buttons, labels, etc. for config group
        """
        layout = QGridLayout()

        checkbox_groupbox = QGroupBox()
        checkbox_layout = QGridLayout()
        checkbox_layout.addWidget(self.save_params_checkbox, 0, 0)
        checkbox_layout.addWidget(self.bigtiff_checkbox, 1, 0)
        checkbox_layout.addWidget(self.open_image_after_reco_checkbox, 2, 0)
        checkbox_layout.addWidget(self.keep_tmp_data_checkbox, 3, 0)
        checkbox_groupbox.setLayout(checkbox_layout)
        layout.addWidget(checkbox_groupbox, 0, 4, 4, 1)

        layout.addWidget(self.input_dir_select, 0, 0)
        layout.addWidget(self.input_dir_entry, 0, 1, 1, 3)
        layout.addWidget(self.output_dir_select, 1, 0)
        layout.addWidget(self.output_dir_entry, 1, 1, 1, 3)
        layout.addWidget(self.temp_dir_select, 2, 0)
        layout.addWidget(self.temp_dir_entry, 2, 1, 1, 3)
        layout.addWidget(self.preproc_checkbox, 3, 0)
        layout.addWidget(self.preproc_entry, 3, 1, 1, 3)

        fdt_groupbox = QGroupBox()
        fdt_layout = QGridLayout()
        fdt_layout.addWidget(self.dir_name_label, 0, 0)
        fdt_layout.addWidget(self.darks_entry, 0, 1)
        fdt_layout.addWidget(self.flats_entry, 0, 2)
        fdt_layout.addWidget(self.tomo_entry, 0, 3)
        fdt_layout.addWidget(self.flats2_entry, 0, 4)
        fdt_layout.addWidget(self.use_common_flats_darks_checkbox, 1, 0)
        fdt_layout.addWidget(self.select_darks_button, 1, 1)
        fdt_layout.addWidget(self.select_flats_button, 1, 2)
        fdt_layout.addWidget(self.select_flats2_button, 1, 4)
        fdt_layout.addWidget(self.darks_absolute_entry, 2, 1)
        fdt_layout.addWidget(self.flats_absolute_entry, 2, 2)
        fdt_layout.addWidget(self.use_flats2_checkbox, 2, 3, Qt.AlignRight)
        fdt_layout.addWidget(self.flats2_absolute_entry, 2, 4)
        fdt_groupbox.setLayout(fdt_layout)
        layout.addWidget(fdt_groupbox, 4, 0, 1, 5)

        layout.addWidget(self.open_settings_file, 5, 0, 1, 3)
        layout.addWidget(self.save_settings_file, 5, 3, 1, 2)
        layout.addWidget(self.quit_button, 6, 0)
        layout.addWidget(self.help_button, 6, 1)
        layout.addWidget(self.delete_reco_dir_button, 6, 2)
        layout.addWidget(self.dry_run_button, 6, 3)
        layout.addWidget(self.reco_button, 6, 4)

        self.setLayout(layout)

    def init_values(self):
        """
        Sets the initial default values of config group
        """
        # If we're on a computer with access to network
        indir = os.path.expanduser('~')#"/beamlinedata/BMIT/projects/"
        if os.path.isdir(indir):
            self.input_dir_entry.setText(indir)
            outdir = os.path.abspath(indir + "/rec")
            self.output_dir_entry.setText(outdir)
        
        self.init_dict_entries()
        
        self.preproc_checkbox.setChecked(EZVARS['inout']['preprocess']['value'])
        self.preproc_entry.setText(EZVARS['inout']['preprocess-command']['value'])
        self.darks_entry.setText(EZVARS['inout']['darks-dir']['value'])
        self.flats_entry.setText(EZVARS['inout']['flats-dir']['value'])
        self.tomo_entry.setText(EZVARS['inout']['tomo-dir']['value'])
        self.flats2_entry.setText(EZVARS['inout']['flats2-dir']['value'])        
        self.use_common_flats_darks_checkbox.setChecked(EZVARS['inout']['shared-flatsdarks']['value'])
        self.darks_absolute_entry.setText(EZVARS['inout']['path2-shared-darks']['value'])
        self.flats_absolute_entry.setText(EZVARS['inout']['path2-shared-flats']['value'])
        self.flats2_absolute_entry.setText(EZVARS['inout']['path2-shared-flats-after']['value'])
        self.temp_dir_entry.setText(os.path.join(os.path.expanduser('~'),"tmp-ezufo"))
        self.keep_tmp_data_checkbox.setChecked(EZVARS['inout']['keep-tmp']['value'])
        self.dry_run_button.setChecked(EZVARS['inout']['dryrun']['value'])
        self.open_image_after_reco_checkbox.setChecked(EZVARS['inout']['open-viewer']['value'])

        
    def set_values_from_params(self):
        """
        Updates displayed values for config group
        Called when .yaml file of params is loaded
        """
        self.input_dir_entry.setText(EZVARS['inout']['input-dir']['value'])
        self.save_params_checkbox.setChecked(EZVARS['inout']['save-params']['value'])
        self.output_dir_entry.setText(EZVARS['inout']['output-dir']['value'])
        self.bigtiff_checkbox.setChecked(EZVARS['inout']['bigtiff-output']['value'])
        self.preproc_checkbox.setChecked(EZVARS['inout']['preprocess']['value'])
        self.preproc_entry.setText(EZVARS['inout']['preprocess-command']['value'])
        self.darks_entry.setText(EZVARS['inout']['darks-dir']['value'])
        self.flats_entry.setText(EZVARS['inout']['flats-dir']['value'])
        self.tomo_entry.setText(EZVARS['inout']['tomo-dir']['value'])
        self.flats2_entry.setText(EZVARS['inout']['flats2-dir']['value'])
        self.temp_dir_entry.setText(EZVARS['inout']['tmp-dir']['value'])
        self.keep_tmp_data_checkbox.setChecked(EZVARS['inout']['keep-tmp']['value'])
        self.dry_run_button.setChecked(EZVARS['inout']['dryrun']['value'])
        self.open_image_after_reco_checkbox.setChecked(EZVARS['inout']['open-viewer']['value'])
        self.use_common_flats_darks_checkbox.setChecked(EZVARS['inout']['shared-flatsdarks']['value'])
        self.darks_absolute_entry.setText(EZVARS['inout']['path2-shared-darks']['value'])
        self.flats_absolute_entry.setText(EZVARS['inout']['path2-shared-flats']['value'])
        self.use_flats2_checkbox.setChecked(EZVARS['inout']['shared-flats-after']['value'])
        self.flats2_absolute_entry.setText(EZVARS['inout']['path2-shared-flats-after']['value'])

    def select_input_dir(self):
        """
        Saves directory specified by user in file-dialog for input tomographic data
        """
        dir_explore = QFileDialog(self)
        dir = dir_explore.getExistingDirectory(directory=self.input_dir_entry.text())
        self.input_dir_entry.setText(dir)
        EZVARS['inout']['input-dir']['value'] = dir

    def set_input_dir(self):
        LOG.debug(str(self.input_dir_entry.text()))
        EZVARS['inout']['input-dir']['value'] = str(self.input_dir_entry.text())

    def select_output_dir(self):
        dir_explore = QFileDialog(self)
        dir = dir_explore.getExistingDirectory(directory=self.output_dir_entry.text())
        self.output_dir_entry.setText(dir)
        EZVARS['inout']['output-dir']['value'] = dir

    def set_output_dir(self):
        LOG.debug(str(self.output_dir_entry.text()))
        EZVARS['inout']['output-dir']['value'] = str(self.output_dir_entry.text())

    def set_big_tiff(self):
        LOG.debug("Bigtiff: " + str(self.bigtiff_checkbox.isChecked()))
        EZVARS['inout']['bigtiff-output']['value'] = bool(self.bigtiff_checkbox.isChecked())

    def set_preproc(self):
        LOG.debug("Preproc: " + str(self.preproc_checkbox.isChecked()))
        EZVARS['inout']['preprocess']['value'] = bool(self.preproc_checkbox.isChecked())

    def set_preproc_entry(self):
        LOG.debug(self.preproc_entry.text())
        EZVARS['inout']['preprocess-command']['value'] = str(self.preproc_entry.text())

    def set_open_image_after_reco(self):
        LOG.debug(
            "Switch to Image Viewer After Reco: "
            + str(self.open_image_after_reco_checkbox.isChecked())
        )
        EZVARS['inout']['open-viewer']['value'] = bool(self.open_image_after_reco_checkbox.isChecked())

    def set_darks(self):
        LOG.debug(self.darks_entry.text())
        self.e_DIRTYP[0] = str(self.darks_entry.text())
        EZVARS['inout']['darks-dir']['value'] = str(self.darks_entry.text())

    def set_flats(self):
        LOG.debug(self.flats_entry.text())
        self.e_DIRTYP[1] = str(self.flats_entry.text())
        EZVARS['inout']['flats-dir']['value'] = str(self.flats_entry.text())

    def set_tomo(self):
        LOG.debug(self.tomo_entry.text())
        self.e_DIRTYP[2] = str(self.tomo_entry.text())
        EZVARS['inout']['tomo-dir']['value'] = str(self.tomo_entry.text())

    def set_flats2(self):
        LOG.debug(self.flats2_entry.text())
        self.e_DIRTYP[3] = str(self.flats2_entry.text())
        EZVARS['inout']['flats2-dir']['value'] = str(self.flats2_entry.text())

    def set_fdt_names(self):
        self.set_darks()
        self.set_flats()
        self.set_flats2()
        self.set_tomo()

    def set_flats_darks_checkbox(self):
        LOG.debug(
            "Use same flats/darks across multiple experiments: "
            + str(self.use_common_flats_darks_checkbox.isChecked())
        )
        EZVARS['inout']['shared-flatsdarks']['value'] = bool(
            self.use_common_flats_darks_checkbox.isChecked()
        )

    def select_darks_button_pressed(self):
        LOG.debug("Select path to darks pressed")
        dir_explore = QFileDialog(self)
        directory = dir_explore.getExistingDirectory(directory=EZVARS['inout']['input-dir']['value'])
        self.darks_absolute_entry.setText(directory)
        EZVARS['inout']['path2-shared-darks']['value'] = directory

    def select_flats_button_pressed(self):
        LOG.debug("Select path to flats pressed")
        dir_explore = QFileDialog(self)
        directory = dir_explore.getExistingDirectory(directory=EZVARS['inout']['input-dir']['value'])
        self.flats_absolute_entry.setText(directory)
        EZVARS['inout']['path2-shared-flats']['value'] = directory

    def select_flats2_button_pressed(self):
        LOG.debug("Select path to flats2 pressed")
        dir_explore = QFileDialog(self)
        directory = dir_explore.getExistingDirectory(directory=EZVARS['inout']['input-dir']['value'])
        self.flats2_absolute_entry.setText(directory)
        EZVARS['inout']['path2-shared-flats-after']['value'] = directory

    def set_common_darks(self):
        LOG.debug("Common darks path: " + str(self.darks_absolute_entry.text()))
        EZVARS['inout']['path2-shared-darks']['value'] = str(self.darks_absolute_entry.text())

    def set_common_flats(self):
        LOG.debug("Common flats path: " + str(self.flats_absolute_entry.text()))
        EZVARS['inout']['path2-shared-flats']['value'] = str(self.flats_absolute_entry.text())

    def set_use_flats2(self):
        LOG.debug("Use common flats2 checkbox: " + str(self.use_flats2_checkbox.isChecked()))
        EZVARS['inout']['shared-flats-after']['value'] = bool(self.use_flats2_checkbox.isChecked())

    def set_common_flats2(self):
        LOG.debug("Common flats2 path: " + str(self.flats2_absolute_entry.text()))
        EZVARS['inout']['path2-shared-flats-after']['value'] = str(self.flats2_absolute_entry.text())

    def select_temp_dir(self):
        dir_explore = QFileDialog(self)
        tmp_dir = dir_explore.getExistingDirectory(directory=self.temp_dir_entry.text())
        self.temp_dir_entry.setText(tmp_dir)
        EZVARS['inout']['tmp-dir']['value'] = tmp_dir

    def set_temp_dir(self):
        LOG.debug(str(self.temp_dir_entry.text()))
        EZVARS['inout']['tmp-dir']['value'] = str(self.temp_dir_entry.text())

    def set_keep_tmp_data(self):
        LOG.debug("Keep tmp: " + str(self.keep_tmp_data_checkbox.isChecked()))
        EZVARS['inout']['keep-tmp']['value'] = bool(self.keep_tmp_data_checkbox.isChecked())

    def quit_button_pressed(self):
        """
        Displays confirmation dialog and cleans temporary directories
        """
        LOG.debug("QUIT")
        reply = QMessageBox.question(
            self,
            "Quit",
            "Are you sure you want to quit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            # remove all directories with projections
            clean_tmp_dirs(EZVARS['inout']['tmp-dir']['value'], self.get_fdt_names())
            # remove axis-search dir too
            tmp = os.path.join(EZVARS['inout']['tmp-dir']['value'], 'axis-search')
            QCoreApplication.instance().quit()
        else:
            pass

    def help_button_pressed(self):
        """
        Displays pop-up help information
        """
        LOG.debug("HELP")
        h = "This utility provides an interface to the ufo-kit software package.\n"
        h += "Use it for batch processing and optimization of reconstruction parameters.\n"
        h += "It creates a list of paths to all CT directories in the _input_ directory.\n"
        h += "A CT directory is defined as directory with at least \n"
        h += "_flats_, _darks_, _tomo_, and, optionally, _flats2_ subdirectories, \n"
        h += "which are not empty and contain only *.tif files. Names of CT\n"
        h += "directories are compared with the directory tree in the _output_ directory.\n"
        h += (
            "(Note: relative directory tree in _input_ is preserved when writing results to the"
            " _output_.)\n"
        )
        h += (
            "Those CT sets will be reconstructed, whose names are not yet in the _output_"
            " directory."
        )
        h += "Program will create an array of ufo/tofu commands according to defined parameters \n"
        h += (
            "and then execute them sequentially. These commands can be also printed on the"
            " screen.\n"
        )
        h += "Note2: if you bin in preprocess the center of rotation will change a lot; \n"
        h += 'Note4: set to "flats" if "flats2" exist but you need to ignore them; \n'
        h += (
            "Created by Sergei Gasilov, BMIT CLS, Dec. 2018.\n Extended by Iain Emslie, Summer"
            " 2021."
        )
        QMessageBox.information(self, "Help", h)

    def delete_button_pressed(self):
        """
        Deletes the directory that contains reconstructed data
        """
        LOG.debug("DELETE")
        msg = "Delete directory with reconstructed data?"
        dialog = QMessageBox.warning(
            self, "Warning: data can be lost", msg, QMessageBox.Yes | QMessageBox.No
        )

        if dialog == QMessageBox.Yes:
            if os.path.exists(str(EZVARS['inout']['output-dir']['value'])):
                LOG.debug("YES")
                if EZVARS['inout']['output-dir']['value'] == EZVARS['inout']['input-dir']['value']:
                    LOG.debug("Cannot delete: output directory is the same as input")
                else:
                    try:
                        rmtree(EZVARS['inout']['output-dir']['value'])
                    except:
                        warning_message('Error while deleting directory')
                    LOG.debug("Directory with reconstructed data was removed")
            else:
                LOG.debug("Directory does not exist")
        else:
            LOG.debug("NO")

    def dryrun_button_pressed(self):
        """
        Sets the dry-run parameter for Tofu to True
        and calls reconstruction
        """
        LOG.debug("DRY")
        EZVARS['inout']['dryrun']['value'] = str(True)
        self.reco_button_pressed()


    def set_save_args(self):
        LOG.debug("Save args: " + str(self.save_params_checkbox.isChecked()))
        EZVARS['inout']['save-params']['value'] = bool(self.save_params_checkbox.isChecked())

    def export_settings_button_pressed(self):
        """
        Saves currently displayed GUI settings
        to an external .yaml file specified by user
        """
        LOG.debug("Save settings pressed")
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(
            self,
            "QFileDialog.getSaveFileName()",
            "",
            "YAML Files (*.yaml);; All Files (*)",
            options=options,
        )
        if fileName:
            LOG.debug("Export YAML Path: " + fileName)
        file_extension = os.path.splitext(fileName)
        if file_extension[-1] == "":
            fileName = fileName + ".yaml"
        # Create and write to YAML file based on given fileName
        self.yaml_io.write_yaml(fileName, parameters.params)

    def import_settings_button_pressed(self):
        """
        Loads external settings from .yaml file specified by user
        Signal is sent to enable updating of displayed GUI values
        """
        LOG.debug("Import settings pressed")
        options = QFileDialog.Options()
        filePath, _ = QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getOpenFileName()",
            "",
            "YAML Files (*.yaml);; All Files (*)",
            options=options,
        )
        if filePath:
            LOG.debug("Import YAML Path: " + filePath)
            yaml_data = self.yaml_io.read_yaml(filePath)
            parameters.params = dict(yaml_data)
            self.signal_update_vals_from_params.emit(parameters.params)

    def reco_button_pressed(self):
        """
        Gets the settings set by the user in the GUI
        These are then passed to execute_reconstruction
        """
        LOG.debug("RECO")
        self.set_fdt_names()
        self.set_common_darks()
        self.set_common_flats()
        self.set_common_flats2()
        self.set_big_tiff()
        self.set_input_dir()
        self.set_output_dir()
        self.set_temp_dir()
        self.set_preproc()
        self.set_preproc_entry()
        LOG.debug(parameters.params)
        run_reco = partial(self.run_reconstruction, parameters.params, batch_run=False)
        QTimer.singleShot(100, run_reco)
        #self.run_reconstruction(parameters.params, batch_run=False)
        
    def createMapFromParamsToDictEntry(self):
        """
        Creates a map from parameters to dictionary entry 
        (e.g. result['<parameter name>'] -> dictionary entry
        """
        result = {}
        for key in MAP_TABLE:
            if(len(key) == 4):
                #Note: Dictionary entries are automatically updated in the map as the program runs
                if(key[1] == 'ezvars' and key[2] in EZVARS and key[3] in EZVARS[key[2]]):
                    result[key[0]] = EZVARS[key[2]][key[3]]     #Updates as dictionary updates
                elif(key[1] == 'sections' and key[2] in SECTIONS and key[3] in SECTIONS[key[2]]):
                    result[key[0]] = SECTIONS[key[2]][key[3]] #Updates as dictionary updates
                else:
                    LOG.debug("Can't create dictionary entry: "+ key[1]+ "["+key[2]+"]"+"["+key[3]+"]"+": "+ key[0]
                              +".\n  Is the parameter spelled correctly?")
            else:
                LOG.debug("Key" + key + "in MAP_TABLE does not have exactly 4 elements.")
        return result
    
    def createMapFromParamsToDictKeys(self):
        """
        Creates a map from parameters to dictionary entry 
        (e.g. result['<parameter name>'] -> {dict name, key1 in dict, key2 in dict[key1]}
        """
        result = {}
        for key in MAP_TABLE:
            if(len(key) == 4):
                result[key[0]] = [key[1],[key[2],key[3]]]
            else:
                LOG.debug("Key" + key + "in MAP_TABLE does not have exactly 4 elements.")
        return result
        
    
    def reset_values_dicts(self):
        """
        Set all the values of dictionary entries to its default
        """
        ## TODO: Add to "import_settings_button_pressed"
        for key1 in EZVARS:
            for key2 in EZVARS[key1]:
                m = EZVARS[key1][key2]
                m['value'] = m['default']
                
        for key1 in SECTIONS:
            for key2 in SECTIONS[key1]:
                m = SECTIONS[key1][key2]
                m['value'] = m['default']
    
    def import_params_to_dicts(self, params):
        """
        Import parameter values into their corresponding dictionary entries
        """
        
        ## TODO: Add to "import_settings_button_pressed"
        # Note: This is a brute-force method to find a key, which should be acceptable for a 
        #   small number of parameters that is only updated when a file is imported
        mapToDictEntry = self.createMapFromParamsToDictEntry()
        for key in params.keys():
            m = mapToDictEntry[key]
            if(key in m):
                try:
                    m['value'] = m['type'](params[key])
                except:
                    raise InvalidInputError("Parameter \"" + params[key] + "\" cannot be converted to the type: " + m['type'])
            else:
                LOG.debug("No mapping to import parameter \'" + key + "\'.")
                
    def add_value_to_dict_entry(self, dict_entry, param_value_str):
        #LOG.debug(str(key), params[str(key)])
        #print(dict_entry, param_value_str, dict_entry['default'])
        if 'action' in dict_entry:
            # no 'type' can be defined in action entries
            dict_entry['value'] = bool(param_value_str)
        elif param_value_str == '':
            # takes default value if empty string
            dict_entry['value'] = dict_entry['type'](dict_entry['default'])
        else:
            dict_entry['value'] = dict_entry['type'](param_value_str)
        print(param_value_str, dict_entry['value'])
        
    def init_dict_entries(self):
        # Place default value in each setting
        for key1 in EZVARS.keys():
            for key2 in EZVARS[key1].keys():
                dict_entry = EZVARS[key1][key2]
                self.add_value_to_dict_entry(dict_entry, '') # Add default value
        
        for key1 in SECTIONS.keys():
            for key2 in SECTIONS[key1].keys():
                dict_entry = SECTIONS[key1][key2]
                self.add_value_to_dict_entry(dict_entry, '') # Add default value
        
    def update_params(self):
        """
        Update parameter values from their corresponding dictionary entries
        """
        # ##TODO: Add to "export_settings_button_pressed"
        # ##TODO: Consider updating the tuples to their string forms
        # mapToDictEntry = self.createMapFromParamsToDictEntry()
        # for key in params.keys():
        #     m = mapToDictEntry[key]
        #     if(key in m):
        #         params[key] =
        #         m['value'] = m['type'](params[key])
    

    def run_reconstruction(self, params, batch_run):
        try:
            self.validate_input()

            args = tk_args(EZVARS['inout']['input-dir']['value'],
                           EZVARS['inout']['tmp-dir']['value'],
                           EZVARS['inout']['output-dir']['value'],
                           EZVARS['inout']['bigtiff-output']['value'],
                           EZVARS['COR']['search-method']['value'],
                           EZVARS['COR']['search-interval']['value'],
                           EZVARS['COR']['search-row']['value'],
                           EZVARS['COR']['patch-size']['value'],
                           EZVARS['COR']['user-defined-ax']['value'],
                           EZVARS['COR']['user-defined-dax']['value'],
                           EZVARS['filters']['rm_spots']['value'],
                           SECTIONS['find-large-spots']['spot-threshold']['value'],
                           SECTIONS['find-large-spots']['gauss-sigma']['value'],
                           EZVARS['RR']['enable']['value'],
                           EZVARS['RR']['use-ufo']['value'],
                           EZVARS['RR']['ufo-2d']['value'],
                           EZVARS['RR']['sx']['value'],
                           EZVARS['RR']['sy']['value'],
                           EZVARS['RR']['spy-narrow-window']['value'],
                           EZVARS['RR']['spy-rm-wide']['value'],
                           EZVARS['RR']['spy-wide-window']['value'],
                           EZVARS['RR']['spy-wide-SNR']['value'],
                           SECTIONS['retrieve-phase']['enable']['value'],
                           SECTIONS['retrieve-phase']['energy']['value'],
                           SECTIONS['retrieve-phase']['pixel-size']['value'],
                           SECTIONS['retrieve-phase']['propagation-distance']['value'][0],  #(?) Not sure what to do with y-direction
                           SECTIONS['retrieve-phase']['regularization-rate']['value'],
                           EZVARS['inout']['input_ROI']['value'],
                           SECTIONS['reading']['y']['value'],
                           SECTIONS['reading']['height']['value'],
                           SECTIONS['reading']['y-step']['value'],
                           EZVARS['inout']['clip_hist']['value'],
                           params['main_region_bit_depth'],
                           params['main_region_histogram_min'],
                           params['main_region_histogram_max'],
                           EZVARS['inout']['preprocess']['value'],
                           EZVARS['inout']['preprocess-command']['value'],
                           params['main_region_rotate_volume_clock'],
                           EZVARS['inout']['output-ROI']['value'],
                           EZVARS['inout']['output-x']['value'],
                           EZVARS['inout']['output-width']['value'],
                           EZVARS['inout']['output-y']['value'],
                           EZVARS['inout']['output-height']['value'],
                           EZVARS['inout']['dryrun']['value'],
                           EZVARS['inout']['save-params']['value'],
                           EZVARS['inout']['keep-tmp']['value'],
                           params['advanced_ffc_sinFFC'],
                           params['advanced_ffc_method'],
                           params['advanced_ffc_eigen_pco_reps'],
                           params['advanced_ffc_eigen_pco_downsample'],
                           params['advanced_ffc_downsample'],
                           EZVARS['inout']['shared-flatsdarks']['value'],
                           EZVARS['inout']['path2-shared-darks']['value'],
                           EZVARS['inout']['path2-shared-flats']['value'],
                           EZVARS['inout']['shared-flats-after']['value'],
                           EZVARS['inout']['path2-shared-flats-after']['value'],
                           # NLMDN Parameters
                           params['advanced_nlmdn_apply_after_reco'],
                           params['advanced_nlmdn_input_dir'],
                           params['advanced_nlmdn_input_is_file'],
                           params['advanced_nlmdn_output_dir'],
                           params['advanced_nlmdn_save_bigtiff'],
                           params['advanced_nlmdn_sim_search_radius'],
                           params['advanced_nlmdn_patch_radius'],
                           params['advanced_nlmdn_smoothing_control'],
                           params['advanced_nlmdn_noise_std'],
                           params['advanced_nlmdn_window'],
                           params['advanced_nlmdn_fast'],
                           params['advanced_nlmdn_estimate_sigma'],
                           params['advanced_nlmdn_dry_run'],
                           # Advanced Parameters
                           params['advanced_advtofu_extended_settings'],
                           params['advanced_advtofu_lamino_angle'],
                           params['advanced_adv_tofu_z_axis_rotation'],
                           params['advanced_advtofu_center_position_z'],
                           params['advanced_advtofu_y_axis_rotation'],
                           params['advanced_advtofu_aux_ffc_dark_scale'],
                           params['advanced_advtofu_aux_ffc_flat_scale'],
                           params['advanced_optimize_verbose_console'],
                           params['advanced_optimize_slice_mem_coeff'],
                           params['advanced_optimize_num_gpus'],
                           params['advanced_optimize_slices_per_device']
                           )
        
            #################
            LOG.debug("Entering parameter values into dictionary entries...")
            
            # self.init_dict_entries()
            
            # Insert values of parameter files into dictionary entries
            map_param_to_dict_entries = self.createMapFromParamsToDictEntry()
            for p in params:
                dict_entry = map_param_to_dict_entries[str(p)]
                self.add_value_to_dict_entry(dict_entry, params[str(p)])
        
            ####################
            
            execute_reconstruction(args, self.get_fdt_names())
            if batch_run is False:
                msg = "Done. See output in terminal for details."
                QMessageBox.information(self, "Finished", msg)
                if not EZVARS['inout']['dryrun']['value']:
                    self.signal_reco_done.emit(params)
                EZVARS['inout']['dryrun']['value'] = bool(False)
        except InvalidInputError as err:
            msg = ""
            err_arg = err.args
            msg += err.args[0]
            QMessageBox.information(self, "Invalid Input Error", msg)

    # NEED TO DETERMINE VALID RANGES
    # ALSO CHECK TYPES SOMEHOW
    def validate_input(self):
        """
        Determines whether user-input values are valid
        """
        # Sigma: e_sig_hor
        # if int(EZVARS['RR']['sx']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: ufo ring-removal sigma horizontal")

        # Sigma: e_sig_ver
        # if int(EZVARS['RR']['sy']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: ufo ring-removal sigma vertical")

        # Window size: main_filters_ring_removal_sarepy_window_size
        # if int(EZVARS['RR']['spy-narrow-window']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: window size")

        # Wind: main_filters_ring_removal_sarepy_window
        # if int(EZVARS['RR']['spy-wide-window']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: wind")

        # SNR: main_filters_ring_removal_sarepy_SNR
        # if int(EZVARS['RR']['spy-wide-SNR']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: SNR")

        # Photon energy: main_pr_photon_energy
        # if float(SECTIONS['retrieve-phase']['energy']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Photon energy [keV]")

        # Pixel size: main_pr_pixel_size
        # if float(SECTIONS['retrieve-phase']['pixel-size']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Pixel size [micron]")

        # Sample detector distance: main_pr_detector_distance
        # Note: Can't restrict_value for tuples -> one value becomes two values (x,y)?
        # if float(SECTIONS['retrieve-phase']['propagation-distance']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Sample-detector distance [m]")

        # # Delta/beta ratio: main_pr_delta_beta_ratio
        # Note: Has diff comment?
        # if int(SECTIONS['retrieve-phase']['regularization-rate']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Delta/beta ratio: (try default if unsure)")

        # First row in projections: main_region_first_row
        # Note: diff comment
        # if int(SECTIONS['reading']['y']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: First row in projections")

        # Number of rows: main_region_number_rows
        # if int(SECTIONS['reading']['height']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Number of rows (ROI height)")

        # # Reconstruct every Nth row: main_region_nth_row
        # if int(SECTIONS['reading']['y-step']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Reconstruct every Nth row")

        # Can be negative when 16-bit selected
        # Min value: main_region_histogram_min
        #if float(parameters.params['main_region_histogram_min']) < 0:
        #    raise InvalidInputError("Value out of range for: Min value in 32-bit histogram")

        # # Max value: main_region_histogram_max
        # # Note: Didn't cap because it might also be negative for 16 bit
        # if float(parameters.params['main_region_histogram_max']) < 0:
        #     raise InvalidInputError("Value out of range for: Max value in 32-bit histogram")

        # # x: main_region_crop_x
        # if int(EZVARS['inout']['output-x']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Crop slices: x")

        # # width: main_region_crop_width
        # if int(EZVARS['inout']['output-width']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Crop slices: width")

        # # y: main_region_crop_y
        # if int(EZVARS['inout']['output-y']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Crop slices: y")

        # # height: main_region_crop_height
        # if int(EZVARS['inout']['output-height']['value']) < 0:
        #     raise InvalidInputError("Value out of range for: Crop slices: height")

        # if int(parameters.params['advanced_ffc_eigen_pco_reps']) < 0:
        #     raise InvalidInputError("Value out of range for: Flat Field Correction: Eigen PCO Repetitions")

        # if int(parameters.params['advanced_ffc_eigen_pco_downsample']) < 0:
        #     raise InvalidInputError("Value out of range for: Flat Field Correction: Eigen PCO Downsample")

        # if int(parameters.params['advanced_ffc_downsample']) < 0:
        #     raise InvalidInputError("Value out of range for: Flat Field Correction: Downsample")

        # Can be negative value
        # Optional: rotate volume: main_region_rotate_volume_clock
        #if float(parameters.params['main_region_rotate_volume_clock']) < 0:
        #    raise InvalidInputError("Value out of range for: Optional: rotate volume clock by [deg]")
        #TODO ADD CHECKING NLMDN SETTINGS
        #TODO ADD CHECKING FOR ADVANCED SETTINGS
        # '''
        # if int(parameters.params['e_adv_rotation_range']) < 0:
        #     raise InvalidInputError("Advanced: Rotation range must be greater than or equal to zero")

        # if float(parameters.params['advanced_advtofu_lamino_angle']) < 0 or float(parameters.params['advanced_advtofu_lamino_angle']) > 90:
        #     raise InvalidInputError("Advanced: Lamino angle must be a float between 0 and 90")

        # if float(parameters.params['advanced_optimize_slice_mem_coeff']) < 0 or float(parameters.params['advanced_optimize_slice_mem_coeff']) > 1:
        #     raise InvalidInputError("Advanced: Slice memory coefficient must be between 0 and 1")
        # '''

    def get_fdt_names(self):
        DIRTYP = []
        for i in self.e_DIRTYP:
            DIRTYP.append(i)
        LOG.debug("Result of get_fdt_names")
        LOG.debug(DIRTYP)
        return DIRTYP

class tk_args():
    def __init__(self, main_config_input_dir, main_config_temp_dir, main_config_output_dir, main_config_save_multipage_tiff,
                main_cor_axis_search_method, main_cor_axis_search_interval, main_cor_search_row_start,
                main_cor_recon_patch_size, main_cor_axis_column, main_cor_axis_increment_step,
                main_filters_remove_spots, main_filters_remove_spots_threshold, main_filters_remove_spots_blur_sigma,
                main_filters_ring_removal, main_filters_ring_removal_ufo_lpf, main_filters_ring_removal_ufo_lpf_1d_or_2d,
                main_filters_ring_removal_ufo_lpf_sigma_horizontal, main_filters_ring_removal_ufo_lpf_sigma_vertical,
                main_filters_ring_removal_sarepy_window_size, main_filters_ring_removal_sarepy_wide, main_filters_ring_removal_sarepy_window, main_filters_ring_removal_sarepy_SNR,
                main_pr_phase_retrieval, main_pr_photon_energy, main_pr_pixel_size, main_pr_detector_distance,
                main_pr_delta_beta_ratio, main_region_select_rows, main_region_first_row, main_region_number_rows, main_region_nth_row, main_region_clip_histogram, main_region_bit_depth, main_region_histogram_min, main_region_histogram_max,
                main_config_preprocess, main_config_preprocess_command, main_region_rotate_volume_clock, main_region_crop_slices, main_region_crop_x, main_region_crop_width, main_region_crop_y, main_region_crop_height,
                main_config_dry_run, main_config_save_params, main_config_keep_temp, advanced_ffc_sinFFC, advanced_ffc_method, advanced_ffc_eigen_pco_reps,
                advanced_ffc_eigen_pco_downsample, advanced_ffc_downsample, main_config_common_flats_darks,
                main_config_darks_path, main_config_flats_path, main_config_flats2_checkbox, main_config_flats2_path,
                advanced_nlmdn_apply_after_reco, advanced_nlmdn_input_dir, advanced_nlmdn_input_is_file, advanced_nlmdn_output_dir, advanced_nlmdn_save_bigtiff,
                advanced_nlmdn_sim_search_radius, advanced_nlmdn_patch_radius, advanced_nlmdn_smoothing_control, advanced_nlmdn_noise_std,
                advanced_nlmdn_window, advanced_nlmdn_fast, advanced_nlmdn_estimate_sigma, advanced_nlmdn_dry_run,
                advanced_advtofu_extended_settings,
                advanced_advtofu_lamino_angle, advanced_adv_tofu_z_axis_rotation, advanced_advtofu_center_position_z, advanced_advtofu_y_axis_rotation,
                advanced_advtofu_aux_ffc_dark_scale, advanced_advtofu_aux_ffc_flat_scale,
                advanced_optimize_verbose_console, advanced_optimize_slice_mem_coeff, advanced_optimize_num_gpus, advanced_optimize_slices_per_device):

        self.args={}
        # PATHS
        self.args['main_config_input_dir']=str(main_config_input_dir)               # EZVARS['inout']['input-dir']
        setattr(self,'main_config_input_dir',self.args['main_config_input_dir'])
        self.args['main_config_output_dir']=str(main_config_output_dir)             # EZVARS['inout']['output-dir']
        setattr(self,'main_config_output_dir',self.args['main_config_output_dir'])
        self.args['main_config_temp_dir']=str(main_config_temp_dir)                 # EZVARS['inout']['tmp-dir']
        setattr(self,'main_config_temp_dir',self.args['main_config_temp_dir'])
        self.args['main_config_save_multipage_tiff']=bool(main_config_save_multipage_tiff)  # EZVARS['inout']['bigtiff-output']
        setattr(self,'main_config_save_multipage_tiff',self.args['main_config_save_multipage_tiff'])
        # center of rotation parameters
        self.args['main_cor_axis_search_method']=int(main_cor_axis_search_method)           # EZVARS['COR']['search-method']
        setattr(self,'main_cor_axis_search_method',self.args['main_cor_axis_search_method'])
        self.args['main_cor_axis_search_interval']=str(main_cor_axis_search_interval)       # EZVARS['COR']['search-interval']
        setattr(self,'main_cor_axis_search_interval',self.args['main_cor_axis_search_interval'])
        self.args['main_cor_recon_patch_size']=int(main_cor_recon_patch_size)               # EZVARS['COR']['patch-size']
        setattr(self,'main_cor_recon_patch_size',self.args['main_cor_recon_patch_size'])
        self.args['main_cor_search_row_start']=int(main_cor_search_row_start)               # EZVARS['COR']['search-row']
        setattr(self,'main_cor_search_row_start',self.args['main_cor_search_row_start'])
        self.args['main_cor_axis_column']=float(main_cor_axis_column)                       # EZVARS['COR']['user-defined-ax']
        setattr(self,'main_cor_axis_column',self.args['main_cor_axis_column'])
        self.args['main_cor_axis_increment_step']=float(main_cor_axis_increment_step)       # EZVARS['COR']['user-defined-dax']
        setattr(self,'main_cor_axis_increment_step',self.args['main_cor_axis_increment_step'])
        #ring removal
        self.args['main_filters_remove_spots']=bool(main_filters_remove_spots)          # EZVARS['filters']['rm_spots']
        setattr(self,'main_filters_remove_spots',self.args['main_filters_remove_spots'])
        self.args['main_filters_remove_spots_threshold']=int(main_filters_remove_spots_threshold) # SECTIONS['find-large-spots']['spot-threshold']
        setattr(self,'main_filters_remove_spots_threshold', self.args['main_filters_remove_spots_threshold'])
        self.args['main_filters_remove_spots_blur_sigma']=int(main_filters_remove_spots_blur_sigma) # SECTIONS['find-large-spots']['gauss-sigma']
        setattr(self,'main_filters_remove_spots_blur_sigma',self.args['main_filters_remove_spots_blur_sigma'])
        self.args['main_filters_ring_removal']=bool(main_filters_ring_removal)                     #EZVARS['RR']['enable']
        setattr(self,'main_filters_ring_removal',self.args['main_filters_ring_removal'])
        self.args['main_filters_ring_removal_ufo_lpf'] = bool(main_filters_ring_removal_ufo_lpf)   #EZVARS['RR']['use-ufo']
        setattr(self, 'main_filters_ring_removal_ufo_lpf', self.args['main_filters_ring_removal_ufo_lpf'])
        self.args['main_filters_ring_removal_ufo_lpf_1d_or_2d'] = bool(main_filters_ring_removal_ufo_lpf_1d_or_2d) #EZVARS['RR']['ufo-2d']
        setattr(self, 'main_filters_ring_removal_ufo_lpf_1d_or_2d', self.args['main_filters_ring_removal_ufo_lpf_1d_or_2d'])
        self.args['main_filters_ring_removal_ufo_lpf_sigma_horizontal'] = int(main_filters_ring_removal_ufo_lpf_sigma_horizontal) #EZVARS['RR']['sx']
        setattr(self,'main_filters_ring_removal_ufo_lpf_sigma_horizontal',self.args['main_filters_ring_removal_ufo_lpf_sigma_horizontal'])
        self.args['main_filters_ring_removal_ufo_lpf_sigma_vertical'] = int(main_filters_ring_removal_ufo_lpf_sigma_vertical)   #EZVARS['RR']['sy']
        setattr(self, 'main_filters_ring_removal_ufo_lpf_sigma_vertical', self.args['main_filters_ring_removal_ufo_lpf_sigma_vertical'])
        self.args['main_filters_ring_removal_sarepy_window_size'] = int(main_filters_ring_removal_sarepy_window_size) #EZVARS['RR']['spy-narrow-window']
        setattr(self, 'main_filters_ring_removal_sarepy_window_size', self.args['main_filters_ring_removal_sarepy_window_size'])
        self.args['main_filters_ring_removal_sarepy_wide'] = bool(main_filters_ring_removal_sarepy_wide) #EZVARS['RR']['spy-rm-wide']
        setattr(self, 'main_filters_ring_removal_sarepy_wide', self.args['main_filters_ring_removal_sarepy_wide'])
        self.args['main_filters_ring_removal_sarepy_window'] = int(main_filters_ring_removal_sarepy_window) #EZVARS['RR']['spy-wide-window']
        setattr(self, 'main_filters_ring_removal_sarepy_window', self.args['main_filters_ring_removal_sarepy_window'])
        self.args['main_filters_ring_removal_sarepy_SNR'] = int(main_filters_ring_removal_sarepy_SNR) #EZVARS['RR']['spy-wide-SNR']
        setattr(self, 'main_filters_ring_removal_sarepy_SNR', self.args['main_filters_ring_removal_sarepy_SNR'])
        # phase retrieval
        self.args['main_pr_phase_retrieval'] = bool(main_pr_phase_retrieval)       #SECTIONS['retrieve-phase']['enable']
        setattr(self, 'main_pr_phase_retrieval', self.args['main_pr_phase_retrieval'])
        self.args['main_pr_photon_energy']=float(main_pr_photon_energy)             #SECTIONS['retrieve-phase']['energy']
        setattr(self,'main_pr_photon_energy',self.args['main_pr_photon_energy'])
        self.args['main_pr_pixel_size']=float(main_pr_pixel_size)*1e-6              #SECTIONS['retrieve-phase']['pixel-size']
        setattr(self,'main_pr_pixel_size',self.args['main_pr_pixel_size'])
        self.args['main_pr_detector_distance']=float(main_pr_detector_distance)     #SECTIONS['retrieve-phase']['propagation-distance']
        setattr(self,'main_pr_detector_distance',self.args['main_pr_detector_distance'])
        self.args['main_pr_delta_beta_ratio']=np.log10(float(main_pr_delta_beta_ratio))  #SECTIONS['retrieve-phase']['regularization-rate']
        setattr(self,'main_pr_delta_beta_ratio',self.args['main_pr_delta_beta_ratio'])   # apply log10 to the input which is delta/beta
        # Crop vertically
        self.args['main_region_select_rows']=bool(main_region_select_rows)              #EZVARS['inout']['input_ROI']
        setattr(self,'main_region_select_rows',self.args['main_region_select_rows'])
        self.args['main_region_first_row']=int(main_region_first_row)                   #SECTIONS['reading']['y']
        setattr(self,'main_region_first_row',self.args['main_region_first_row'])
        self.args['main_region_number_rows']=int(main_region_number_rows)               #SECTIONS['reading']['height']
        setattr(self,'main_region_number_rows',self.args['main_region_number_rows'])
        self.args['main_region_nth_row']=int(main_region_nth_row)                       #SECTIONS['reading']['y-step']
        setattr(self,'main_region_nth_row',self.args['main_region_nth_row'])
        # conv to 8 bit
        self.args['main_region_clip_histogram']=bool(main_region_clip_histogram)        #EZVARS['inout']['clip_hist']
        setattr(self,'main_region_clip_histogram',self.args['main_region_clip_histogram'])
        self.args['main_region_bit_depth']=int(main_region_bit_depth)                   #SECTIONS['general']['output-bitdepth']
        setattr(self,'main_region_bit_depth',self.args['main_region_bit_depth'])
        self.args['main_region_histogram_min']=float(main_region_histogram_min)         #SECTIONS['general']['output-minimum']
        setattr(self,'main_region_histogram_min',self.args['main_region_histogram_min'])
        self.args['main_region_histogram_max']=float(main_region_histogram_max)             #SECTIONS['general']['output-maximum']
        setattr(self,'main_region_histogram_max',self.args['main_region_histogram_max'])
        # preprocessing attributes
        self.args['main_config_preprocess']=bool(main_config_preprocess)             #EZVARS['inout']['preprocess']
        setattr(self,'main_config_preprocess',self.args['main_config_preprocess'])
        self.args['main_config_preprocess_command']=main_config_preprocess_command     #EZVARS['inout']['preprocess-command']
        setattr(self,'main_config_preprocess_command',self.args['main_config_preprocess_command'])
        # ROI in slice
        self.args['main_region_crop_slices']=bool(main_region_crop_slices)              #EZVARS['inout']['output-ROI']
        setattr(self,'main_region_crop_slices',self.args['main_region_crop_slices'])
        self.args['main_region_crop_x']=int(main_region_crop_x)                         #EZVARS['inout']['output-x']
        setattr(self,'main_region_crop_x',self.args['main_region_crop_x'])
        self.args['main_region_crop_width']=int(main_region_crop_width)                 #EZVARS['inout']['output-width']
        setattr(self,'main_region_crop_width',self.args['main_region_crop_width'])
        self.args['main_region_crop_y']=int(main_region_crop_y)                         #EZVARS['inout']['output-y']
        setattr(self,'main_region_crop_y',self.args['main_region_crop_y'])
        self.args['main_region_crop_height']=int(main_region_crop_height)               #EZVARS['inout']['output-height']
        setattr(self,'main_region_crop_height',self.args['main_region_crop_height'])
        # Optional FBP params
        self.args['main_region_rotate_volume_clock']= float(main_region_rotate_volume_clock)   #SECTIONS['general-reconstruction']['volume-angle-z']
        setattr(self,'main_region_rotate_volume_clock',self.args['main_region_rotate_volume_clock'])  #
        # misc settings
        self.args['main_config_dry_run']=bool(main_config_dry_run)    #EZVARS['inout']['dryrun']
        setattr(self,'main_config_dry_run',self.args['main_config_dry_run'])
        self.args['main_config_save_params']=bool(main_config_save_params)      #EZVARS['inout']['save-params']
        setattr(self,'main_config_save_params',self.args['main_config_save_params'])
        self.args['main_config_keep_temp']=bool(main_config_keep_temp)          #EZVARS['inout']['keep-tmp']
        setattr(self,'main_config_keep_temp',self.args['main_config_keep_temp'])
        #sinFFC settings
        self.args['advanced_ffc_sinFFC']=bool(advanced_ffc_sinFFC)          #EZVARS['flat-correction']['smart-ffc']
        setattr(self,'advanced_ffc_sinFFC', self.args['advanced_ffc_sinFFC'])
        self.args['advanced_ffc_method'] = str(advanced_ffc_method)         #EZVARS['flat-correction']['smart-ffc-method']
        setattr(self, 'advanced_ffc_method', self.args['advanced_ffc_method'])
        self.args['advanced_ffc_eigen_pco_reps']=int(advanced_ffc_eigen_pco_reps)  #EZVARS['flat-correction']['eigen-pco-reps']
        setattr(self, 'advanced_ffc_eigen_pco_reps', self.args['advanced_ffc_eigen_pco_reps'])
        self.args['advanced_ffc_eigen_pco_downsample'] = int(advanced_ffc_eigen_pco_downsample)  #EZVARS['flat-correction']['eigen-pco-downsample']
        setattr(self, 'advanced_ffc_eigen_pco_downsample', self.args['advanced_ffc_eigen_pco_downsample'])
        self.args['advanced_ffc_downsample'] = int(advanced_ffc_downsample)   #EZVARS['flat-correction']['downsample']
        setattr(self, 'advanced_ffc_downsample', self.args['advanced_ffc_downsample'])
        #Settings for using flats/darks across multiple experiments
        self.args['main_config_common_flats_darks'] = bool(main_config_common_flats_darks) #EZVARS['inout']['shared-flatsdarks']
        setattr(self, 'main_config_common_flats_darks', self.args['main_config_common_flats_darks'])
        self.args['main_config_darks_path'] = str(main_config_darks_path)  #EZVARS['inout']['path2-shared-darks']
        setattr(self, 'main_config_darks_path', self.args['main_config_darks_path'])
        self.args['main_config_flats_path'] = str(main_config_flats_path)   #EZVARS['inout']['path2-shared-flats']
        setattr(self, 'main_config_flats_path', self.args['main_config_flats_path'])
        self.args['main_config_flats2_checkbox'] = bool(main_config_flats2_checkbox)  #EZVARS['inout']['shared-flats-after']
        setattr(self, 'main_config_flats2_checkbox', self.args['main_config_flats2_checkbox'])
        self.args['main_config_flats2_path'] = str(main_config_flats2_path)    #EZVARS['inout']['path2-shared-flats-after']
        setattr(self, 'main_config_flats2_path', self.args['main_config_flats2_path'])
        #NLMDN Settings
        self.args['advanced_nlmdn_apply_after_reco'] = bool(advanced_nlmdn_apply_after_reco) #EZVARS['nlmdn']['do-after-reco']
        setattr(self, 'advanced_nlmdn_apply_after_reco', self.args['advanced_nlmdn_apply_after_reco'])
        self.args['advanced_nlmdn_input_dir'] = str(advanced_nlmdn_input_dir)     #EZVARS['nlmdn']['input-dir']
        setattr(self, 'advanced_nlmdn_input_dir', self.args['advanced_nlmdn_input_dir'])
        self.args['advanced_nlmdn_input_is_file'] = bool(advanced_nlmdn_input_is_file)  #EZVARS['nlmdn']['input-is-1file']
        setattr(self, 'advanced_nlmdn_input_is_file', self.args['advanced_nlmdn_input_is_file'])
        self.args['advanced_nlmdn_output_dir'] = str(advanced_nlmdn_output_dir)  #EZVARS['nlmdn']['output_pattern']
        setattr(self, 'advanced_nlmdn_output_dir', self.args['advanced_nlmdn_output_dir'])
        self.args['advanced_nlmdn_save_bigtiff'] = bool(advanced_nlmdn_save_bigtiff)  #EZVARS['nlmdn']['bigtiff_output']
        setattr(self, 'advanced_nlmdn_save_bigtiff', self.args['advanced_nlmdn_save_bigtiff'])
        self.args['advanced_nlmdn_sim_search_radius'] = str(advanced_nlmdn_sim_search_radius) #EZVARS['nlmdn']['search-radius']
        setattr(self, 'advanced_nlmdn_sim_search_radius', self.args['advanced_nlmdn_sim_search_radius']) #positive integer
        self.args['advanced_nlmdn_patch_radius'] = str(advanced_nlmdn_patch_radius)  #EZVARS['nlmdn']['patch-radius']
        setattr(self, 'advanced_nlmdn_patch_radius', self.args['advanced_nlmdn_patch_radius'])
        self.args['advanced_nlmdn_smoothing_control'] = str(advanced_nlmdn_smoothing_control)  #EZVARS['nlmdn']['h']
        setattr(self, 'advanced_nlmdn_smoothing_control', self.args['advanced_nlmdn_smoothing_control'])
        self.args['advanced_nlmdn_noise_std'] = str(advanced_nlmdn_noise_std)  #EZVARS['nlmdn']['sigma']
        setattr(self, 'advanced_nlmdn_noise_std', self.args['advanced_nlmdn_noise_std'])
        self.args['advanced_nlmdn_window'] = str(advanced_nlmdn_window)  #EZVARS['nlmdn']['window']
        setattr(self, 'advanced_nlmdn_window', self.args['advanced_nlmdn_window'])
        self.args['advanced_nlmdn_fast'] = bool(advanced_nlmdn_fast)  #EZVARS['nlmdn']['fast']
        setattr(self, 'advanced_nlmdn_fast', self.args['advanced_nlmdn_fast'])
        self.args['advanced_nlmdn_estimate_sigma'] = bool(advanced_nlmdn_estimate_sigma) #EZVARS['nlmdn']['estimate-sigma']
        setattr(self, 'advanced_nlmdn_estimate_sigma', self.args['advanced_nlmdn_estimate_sigma'])
        self.args['advanced_nlmdn_dry_run'] = bool(advanced_nlmdn_dry_run)   #EZVARS['nlmdn']['dryrun']
        setattr(self, 'advanced_nlmdn_dry_run', self.args['advanced_nlmdn_dry_run'])
        #Advanced Settings
        self.args['advanced_advtofu_extended_settings'] = bool(advanced_advtofu_extended_settings)  #EZVARS['advanced']['more-reco-params']
        setattr(self, 'advanced_advtofu_extended_settings', self.args['advanced_advtofu_extended_settings'])
        self.args['advanced_advtofu_lamino_angle'] = str(advanced_advtofu_lamino_angle)    #SECTIONS['general-reconstruction']['axis-angle-x']
        setattr(self, 'advanced_advtofu_lamino_angle', self.args['advanced_advtofu_lamino_angle'])
        self.args['advanced_adv_tofu_z_axis_rotation'] = str(advanced_adv_tofu_z_axis_rotation) #SECTIONS['general-reconstruction']['overall-angle']
        setattr(self, 'advanced_adv_tofu_z_axis_rotation', self.args['advanced_adv_tofu_z_axis_rotation'])
        self.args['advanced_advtofu_center_position_z'] = str(advanced_advtofu_center_position_z) #SECTIONS['general-reconstruction']['center-position-z']
        setattr(self, 'advanced_advtofu_center_position_z', self.args['advanced_advtofu_center_position_z'])
        self.args['advanced_advtofu_y_axis_rotation'] = str(advanced_advtofu_y_axis_rotation)   #SECTIONS['general-reconstruction']['axis-angle-y']
        setattr(self, 'advanced_advtofu_y_axis_rotation', self.args['advanced_advtofu_y_axis_rotation'])
        self.args['advanced_advtofu_aux_ffc_dark_scale'] = str(advanced_advtofu_aux_ffc_dark_scale) #SECTIONS['flat-correction']['dark-scale']
        setattr(self, 'advanced_advtofu_aux_ffc_dark_scale', self.args['advanced_advtofu_aux_ffc_dark_scale'])
        self.args['advanced_advtofu_aux_ffc_flat_scale'] = str(advanced_advtofu_aux_ffc_flat_scale)   #SECTIONS['flat-correction']['flat-scale']
        setattr(self, 'advanced_advtofu_aux_ffc_flat_scale', self.args['advanced_advtofu_aux_ffc_flat_scale'])
        # SECTIONS['sinos']['pass-size'] must be added to RR groupbox
        #Optimization
        self.args['advanced_optimize_verbose_console'] = bool(advanced_optimize_verbose_console) #SECTIONS['general']['verbose']
        setattr(self, 'advanced_optimize_verbose_console', self.args['advanced_optimize_verbose_console'])
        self.args['advanced_optimize_slice_mem_coeff'] = str(advanced_optimize_slice_mem_coeff) #SECTIONS['general-reconstruction']['slice-memory-coeff']
        setattr(self, 'advanced_optimize_slice_mem_coeff', self.args['advanced_optimize_slice_mem_coeff'])
        self.args['advanced_optimize_num_gpus'] = str(advanced_optimize_num_gpus)  #SECTIONS['general-reconstruction']['data-splitting-policy']
        setattr(self, 'advanced_optimize_num_gpus', self.args['advanced_optimize_num_gpus'])  # replace by 'data-splitting-policy' !!
        self.args['advanced_optimize_slices_per_device'] = str(advanced_optimize_slices_per_device)  # 'num-gpu-threads' ??
        setattr(self, 'advanced_optimize_slices_per_device', self.args['advanced_optimize_slices_per_device'])

        LOG.debug("Contents of arg dict: ")
        LOG.debug(self.args.items())


class InvalidInputError(Exception):
    """
    Error to be raised when input values from GUI are out of range or invalid
    """
