from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class WelcomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.is_modified = None
        self.editor = None
        self.filepath = None
        layout.addStretch(1)
        self.tabname = "Welcome"
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)

        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setSpacing(0)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_wrapper = QWidget()
        title_wrapper_layout = QHBoxLayout(title_wrapper)
        title_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        title_wrapper_layout.setSpacing(10)

        title_label = QLabel("Zerionyx EDITOR")
        title_label.setStyleSheet(
            """
            QLabel {
                color: #808080;
                font-size: 58px;
                font-weight: bold;
            }
        """
        )
        title_label.setAlignment(Qt.AlignLeft)

        icon_label = QLabel()
        icon_pixmap = QPixmap("icons:/Zerionyx-gray-icon.ico")
        icon_label.setPixmap(
            icon_pixmap.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

        title_wrapper_layout.addWidget(title_label)
        title_wrapper_layout.addWidget(icon_label)
        title_wrapper_layout.addStretch()

        title_layout.addWidget(title_wrapper)

        subtitle_label = QLabel("Welcome to Zerionyx Editor!")
        subtitle_label.setStyleSheet(
            """
            QLabel {
                color: #666666;
                font-size: 32px;
                margin-top: -5px;
                font-weight: bold;
            }
        """
        )
        subtitle_label.setAlignment(Qt.AlignLeft)

        title_layout.addWidget(subtitle_label)

        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setSpacing(8)
        actions_layout.setContentsMargins(0, 20, 0, 0)

        button_style = """
            QPushButton {
                color: #0098ff;
                background: transparent;
                border: none;
                text-align: left;
                font-size: 22px;
                padding: 5px;
            }
            QPushButton:hover {
                background: #323232;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background: #3a3a3a;
            }
        """

        new_file_btn = QPushButton("New File...")
        new_file_btn.setStyleSheet(button_style)
        new_file_btn.clicked.connect(lambda: self.window().new_file())

        open_file_btn = QPushButton("Open File...")
        open_file_btn.setStyleSheet(button_style)
        open_file_btn.clicked.connect(lambda: self.window().open_file())

        open_folder_btn = QPushButton("Open Folder...")
        open_folder_btn.setStyleSheet(button_style)
        open_folder_btn.clicked.connect(lambda: self.window().open_folder())

        actions_layout.addWidget(new_file_btn)
        actions_layout.addWidget(open_file_btn)
        actions_layout.addWidget(open_folder_btn)
        actions_layout.addStretch()

        center_layout.addStretch()
        center_layout.addWidget(title_container)
        center_layout.addWidget(actions_widget)
        center_layout.addStretch()
        center_container.setFixedWidth(565)
        layout.addWidget(center_container)

        layout.addStretch(2)
