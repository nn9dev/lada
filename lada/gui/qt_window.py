import os
import pathlib
from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QApplication,
    QStackedWidget, QProgressBar, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFrame, QMenuBar,
    QMenu, QStatusBar, QSplitter, QDialog
)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction, QKeySequence

from lada.gui.qt_video_preview import VideoPreview
from lada.gui.qt_timeline import Timeline
from lada.gui.qt_config_sidebar import ConfigSidebar
from lada.gui.qt_shortcuts import ShortcutsManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.shortcuts = ShortcutsManager()
        self.setup_ui()
        self.setup_menus()
        self.setup_shortcuts()
        self.setup_status_bar()
        self.setup_connections()
    
    def setup_ui(self):
        self.setWindowTitle("Lada")
        self.setMinimumSize(1280, 720)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Create main content area
        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create stacked widget for different views
        self.stack = QStackedWidget()
        main_content_layout.addWidget(self.stack)
        
        # Create main page
        main_page = QWidget()
        main_page_layout = QVBoxLayout(main_page)
        
        # Add video preview
        self.video_preview = VideoPreview()
        main_page_layout.addWidget(self.video_preview)
        
        # Add timeline
        self.timeline = Timeline()
        main_page_layout.addWidget(self.timeline)
        
        # Add control buttons
        controls_layout = QHBoxLayout()
        
        self.play_button = QPushButton("Play")
        self.play_button.setFixedWidth(100)
        controls_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setFixedWidth(100)
        controls_layout.addWidget(self.stop_button)
        
        self.export_button = QPushButton("Export")
        self.export_button.setFixedWidth(100)
        controls_layout.addWidget(self.export_button)
        
        controls_layout.addStretch()
        main_page_layout.addLayout(controls_layout)
        
        # Add main page to stack
        self.stack.addWidget(main_page)
        
        # Create export page
        export_page = QWidget()
        export_layout = QVBoxLayout(export_page)
        
        # Add export page to stack
        self.stack.addWidget(export_page)
        
        # Create custom export progress dialog
        self.export_progress = QDialog(self)
        self.export_progress.setWindowTitle("Exporting video...")
        self.export_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.export_progress.setFixedSize(300, 100)
        
        progress_layout = QVBoxLayout(self.export_progress)
        
        self.export_progress_bar = QProgressBar()
        self.export_progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.export_progress_bar)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.on_export_canceled)
        progress_layout.addWidget(cancel_button)
        
        self.export_progress.hide()
        
        # Add config sidebar
        self.config_sidebar = ConfigSidebar()
        self.config_sidebar.setFixedWidth(300)
        
        # Add widgets to splitter
        splitter.addWidget(main_content)
        splitter.addWidget(self.config_sidebar)
        
        # Set initial splitter sizes
        splitter.setSizes([1000, 300])
    
    def setup_menus(self):
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.on_open)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = self.menuBar().addMenu("&Edit")
        
        preferences_action = QAction("&Preferences...", self)
        preferences_action.triggered.connect(self.on_preferences)
        edit_menu.addAction(preferences_action)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        
        toggle_sidebar_action = QAction("&Toggle Sidebar", self)
        toggle_sidebar_action.setShortcut("Ctrl+B")
        toggle_sidebar_action.triggered.connect(self.on_toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        about_action = QAction("&About...", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)
    
    def setup_shortcuts(self):
        # Register shortcut groups
        self.shortcuts.register_group("file", "File")
        self.shortcuts.register_group("view", "View")
        
        # Add shortcuts
        self.shortcuts.add("file", "open", "Ctrl+O", self.on_open, "Open video file")
        self.shortcuts.add("view", "toggle_sidebar", "Ctrl+B", self.on_toggle_sidebar, "Toggle sidebar")
    
    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add status labels
        self.status_position = QLabel()
        self.status_bar.addPermanentWidget(self.status_position)
        
        self.status_duration = QLabel()
        self.status_bar.addPermanentWidget(self.status_duration)
    
    def setup_connections(self):
        # Connect timeline signals
        self.timeline.seek_requested.connect(self.video_preview.seek_video)
        self.timeline.cursor_position_changed.connect(self.on_cursor_position_changed)
        
        # Connect video preview signals
        self.video_preview.position_changed.connect(self.timeline.set_position)
        self.video_preview.duration_changed.connect(self.timeline.set_duration)
        self.video_preview.duration_changed.connect(self.on_duration_changed)
        self.video_preview.video_export_progress.connect(self.on_export_progress)
        self.video_preview.video_export_finished.connect(self.on_export_finished)
        
        # Connect config sidebar signals
        self.config_sidebar.device_changed.connect(self.video_preview.set_device)
        self.config_sidebar.preview_mode_changed.connect(self.video_preview.set_mosaic_detection)
        self.config_sidebar.restoration_model_changed.connect(self.video_preview.set_mosaic_restoration_model)
        self.config_sidebar.buffer_duration_changed.connect(self.video_preview.set_buffer_queue_min_thresh_time)
        self.config_sidebar.max_clip_duration_changed.connect(self.video_preview.set_max_clip_duration)
        
        # Connect button signals
        self.play_button.clicked.connect(self.video_preview.toggle_play_pause)
        self.stop_button.clicked.connect(self.video_preview.media_player.stop)
        self.export_button.clicked.connect(self.on_export)
    
    def on_open(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)"
        )
        
        if file_path:
            self.video_preview.open_video_file(file_path, self.config_sidebar.get_mute_audio())
    
    def on_export(self):
        if not self.video_preview.is_loaded():
            QMessageBox.warning(self, "Export", "No video loaded")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Video",
            "",
            "MP4 Files (*.mp4);;All Files (*.*)"
        )
        
        if file_path:
            self.stack.setCurrentIndex(1)  # Switch to export page
            self.export_progress.show()
            
            self.video_preview.export_video(
                file_path,
                self.config_sidebar.get_export_codec(),
                self.config_sidebar.get_export_crf()
            )
    
    def on_export_progress(self, progress: float):
        self.export_progress_bar.setValue(int(progress * 100))
    
    def on_export_finished(self):
        self.export_progress.close()
        self.stack.setCurrentIndex(0)  # Switch back to main page
        QMessageBox.information(self, "Export", "Video export completed successfully!")
    
    def on_export_canceled(self):
        # TODO: Implement export cancellation
        pass
    
    def on_preferences(self):
        # TODO: Implement preferences dialog
        pass
    
    def on_toggle_sidebar(self):
        self.config_sidebar.setVisible(not self.config_sidebar.isVisible())
    
    def on_about(self):
        QMessageBox.about(
            self,
            "About Lada",
            "Lada - Video Restoration Tool\n\n"
            "A tool for restoring and enhancing video quality using AI models."
        )
    
    def on_cursor_position_changed(self, position: float):
        self.status_position.setText(f"Position: {position:.2f}s")
    
    def on_duration_changed(self, duration: float):
        self.status_duration.setText(f"Duration: {duration:.2f}s")
    
    def closeEvent(self, event):
        # TODO: Add confirmation dialog if video is being processed
        event.accept() 