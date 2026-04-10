# ============================================
# tools/llm/providers/base.py - 适配器基类
# 职责: 定义统一接口
# ============================================

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseProvider(ABC):
    """
    LLM厂商适配器基类
    
    所有厂商适配器必须实现此接口
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称"""
        pass

    @abstractmethod
    def build_request(
        self,
        messages: List[Dict],
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.8,
        max_tokens: int = 200,
        **kwargs
    ) -> tuple:
        """
        构建请求
        
        Args:
            messages: 消息列表
            model: 模型名称
            base_url: API地址
            api_key: API密钥
            temperature: 温度
            max_tokens: 最大token
            
        Returns:
            tuple: (url, headers, payload)
        """
        pass

    @abstractmethod
    def parse_response(self, response_data: dict) -> str:
        """
        解析响应
        
        Args:
            response_data: API返回的JSON数据
            
        Returns:
            str: 提取的文本内容
        """
        pass

    def get_endpoint(self, base_url: str) -> str:
        """
        获取完整API地址 (子类可覆盖)
        
        Args:
            base_url: 基础地址
            
        Returns:
            str: 完整地址
        """
        return base_url
