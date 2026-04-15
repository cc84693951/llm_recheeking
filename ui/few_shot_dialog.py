import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QListWidget, QMessageBox, QFileDialog
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class FewShotDialog(QDialog):
    def __init__(self, few_shots, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Few-Shot 管理")
        self.setMinimumSize(500, 550)
        self.few_shots = list(few_shots) if few_shots else []
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self._refresh_list()
        layout.addWidget(QLabel("示例列表"))
        layout.addWidget(self.list_widget)

        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("User 内容:"))
        self.user_edit = QTextEdit()
        self.user_edit.setMaximumHeight(80)
        form_layout.addWidget(self.user_edit)

        img_layout = QHBoxLayout()
        self.lbl_image = QLabel("图片: 无")
        self.lbl_image.setWordWrap(True)
        self.btn_select_image = QPushButton("选择图片")
        self.btn_clear_image = QPushButton("清除图片")
        img_layout.addWidget(self.lbl_image, 1)
        img_layout.addWidget(self.btn_select_image)
        img_layout.addWidget(self.btn_clear_image)
        form_layout.addLayout(img_layout)

        # 图片预览
        preview_layout = QHBoxLayout()
        self.img_preview = QLabel("暂无图片预览")
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.setFixedSize(200, 200)
        self.img_preview.setStyleSheet("border: 1px solid gray; background-color: #2b2b2b; color: #cccccc;")
        self.img_preview.setScaledContents(True)
        preview_layout.addWidget(self.img_preview)
        form_layout.addLayout(preview_layout)

        form_layout.addWidget(QLabel("Assistant 内容:"))
        self.assistant_edit = QTextEdit()
        self.assistant_edit.setMaximumHeight(80)
        form_layout.addWidget(self.assistant_edit)
        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("添加")
        self.btn_update = QPushButton("更新选中")
        self.btn_delete = QPushButton("删除选中")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_ok = QPushButton("确定")
        bottom.addWidget(self.btn_ok)
        layout.addLayout(bottom)

        self.btn_add.clicked.connect(self.add_item)
        self.btn_update.clicked.connect(self.update_item)
        self.btn_delete.clicked.connect(self.delete_item)
        self.btn_ok.clicked.connect(self.accept)
        self.list_widget.currentRowChanged.connect(self.load_item)
        self.btn_select_image.clicked.connect(self._select_image)
        self.btn_clear_image.clicked.connect(self._clear_image)
        self._current_image_path = ""

    def _refresh_list(self):
        self.list_widget.clear()
        for i, shot in enumerate(self.few_shots):
            has_img = "[图] " if shot.get("image_path") else ""
            label = f"#{i} {has_img}User: {shot.get('user','')[:20]}..."
            self.list_widget.addItem(label)

    def _update_preview(self, path):
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.img_preview.width(), self.img_preview.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.img_preview.setPixmap(scaled)
                return
        self.img_preview.setText("暂无图片预览")
        self.img_preview.setPixmap(QPixmap())

    def _select_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        if path:
            self._current_image_path = path
            self.lbl_image.setText(f"图片: {os.path.basename(path)}")
            self._update_preview(path)

    def _clear_image(self):
        self._current_image_path = ""
        self.lbl_image.setText("图片: 无")
        self._update_preview("")

    def add_item(self):
        user = self.user_edit.toPlainText().strip()
        assistant = self.assistant_edit.toPlainText().strip()
        if not user and not assistant:
            QMessageBox.warning(self, "提示", "内容不能为空")
            return
        shot = {"user": user, "assistant": assistant}
        if self._current_image_path:
            shot["image_path"] = self._current_image_path
        self.few_shots.append(shot)
        self._refresh_list()
        self.user_edit.clear()
        self.assistant_edit.clear()
        self._clear_image()

    def update_item(self):
        idx = self.list_widget.currentRow()
        if idx < 0:
            return
        user = self.user_edit.toPlainText().strip()
        assistant = self.assistant_edit.toPlainText().strip()
        shot = {"user": user, "assistant": assistant}
        if self._current_image_path:
            shot["image_path"] = self._current_image_path
        self.few_shots[idx] = shot
        self._refresh_list()

    def delete_item(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            del self.few_shots[idx]
            self._refresh_list()
            self._clear_image()

    def load_item(self, idx):
        if 0 <= idx < len(self.few_shots):
            shot = self.few_shots[idx]
            self.user_edit.setPlainText(shot.get("user", ""))
            self.assistant_edit.setPlainText(shot.get("assistant", ""))
            img_path = shot.get("image_path", "")
            self._current_image_path = img_path
            if img_path:
                self.lbl_image.setText(f"图片: {os.path.basename(img_path)}")
            else:
                self.lbl_image.setText("图片: 无")
            self._update_preview(img_path)
        else:
            self._clear_image()

    def get_few_shots(self):
        return self.few_shots
