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
from PyQt5.QtCore import QCoreApplication, QTimer, pyqtSignal, Qt
from tofu.ez.main import execute_reconstruction, clean_tmp_dirs
from tofu.ez.yaml_in_out import Yaml_IO
from tofu.ez.GUI.message_dialog import warning_message

import tofu.ez.params as parameters # NEED UPDATE
from tofu.ez.params import EZVARS, MAP_TABLE
from tofu.config import SECTIONS
from tofu.util import add_value_to_dict_entry, reverse_tupleize
import argparse

LOG = logging.getLogger(__name__)

class ConfigGroup(QGroupBox):
    """
    Setup and configuration settings
    """

    # Used to send signal to ezufo_launcher when settings are imported https://stackoverflow.com/questions/2970312/pyqt4-qtcore-pyqtsignal-object-has-no-attribute-connect
    signal_update_vals_from_params = pyqtSignal()
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

    def load_values(self):
        """
        Updates displayed values for config group
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
        self.set_input_dir()

    def set_input_dir(self):
        LOG.debug(str(self.input_dir_entry.text()))
        dict_entry = EZVARS['inout']['input-dir']
        dir = self.input_dir_entry.text().strip()
        add_value_to_dict_entry(dict_entry, dir)
        self.input_dir_entry.setText(dir)

    def select_output_dir(self):
        dir_explore = QFileDialog(self)
        dir = dir_explore.getExistingDirectory(directory=self.output_dir_entry.text())
        self.output_dir_entry.setText(dir)
        self.set_output_dir()

    def set_output_dir(self):
        LOG.debug(str(self.output_dir_entry.text()))
        dict_entry = EZVARS['inout']['output-dir']
        dir = self.output_dir_entry.text().strip()
        add_value_to_dict_entry(dict_entry, dir)
        self.output_dir_entry.setText(dir)

    def set_big_tiff(self):
        LOG.debug("Bigtiff: " + str(self.bigtiff_checkbox.isChecked()))
        dict_entry = EZVARS['inout']['bigtiff-output']
        add_value_to_dict_entry(dict_entry, self.bigtiff_checkbox.isChecked())

    def set_preproc(self):
        LOG.debug("Preproc: " + str(self.preproc_checkbox.isChecked()))
        dict_entry = EZVARS['inout']['preprocess']
        add_value_to_dict_entry(dict_entry, self.preproc_checkbox.isChecked())

    def set_preproc_entry(self):
        LOG.debug(self.preproc_entry.text())
        dict_entry = EZVARS['inout']['preprocess-command']
        text  = self.preproc_entry.text().strip()
        add_value_to_dict_entry(dict_entry, text)
        self.preproc_entry.setText(text)

    def set_open_image_after_reco(self):
        LOG.debug(
            "Switch to Image Viewer After Reco: "
            + str(self.open_image_after_reco_checkbox.isChecked())
        )
        dict_entry = EZVARS['inout']['open-viewer']
        add_value_to_dict_entry(dict_entry, self.open_image_after_reco_checkbox.isChecked())

    def set_darks(self):
        LOG.debug(self.darks_entry.text())
        self.e_DIRTYP[0] = str(self.darks_entry.text())
        dict_entry = EZVARS['inout']['darks-dir']
        dir = self.darks_entry.text().strip()
        add_value_to_dict_entry(dict_entry, dir)
        self.darks_entry.setText(dir)

    def set_flats(self):
        LOG.debug(self.flats_entry.text())
        self.e_DIRTYP[1] = str(self.flats_entry.text())
        dict_entry = EZVARS['inout']['flats-dir']
        dir = self.flats_entry.text().strip()
        add_value_to_dict_entry(dict_entry, dir)
        self.flats_entry.setText(dir)

    def set_tomo(self):
        LOG.debug(self.tomo_entry.text())
        self.e_DIRTYP[2] = str(self.tomo_entry.text())
        dict_entry = EZVARS['inout']['tomo-dir']
        dir = self.tomo_entry.text().strip()
        add_value_to_dict_entry(dict_entry, dir)
        self.tomo_entry.setText(dir)

    def set_flats2(self):
        LOG.debug(self.flats2_entry.text())
        self.e_DIRTYP[3] = str(self.flats2_entry.text())
        dict_entry = EZVARS['inout']['flats2-dir']
        dir = self.flats2_entry.text().strip()
        add_value_to_dict_entry(dict_entry, dir)
        self.flats2_entry.setText(dir)

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
        dict_entry = EZVARS['inout']['shared-flatsdarks']
        add_value_to_dict_entry(dict_entry, self.use_common_flats_darks_checkbox.isChecked())

    def select_darks_button_pressed(self):
        LOG.debug("Select path to darks pressed")
        dir_explore = QFileDialog(self)
        directory = dir_explore.getExistingDirectory(directory=EZVARS['inout']['input-dir']['value'])
        self.darks_absolute_entry.setText(directory)
        self.set_common_darks()

    def select_flats_button_pressed(self):
        LOG.debug("Select path to flats pressed")
        dir_explore = QFileDialog(self)
        directory = dir_explore.getExistingDirectory(directory=EZVARS['inout']['input-dir']['value'])
        self.flats_absolute_entry.setText(directory)
        self.set_common_flats()

    def select_flats2_button_pressed(self):
        LOG.debug("Select path to flats2 pressed")
        dir_explore = QFileDialog(self)
        directory = dir_explore.getExistingDirectory(directory=EZVARS['inout']['input-dir']['value'])
        self.flats2_absolute_entry.setText(directory)
        self.set_common_flats2()

    def set_common_darks(self):
        LOG.debug("Common darks path: " + str(self.darks_absolute_entry.text()))
        dict_entry = EZVARS['inout']['path2-shared-darks']
        text = self.darks_absolute_entry.text().strip()
        add_value_to_dict_entry(dict_entry, text)
        self.darks_absolute_entry.setText(text)

    def set_common_flats(self):
        LOG.debug("Common flats path: " + str(self.flats_absolute_entry.text()))
        dict_entry = EZVARS['inout']['path2-shared-flats']
        text = self.flats_absolute_entry.text().strip()
        add_value_to_dict_entry(dict_entry, text)
        self.flats_absolute_entry.setText(text)

    def set_use_flats2(self):
        LOG.debug("Use common flats2 checkbox: " + str(self.use_flats2_checkbox.isChecked()))
        dict_entry = EZVARS['inout']['shared-flats-after']
        text = self.use_flats2_checkbox.text().strip()
        add_value_to_dict_entry(dict_entry, text)
        self.use_flats2_checkbox.setText(text)

    def set_common_flats2(self):
        LOG.debug("Common flats2 path: " + str(self.flats2_absolute_entry.text()))
        dict_entry = EZVARS['inout']['path2-shared-flats-after']
        text = self.flats2_absolute_entry.text().strip()
        add_value_to_dict_entry(dict_entry, text)
        self.flats2_absolute_entry.setText(text)

    def select_temp_dir(self):
        dir_explore = QFileDialog(self)
        tmp_dir = dir_explore.getExistingDirectory(directory=self.temp_dir_entry.text())
        self.temp_dir_entry.setText(tmp_dir)
        self.set_temp_dir()

    def set_temp_dir(self):
        LOG.debug(str(self.temp_dir_entry.text()))
        dict_entry = EZVARS['inout']['tmp-dir']
        text = self.temp_dir_entry.text().strip()
        add_value_to_dict_entry(dict_entry, text)
        self.temp_dir_entry.setText(text)

    def set_keep_tmp_data(self):
        LOG.debug("Keep tmp: " + str(self.keep_tmp_data_checkbox.isChecked()))
        dict_entry = EZVARS['inout']['keep-tmp']
        add_value_to_dict_entry(dict_entry, self.keep_tmp_data_checkbox.isChecked())

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
        # self.yaml_io.write_yaml(fileName, parameters.params)
        self.export_values(fileName)

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
            self.import_values(filePath)
            self.signal_update_vals_from_params.emit()

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
        #LOG.debug(parameters.params)
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
    
    def extract_values_from_dict(self, dict):
        new_dict = {}
        for key1 in dict.keys():
            new_dict[key1] = {}
            for key2 in dict[key1].keys():
                dict_entry = dict[key1][key2]
                if 'value' in dict_entry:
                    new_dict[key1][key2] = {}
                    value_type = type(dict_entry['value'])
                    if value_type is list or value_type is tuple:
                        new_dict[key1][key2]['value'] = str(reverse_tupleize()(dict_entry['value']))
                    else:                      
                        new_dict[key1][key2]['value'] = dict_entry['value']
        return new_dict                   
    
    def import_values_from_dict(self, dict, imported_dict):
        for key1 in imported_dict.keys():
            for key2 in imported_dict[key1].keys():
                print(key1, key2, imported_dict[key1][key2]['value'], type(imported_dict[key1][key2]['value']))
                add_value_to_dict_entry(dict[key1][key2],imported_dict[key1][key2]['value'])
    
    def export_values(self, filePath):
        combined_dict = {}
        combined_dict['sections'] = self.extract_values_from_dict(SECTIONS)
        combined_dict['ezvars'] = self.extract_values_from_dict(EZVARS)
        self.yaml_io.write_yaml(filePath, combined_dict)
        
    def import_values(self, filePath):
        yaml_data = dict(self.yaml_io.read_yaml(filePath))
        self.import_values_from_dict(EZVARS,yaml_data['ezvars'])
        self.import_values_from_dict(SECTIONS,yaml_data['sections'])
        print(dict(yaml_data))
    
    def import_values_from_params(self, params):
        """
        Import parameter values into their corresponding dictionary entries
        """             
        LOG.debug("Entering parameter values into dictionary entries")
        map_param_to_dict_entries = self.createMapFromParamsToDictEntry()
        for p in params:
            dict_entry = map_param_to_dict_entries[str(p)]
            add_value_to_dict_entry(dict_entry, params[str(p)])

    def run_reconstruction(self, params, batch_run):
        try:            
            execute_reconstruction(self.get_fdt_names())
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

    def get_fdt_names(self):
        DIRTYP = []
        for i in self.e_DIRTYP:
            DIRTYP.append(i)
        LOG.debug("Result of get_fdt_names")
        LOG.debug(DIRTYP)
        return DIRTYP

class InvalidInputError(Exception):
    """
    Error to be raised when input values from GUI are out of range or invalid
    """
