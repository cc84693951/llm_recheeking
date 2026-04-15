from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout


class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("送检进度")
        self.setModal(True)
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        self.label = QLabel("准备中...")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addLayout(btn_layout)
        self.btn_cancel.clicked.connect(self.reject)

    def set_progress(self, current, total):
        if total > 0:
            pct = int(current * 100 / total)
            self.progress.setValue(pct)
            self.label.setText(f"进度: {current} / {total}")

    def finish(self):
        self.progress.setValue(100)
        self.label.setText("完成")
        self.btn_cancel.setText("关闭")
