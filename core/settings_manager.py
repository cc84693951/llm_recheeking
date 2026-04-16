import json
import os
from config import CONFIG_PATH, DEFAULT_MODEL_PARAMS, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT


class SettingsManager:
    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self._data = self._load()
        # 首次启动时立即生成配置文件
        if not os.path.exists(self.path):
            self.save()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return self._default()

    def _default(self):
        return {
            "api_mode": "cloud",  # cloud | local
            "cloud_api_key": "",
            "cloud_base_url": "https://api.siliconflow.cn/v1",
            "local_base_url": "http://localhost:11434/v1",
            "local_api_key": "",
            "selected_model": "",
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "user_prompt": DEFAULT_USER_PROMPT,
            "model_params": DEFAULT_MODEL_PARAMS.copy(),
            "few_shots": [],
        }

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def all(self):
        return self._data.copy()
