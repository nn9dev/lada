import torch
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QCheckBox, QGroupBox,
    QRadioButton, QButtonGroup
)
from PyQt6.QtCore import pyqtSignal

class ConfigSidebar(QWidget):
    # Signals
    device_changed = pyqtSignal(str)
    preview_mode_changed = pyqtSignal(bool)
    restoration_model_changed = pyqtSignal(str)
    buffer_duration_changed = pyqtSignal(float)
    max_clip_duration_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_connections()
        self.setup_initial_state()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Device selection
        device_group = QGroupBox("Device")
        device_layout = QVBoxLayout(device_group)
        
        self.device_buttons = QButtonGroup()
        self.cpu_radio = QRadioButton("CPU")
        self.gpu_radio = QRadioButton("GPU")
        self.device_buttons.addButton(self.cpu_radio)
        self.device_buttons.addButton(self.gpu_radio)
        
        device_layout.addWidget(self.cpu_radio)
        device_layout.addWidget(self.gpu_radio)
        layout.addWidget(device_group)
        
        # Preview mode
        preview_group = QGroupBox("Preview Mode")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_mode_buttons = QButtonGroup()
        self.normal_radio = QRadioButton("Normal")
        self.mosaic_detection_radio = QRadioButton("Mosaic Detection")
        self.preview_mode_buttons.addButton(self.normal_radio)
        self.preview_mode_buttons.addButton(self.mosaic_detection_radio)
        
        preview_layout.addWidget(self.normal_radio)
        preview_layout.addWidget(self.mosaic_detection_radio)
        layout.addWidget(preview_group)
        
        # Restoration model
        model_group = QGroupBox("Restoration Model")
        model_layout = QVBoxLayout(model_group)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "BasicVSR++ Generic v1.2",
            "DeepMosaics Clean Youknow"
        ])
        model_layout.addWidget(self.model_combo)
        layout.addWidget(model_group)
        
        # Buffer settings
        buffer_group = QGroupBox("Buffer Settings")
        buffer_layout = QVBoxLayout(buffer_group)
        
        # Buffer duration
        buffer_duration_layout = QHBoxLayout()
        buffer_duration_layout.addWidget(QLabel("Buffer Duration:"))
        self.buffer_duration_spin = QSpinBox()
        self.buffer_duration_spin.setRange(0, 60)
        self.buffer_duration_spin.setSuffix(" s")
        buffer_duration_layout.addWidget(self.buffer_duration_spin)
        buffer_layout.addLayout(buffer_duration_layout)
        
        # Max clip duration
        max_clip_layout = QHBoxLayout()
        max_clip_layout.addWidget(QLabel("Max Clip Duration:"))
        self.max_clip_spin = QSpinBox()
        self.max_clip_spin.setRange(1, 600)
        self.max_clip_spin.setSuffix(" s")
        max_clip_layout.addWidget(self.max_clip_spin)
        buffer_layout.addLayout(max_clip_layout)
        
        layout.addWidget(buffer_group)
        
        # Export settings
        export_group = QGroupBox("Export Settings")
        export_layout = QVBoxLayout(export_group)
        
        # Codec selection
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("Codec:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["h264", "hevc", "h264_nvenc", "hevc_nvenc"])
        codec_layout.addWidget(self.codec_combo)
        export_layout.addLayout(codec_layout)
        
        # CRF setting
        crf_layout = QHBoxLayout()
        crf_layout.addWidget(QLabel("CRF:"))
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(23)
        crf_layout.addWidget(self.crf_spin)
        export_layout.addLayout(crf_layout)
        
        layout.addWidget(export_group)
        
        # Audio settings
        audio_group = QGroupBox("Audio")
        audio_layout = QVBoxLayout(audio_group)
        
        self.mute_checkbox = QCheckBox("Mute Audio")
        audio_layout.addWidget(self.mute_checkbox)
        layout.addWidget(audio_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def setup_connections(self):
        # Device selection
        self.device_buttons.buttonClicked.connect(self.on_device_changed)
        
        # Preview mode
        self.preview_mode_buttons.buttonClicked.connect(self.on_preview_mode_changed)
        
        # Restoration model
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        
        # Buffer settings
        self.buffer_duration_spin.valueChanged.connect(self.on_buffer_duration_changed)
        self.max_clip_spin.valueChanged.connect(self.on_max_clip_duration_changed)
    
    def setup_initial_state(self):
        # Set initial device
        if torch.cuda.is_available():
            self.gpu_radio.setChecked(True)
        else:
            self.cpu_radio.setChecked(True)
        
        # Set initial preview mode
        self.normal_radio.setChecked(True)
        
        # Set initial buffer settings
        self.buffer_duration_spin.setValue(0)  # Auto
        self.max_clip_spin.setValue(180)  # 3 minutes
    
    def on_device_changed(self, button):
        device = "cuda:0" if button == self.gpu_radio else "cpu"
        self.device_changed.emit(device)
    
    def on_preview_mode_changed(self, button):
        enabled = button == self.mosaic_detection_radio
        self.preview_mode_changed.emit(enabled)
    
    def on_model_changed(self, text):
        model_map = {
            "BasicVSR++ Generic v1.2": "basicvsrpp-generic-1.2",
            "DeepMosaics Clean Youknow": "deepmosaics-clean-youknow"
        }
        self.restoration_model_changed.emit(model_map[text])
    
    def on_buffer_duration_changed(self, value):
        self.buffer_duration_changed.emit(float(value))
    
    def on_max_clip_duration_changed(self, value):
        self.max_clip_duration_changed.emit(value)
    
    def get_device(self) -> str:
        return "cuda:0" if self.gpu_radio.isChecked() else "cpu"
    
    def get_mute_audio(self) -> bool:
        return self.mute_checkbox.isChecked()
    
    def get_export_codec(self) -> str:
        return self.codec_combo.currentText()
    
    def get_export_crf(self) -> int:
        return self.crf_spin.value()
    
    def set_disabled(self, disabled: bool):
        self.setEnabled(not disabled) 