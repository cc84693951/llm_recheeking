import json
import os
import logging
import requests
from config import SILICON_FLOW_MODELS_URL, FALLBACK_MODELS, BASE_DIR

logger = logging.getLogger("llm_client")

# 模型缓存文件路径
MODELS_CACHE_PATH = os.path.join(BASE_DIR, "models_cache.json")


def _load_cache():
    """加载本地模型缓存"""
    if os.path.exists(MODELS_CACHE_PATH):
        try:
            with open(MODELS_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cloud": [], "local": [], "custom": []}


def _save_cache(cache):
    """保存模型缓存到本地 JSON"""
    try:
        with open(MODELS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[MODEL CACHE] 保存缓存失败: {e}")


def fetch_models(api_mode, base_url, api_key=""):
    """根据 api_mode 从对应端点拉取模型列表

    Args:
        api_mode: "cloud" 或 "local"
        base_url: API 基础地址（如 https://api.siliconflow.cn/v1）
        api_key: 可选的 API Key

    Returns:
        (models, error) 元组：成功时 error 为 None，失败时 models 为空列表
    """
    if not base_url:
        return [], "未配置 Base URL"

    # 构建 models 端点
    url = base_url.rstrip("/")
    if api_mode == "cloud":
        url = SILICON_FLOW_MODELS_URL
    else:
        url = f"{url}/models"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    logger.info(f"[MODEL FETCH] mode={api_mode} url={url}")

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        models = []
        for item in data.get("data", []):
            model_id = item.get("id") or item.get("model")
            if model_id:
                models.append(model_id)
        if models:
            # 拉取成功，更新缓存
            cache = _load_cache()
            cache[api_mode] = models
            _save_cache(cache)
            logger.info(f"[MODEL FETCH] 成功获取 {len(models)} 个模型")
            return models, None
        else:
            return [], "服务返回的模型列表为空"
    except requests.exceptions.ConnectionError:
        return [], f"无法连接到 {url}，请检查地址是否正确或服务是否启动"
    except requests.exceptions.Timeout:
        return [], f"连接超时，服务 {url} 未在 10 秒内响应"
    except requests.exceptions.HTTPError as e:
        return [], f"HTTP 错误: {e}"
    except Exception as e:
        return [], f"获取模型列表失败: {e}"


def get_cached_models(api_mode):
    """获取本地缓存的模型列表"""
    cache = _load_cache()
    return cache.get(api_mode, [])


def get_custom_models():
    """获取用户自定义输入过的模型列表"""
    cache = _load_cache()
    return cache.get("custom", [])


def save_custom_model(model_name):
    """保存用户自定义输入的模型名到缓存"""
    if not model_name or not model_name.strip():
        return
    model_name = model_name.strip()
    cache = _load_cache()
    custom = cache.get("custom", [])
    if model_name not in custom:
        custom.append(model_name)
        cache["custom"] = custom
        _save_cache(cache)
        logger.info(f"[MODEL CACHE] 保存自定义模型: {model_name}")


def get_fallback_models():
    """获取硬编码的备选模型列表（仅云端模式）"""
    return FALLBACK_MODELS.copy()
