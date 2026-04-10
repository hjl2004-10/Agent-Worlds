# api/misc.py - LLM渠道、精灵图等杂项路由

from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api", tags=["misc"])

_PROJECT_ROOT = Path(__file__).parent.parent


@router.get("/llm/channels")
async def api_llm_channels():
    from tools import llm_l2
    config = llm_l2.load_config()
    channels_data = config.get("channels", {})
    routing = config.get("routing", {})

    channels = []
    for channel_id, channel_config in channels_data.items():
        models_dict = channel_config.get("models", {})
        models = [k for k in models_dict.keys() if k != "default"]
        default_model = models_dict.get("default", "")
        channels.append({
            "id": channel_id,
            "name": channel_id.capitalize(),
            "models": models,
            "default_model": default_model,
            "provider": channel_config.get("provider", "openai")
        })

    return {
        "status": "ok",
        "channels": channels,
        "default_channel": routing.get("default_channel", ""),
        "default_model": routing.get("default_model")
    }


class ChannelCreateRequest(BaseModel):
    id: str
    provider: str = "openai"
    base_url: str = ""
    api_key: str = ""
    default_model: Optional[str] = None


class ChannelUpdateRequest(BaseModel):
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None


class ModelAddRequest(BaseModel):
    model_name: str
    temperature: float = 0.8
    max_tokens: int = 500


class RoutingUpdateRequest(BaseModel):
    default_channel: str


@router.post("/llm/channels")
async def api_create_channel(req: ChannelCreateRequest):
    """创建新渠道"""
    from tools import llm_l2
    config = llm_l2.load_config()
    channels = config.setdefault("channels", {})
    if req.id in channels:
        return {"status": "error", "message": f"渠道 '{req.id}' 已存在"}
    channels[req.id] = {
        "provider": req.provider,
        "base_url": req.base_url,
        "api_key": req.api_key,
        "models": {"default": req.default_model or ""}
    }
    llm_l2.save_config(config)
    return {"status": "ok", "message": f"渠道 '{req.id}' 创建成功"}


@router.put("/llm/channels/{channel_id}")
async def api_update_channel(channel_id: str, req: ChannelUpdateRequest):
    """更新渠道配置"""
    from tools import llm_l2
    config = llm_l2.load_config()
    channels = config.get("channels", {})
    if channel_id not in channels:
        return {"status": "error", "message": f"渠道 '{channel_id}' 不存在"}
    ch = channels[channel_id]
    if req.provider is not None:
        ch["provider"] = req.provider
    if req.base_url is not None:
        ch["base_url"] = req.base_url
    if req.api_key is not None:
        ch["api_key"] = req.api_key
    if req.default_model is not None:
        ch["models"]["default"] = req.default_model
    llm_l2.save_config(config)
    return {"status": "ok", "message": f"渠道 '{channel_id}' 更新成功"}


@router.delete("/llm/channels/{channel_id}")
async def api_delete_channel(channel_id: str):
    """删除渠道"""
    from tools import llm_l2
    config = llm_l2.load_config()
    channels = config.get("channels", {})
    if channel_id not in channels:
        return {"status": "error", "message": f"渠道 '{channel_id}' 不存在"}
    del channels[channel_id]
    # 如果删的是默认渠道，清空默认
    routing = config.get("routing", {})
    if routing.get("default_channel") == channel_id:
        routing["default_channel"] = ""
    llm_l2.save_config(config)
    return {"status": "ok", "message": f"渠道 '{channel_id}' 已删除"}


@router.post("/llm/channels/{channel_id}/models")
async def api_add_model(channel_id: str, req: ModelAddRequest):
    """向渠道添加模型"""
    from tools import llm_l2
    config = llm_l2.load_config()
    channels = config.get("channels", {})
    if channel_id not in channels:
        return {"status": "error", "message": f"渠道 '{channel_id}' 不存在"}
    models = channels[channel_id].setdefault("models", {})
    models[req.model_name] = {
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }
    # 如果是第一个模型，设为默认
    if not models.get("default"):
        models["default"] = req.model_name
    llm_l2.save_config(config)
    return {"status": "ok", "message": f"模型 '{req.model_name}' 已添加"}


@router.delete("/llm/channels/{channel_id}/models/{model_name}")
async def api_delete_model(channel_id: str, model_name: str):
    """从渠道删除模型"""
    from tools import llm_l2
    config = llm_l2.load_config()
    channels = config.get("channels", {})
    if channel_id not in channels:
        return {"status": "error", "message": f"渠道 '{channel_id}' 不存在"}
    models = channels[channel_id].get("models", {})
    if model_name not in models or model_name == "default":
        return {"status": "error", "message": f"模型 '{model_name}' 不存在"}
    del models[model_name]
    if models.get("default") == model_name:
        remaining = [k for k in models if k != "default"]
        models["default"] = remaining[0] if remaining else ""
    llm_l2.save_config(config)
    return {"status": "ok", "message": f"模型 '{model_name}' 已删除"}


@router.get("/llm/channels/{channel_id}/fetch-models")
async def api_fetch_remote_models(channel_id: str):
    """从远程 API 获取可用模型列表，同时验证 key 是否有效"""
    import httpx
    from tools import llm_l2
    config = llm_l2.load_config()
    channels = config.get("channels", {})
    if channel_id not in channels:
        return {"status": "error", "message": f"渠道 '{channel_id}' 不存在"}
    ch = channels[channel_id]
    base_url = ch.get("base_url", "").rstrip("/")
    api_key = ch.get("api_key", "")
    provider = ch.get("provider", "openai")
    if not base_url:
        return {"status": "error", "message": "渠道未配置 base_url"}

    # 两种协议都尝试 /v1/models
    url = f"{base_url}/v1/models"
    headers: dict[str, str] = {}
    if provider == "claude":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "message": f"请求失败 (HTTP {resp.status_code}): {resp.text[:200]}",
                }
            data = resp.json()
            # OpenAI 格式: { "data": [{"id": "model-name"}, ...] }
            models = []
            if "data" in data and isinstance(data["data"], list):
                for item in data["data"]:
                    model_id = item.get("id") or item.get("name") or str(item)
                    models.append(model_id)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        models.append(item)
                    elif isinstance(item, dict):
                        models.append(item.get("id") or item.get("name") or str(item))
            return {"status": "ok", "models": sorted(models)}
    except httpx.TimeoutException:
        return {"status": "error", "message": "请求超时 (15s)，请检查 base_url 是否可达"}
    except Exception as e:
        return {"status": "error", "message": f"连接失败: {str(e)}"}


@router.put("/llm/routing")
async def api_update_routing(req: RoutingUpdateRequest):
    """更新默认路由"""
    from tools import llm_l2
    config = llm_l2.load_config()
    config.setdefault("routing", {})["default_channel"] = req.default_channel
    llm_l2.save_config(config)
    return {"status": "ok", "message": f"默认渠道已设为 '{req.default_channel}'"}


@router.get("/sprites")
async def api_sprites():
    sprites_dir = _PROJECT_ROOT / "static" / "public" / "sprites"
    sprites = []
    if sprites_dir.exists():
        for f in sprites_dir.glob("*_16x16.png"):
            sprite_id = f.stem.replace("_16x16", "")
            sprites.append(sprite_id)
        for f in sprites_dir.glob("*_48x48.png"):
            sprites.append(f.stem)
    return {"status": "ok", "sprites": sorted(sprites)}
