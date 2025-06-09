import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from src.editor_tab import EditorTab
from src.image_viewer import ImageViewer
import os
from src.file_tree import FileTreeDelegate, FileTreeView
from src.welcome_screen import WelcomeScreen

from PyQt5.QtWidgets import (
    QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.Qsci import QsciScintilla
import re


class FindReplaceDialog(QDialog):
    def __init__(self, parent=None, editor=None):
        super().__init__(parent)
        self.setWindowTitle("Find & Replace")
        self.setModal(False)
        self.editor = editor

        layout = QGridLayout(self)

        self.find_label = QLabel("Find:")
        self.find_input = QLineEdit()
        self.replace_label = QLabel("Replace:")
        self.replace_input = QLineEdit()
        self.case_checkbox = QCheckBox("Case sensitive")
        self.find_btn = QPushButton("Find Next")
        self.replace_btn = QPushButton("Replace")
        self.replace_all_btn = QPushButton("Replace All")
        self.close_btn = QPushButton("Close")

        layout.addWidget(self.find_label, 0, 0)
        layout.addWidget(self.find_input, 0, 1, 1, 3)
        layout.addWidget(self.replace_label, 1, 0)
        layout.addWidget(self.replace_input, 1, 1, 1, 3)
        layout.addWidget(self.case_checkbox, 2, 0)
        layout.addWidget(self.find_btn, 2, 1)
        layout.addWidget(self.replace_btn, 2, 2)
        layout.addWidget(self.replace_all_btn, 2, 3)
        layout.addWidget(self.close_btn, 3, 0, 1, 4)

        self.find_btn.clicked.connect(self.find_next)
        self.replace_btn.clicked.connect(self.replace_one)
        self.replace_all_btn.clicked.connect(self.replace_all)
        self.close_btn.clicked.connect(self.close)

        self.find_shortcut = QShortcut(QKeySequence("Return"), self)
        self.find_shortcut.activated.connect(self.find_next)
        self.replace_shortcut = QShortcut(QKeySequence("Shift+Return"), self)
        self.replace_shortcut.activated.connect(self.replace_one)
        self.replace_all_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.replace_all_shortcut.activated.connect(self.replace_all)

        self.find_input.setFocus()

    def find_next(self):
        if not self.editor:
            return

        text = self.find_input.text()
        if not text:
            return

        case_sensitive = self.case_checkbox.isChecked()

        found = self.editor.findFirst(
            text,
            False,
            case_sensitive,
            False,
            True,
            True
        )

        if not found:
            QMessageBox.information(self, "Find", "No more matches found.")

    def replace_one(self):
        if not self.editor:
            return

        selected = self.editor.selectedText()
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        case_sensitive = self.case_checkbox.isChecked()

        if (case_sensitive and selected == find_text) or \
           (not case_sensitive and selected.lower() == find_text.lower()):
            self.editor.replaceSelectedText(replace_text)

        self.find_next()

    def replace_all(self):
        if not self.editor:
            return

        find_text = self.find_input.text()
        replace_text = self.replace_input.text()

        if not find_text:
            return

        content = self.editor.text()

        if self.case_checkbox.isChecked():
            new_content = content.replace(find_text, replace_text)
        else:
            new_content = re.sub(re.escape(find_text), replace_text, content, flags=re.IGNORECASE)

        self.editor.setText(new_content)


class MainWindow(QMainWindow):
    def __init__(self):

        super().__init__()
        self.settings_file = os.path.join(
            os.path.dirname(__file__), "settings.json"
        )
        self.content_cache = None
        self.setWindowTitle("Zerion Editor")
        QDir.addSearchPath(
            "icons",
            os.path.join(os.path.dirname(__file__), f".{os.sep}src{os.sep}icons"),
        )
        self.setWindowIcon(
            QIcon("icons:/zerion-icon.png")
        )
        self.resize(1300, 900)
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            """
            QStatusBar {
                background: #252526;
                color: #808080;
                font-size: 18px;
                border-top: 1px solid #1e1e1e;
                padding: 2px 4px;
            }
            QStatusBar QLabel {
                color: #808080;
                font-size: 16px; 
                text-align: right;
                padding-left: 4px;
            }
        """
        )
        self.setStatusBar(self.status_bar)

        self.status_position = QLabel()
        self.status_file = QLabel()
        self.status_folder = QLabel()
        self.status_bar.addPermanentWidget(
            self.status_position
        )
        self.status_bar.addPermanentWidget(
            self.status_file
        )
        self.status_bar.addPermanentWidget(
            self.status_folder
        )

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.left_container = QWidget()
        left_layout = QVBoxLayout(
            self.left_container
        )
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        explorer_header = QWidget()
        explorer_header.setFixedHeight(
            35
        )
        header_layout = QHBoxLayout(
            explorer_header
        )
        header_layout.setContentsMargins(
            10, 0, 4, 0
        )

        header_label = QLabel("EXPLORER")
        header_label.setStyleSheet(
            """
            QLabel {
                color: #808080;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
        """
        )

        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self.toggle_tree = QPushButton()
        self.toggle_tree.setIcon(
            QIcon("icons:/close.ico")
        )
        self.toggle_tree.setFixedSize(24, 24)
        self.toggle_tree.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #323232;
            }
            QPushButton:pressed {
                background: #3a3a3a;
            }
        """
        )
        self.toggle_tree.clicked.connect(
            self.toggle_file_tree
        )
        header_layout.addWidget(self.toggle_tree)

        left_layout.addWidget(
            explorer_header
        )

        self.folder_section = QWidget()
        folder_layout = QHBoxLayout(
            self.folder_section
        )
        folder_layout.setContentsMargins(
            10, 4, 4, 4
        )

        folder_name = os.path.basename(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.folder_label = QLabel(folder_name.upper())
        self.folder_label.setStyleSheet(
            """
            QLabel {
                color: #e0e0e0;
                font-size: 11px;
                font-weight: 500;
            }
        """
        )
        folder_layout.addWidget(self.folder_label)
        folder_layout.addStretch()

        left_layout.addWidget(self.folder_section)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        splitter.addWidget(
            self.left_container
        )

        tabs_container = QWidget()
        tabs_layout = QVBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setTabBar(QTabBar())
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setMovable(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.currentChanged.connect(
            self.on_tab_changed
        )
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #252526;
                color: #d4d4d4;
                padding: 6px 12px;
                border: none;
                min-width: 100px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #1a1a1a;
                border-bottom: 2px solid #0098ff;
            }
            QTabBar::tab:hover {
                background: #323232;
            }
            QTabBar::tab:last {
                margin-right: 0px;
            }
            QTabBar::close-button {
                image: url(icons:/close.ico);
                margin: 2px;
            }
            QTabWidget {
                background: #1a1a1a;
                border: none;
            }
            QTabBar {
                background: #1a1a1a;
                border: none;
                alignment: left;
            }
            QTabBar::scroller { 
                width: 24px;
            }
            QTabBar QToolButton {
                background: #252526;
                border: none;
                margin: 0;
                padding: 0;
                border-radius: 0px;
            }
            QTabBar QToolButton::right-arrow {
                image: url(icons:/chevron-right.ico);
                width: 16px;
                height: 16px;
            }
            QTabBar QToolButton::left-arrow {
                image: url(icons:/chevron-left.ico);
                width: 16px;
                height: 16px;
            }
            QTabBar QToolButton:hover {
                background: #323232;
            }
            QTabBar::tab:first {
                margin-left: 0px;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
            """
        )
        tabs_layout.addWidget(self.tabs)

        splitter.addWidget(tabs_container)

        self.splitter = splitter
        self.tree_width = 230

        self.splitter.splitterMoved.connect(
            self.on_splitter_moved
        )
        self.resizeEvent = self.on_resize

        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath("")
        self.current_project_dir = None

        self.fs_watcher = QFileSystemWatcher()
        self.fs_watcher.directoryChanged.connect(
            self.on_directory_changed
        )
        self.fs_watcher.fileChanged.connect(
            self.on_file_changed
        )

        self.left_container.hide()
        self.folder_section.hide()
        self.splitter.setSizes(
            [0, self.width()]
        )
        self.file_tree = FileTreeView(self)
        self.fs_model.setReadOnly(False)
        self.file_tree.setFocusPolicy(Qt.NoFocus)
        self.file_tree.setModel(self.fs_model)
        self.file_tree.setRootIndex(
            self.fs_model.index("")
        )
        self.file_tree.setEditTriggers(
            QTreeView.EditTrigger.NoEditTriggers
        )
        self.file_tree.setContextMenuPolicy(
            Qt.CustomContextMenu
        )
        self.file_tree.customContextMenuRequested.connect(
            self.show_context_menu
        )
        self.file_tree.setIndentation(12)
        self.file_tree.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        self.file_tree.setDragEnabled(True)
        self.file_tree.setAcceptDrops(True)
        self.file_tree.setDropIndicatorShown(True)
        self.file_tree.setDragDropMode(
            QAbstractItemView.DragDrop
        )

        self.file_tree.setHeaderHidden(True)
        self.file_tree.setAnimated(
            False
        )
        self.file_tree.setUniformRowHeights(True)

        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)

        self.file_tree.clicked.connect(
            self.on_file_tree_clicked
        )

        self.fs_model.setFilter(
            QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files | QDir.Drives
        )

        self.file_tree.setIconSize(QSize(16, 16))
        self.tree_delegate = FileTreeDelegate()
        self.file_tree.setItemDelegate(
            self.tree_delegate
        )

        left_layout.addWidget(self.file_tree)

        self.file_tree.setStyleSheet(
            """
            QTreeView {
                background-color: #252526;
                border: none;
                color: #d4d4d4;
                selection-background-color: transparent;
                padding-left: 5px;
            }
            QTreeView::item {
                padding: 4px;
                border-radius: 4px;
                margin: 1px 4px;
            }
            QTreeView::item:hover {
                background: #323232;
            }
            QTreeView::item:selected {
                background: #323232;
                color: #ffffff;
            }
            QTreeView::branch {
                background: transparent;
                border-image: none;
                padding-left: 2px;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                image: url(icons:/chevron-right.ico);
                padding: 2px;
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                image: url(icons:/chevron-down.ico);
                padding: 2px;
            }
            QTreeView::branch:selected {
                background: #323232;
            }
        """
        )

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #1a1a1a;
                color: #d4d4d4;
            }
            QToolTip {
                background-color: #252526;
                color: #d4d4d4;
                border-radius: 4px;
                padding: 4px;
            }
            QMenuBar {
                background-color: #252526;
                color: #d4d4d4;
                border: none;
            }
            QMenuBar::item {
                background: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #323232;
            }
            QMenuBar::item:pressed {
                background-color: #3a3a3a;
            }
            QMenu {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 20px;
                border-radius: 0px;
            }
            QMenu::item:selected {
                background-color: #323232;
            }
            QMenu::separator {
                height: 1px;
                background: #3a3a3a;
                margin: 4px 0px;
            }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background: #404040;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4a4a4a;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: #1a1a1a;
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background: #404040;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #4a4a4a;
            }
        """
        )

        self.preview_action = QAction("Toggle Preview", self)
        self.preview_action.setShortcut(QKeySequence("Ctrl+P"))
        self.preview_action.triggered.connect(self.toggle_preview)

        self.create_menu_bar()

        self.welcome_screen = WelcomeScreen()
        self.tabs.addTab(
            self.welcome_screen, self.welcome_screen.tabname
        )

        self.clipboard_path = None
        self.clipboard_operation = None

        self.check_timer = QTimer()
        self.check_timer.timeout.connect(
            self.check_path_exists
        )
        self.check_timer.start(500)

        self.find_replace_dialog = None

    def show_status_message(
        self, msg, timeout=2000
    ):
        self.status_bar.showMessage(msg, timeout)

    def file_tree_(self):
        if not self.current_project_dir:
            self.open_folder()
            if not self.current_project_dir:
                return
            self.left_container.show()
            total = (
                self.splitter.sizes()[0] + self.splitter.sizes()[1]
            )
            self.splitter.setSizes(
                [self.tree_width, total - self.tree_width]
            )
        else:
            if (
                not self.left_container.isVisible()
            ):
                self.left_container.show()
                total = (
                    self.splitter.sizes()[0] + self.splitter.sizes()[1]
                )
                self.splitter.setSizes(
                    [self.tree_width, total - self.tree_width]
                )

    def toggle_file_tree(self):
        if not self.current_project_dir:
            self.file_tree_()
            return
        if self.left_container.isVisible():
            self.tree_width = self.splitter.sizes()[
                0
            ]
            self.left_container.hide()
            self.splitter.setSizes(
                [0, self.width()]
            )
        else:
            self.left_container.show()
            total = (
                self.splitter.sizes()[0] + self.splitter.sizes()[1]
            )
            self.splitter.setSizes(
                [self.tree_width, total - self.tree_width]
            )

    def on_splitter_moved(self, pos, index):
        if self.left_container.isVisible():
            self.tree_width = self.splitter.sizes()[
                0
            ]

    def on_resize(self, event):
        if self.left_container.isVisible():
            total = (
                self.splitter.sizes()[0] + self.splitter.sizes()[1]
            )
            self.splitter.setSizes(
                [self.tree_width, total - self.tree_width]
            )
        super().resizeEvent(event)

    def create_menu_bar(self):
        menubar = self.menuBar()

        menubar.setStyleSheet(
            """
            QMenuBar {
                background-color: #252526;
                border: none;
                padding: 2px;
                min-height: 28px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 4px 8px;
                margin: 0;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: #323232;
            }
            QMenuBar::item:pressed {
                background: #3a3a3a;
            }
            QMenu {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #323232;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 20px;
            }
            QMenu::item:selected {
                background-color: #323232;
            }
            QMenu::separator {
                height: 1px;
                background: #323232;
                margin: 4px 0px;
            }
        """
        )
        file_menu = menubar.addMenu("File")
        file_menu.addAction(
            "New...", self.new_file, QKeySequence.New
        )

        file_menu.addAction(
            "Open...", self.open_file, QKeySequence.Open
        )
        file_menu.addAction(
            "Open Folder...", self.open_folder, QKeySequence("Ctrl+K")
        )
        file_menu.addAction(
            "Close Folder", self.close_folder, QKeySequence("Ctrl+Shift+K")
        )
        file_menu.addAction(
            "Save", self.save_file, QKeySequence.Save
        )
        file_menu.addAction(
            "Save As...", self.save_file_as, QKeySequence("Ctrl+Shift+S")
        )
        file_menu.addSeparator()
        file_menu.addAction(
            "Toggle File Tree", self.toggle_file_tree, QKeySequence("Ctrl+B")
        )
        file_menu.addAction(
            "Explorer", self.file_tree_, QKeySequence("Ctrl+Shift+E")
        )
        file_menu.addSeparator()
        file_menu.addAction(
            "Exit", self.close, QKeySequence("Ctrl+Q")
        )

        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction(
            "Undo", self.undo, QKeySequence.Undo
        )
        edit_menu.addAction(
            "Redo", self.redo, QKeySequence.Redo
        )
        edit_menu.addSeparator()
        edit_menu.addAction(
            "Cut", self.cut, QKeySequence.Cut
        )
        edit_menu.addAction(
            "Copy", self.copy, QKeySequence.Copy
        )
        edit_menu.addAction(
            "Paste", self.paste, QKeySequence.Paste
        )
        edit_menu.addSeparator()
        edit_menu.addAction(
            "Select All", self.select_all, QKeySequence.SelectAll
        )
        edit_menu.addSeparator()
        edit_menu.addAction(
            "Find", self.show_find_dialog, QKeySequence("Ctrl+F")
        )
        edit_menu.addAction(
            "Replace", self.show_replace_dialog, QKeySequence("Ctrl+H")
        )

        view_menu = menubar.addMenu("View")
        view_menu.addAction(self.preview_action)
        self.preview_action.setVisible(False)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Open Folder",
            (
                os.path.dirname(os.path.abspath(__file__))
                if not self.current_project_dir
                else self.current_project_dir
            ),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )

        if folder:
            if self.fs_watcher.directories():
                self.fs_watcher.removePaths(self.fs_watcher.directories())
            if self.fs_watcher.files():
                self.fs_watcher.removePaths(self.fs_watcher.files())

            self.current_project_dir = folder
            self.fs_model.setRootPath(folder)
            root_index = self.fs_model.index(folder)
            self.file_tree.setRootIndex(
                root_index
            )
            self.folder_label.setText(
                os.path.basename(folder).upper()
            )
            self.setWindowTitle(
                f"Zerion Editor - {os.path.basename(folder)}"
            )

            self.fs_watcher.addPath(folder)

            self.folder_section.show()
            self.left_container.show()
            self.splitter.setSizes(
                [self.tree_width, self.width() - self.tree_width]
            )
            self.show_status_message(
                f"Folder - {folder}"
            )

    def on_directory_changed(self, path):
        self.fs_model.setRootPath(
            self.current_project_dir
        )

        if path not in self.fs_watcher.directories():
            self.fs_watcher.addPath(path)

    def close_tabs_for_deleted_file(self, path):
        tabs_to_remove = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if (
                hasattr(tab, "filepath") and tab.filepath == path
            ):
                tabs_to_remove.append(i)
        for i in reversed(tabs_to_remove):
            self.tabs.removeTab(i)

    def on_file_changed(self, path):
        if not os.path.exists(path):
            self.close_tabs_for_deleted_file(path)

            if path in self.fs_watcher.files():
                self.fs_watcher.removePath(path)
            return

        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if (
                hasattr(tab, "filepath") and tab.filepath == path
            ):
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        content = file.read()
                    if not tab.is_modified:
                        tab.editor.setText(content)
                except:
                    pass
                break

        if (
            os.path.exists(path) and path not in self.fs_watcher.files()
        ):
            self.fs_watcher.addPath(path)

    def update_folder_title(self):
        folder_name = os.path.basename(self.current_project_dir)
        self.folder_label.setText(folder_name.upper())
        self.setWindowTitle(f"Zerion Editor - {folder_name}")

    def select_all(self):
        if editor := self.get_current_editor():
            editor.selectAll()

    def get_current_editor(self):
        current = self.tabs.currentWidget()
        return current.editor if current else None

    def undo(self):
        if editor := self.get_current_editor():
            editor.undo()

    def redo(self):
        if editor := self.get_current_editor():
            editor.redo()

    def cut(self):
        if editor := self.get_current_editor():
            editor.cut()

    def copy(self):
        if editor := self.get_current_editor():
            editor.copy()

    def paste(self):
        if editor := self.get_current_editor():
            editor.paste()

    def new_file(self):
        tab = EditorTab(main_window=self)
        index = self.tabs.addTab(tab, "Untitled")
        self.tabs.setCurrentIndex(index)
        tab.editor.setFocus()

    def open_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Zerion Files (*.zer);;All Files (*.*)"
        )
        if fname:
            self.open_specific_file(fname)

    def on_file_tree_clicked(self, index):
        path = self.fs_model.filePath(index)
        if os.path.isfile(path):
            self.open_specific_file(path)
        else:
            self.show_status_message(f"Folder - {path}")

    def open_specific_file(self, path):
        abs_path = os.path.abspath(path)
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab.filepath and os.path.abspath(tab.filepath) == abs_path:
                self.tabs.setCurrentIndex(i)
                return

        try:
            image_extensions = [
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".bmp",
                ".ico",
                ".webp",
                ".tiff",
                ".tif",
                ".svg",
                ".psd",
                ".raw",
                ".heif",
                ".heic",
            ]
            file_ext = os.path.splitext(path)[1].lower()
            if file_ext in image_extensions:
                tab = ImageViewer(abs_path)
            else:
                with open(path, "rb") as f:
                    content = f.read().decode("utf-8")
                name: str = os.path.basename(path)
                tab = EditorTab(
                    abs_path, main_window=self
                )
                tab.editor.setText(content)
                tab.save()
            index = self.tabs.addTab(tab, tab.tabname)
            self.tabs.setCurrentIndex(index)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open file: {str(e)}")

    def save_file(self):
        current = self.tabs.currentWidget()
        if not current:
            return
        if isinstance(current, WelcomeScreen):
            return
        if not current.filepath:
            self.save_file_as()
        else:
            if isinstance(current, ImageViewer):
                return
            content = current.editor.text().encode("utf-8")
            try:
                with open(current.filepath, "wb") as f:
                    f.write(content)
                current.save()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not save file: {str(e)}")

    def save_file_as(self):
        current = self.tabs.currentWidget()
        if not current:
            return
        if isinstance(current, WelcomeScreen):
            return
        if isinstance(current, ImageViewer):
            return
        fname, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "Zerion Files (*.zer);;All Files (*.*)"
        )
        if fname:
            current.filepath = fname
            name = os.path.basename(fname)
            self.tabs.setTabText(
                self.tabs.currentIndex(), name
            )
            self.save_file()
        else:
            return

    def close_tab(self, index):
        tab = self.tabs.widget(index)
        if tab.is_modified:
            reply = QMessageBox.question(
                self,
                "Save Changes",
                "This file has unsaved changes. Save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return False
            elif reply == QMessageBox.Discard:
                pass

        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.close()
        return True

    def close_file_tab(self, filepath):
        abs_path = os.path.abspath(filepath)
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if (
                tab.filepath and os.path.abspath(tab.filepath) == abs_path
            ):
                self.tabs.removeTab(i)
                break

        if self.tabs.count() == 0:
            self.close()

    def closeEvent(self, event):
        while self.tabs.count() > 0:
            tab = self.tabs.widget(0)
            if tab.is_modified:
                reply = QMessageBox.question(
                    self,
                    "Save Changes",
                    "This file has unsaved changes. Save before closing?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                )
                if reply == QMessageBox.Save:
                    self.save_file()
                    if tab.is_modified:
                        event.ignore()
                        return
                elif reply == QMessageBox.Cancel:
                    event.ignore()
                    return
                elif reply == QMessageBox.Discard:
                    pass
            self.tabs.removeTab(0)
        event.accept()

    def show_context_menu(self, position):
        index = self.file_tree.indexAt(position)
        context_menu = QMenu()
        context_menu.setStyleSheet(
            """
            QMenu {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #323232;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 20px;
            }
            QMenu::item:selected {
                background-color: #323232;
            }
            QMenu::separator {
                height: 1px;
                background: #323232;
                margin: 4px 0px;
            }"""
        )

        if index.isValid():
            path = self.fs_model.filePath(index)
            is_dir = os.path.isdir(path)

            if is_dir:
                new_file_action = context_menu.addAction("New File")
                new_file_action.triggered.connect(lambda: self.create_new_file(index))
                new_folder_action = context_menu.addAction("New Folder")
                new_folder_action.triggered.connect(
                    lambda: self.create_new_folder(index)
                )
                context_menu.addSeparator()

            copy_action = context_menu.addAction("Copy")
            copy_action.triggered.connect(lambda: self.copy_item(index))
            cut_action = context_menu.addAction("Cut")
            cut_action.triggered.connect(lambda: self.cut_item(index))

            if self.clipboard_path:
                paste_action = context_menu.addAction("Paste")
                paste_action.triggered.connect(lambda: self.paste_item(index))

            context_menu.addSeparator()
            delete_action = context_menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self.delete_item(index))
            rename_action = context_menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self.rename_item(index))
        else:
            new_file_action = context_menu.addAction("New File")
            new_file_action.triggered.connect(lambda: self.create_new_file(index))
            new_folder_action = context_menu.addAction("New Folder")
            new_folder_action.triggered.connect(lambda: self.create_new_folder(index))
            if self.clipboard_path:
                context_menu.addSeparator()
                paste_action = context_menu.addAction("Paste")
                paste_action.triggered.connect(lambda: self.paste_item(index))

        context_menu.exec_(self.file_tree.viewport().mapToGlobal(position))

    def check_path_exists(self):
        if self.current_project_dir and not os.path.exists(self.current_project_dir):
            QMessageBox.warning(
                self,
                "Directory Error",
                "This working directory no longer exists.\nPlease reopen a valid folder.",
            )
            self.current_project_dir = None
            self.left_container.hide()
            self.folder_section.hide()
            self.splitter.setSizes([0, self.width()])
            return False

        tabs_to_close = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "filepath") and tab.filepath:
                if not os.path.exists(tab.filepath):
                    QMessageBox.warning(
                        self,
                        "File Error",
                        f"This file '{os.path.basename(tab.filepath)}' no longer exists.",
                    )
                    tabs_to_close.append(i)

        for i in reversed(tabs_to_close):
            self.tabs.removeTab(i)

        return True

    def create_new_file(self, index):
        if not self.check_path_exists():
            return

        if index.isValid():
            path = self.fs_model.filePath(index)
            if not os.path.isdir(path):
                path = os.path.dirname(path)
        else:
            path = self.current_project_dir

        self.show_status_message(f"Folder - {path}")

        file_name, ok = QInputDialog.getText(
            self, "New File", "Enter file name:", QLineEdit.Normal, ""
        )

        if ok and file_name:
            file_path = os.path.join(path, file_name)

            if os.path.exists(file_path):
                QMessageBox.warning(self, "Error", "File already exists!")
                return

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("")

                self.open_specific_file(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create file: {str(e)}")

    def create_new_folder(self, index):
        if not self.check_path_exists():
            return

        if index.isValid():
            path = self.fs_model.filePath(index)
            if not os.path.isdir(path):
                path = os.path.dirname(path)
        else:
            path = self.current_project_dir

        self.show_status_message(f"Folder - {path}")

        folder_name, ok = QInputDialog.getText(
            self, "New Folder", "Enter folder name:", QLineEdit.Normal, ""
        )
        if ok and folder_name:
            folder_path = os.path.join(path, folder_name)
            try:
                os.makedirs(folder_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create folder: {str(e)}")

    def copy_item(self, index):
        path = self.fs_model.filePath(index)
        self.show_status_message(f"Folder - {os.path.dirname(path)}")
        self.clipboard_path = path
        self.clipboard_operation = "copy"

    def cut_item(self, index):
        path = self.fs_model.filePath(index)
        self.show_status_message(f"Folder - {os.path.dirname(path)}")
        self.close_file_tab(path)
        self.clipboard_path = path
        self.clipboard_operation = "cut"

    def paste_item(self, index):
        if not self.check_path_exists():
            return

        if not self.clipboard_path:
            return

        target_path = self.current_project_dir
        if index.isValid():
            path = self.fs_model.filePath(index)
            target_path = (
                path if os.path.isdir(path) else os.path.dirname(path)
            )

        self.show_status_message(
            f"Folder - {target_path}"
        )

        try:
            filename = os.path.basename(
                self.clipboard_path
            )
            new_path = os.path.join(target_path, filename)

            if os.path.exists(
                new_path
            ):
                self.close_file_tab(
                    new_path
                )
                reply = QMessageBox.question(
                    self,
                    "File exists",
                    "File already exists. Replace it?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return

            import shutil

            if self.clipboard_operation == "copy":
                if os.path.isdir(self.clipboard_path):
                    shutil.copytree(self.clipboard_path, new_path)
                else:
                    with open(self.clipboard_path, "rb") as src:
                        content = src.read()
                    with open(new_path, "wb") as dst:
                        dst.write(content)
            else:
                self.close_file_tab(
                    self.clipboard_path
                )
                shutil.move(
                    self.clipboard_path, new_path
                )
                self.clipboard_path = None

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Operation failed: {str(e)}")

    def delete_item(self, index):
        if not self.check_path_exists():
            return

        path = self.fs_model.filePath(index)
        self.show_status_message(
            f"Folder - {os.path.dirname(path)}"
        )
        try:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete '{os.path.basename(path)}'?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.close_file_tab(path)
                import shutil

                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not delete: {str(e)}")

    def rename_item(self, index):
        if not self.check_path_exists():
            return

        old_path = self.fs_model.filePath(index)
        self.show_status_message(
            f"Folder - {os.path.dirname(old_path)}"
        )
        old_name = os.path.basename(old_path)

        new_name, ok = QInputDialog.getText(
            self, "Rename", "Enter new name:", QLineEdit.Normal, old_name
        )

        if (
            ok and new_name and new_name != old_name
        ):
            try:
                new_path = os.path.join(
                    os.path.dirname(old_path), new_name
                )
                self.close_file_tab(old_path)
                os.rename(old_path, new_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not rename: {str(e)}")

    def on_tab_changed(self, index):
        if index == -1:
            return

        current = self.tabs.widget(index)
        if current is None:
            return

        tab = self.tabs.widget(index)
        if isinstance(tab, WelcomeScreen):
            self.show_status_message("Welcome")
            self.status_position.clear()
            self.status_file.clear()
            self.status_folder.clear()
        elif isinstance(tab, ImageViewer):
            self.show_status_message("Ready")
            self.status_position.clear()
            self.status_file.setText(
                f"File - {tab.filepath}"
            )
        else:
            line, col = tab.editor.getCursorPosition()
            self.show_status_message("Ready")
            self.status_position.setText(
                f"Ln {line + 1}, Col {col + 1}"
            )
            if tab.filepath:
                self.status_file.setText(
                    f"File - {tab.filepath}"
                )
            else:
                self.status_file.setText(
                    "File - Untitled"
                )
                self.status_folder.clear()

    def toggle_preview(self):
        current = self.tabs.currentWidget()
        if hasattr(current, "is_markdown") and current.is_markdown:
            current.toggle_markdown_preview()

    def close_folder(self):
        if self.fs_watcher.directories():
            self.fs_watcher.removePaths(
                self.fs_watcher.directories()
            )
        if self.fs_watcher.files():
            self.fs_watcher.removePaths(self.fs_watcher.files())

        self.current_project_dir = None
        self.fs_model.setRootPath("")
        self.file_tree.setRootIndex(
            self.fs_model.index("")
        )
        self.left_container.hide()
        self.folder_section.hide()
        self.splitter.setSizes([0, self.width()])

        self.setWindowTitle("Zerion Editor")
        self.show_status_message("Folder closed")
        self.status_folder.clear()

    def show_find_dialog(self):
        editor = self.get_current_editor()
        if not editor:
            return
        if not self.find_replace_dialog or self.find_replace_dialog.editor != editor:
            self.find_replace_dialog = FindReplaceDialog(self, editor)
        self.find_replace_dialog.replace_input.hide()
        self.find_replace_dialog.replace_label.hide()
        self.find_replace_dialog.replace_btn.hide()
        self.find_replace_dialog.replace_all_btn.hide()
        self.find_replace_dialog.show()
        self.find_replace_dialog.find_input.setFocus()

    def show_replace_dialog(self):
        editor = self.get_current_editor()
        if not editor:
            return
        if not self.find_replace_dialog or self.find_replace_dialog.editor != editor:
            self.find_replace_dialog = FindReplaceDialog(self, editor)
        self.find_replace_dialog.replace_input.show()
        self.find_replace_dialog.replace_label.show()
        self.find_replace_dialog.replace_btn.show()
        self.find_replace_dialog.replace_all_btn.show()
        self.find_replace_dialog.show()
        self.find_replace_dialog.replace_input.setFocus()


def main():
    app = QApplication(sys.argv)
    app.setStyle(
        "Fusion"
    )
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
