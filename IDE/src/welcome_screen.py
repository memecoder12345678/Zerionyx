from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class WelcomeScreen(QWidget):
    def __init__(self, parent=None):  # hàm khởi tạo
        super().__init__(parent)  # gọi hàm khởi tạo của lớp cha
        layout = QHBoxLayout(self)  # tạo layout ngang
        layout.setContentsMargins(0, 0, 0, 0)  # thiết lập khoảng cách giữa các widget
        self.is_modified = None  # đánh dấu không có hình ảnh được chỉnh sửa
        self.editor = None  # đánh dấu không có editor
        self.filepath = None  # đánh dấu không có đường dẫn file
        layout.addStretch(1)  # thêm khoảng trống vào đầu layout
        self.tabname = "Welcome"  # lấy tên tab
        center_container = QWidget()  # tạo container trung tâm
        center_layout = QVBoxLayout(center_container)  # tạo layout dọc

        title_container = QWidget()  # tạo container tiêu đề
        title_layout = QVBoxLayout(title_container)  # tạo layout dọc
        title_layout.setSpacing(0)  # thiết lập khoảng cách giữa các widget
        title_layout.setContentsMargins(
            0, 0, 0, 0
        )  # thiết lập khoảng cách giữa các widget

        title_wrapper = QWidget()  # tạo wrapper tiêu đề
        title_wrapper_layout = QHBoxLayout(title_wrapper)  # tạo layout ngang
        title_wrapper_layout.setContentsMargins(
            0, 0, 0, 0
        )  # thiết lập khoảng cách giữa các widget
        title_wrapper_layout.setSpacing(10)  # thiết lập khoảng cách giữa các widget

        title_label = QLabel("ZERION EDITOR")  # tạo label tiêu đề
        title_label.setStyleSheet(
            """
            QLabel {
                color: #808080;
                font-size: 58px;
                font-weight: bold;
            }
        """
        )  # thiết lập kiểu dáng label
        title_label.setAlignment(Qt.AlignLeft)  # căn chỉnh label ở bên trái

        icon_label = QLabel()  # tạo label biểu tượng
        icon_pixmap = QPixmap("icons:/zerion-gray-icon.ico")  # tạo đối tượng QPixmap
        icon_label.setPixmap(
            icon_pixmap.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )  # thu phóng biểu tượng

        title_wrapper_layout.addWidget(title_label)  # thêm label tiêu đề vào wrapper
        title_wrapper_layout.addWidget(icon_label)  # thêm label biểu tượng vào wrapper
        title_wrapper_layout.addStretch()  # thêm khoảng trống vào cuối wrapper

        title_layout.addWidget(title_wrapper)  # thêm wrapper tiêu đề vào layout

        subtitle_label = QLabel("Welcome to Zerion Editor!")  # tạo label phụ đề
        subtitle_label.setStyleSheet(
            """
            QLabel {
                color: #666666;
                font-size: 32px;
                margin-top: -5px;
                font-weight: bold;
            }
        """
        )  # thiết lập kiểu dáng label phụ đề
        subtitle_label.setAlignment(Qt.AlignLeft)  # căn chỉnh label phụ đề ở bên trái

        title_layout.addWidget(subtitle_label)  # thêm label phụ đề vào layout

        actions_widget = QWidget()  # tạo widget chứa các nút hành động
        actions_layout = QVBoxLayout(actions_widget)  # tạo layout dọc
        actions_layout.setSpacing(8)  # thiết lập khoảng cách giữa các widget
        actions_layout.setContentsMargins(
            0, 20, 0, 0
        )  # thiết lập khoảng cách giữa các widget

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
        """  # thiết lập kiểu dáng nút

        new_file_btn = QPushButton("New File...")  # tạo nút mới
        new_file_btn.setStyleSheet(button_style)  # thiết lập kiểu dáng nút mới
        new_file_btn.clicked.connect(
            lambda: self.window().new_file()
        )  # kết nối nút mới với hàm new_file

        open_file_btn = QPushButton("Open File...")  # tạo nút mở file
        open_file_btn.setStyleSheet(button_style)  # thiết lập kiểu dáng nút mở file
        open_file_btn.clicked.connect(
            lambda: self.window().open_file()
        )  # kết nối nút mở file với hàm open_file

        open_folder_btn = QPushButton("Open Folder...")  # tạo nút mở thư mục
        open_folder_btn.setStyleSheet(
            button_style
        )  # thiết lập kiểu dáng nút mở thư mục
        open_folder_btn.clicked.connect(
            lambda: self.window().open_folder()
        )  # kết nối nút mở thư mục với hàm open_folder

        actions_layout.addWidget(new_file_btn)  # thêm nút mới vào layout
        actions_layout.addWidget(open_file_btn)  # thêm nút mở file vào layout
        actions_layout.addWidget(open_folder_btn)  # thêm nút mở thư mục vào layout
        actions_layout.addStretch()  # thêm khoảng trống vào cuối layout

        center_layout.addStretch()  # thêm khoảng trống vào đầu layout
        center_layout.addWidget(title_container)  # thêm container tiêu đề vào layout
        center_layout.addWidget(actions_widget)  # thêm widget hành động vào layout
        center_layout.addStretch()  # thêm khoảng trống vào cuối layout

        center_container.setFixedWidth(535)  # thiết lập chiều rộng container chính
        layout.addWidget(center_container)  # thêm container chính vào layout

        layout.addStretch(2)  # thêm khoảng trống vào cuối layout
