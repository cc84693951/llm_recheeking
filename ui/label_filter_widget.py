from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QCheckBox, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal


class LabelFilterWidget(QWidget):
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.addWidget(QLabel("送检 Label 过滤"))
        self.list_widget = QListWidget()
        self.layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("全选")
        self.btn_clear = QPushButton("清空")
        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_clear)
        self.layout.addLayout(btn_layout)

        self.btn_select_all.clicked.connect(self.select_all)
        self.btn_clear.clicked.connect(self.clear_all)

    def refresh(self, labels):
        self.list_widget.clear()
        for label in sorted(set(labels)):
            item = QListWidgetItem(label)
            item.setCheckState(2)  # Checked
            self.list_widget.addItem(item)
        self.selection_changed.emit()

    def select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(2)
        self.selection_changed.emit()

    def clear_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(0)
        self.selection_changed.emit()

    def get_selected_labels(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == 2:
                selected.append(item.text())
        return selected
