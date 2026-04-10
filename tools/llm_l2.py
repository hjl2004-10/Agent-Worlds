# ============================================
# tools/llm_l2.py - LLM原子层
# 职责: 纯计算，配置加载、响应解析
# ============================================

import json
import os

# 配置文件路径
CONFIG_PATH = "config/llm.json"

# 缓存配置
_config_cache = None


def load_config() -> dict:
    """
    加载 LLM 配置文件
    
    Returns:
        dict: 配置字典
    """
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"配置文件不存在: {CONFIG_PATH}\n"
            f"请先复制模板: cp config/llm.json.example config/llm.json\n"
            f"然后编辑 config/llm.json 填入你的 API Key"
        )
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        _config_cache = json.load(f)
    
    return _config_cache


def reload_config() -> dict:
    """强制重新加载配置"""
    global _config_cache
    _config_cache = None
    return load_config()


def get_channel_config(channel_name: str) -> dict:
    """
    获取渠道配置
    
    Args:
        channel_name: 渠道名称
        
    Returns:
        dict: 渠道配置
    """
    config = load_config()
    channels = config.get("channels", {})
    
    if channel_name not in channels:
        raise ValueError(f"渠道不存在: {channel_name}")
    
    return channels[channel_name]


def get_default_channel() -> str:
    """获取默认渠道名称"""
    config = load_config()
    routing = config.get("routing", {})
    return routing.get("default_channel", "")


def get_model_config(channel_config: dict, model_name: str = None) -> tuple:
    """
    获取模型配置
    
    Args:
        channel_config: 渠道配置
        model_name: 模型名称 (None 则使用默认)
        
    Returns:
        tuple: (model_name, model_config)
    """
    models = channel_config.get("models", {})
    
    # 如果未指定模型，使用默认
    if model_name is None:
        model_name = models.get("default", "")
    
    # 获取模型特定配置
    model_config = models.get(model_name, {})
    
    return model_name, model_config


def save_config(config: dict):
    """保存配置到文件并刷新缓存"""
    global _config_cache
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    _config_cache = config


def parse_json_response(response_text: str) -> dict:
    """
    解析 JSON 响应文本
    
    Args:
        response_text: 响应文本
        
    Returns:
        dict: 解析后的字典
    """
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {e}")
