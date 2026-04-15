from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QLabel, QGroupBox, QHBoxLayout, QPushButton
)


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setMinimumWidth(400)
        self.settings = settings
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["cloud", "local"])
        self.mode_combo.setCurrentText(settings.get("api_mode", "cloud"))
        form.addRow("API 模式", self.mode_combo)

        cloud_group = QGroupBox("云端设置 (硅基流动)")
        cloud_layout = QFormLayout()
        self.cloud_url = QLineEdit(settings.get("cloud_base_url", ""))
        self.cloud_key = QLineEdit(settings.get("cloud_api_key", ""))
        self.cloud_key.setEchoMode(QLineEdit.Password)
        cloud_layout.addRow("Base URL", self.cloud_url)
        cloud_layout.addRow("API Key", self.cloud_key)
        cloud_group.setLayout(cloud_layout)

        local_group = QGroupBox("本地设置 (OpenAI 兼容)")
        local_layout = QFormLayout()
        self.local_url = QLineEdit(settings.get("local_base_url", ""))
        self.local_key = QLineEdit(settings.get("local_api_key", ""))
        self.local_key.setEchoMode(QLineEdit.Password)
        local_layout.addRow("Base URL", self.local_url)
        local_layout.addRow("API Key", self.local_key)
        local_group.setLayout(local_layout)

        layout.addLayout(form)
        layout.addWidget(cloud_group)
        layout.addWidget(local_group)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def save(self):
        self.settings.set("api_mode", self.mode_combo.currentText())
        self.settings.set("cloud_base_url", self.cloud_url.text().strip())
        self.settings.set("cloud_api_key", self.cloud_key.text().strip())
        self.settings.set("local_base_url", self.local_url.text().strip())
        self.settings.set("local_api_key", self.local_key.text().strip())
        self.settings.save()
        self.accept()
