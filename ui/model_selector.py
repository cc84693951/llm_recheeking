from PyQt5.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLineEdit, QPushButton, QMessageBox
from core.model_fetcher import fetch_silicon_flow_models


class ModelSelector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setMinimumWidth(200)
        self.btn_refresh = QPushButton("刷新模型")
        self.layout.addWidget(self.combo)
        self.layout.addWidget(self.btn_refresh)
        self.btn_refresh.clicked.connect(self.refresh_models)
        self.models = []

    def set_current_text(self, text):
        self.combo.setCurrentText(text)

    def current_text(self):
        return self.combo.currentText().strip()

    def refresh_models(self, api_key=""):
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("刷新中...")
        try:
            models = fetch_silicon_flow_models(api_key)
            self.models = models
            current = self.combo.currentText()
            self.combo.clear()
            self.combo.addItems(models)
            self.combo.setCurrentText(current)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"获取模型列表失败: {e}")
        finally:
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setText("刷新模型")
