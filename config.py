import os

APP_NAME = "LLM ReCheck"
VERSION = "1.0.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "settings.json")

DEFAULT_SYSTEM_PROMPT = """你是一个图像内容审核助手。请仔细查看用户提供的图片，判断图中目标是否存在异常或不符合要求的情况。请用一句话简要给出结论，如果正常请回答"正常"，如果不正常请说明原因。"""

DEFAULT_USER_PROMPT = """请对这张图片中的目标进行复判，给出你的判断结果。"""

DEFAULT_FEW_SHOTS = []

SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp")

DEFAULT_MODEL_PARAMS = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 512,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
}

SILICON_FLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICON_FLOW_MODELS_URL = "https://api.siliconflow.cn/v1/models"

FALLBACK_MODELS = [
    "Qwen/Qwen2-VL-72B-Instruct",
    "Pro/Qwen/Qwen2-VL-7B-Instruct",
    "deepseek-ai/deepseek-vl2",
    "OpenGVLab/InternVL2-26B",
    "Qwen/Qwen3-VL-32B-Thinking",
    "Qwen/Qwen3-VL-32B-Instruct",
    "Qwen/Qwen3-VL-8B-Instruct",
    "Qwen/Qwen3-VL-8B-Thinking",
    "Pro/moonshotai/Kimi-K2.5",
    "Qwen/Qwen3.5-397B-A17B",
    "Qwen/Qwen3.5-122B-A10B",
    "PaddlePaddle/PaddleOCR-VL",
    "zai-org/GLM-4.5V",
    "zai-org/GLM-4.6V",
    "deepseek-ai/DeepSeek-OCR",
]
