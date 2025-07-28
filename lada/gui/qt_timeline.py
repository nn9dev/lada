from PyQt6.QtWidgets import QWidget, QSlider, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

class Timeline(QWidget):
    seek_requested = pyqtSignal(int)  # position in nanoseconds
    cursor_position_changed = pyqtSignal(int)  # position in nanoseconds
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
        # Initialize state
        self._duration_ns = 0
        self._position_ns = 0
        self._cursor_position_ns = 0
    
    def setup_ui(self):
        # Create slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setTracking(True)  # Update while dragging
        self.slider.sliderMoved.connect(self.on_slider_moved)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.slider)
        layout.setContentsMargins(0, 0, 0, 0)
    
    def set_duration(self, duration_ns: int):
        self._duration_ns = duration_ns
        self.slider.setMaximum(duration_ns)
    
    def set_position(self, position_ns: int):
        if self.slider.isSliderDown():
            return
        
        self._position_ns = position_ns
        self.slider.setValue(position_ns)
    
    def on_slider_moved(self, position: int):
        self._cursor_position_ns = position
        self.cursor_position_changed.emit(position)
    
    def on_slider_pressed(self):
        # Store current position to restore if cancelled
        self._previous_position_ns = self._position_ns
    
    def on_slider_released(self):
        # Seek to the new position
        self.seek_requested.emit(self._cursor_position_ns) 