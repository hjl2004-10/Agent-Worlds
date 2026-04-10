# ============================================
# tools/mcp_client_l1.py - MCP客户端业务层
# 职责: 个体作用域，管理持久 MCP Server 连接
# ============================================

import httpx
from contextlib import AsyncExitStack
from mcp.client.streamable_http import streamable_http_client
from mcp.client.sse import sse_client
from mcp import ClientSession
from tools.mcp_client_l2 import mcp_tool_to_anthropic, mcp_result_to_string

# SSE 读超时: 设足够大，支持 24 小时后台运行 (默认 300s 太短)
SSE_READ_TIMEOUT = 86400 * 7  # 7天


def _make_httpx_client(**kwargs):
    """创建禁用系统代理的 httpx 客户端"""
    kwargs['trust_env'] = False
    return httpx.AsyncClient(**kwargs)


def _make_bare_httpx_client():
    """创建禁用系统代理的 httpx 客户端实例"""
    return httpx.AsyncClient(trust_env=False)


def _is_sse_url(url):
    """判断 URL 是否是 SSE 端点"""
    return url.rstrip('/').endswith('/sse')


class PersistentMCPSession:
    """持久化的 MCP Server 连接

    连接建立后保持 session 不断开，所有工具调用复用同一个 session。
    如果连接因超时断开，call_tool 时自动重连。
    """

    def __init__(self, url, server_name):
        self.url = url
        self.server_name = server_name
        self.session = None
        self._exit_stack = None
        self._connected = False
        self.tool_defs = []

    async def connect(self):
        """建立持久连接，返回工具定义列表"""
        if self._connected:
            return self.tool_defs

        # 清理旧连接 (如果有)
        await self._cleanup()

        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        is_sse = _is_sse_url(self.url)
        order = [True, False] if is_sse else [False, True]
        labels = {True: "SSE", False: "Streamable HTTP"}
        last_error = None

        for try_sse in order:
            transport_name = labels[try_sse]
            try:
                print(f"  [MCP] 尝试 {transport_name} 连接 {self.server_name}...")
                if try_sse:
                    streams = await self._exit_stack.enter_async_context(
                        sse_client(
                            self.url,
                            httpx_client_factory=_make_httpx_client,
                            sse_read_timeout=SSE_READ_TIMEOUT,
                        )
                    )
                    read_stream, write_stream = streams
                else:
                    streams = await self._exit_stack.enter_async_context(
                        streamable_http_client(self.url, http_client=_make_bare_httpx_client())
                    )
                    read_stream, write_stream = streams[0], streams[1]

                self.session = await self._exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                await self.session.initialize()

                result = await self.session.list_tools()
                self.tool_defs = []
                for tool in result.tools:
                    tool_def = mcp_tool_to_anthropic(tool, self.server_name)
                    self.tool_defs.append(tool_def)
                    print(f"  [MCP] {self.server_name}/{tool.name}: {tool.description or '(no desc)'}")

                self._connected = True
                print(f"  [MCP] {self.server_name} 连接成功 ({transport_name}), 会话已保持")
                return self.tool_defs

            except Exception as e:
                last_error = e
                detail = str(e)
                if hasattr(e, 'exceptions'):
                    detail = "; ".join(str(sub) for sub in e.exceptions)
                elif e.__cause__:
                    detail = str(e.__cause__)
                print(f"  [MCP] {transport_name} 连接失败: {detail}")
                continue

        # 全部失败，清理
        await self._cleanup()
        raise last_error

    async def call_tool(self, tool_name, arguments):
        """在持久会话上调用工具，连接断了自动重连"""
        if not self._connected or not self.session:
            # 尝试重连
            print(f"  [MCP] {self.server_name} 未连接，尝试重连...")
            await self.connect()

        try:
            result = await self.session.call_tool(tool_name, arguments)
            return mcp_result_to_string(result)
        except Exception as e:
            # 可能是超时断连，尝试重连一次
            err_str = str(e).lower()
            if 'timeout' in err_str or 'closed' in err_str or 'eof' in err_str:
                print(f"  [MCP] {self.server_name} 连接已断开，正在重连...")
                self._connected = False
                await self._cleanup()
                await self.connect()
                result = await self.session.call_tool(tool_name, arguments)
                return mcp_result_to_string(result)
            raise

    async def _cleanup(self):
        """清理连接资源"""
        if self._exit_stack:
            try:
                await self._exit_stack.__aexit__(None, None, None)
            except Exception:
                pass
            self._exit_stack = None
        self.session = None
        self._connected = False

    async def close(self):
        """关闭持久连接"""
        await self._cleanup()
        print(f"  [MCP] {self.server_name} 连接已关闭")

    @property
    def is_connected(self):
        return self._connected
