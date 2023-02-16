import logging
from PyQt5.QtWidgets import QGridLayout, QLabel, QGroupBox, QLineEdit, QCheckBox

import tofu.ez.params as parameters
from tofu.ez.params import EZVARS
from tofu.config import SECTIONS
from tofu.util import add_value_to_dict_entry

LOG = logging.getLogger(__name__)


class OptimizationGroup(QGroupBox):
    """
    Optimization settings
    """

    def __init__(self):
        super().__init__()

        self.setTitle("Optimization Settings")
        self.setStyleSheet("QGroupBox {color: orange;}")

        self.verbose_switch = QCheckBox("Enable verbose console output")
        self.verbose_switch.stateChanged.connect(self.set_verbose_switch)

        self.slice_memory_label = QLabel("Slice memory coefficient")
        self.slice_memory_entry = QLineEdit()
        tmpstr="Fraction of VRAM which will be used to store images \n" \
               "Reserve ~2 GB of VRAM for computation \n" \
               "Decrease the coefficient if you have very large data and start getting errors"
        self.slice_memory_entry.setToolTip(tmpstr)
        self.slice_memory_label.setToolTip(tmpstr)
        self.slice_memory_entry.editingFinished.connect(self.set_slice)

        self.num_GPU_label = QLabel("Number of GPUs")
        self.num_GPU_entry = QLineEdit()
        self.num_GPU_entry.editingFinished.connect(self.set_num_gpu)

        self.slices_per_device_label = QLabel("Slices per device")
        self.slices_per_device_entry = QLineEdit()
        self.slices_per_device_entry.editingFinished.connect(self.set_slices_per_device)

        self.set_layout()

    def set_layout(self):
        layout = QGridLayout()

        layout.addWidget(self.verbose_switch, 0, 0)

        gpu_group = QGroupBox("GPU optimization")
        gpu_group.setCheckable(True)
        gpu_group.setChecked(False)
        gpu_layout = QGridLayout()
        gpu_layout.addWidget(self.slice_memory_label, 0, 0)
        gpu_layout.addWidget(self.slice_memory_entry, 0, 1)
        gpu_layout.addWidget(self.num_GPU_label, 1, 0)
        gpu_layout.addWidget(self.num_GPU_entry, 1, 1)
        gpu_layout.addWidget(self.slices_per_device_label, 2, 0)
        gpu_layout.addWidget(self.slices_per_device_entry, 2, 1)
        gpu_group.setLayout(gpu_layout)

        layout.addWidget(gpu_group, 1, 0)

        self.setLayout(layout)

    def set_values_from_params(self):
        self.verbose_switch.setChecked(bool(SECTIONS['general']['verbose']['value']))
        self.slice_memory_entry.setText(str(SECTIONS['general-reconstruction']['slice-memory-coeff']['value']))
        self.num_GPU_entry.setText(str(SECTIONS['general-reconstruction']['data-splitting-policy']['value']))
        self.slices_per_device_entry.setText(str(SECTIONS['general-reconstruction']['num-gpu-threads']['value']))

    def set_verbose_switch(self):
        LOG.debug("Verbose: " + str(self.verbose_switch.isChecked()))
        dict_entry = SECTIONS['general']['verbose']
        add_value_to_dict_entry(dict_entry, str(self.verbose_switch.isChecked()))

    def set_slice(self):
        LOG.debug(self.slice_memory_entry.text())
        dict_entry = SECTIONS['general-reconstruction']['slice-memory-coeff']
        add_value_to_dict_entry(dict_entry, str(self.slice_memory_entry.text()))
        self.slice_memory_entry.setText(str(dict_entry['value']))

    def set_num_gpu(self):
        LOG.debug(self.num_GPU_entry.text())
        dict_entry = SECTIONS['general-reconstruction']['data-splitting-policy']
        add_value_to_dict_entry(dict_entry, str(self.num_GPU_entry.text()))
        self.num_GPU_entry.setText(str(dict_entry['value']))

    def set_slices_per_device(self):
        LOG.debug(self.slices_per_device_entry.text())
        dict_entry = SECTIONS['general-reconstruction']['num-gpu-threads']
        add_value_to_dict_entry(dict_entry, str(self.slices_per_device_entry.text()))
        self.slices_per_device_entry.setText(str(dict_entry['value']))