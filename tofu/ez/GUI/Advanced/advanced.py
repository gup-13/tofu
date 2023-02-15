import logging
from PyQt5.QtWidgets import QGridLayout, QLabel, QGroupBox, QLineEdit

import tofu.ez.params as parameters
from tofu.config import SECTIONS
from tofu.ez.params import EZVARS

LOG = logging.getLogger(__name__)


class AdvancedGroup(QGroupBox):
    """
    Advanced Tofu Reco settings
    """

    def __init__(self):
        super().__init__()

        self.setTitle("Advanced TOFU Reconstruction Settings")
        self.setStyleSheet("QGroupBox {color: green;}")

        # LAMINO
        self.lamino_group = QGroupBox("Extended Settings of Reconstruction Algorithms")
        self.lamino_group.clicked.connect(self.set_lamino_group)

        self.lamino_angle_label = QLabel("Laminographic angle                              ")
        self.lamino_angle_entry = QLineEdit()
        self.lamino_angle_entry.editingFinished.connect(self.set_lamino_angle)

        self.overall_rotation_label = QLabel("Overall rotation range about CT Z-axis")
        self.overall_rotation_entry = QLineEdit()
        self.overall_rotation_entry.editingFinished.connect(self.set_overall_rotation)

        self.center_position_z_label = QLabel("Center Position Z                              ")
        self.center_position_z_entry = QLineEdit()
        self.center_position_z_entry.editingFinished.connect(self.set_center_position_z)

        self.axis_rotation_y_label = QLabel(
            "Sample rotation about the beam Y-axis                             "
        )
        self.axis_rotation_y_entry = QLineEdit()
        self.axis_rotation_y_entry.editingFinished.connect(self.set_rotation_about_beam)

        # AUXILIARY FFC
        self.dark_scale_label = QLabel("Dark scale                              ")
        self.dark_scale_entry = QLineEdit()
        self.dark_scale_entry.editingFinished.connect(self.set_dark_scale)

        self.flat_scale_label = QLabel("Flat scale                              ")
        self.flat_scale_entry = QLineEdit()
        self.flat_scale_entry.editingFinished.connect(self.set_flat_scale)

        self.set_layout()

    def set_layout(self):
        layout = QGridLayout()

        self.lamino_group.setCheckable(True)
        self.lamino_group.setChecked(False)
        lamino_layout = QGridLayout()
        lamino_layout.addWidget(self.lamino_angle_label, 0, 0)
        lamino_layout.addWidget(self.lamino_angle_entry, 0, 1)
        lamino_layout.addWidget(self.overall_rotation_label, 1, 0)
        lamino_layout.addWidget(self.overall_rotation_entry, 1, 1)
        lamino_layout.addWidget(self.center_position_z_label, 2, 0)
        lamino_layout.addWidget(self.center_position_z_entry, 2, 1)
        lamino_layout.addWidget(self.axis_rotation_y_label, 3, 0)
        lamino_layout.addWidget(self.axis_rotation_y_entry, 3, 1)
        self.lamino_group.setLayout(lamino_layout)

        aux_group = QGroupBox("Auxiliary FFC Settings")
        aux_group.setCheckable(True)
        aux_group.setChecked(False)
        aux_layout = QGridLayout()
        aux_layout.addWidget(self.dark_scale_label, 0, 0)
        aux_layout.addWidget(self.dark_scale_entry, 0, 1)
        aux_layout.addWidget(self.flat_scale_label, 1, 0)
        aux_layout.addWidget(self.flat_scale_entry, 1, 1)
        aux_group.setLayout(aux_layout)

        layout.addWidget(self.lamino_group)
        layout.addWidget(aux_group)

        self.setLayout(layout)

    #def init_values(self):
        # self.lamino_group.setChecked(False)
        # EZVARS['advanced']['more-reco-params']['value'] = False
        # self.lamino_angle_entry.setText("30")
        # SECTIONS['cone-beam-weight']['axis-angle-x']['value'] = 30
        # self.overall_rotation_entry.setText("360")
        # SECTIONS['general-reconstruction']['overall-angle']['value'] = 360
        # self.center_position_z_entry.setText("")
        # SECTIONS['cone-beam-weight']['center-position-z']['value'] = 0
        # self.axis_rotation_y_entry.setText("")
        # SECTIONS['general-reconstruction']['axis-angle-y']['value'] = 0
        # self.dark_scale_entry.setText("")
        # EZVARS['flat-correction']['dark-scale']['value'] = 1
        # self.flat_scale_entry.setText("")
        # EZVARS['flat-correction']['flat-scale']['value'] = 1

    def set_values_from_params(self):
        self.lamino_group.setChecked(EZVARS['advanced']['more-reco-params']['value'])
        self.lamino_angle_entry.setText(str(SECTIONS['cone-beam-weight']['axis-angle-x']['value']))
        self.overall_rotation_entry.setText(str(SECTIONS['general-reconstruction']['overall-angle']['value']))
        self.center_position_z_entry.setText(str(SECTIONS['cone-beam-weight']['center-position-z']['value']))
        self.axis_rotation_y_entry.setText(str(SECTIONS['general-reconstruction']['axis-angle-y']['value']))
        self.dark_scale_entry.setText(str(EZVARS['flat-correction']['dark-scale']['value']))
        self.flat_scale_entry.setText(str(EZVARS['flat-correction']['flat-scale']['value']))

    def set_lamino_group(self):
        LOG.debug("Lamino: " + str(self.lamino_group.isChecked()))
        EZVARS['advanced']['more-reco-params']['value'] = bool(self.lamino_group.isChecked())

    def set_lamino_angle(self):
        LOG.debug(self.lamino_angle_entry.text())
        SECTIONS['cone-beam-weight']['axis-angle-x']['value'] = float(self.lamino_angle_entry.text())

    def set_overall_rotation(self):
        LOG.debug(self.overall_rotation_entry.text())
        SECTIONS['general-reconstruction']['overall-angle']['value'] = float(self.overall_rotation_entry.text())

    def set_center_position_z(self):
        LOG.debug(self.center_position_z_entry.text())
        SECTIONS['cone-beam-weight']['center-position-z']['value'] = float(self.center_position_z_entry.text())

    def set_rotation_about_beam(self):
        LOG.debug(self.axis_rotation_y_entry.text())
        SECTIONS['general-reconstruction']['axis-angle-y']['value'] = float(self.axis_rotation_y_entry.text())

    def set_dark_scale(self):
        LOG.debug(self.dark_scale_entry.text())
        EZVARS['flat-correction']['dark-scale']['value'] = float(self.dark_scale_entry.text())

    def set_flat_scale(self):
        LOG.debug(self.flat_scale_entry.text())
        EZVARS['flat-correction']['flat-scale']['value'] = float(self.flat_scale_entry.text())
