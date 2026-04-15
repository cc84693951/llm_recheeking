from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QLabel, QLineEdit,
    QHBoxLayout, QPushButton, QMessageBox
)
from PyQt5.QtCore import pyqtSignal


class LabelListWidget(QWidget):
    label_selected = pyqtSignal(str)
    label_changed = pyqtSignal(str, str)  # old, new
    bbox_delete_requested = pyqtSignal()   # 请求删除当前选中框

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel("标签列表"))
        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(240)
        layout.addWidget(self.list_widget)

        edit_layout = QHBoxLayout()
        self.edit_label = QLineEdit()
        self.edit_label.setPlaceholderText("修改选中标签")
        self.btn_edit = QPushButton("修改")
        edit_layout.addWidget(self.edit_label)
        edit_layout.addWidget(self.btn_edit)
        layout.addLayout(edit_layout)

        action_layout = QHBoxLayout()
        self.btn_delete = QPushButton("删除框")
        action_layout.addWidget(self.btn_delete)
        layout.addLayout(action_layout)

        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self._labels = []
        self._last_selected_label = ""

    def refresh(self, bbox_manager):
        # 记住之前选中的 label
        prev_label = self._last_selected_label
        self.list_widget.clear()
        labels = []
        for idx, bbox in enumerate(bbox_manager.bboxes):
            label = bbox.label or f"#{idx}"
            text = f"{label}  ({bbox.x},{bbox.y},{bbox.w},{bbox.h})"
            if text not in labels:
                labels.append(text)
                self.list_widget.addItem(text)
        self._labels = labels
        # 恢复选中
        if prev_label:
            for i in range(self.list_widget.count()):
                item_text = self.list_widget.item(i).text()
                item_label = item_text.split("  ")[0]
                if item_label == prev_label:
                    self.list_widget.setCurrentRow(i)
                    break

    def _on_item_clicked(self, item):
        text = item.text()
        label = text.split("  ")[0]
        self._last_selected_label = label
        self.label_selected.emit(label)
        self.edit_label.setText(label)

    def _on_selection_changed(self):
        item = self.list_widget.currentItem()
        if item:
            text = item.text()
            label = text.split("  ")[0]
            self._last_selected_label = label
            self.edit_label.setText(label)

    def _on_edit(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先点击列表选中一个标签")
            return
        current_text = item.text()
        current_label = current_text.split("  ")[0]
        new = self.edit_label.text().strip()
        if not new:
            QMessageBox.information(self, "提示", "标签名称不能为空")
            return
        if new != current_label:
            self.label_changed.emit(current_label, new)
            self._last_selected_label = new

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先点击列表选中一个标签对应的框")
            return
        self.bbox_delete_requested.emit()
