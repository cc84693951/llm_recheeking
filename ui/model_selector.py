from PyQt5.QtWidgets import QWidget, QHBoxLayout, QComboBox, QPushButton, QMessageBox
from core.model_fetcher import (
    fetch_models, get_cached_models, get_custom_models,
    save_custom_model, get_fallback_models
)


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
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)

        # 当前 API 配置，由外部设置
        self._api_mode = "cloud"
        self._base_url = ""
        self._api_key = ""

    def set_api_config(self, api_mode, base_url, api_key):
        """更新当前 API 配置，刷新时使用"""
        self._api_mode = api_mode
        self._base_url = base_url
        self._api_key = api_key

    def set_current_text(self, text):
        self.combo.setCurrentText(text)

    def current_text(self):
        return self.combo.currentText().strip()

    def _build_model_list(self, fetched_models):
        """合并拉取到的模型、缓存模型和自定义模型，去重并保持顺序"""
        seen = set()
        result = []
        # 优先显示刚拉取到的模型
        for m in fetched_models:
            if m not in seen:
                seen.add(m)
                result.append(m)
        # 追加自定义模型
        for m in get_custom_models():
            if m not in seen:
                seen.add(m)
                result.append(m)
        return result

    def load_cached_models(self):
        """从缓存加载模型列表（启动时或切换模式时调用）"""
        cached = get_cached_models(self._api_mode)
        if not cached and self._api_mode == "cloud":
            cached = get_fallback_models()
        all_models = self._build_model_list(cached)
        current = self.combo.currentText()
        self.combo.clear()
        if all_models:
            self.combo.addItems(all_models)
        self.combo.setCurrentText(current)

    def _on_refresh_clicked(self):
        """点击刷新按钮"""
        self.refresh_models()

    def refresh_models(self):
        """根据当前 api_mode 从对应端点拉取模型列表"""
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("刷新中...")
        try:
            models, error = fetch_models(self._api_mode, self._base_url, self._api_key)
            if error:
                # 拉取失败，尝试用缓存
                cached = get_cached_models(self._api_mode)
                if cached:
                    QMessageBox.warning(
                        self, "提示",
                        f"拉取模型列表失败: {error}\n\n已加载上次缓存的模型列表。"
                    )
                    models = cached
                elif self._api_mode == "cloud":
                    QMessageBox.warning(
                        self, "提示",
                        f"拉取模型列表失败: {error}\n\n已加载内置备选模型列表。"
                    )
                    models = get_fallback_models()
                else:
                    QMessageBox.warning(
                        self, "提示",
                        f"拉取模型列表失败: {error}\n\n"
                        f"请检查本地服务是否启动，或在下拉框中手动输入模型名称。"
                    )
                    models = []

            all_models = self._build_model_list(models)
            current = self.combo.currentText()
            self.combo.clear()
            if all_models:
                self.combo.addItems(all_models)
            self.combo.setCurrentText(current)
        finally:
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setText("刷新模型")

    def remember_current_model(self):
        """将当前手动输入的模型名存入自定义缓存（送检时调用）"""
        model = self.current_text()
        if not model:
            return
        # 如果不在已知列表中，则视为自定义模型
        existing = [self.combo.itemText(i) for i in range(self.combo.count())]
        if model not in existing:
            save_custom_model(model)
            # 同时加入下拉列表
            self.combo.addItem(model)
