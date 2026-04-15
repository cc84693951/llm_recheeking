from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal


class FileListWidget(QWidget):
    item_selected = pyqtSignal(int)
    open_image_clicked = pyqtSignal()
    open_folder_clicked = pyqtSignal()
    open_annotation_clicked = pyqtSignal()
    save_all_clicked = pyqtSignal()
    export_excel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)

        # 文件操作按钮
        btn_layout = QHBoxLayout()
        self.btn_open_image = QPushButton("打开图片")
        self.btn_open_folder = QPushButton("打开文件夹")
        btn_layout.addWidget(self.btn_open_image)
        btn_layout.addWidget(self.btn_open_folder)
        self.layout.addLayout(btn_layout)

        anno_layout = QHBoxLayout()
        self.btn_open_annotation = QPushButton("导入标注")
        self.btn_open_annotation.setToolTip("批量导入 VOC / YOLO / COCO 标注")
        anno_layout.addWidget(self.btn_open_annotation)
        self.layout.addLayout(anno_layout)

        export_layout = QHBoxLayout()
        self.btn_save_all = QPushButton("保存所有结果")
        self.btn_export_excel = QPushButton("导出 Excel")
        export_layout.addWidget(self.btn_save_all)
        export_layout.addWidget(self.btn_export_excel)
        self.layout.addLayout(export_layout)

        self.label = QLabel("文件列表")
        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(240)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.list_widget)
        self.files = []
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.btn_open_image.clicked.connect(self.open_image_clicked.emit)
        self.btn_open_folder.clicked.connect(self.open_folder_clicked.emit)
        self.btn_open_annotation.clicked.connect(self.open_annotation_clicked.emit)
        self.btn_save_all.clicked.connect(self.save_all_clicked.emit)
        self.btn_export_excel.clicked.connect(self.export_excel_clicked.emit)

    def set_files(self, files):
        self.files = files
        self.list_widget.clear()
        for f in files:
            self.list_widget.addItem(f)

    def select_index(self, idx):
        if 0 <= idx < self.list_widget.count():
            self.list_widget.setCurrentRow(idx)

    def _on_row_changed(self, idx):
        if 0 <= idx < len(self.files):
            self.item_selected.emit(idx)
