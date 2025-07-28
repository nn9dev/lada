import logging
import os
import pathlib
import tempfile
import threading
import queue
import time
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QUrl
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from lada.gui.config import MODEL_NAMES_TO_FILES
from lada.gui.qt_timeline import Timeline
from lada.lib import audio_utils, video_utils, threading_utils
from lada.lib.frame_restorer import load_models, FrameRestorer, PassthroughFrameRestorer
from lada import MODEL_WEIGHTS_DIR, LOG_LEVEL

logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)

class VideoPreview(QWidget):
    # Signals
    position_changed = pyqtSignal(float)
    duration_changed = pyqtSignal(float)
    video_preview_init_done = pyqtSignal()
    video_preview_reinit = pyqtSignal()
    video_export_finished = pyqtSignal()
    video_export_progress = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_media_player()
        self.setup_state()
        
        # Initialize state
        self._passthrough = False
        self._mosaic_detection = False
        self._mosaic_restoration_model_name = 'basicvsrpp-generic-1.2'
        self._device = "cpu"
        self._video_preview_init_done = False
        self._max_clip_duration = 180
        self._buffer_queue_min_thresh_time = 0
        self._buffer_queue_min_thresh_time_auto_min = 2.
        self._buffer_queue_min_thresh_time_auto_max = 10.
        self._buffer_queue_min_thresh_time_auto = self._buffer_queue_min_thresh_time_auto_min
        
        # Video playback
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        # Frame restoration
        self.frame_restorer: Optional[FrameRestorer] = None
        self.frame_restorer_lock = threading.Lock()
        self.file_duration_ns = 0
        self.frame_duration_ns = None
        self.current_timestamp_ns = 0
        self.video_metadata = None
        self.has_audio = True
        self.models_cache = None
        self.should_be_paused = False
        self.seek_in_progress = False
        self.waiting_for_data = False
        self.eos = False
        
        # Connect signals
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.timeline.seek_requested.connect(self.seek_video)
        self.timeline.cursor_position_changed.connect(self.show_cursor_position)
        self.media_player.errorOccurred.connect(self.on_error)
        
        # Set up update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_current_position)
        self.update_timer.start(100)  # Update every 100ms
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Video widget
        self.video_widget = QVideoWidget()
        layout.addWidget(self.video_widget)
        
        # Timeline
        self.timeline = Timeline()
        layout.addWidget(self.timeline)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Play/Pause button
        self.play_pause_button = QPushButton()
        self.play_pause_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay))
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        controls_layout.addWidget(self.play_pause_button)
        
        # Mute button
        self.mute_button = QPushButton()
        self.mute_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaVolume))
        self.mute_button.clicked.connect(self.toggle_mute)
        controls_layout.addWidget(self.mute_button)
        
        # Time labels
        self.current_time_label = QLabel("00:00:00")
        self.cursor_time_label = QLabel("00:00:00")
        controls_layout.addWidget(self.current_time_label)
        controls_layout.addWidget(self.cursor_time_label)
        
        layout.addLayout(controls_layout)
    
    def setup_media_player(self):
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Connect media player signals
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.media_player.errorOccurred.connect(self.on_error)
    
    def setup_state(self):
        self.cap = None
        self.current_frame = None
        self.is_playing = False
        self.device = "cpu"
        self.mosaic_detection = False
        self.restoration_model = None
        self.buffer_duration = 0.0
        self.max_clip_duration = 180
        self.buffer_queue_min_thresh_time_auto_min = 2.0
        self.buffer_queue_min_thresh_time_auto_max = 10.0
        self.buffer_queue_min_thresh_time_auto = self.buffer_queue_min_thresh_time_auto_min
        
        self.frame_restorer = None
        self.frame_restorer_lock = threading.Lock()
        self.appsource_thread = None
        self.appsource_queue = queue.Queue()
        self.appsource_thread_should_be_running = False
        self.appsource_thread_stop_requested = False
        
        self.seek_in_progress = False
        self.waiting_for_data = False
        self.eos = False
    
    def set_device(self, device: str):
        if self._device == device:
            return
        self._device = device
        self.models_cache = None
        if self._video_preview_init_done:
            self.reset_frame_restorer()
    
    def set_mosaic_detection(self, enabled: bool):
        if self._mosaic_detection == enabled:
            return
        self._mosaic_detection = enabled
        if self._video_preview_init_done:
            self.reset_frame_restorer()
    
    def set_mosaic_restoration_model(self, model_name: str):
        if self._mosaic_restoration_model_name == model_name:
            return
        self._mosaic_restoration_model_name = model_name
        if self._video_preview_init_done:
            self.reset_frame_restorer()
    
    def set_buffer_queue_min_thresh_time(self, time: float):
        if self._buffer_queue_min_thresh_time == time:
            return
        self._buffer_queue_min_thresh_time = time
        if self._video_preview_init_done:
            self.update_buffer_settings()
    
    def set_max_clip_duration(self, duration: int):
        if self._max_clip_duration == duration:
            return
        self._max_clip_duration = duration
        if self._video_preview_init_done and self._buffer_queue_min_thresh_time == 0:
            self._buffer_queue_min_thresh_time_auto = float(self._max_clip_duration / self.video_metadata.video_fps_exact)
            self.reset_frame_restorer()
    
    def set_preview_enabled(self, enabled: bool):
        self._passthrough = not enabled
        if self._video_preview_init_done:
            self.reset_frame_restorer()
    
    def toggle_play_pause(self):
        if not self._video_preview_init_done or self.seek_in_progress:
            return
        
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def toggle_mute(self):
        self.audio_output.setMuted(not self.audio_output.isMuted())
        self.update_mute_button()
    
    def update_mute_button(self):
        icon = (self.style().StandardPixmap.SP_MediaVolumeMuted 
                if self.audio_output.isMuted() 
                else self.style().StandardPixmap.SP_MediaVolume)
        self.mute_button.setIcon(self.style().standardIcon(icon))
    
    def seek_video(self, position_ns: int):
        if not self._video_preview_init_done:
            return
        
        self.seek_in_progress = True
        self.media_player.setPosition(position_ns // 1_000_000)  # Convert to milliseconds
        self.seek_in_progress = False
    
    def show_cursor_position(self, position_ns: int):
        self.cursor_time_label.setText(self.format_time(position_ns))
    
    def open_video_file(self, file_path: str, mute_audio: bool):
        self.video_preview_reinit.emit()
        
        # Load video metadata
        self.video_metadata = video_utils.get_video_meta_data(file_path)
        self.file_duration_ns = int(self.video_metadata.duration * 1_000_000_000)  # Convert seconds to nanoseconds
        self.frame_duration_ns = int(1_000_000_000 / self.video_metadata.video_fps_exact)
        
        # Set up media player
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.audio_output.setMuted(mute_audio)
        self.update_mute_button()
        
        # Initialize models cache
        try:
            mosaic_restoration_model_path = MODEL_NAMES_TO_FILES[self._mosaic_restoration_model_name]
            logger.info(f"Loading mosaic restoration model from: {mosaic_restoration_model_path}")
            if not os.path.exists(mosaic_restoration_model_path):
                raise FileNotFoundError(f"Mosaic restoration model not found at: {mosaic_restoration_model_path}")
            
            mosaic_detection_model_path = os.path.join(MODEL_WEIGHTS_DIR, 'lada_mosaic_detection_model_v3.pt')
            logger.info(f"Loading mosaic detection model from: {mosaic_detection_model_path}")
            if not os.path.exists(mosaic_detection_model_path):
                raise FileNotFoundError(f"Mosaic detection model not found at: {mosaic_detection_model_path}")
            
            mosaic_detection_model, mosaic_restoration_model, mosaic_restoration_model_preferred_pad_mode = load_models(
                self._device, self._mosaic_restoration_model_name, mosaic_restoration_model_path, None,
                mosaic_detection_model_path
            )
            
            self.models_cache = dict(
                mosaic_restoration_model_name=self._mosaic_restoration_model_name,
                mosaic_detection_model=mosaic_detection_model,
                mosaic_restoration_model=mosaic_restoration_model,
                mosaic_restoration_model_preferred_pad_mode=mosaic_restoration_model_preferred_pad_mode
            )
            logger.info("Models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
            raise
        
        # Set up frame restorer
        self.setup_frame_restorer()
        
        # Update UI
        self.timeline.set_duration(self.file_duration_ns)
        self.video_preview_init_done.emit()
        self._video_preview_init_done = True
    
    def setup_frame_restorer(self):
        with self.frame_restorer_lock:
            if self.frame_restorer:
                self.frame_restorer.stop()
            
            if self._passthrough:
                self.frame_restorer = PassthroughFrameRestorer(self.video_metadata.video_file)
            else:
                self.frame_restorer = FrameRestorer(
                    self._device,
                    self.video_metadata.video_file,
                    True,
                    self._max_clip_duration,
                    self._mosaic_restoration_model_name,
                    self.models_cache["mosaic_detection_model"],
                    self.models_cache["mosaic_restoration_model"],
                    self.models_cache["mosaic_restoration_model_preferred_pad_mode"],
                    mosaic_detection=self._mosaic_detection
                )
            
            self.frame_restorer.start()
    
    def reset_frame_restorer(self):
        self.setup_frame_restorer()
        self.seek_video(self.current_timestamp_ns)
    
    def update_buffer_settings(self):
        if self._buffer_queue_min_thresh_time == 0:
            self._buffer_queue_min_thresh_time_auto = min(
                self._buffer_queue_min_thresh_time_auto_max,
                max(
                    self._buffer_queue_min_thresh_time_auto_min,
                    float(self._max_clip_duration / self.video_metadata.video_fps_exact)
                )
            )
    
    def on_position_changed(self, position_ms: int):
        self.current_timestamp_ns = position_ms * 1_000_000
        self.update_current_position()
    
    def on_duration_changed(self, duration_ms: int):
        self.file_duration_ns = duration_ms * 1_000_000
        self.timeline.set_duration(self.file_duration_ns)
    
    def on_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        icon = (self.style().StandardPixmap.SP_MediaPause 
                if state == QMediaPlayer.PlaybackState.PlayingState 
                else self.style().StandardPixmap.SP_MediaPlay)
        self.play_pause_button.setIcon(self.style().standardIcon(icon))
    
    def update_current_position(self):
        self.current_time_label.setText(self.format_time(self.current_timestamp_ns))
        self.timeline.set_position(self.current_timestamp_ns)
    
    def format_time(self, time_ns: int) -> str:
        seconds = time_ns // 1_000_000_000
        minutes = seconds // 60
        hours = minutes // 60
        return f"{hours:02d}:{minutes % 60:02d}:{seconds % 60:02d}"
    
    def export_video(self, file_path: str, video_codec: str, crf: int):
        def run_export():
            try:
                self.frame_restorer.export_video(
                    file_path,
                    video_codec,
                    crf,
                    progress_callback=lambda p: self.video_export_progress.emit(p)
                )
                self.video_export_finished.emit()
            except Exception as e:
                logger.error(f"Export failed: {e}")
                # TODO: Show error dialog
        
        threading.Thread(target=run_export, daemon=True).start()
    
    def close(self):
        if self.frame_restorer:
            self.frame_restorer.stop()
        self.media_player.stop()
        self.update_timer.stop()
    
    def on_error(self, error, error_string):
        print(f"Media player error: {error_string}")
    
    def is_loaded(self) -> bool:
        return self.cap is not None
    
    def export(self, file_path: str, codec: str, crf: int, mute: bool):
        if not self.is_loaded():
            return
        
        def run_export():
            self.video_preview_reinit.emit()
            self.mosaic_detection = False
            self.passthrough = False
            
            if self.frame_restorer:
                self.frame_restorer.stop()
            
            self.setup_frame_restorer()
            
            progress_update_step_size = 100
            success = True
            
            try:
                self.frame_restorer.start(start_ns=0)
                
                with video_utils.VideoWriter(
                    file_path,
                    self.video_metadata.video_width,
                    self.video_metadata.video_height,
                    self.video_metadata.video_fps_exact,
                    codec,
                    time_base=self.video_metadata.time_base,
                    crf=crf
                ) as video_writer:
                    for frame_num, elem in enumerate(self.frame_restorer):
                        if elem is None:
                            success = False
                            break
                        
                        restored_frame, restored_frame_pts = elem
                        video_writer.write(restored_frame, restored_frame_pts, bgr2rgb=True)
                        
                        if frame_num % progress_update_step_size == 0:
                            self.video_export_progress.emit(frame_num / self.video_metadata.frames_count)
            
            except Exception as e:
                success = False
                print(f"Error on export: {e}")
            
            finally:
                self.frame_restorer.stop()
            
            if success:
                if not mute:
                    audio_utils.combine_audio_video_files(
                        self.video_metadata,
                        file_path,
                        file_path
                    )
                self.video_export_progress.emit(1.0)
                self.video_export_finished.emit()
        
        export_thread = threading.Thread(target=run_export)
        export_thread.start()
    
    def closeEvent(self, event):
        if self.frame_restorer:
            self.stop_appsource_worker()
        if self.cap is not None:
            self.cap.release()
        event.accept() 