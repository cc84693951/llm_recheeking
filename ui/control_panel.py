from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QDoubleSpinBox, QSpinBox, QCheckBox,
    QGroupBox, QFormLayout, QMessageBox, QComboBox
)
from PyQt5.QtCore import pyqtSignal
from ui.model_selector import ModelSelector


class ControlPanel(QWidget):
    inspect_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    few_shot_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    expand_preview_changed = pyqtSignal(bool)
    scope_changed = pyqtSignal()
    preview_system_md_clicked = pyqtSignal()
    import_system_md_clicked = pyqtSignal()
    export_system_md_clicked = pyqtSignal()
    preview_user_md_clicked = pyqtSignal()
    import_user_md_clicked = pyqtSignal()
    export_user_md_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 模型选择
        layout.addWidget(QLabel("模型选择"))
        self.model_selector = ModelSelector()
        layout.addWidget(self.model_selector)

        # 系统提示词
        layout.addWidget(QLabel("系统提示词"))
        self.system_prompt = QTextEdit()
        self.system_prompt.setMaximumHeight(80)
        layout.addWidget(self.system_prompt)
        sys_btn_layout = QHBoxLayout()
        self.btn_sys_preview = QPushButton("预览")
        self.btn_sys_import = QPushButton("导入 MD")
        self.btn_sys_export = QPushButton("导出 MD")
        sys_btn_layout.addWidget(self.btn_sys_preview)
        sys_btn_layout.addWidget(self.btn_sys_import)
        sys_btn_layout.addWidget(self.btn_sys_export)
        layout.addLayout(sys_btn_layout)

        # 用户提示词
        layout.addWidget(QLabel("用户提示词"))
        self.user_prompt = QTextEdit()
        self.user_prompt.setMaximumHeight(80)
        layout.addWidget(self.user_prompt)
        usr_btn_layout = QHBoxLayout()
        self.btn_usr_preview = QPushButton("预览")
        self.btn_usr_import = QPushButton("导入 MD")
        self.btn_usr_export = QPushButton("导出 MD")
        usr_btn_layout.addWidget(self.btn_usr_preview)
        usr_btn_layout.addWidget(self.btn_usr_import)
        usr_btn_layout.addWidget(self.btn_usr_export)
        layout.addLayout(usr_btn_layout)

        # few-shot & settings
        btn_layout = QHBoxLayout()
        self.btn_few_shot = QPushButton("Few-Shot")
        self.btn_settings = QPushButton("系统设置")
        btn_layout.addWidget(self.btn_few_shot)
        btn_layout.addWidget(self.btn_settings)
        layout.addLayout(btn_layout)

        # 模型参数
        param_group = QGroupBox("模型参数")
        param_form = QFormLayout()
        self.spin_temperature = QDoubleSpinBox()
        self.spin_temperature.setRange(0, 2)
        self.spin_temperature.setSingleStep(0.1)
        self.spin_temperature.setValue(0.7)
        param_form.addRow("Temperature", self.spin_temperature)

        self.spin_top_p = QDoubleSpinBox()
        self.spin_top_p.setRange(0, 1)
        self.spin_top_p.setSingleStep(0.05)
        self.spin_top_p.setValue(0.9)
        param_form.addRow("Top P", self.spin_top_p)

        self.spin_max_tokens = QSpinBox()
        self.spin_max_tokens.setRange(1, 8192)
        self.spin_max_tokens.setValue(512)
        param_form.addRow("Max Tokens", self.spin_max_tokens)

        self.spin_freq_penalty = QDoubleSpinBox()
        self.spin_freq_penalty.setRange(-2, 2)
        self.spin_freq_penalty.setSingleStep(0.1)
        self.spin_freq_penalty.setValue(0.0)
        param_form.addRow("Frequency Penalty", self.spin_freq_penalty)

        self.spin_pres_penalty = QDoubleSpinBox()
        self.spin_pres_penalty.setRange(-2, 2)
        self.spin_pres_penalty.setSingleStep(0.1)
        self.spin_pres_penalty.setValue(0.0)
        param_form.addRow("Presence Penalty", self.spin_pres_penalty)
        param_group.setLayout(param_form)
        layout.addWidget(param_group)

        # 扩展倍数
        expand_group = QGroupBox("扩展倍数")
        expand_layout = QVBoxLayout()
        self.chk_preview = QCheckBox("预览扩展框")
        expand_layout.addWidget(self.chk_preview)

        def add_expand_row(label, checkbox_name, spin_name, default=1.0):
            row = QHBoxLayout()
            chk = QCheckBox(label)
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setRange(0.001, 99)
            spin.setSingleStep(0.1)
            spin.setValue(default)
            spin.setEnabled(False)
            chk.toggled.connect(spin.setEnabled)
            row.addWidget(chk)
            row.addWidget(spin)
            expand_layout.addLayout(row)
            setattr(self, checkbox_name, chk)
            setattr(self, spin_name, spin)

        add_expand_row("中心", "chk_center", "spin_center", 1.0)
        add_expand_row("上", "chk_top", "spin_top", 1.0)
        add_expand_row("下", "chk_bottom", "spin_bottom", 1.0)
        add_expand_row("左", "chk_left", "spin_left", 1.0)
        add_expand_row("右", "chk_right", "spin_right", 1.0)

        # 互斥逻辑：勾选中心时禁用四方向；勾选四方向任一，禁用中心
        def on_center_toggled(checked):
            for chk in (self.chk_top, self.chk_bottom, self.chk_left, self.chk_right):
                chk.setEnabled(not checked)
                if checked:
                    chk.setChecked(False)

        def on_dir_toggled(checked):
            if checked:
                self.chk_center.setEnabled(False)
                self.chk_center.setChecked(False)
            else:
                # 如果所有方向都没勾选，恢复中心可用
                if not any((self.chk_top.isChecked(), self.chk_bottom.isChecked(),
                            self.chk_left.isChecked(), self.chk_right.isChecked())):
                    self.chk_center.setEnabled(True)

        self.chk_center.toggled.connect(on_center_toggled)
        for chk in (self.chk_top, self.chk_bottom, self.chk_left, self.chk_right):
            chk.toggled.connect(on_dir_toggled)

        expand_group.setLayout(expand_layout)
        layout.addWidget(expand_group)

        # 送检范围
        scope_layout = QHBoxLayout()
        scope_layout.addWidget(QLabel("送检范围:"))
        self.combo_scope = QComboBox()
        self.combo_scope.addItems(["当前图片", "所有图片"])
        scope_layout.addWidget(self.combo_scope)
        layout.addLayout(scope_layout)

        # 操作按钮
        action_layout = QHBoxLayout()
        self.btn_inspect = QPushButton("开始送检")
        self.btn_save = QPushButton("保存结果")
        action_layout.addWidget(self.btn_inspect)
        action_layout.addWidget(self.btn_save)
        layout.addLayout(action_layout)

        layout.addStretch()

        # signals
        self.btn_inspect.clicked.connect(self.inspect_clicked.emit)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.btn_few_shot.clicked.connect(self.few_shot_clicked.emit)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        self.chk_preview.stateChanged.connect(lambda: self.expand_preview_changed.emit(self.chk_preview.isChecked()))
        self.combo_scope.currentIndexChanged.connect(self.scope_changed.emit)
        self.btn_sys_preview.clicked.connect(self.preview_system_md_clicked.emit)
        self.btn_sys_import.clicked.connect(self.import_system_md_clicked.emit)
        self.btn_sys_export.clicked.connect(self.export_system_md_clicked.emit)
        self.btn_usr_preview.clicked.connect(self.preview_user_md_clicked.emit)
        self.btn_usr_import.clicked.connect(self.import_user_md_clicked.emit)
        self.btn_usr_export.clicked.connect(self.export_user_md_clicked.emit)

    def get_prompts(self):
        return self.system_prompt.toPlainText(), self.user_prompt.toPlainText()

    def set_prompts(self, system, user):
        self.system_prompt.setPlainText(system)
        self.user_prompt.setPlainText(user)

    def get_params(self):
        return {
            "temperature": self.spin_temperature.value(),
            "top_p": self.spin_top_p.value(),
            "max_tokens": self.spin_max_tokens.value(),
            "frequency_penalty": self.spin_freq_penalty.value(),
            "presence_penalty": self.spin_pres_penalty.value(),
        }

    def set_params(self, params):
        self.spin_temperature.setValue(params.get("temperature", 0.7))
        self.spin_top_p.setValue(params.get("top_p", 0.9))
        self.spin_max_tokens.setValue(params.get("max_tokens", 512))
        self.spin_freq_penalty.setValue(params.get("frequency_penalty", 0.0))
        self.spin_pres_penalty.setValue(params.get("presence_penalty", 0.0))

    def get_inspect_scope(self):
        return "current" if self.combo_scope.currentIndex() == 0 else "all"

    def get_expand_settings(self):
        settings = {}
        if self.chk_center.isChecked():
            settings["center"] = self.spin_center.value()
        if self.chk_top.isChecked():
            settings["top"] = self.spin_top.value()
        if self.chk_bottom.isChecked():
            settings["bottom"] = self.spin_bottom.value()
        if self.chk_left.isChecked():
            settings["left"] = self.spin_left.value()
        if self.chk_right.isChecked():
            settings["right"] = self.spin_right.value()
        return settings

    def set_expand_settings(self, settings):
        def set_one(chk, spin, key):
            val = settings.get(key)
            if val is not None:
                chk.setChecked(True)
                spin.setValue(val)
            else:
                chk.setChecked(False)
        set_one(self.chk_center, self.spin_center, "center")
        set_one(self.chk_top, self.spin_top, "top")
        set_one(self.chk_bottom, self.spin_bottom, "bottom")
        set_one(self.chk_left, self.spin_left, "left")
        set_one(self.chk_right, self.spin_right, "right")
