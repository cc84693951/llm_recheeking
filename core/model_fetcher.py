import requests
from config import SILICON_FLOW_MODELS_URL, FALLBACK_MODELS


def fetch_silicon_flow_models(api_key=""):
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = requests.get(SILICON_FLOW_MODELS_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        models = []
        for item in data.get("data", []):
            model_id = item.get("id") or item.get("model")
            if model_id:
                models.append(model_id)
        return models if models else FALLBACK_MODELS.copy()
    except Exception:
        return FALLBACK_MODELS.copy()
