import base64
import io
import os
import time
import logging
import requests
from PIL import Image

# 配置 llm_client 日志
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("llm_client")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.FileHandler(os.path.join(LOG_DIR, "api_calls.log"), encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class LLMClient:
    def __init__(self, api_mode, base_url, api_key, model_name):
        self.api_mode = api_mode
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.session = requests.Session()

    def _encode_image(self, pil_image):
        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode()

    def _encode_image_path(self, image_path, target_size=None):
        pil_image = Image.open(image_path).convert("RGB")
        if target_size:
            pil_image = pil_image.resize(target_size, Image.LANCZOS)
        return self._encode_image(pil_image)

    def inspect(self, pil_image, system_prompt, user_prompt, few_shots, params):
        if not self.model_name:
            raise ValueError("未选择模型")

        image_b64 = self._encode_image(pil_image)
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if self.api_mode == "local" and not self.api_key:
            headers.pop("Authorization", None)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for shot in few_shots:
            user_content = []
            if shot.get("user"):
                user_content.append({"type": "text", "text": shot["user"]})
            if shot.get("image_path"):
                try:
                    b64 = self._encode_image_path(shot["image_path"], target_size=(336, 336))
                    user_content.append(
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    )
                except Exception as e:
                    user_content.append({"type": "text", "text": f"[图片读取失败: {e}]"})
            if user_content:
                if len(user_content) == 1 and user_content[0].get("type") == "text":
                    messages.append({"role": "user", "content": user_content[0]["text"]})
                else:
                    messages.append({"role": "user", "content": user_content})
            if shot.get("assistant"):
                messages.append({"role": "assistant", "content": shot["assistant"]})

        content = [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ]
        messages.append({"role": "user", "content": content})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": params.get("temperature", 0.3),
            "top_p": params.get("top_p", 0.8),
            "max_tokens": params.get("max_tokens", 512),
            "frequency_penalty": params.get("frequency_penalty", 0.0),
            "presence_penalty": params.get("presence_penalty", 0.0),
        }

        logger.info(
            f"[API START] model={self.model_name} url={url} "
            f"msg_count={len(messages)} temperature={payload['temperature']} max_tokens={payload['max_tokens']}"
        )

        last_exception = None
        for attempt in range(3):
            logger.info(f"[API ATTEMPT {attempt + 1}/3] base64_len={len(image_b64)}")

            try:
                # 连接超时 10 秒，读取超时 120 秒
                response = self.session.post(url, headers=headers, json=payload, timeout=(10, 120))
                if response.ok:
                    data = response.json()
                    result_text = data["choices"][0]["message"]["content"]
                    logger.info(f"[API SUCCESS] attempt={attempt + 1} result_len={len(result_text)}")
                    return result_text

                detail = ""
                try:
                    detail = response.json()
                except Exception:
                    detail = response.text[:500]
                last_exception = RuntimeError(
                    f"服务器返回 HTTP {response.status_code}。\n"
                    f"模型: {self.model_name}\n"
                    f"详情: {detail}"
                )
                logger.error(
                    f"[API HTTP ERROR] attempt={attempt + 1} status={response.status_code} "
                    f"detail={detail}"
                )
                if response.status_code in (429,):
                    time.sleep(2 ** attempt)
                else:
                    time.sleep(1)
            except requests.exceptions.Timeout as e:
                last_exception = RuntimeError("请求超时：服务器在 120 秒内未响应，请检查网络或稍后重试。")
                logger.error(f"[API TIMEOUT] attempt={attempt + 1} error={e}")
                time.sleep(1)
            except requests.exceptions.ConnectionError as e:
                last_exception = RuntimeError(f"连接失败：无法连接到 {self.base_url}，请检查 URL 是否正确或服务是否启动。\n详情: {e}")
                logger.error(f"[API CONNECTION ERROR] attempt={attempt + 1} error={e}")
                time.sleep(1)
            except Exception as e:
                last_exception = RuntimeError(f"未知错误: {e}")
                logger.error(f"[API UNKNOWN ERROR] attempt={attempt + 1} error={e}")
                time.sleep(1)

        logger.error(f"[API FAILED] 重试 3 次后仍然失败。last_error={last_exception}")
        raise RuntimeError(f"重试 3 次后仍然失败。\n最后一次错误: {last_exception}")
