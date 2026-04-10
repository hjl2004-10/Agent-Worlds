# ============================================
# tools/mcp_client_l2.py - MCP客户端原子层
# 职责: 纯格式转换，无状态
# ============================================


def mcp_tool_to_anthropic(mcp_tool, server_name):
    """将 MCP Tool 对象转换为 Anthropic 工具定义格式

    Args:
        mcp_tool: mcp.types.Tool (name, description, inputSchema)
        server_name: MCP server 名称，用于命名空间

    Returns:
        dict: {"name": "mcp__{server}__{tool}", "description": ..., "input_schema": ...}
    """
    return {
        "name": f"mcp__{server_name}__{mcp_tool.name}",
        "description": f"[MCP:{server_name}] {mcp_tool.description or mcp_tool.name}",
        "input_schema": mcp_tool.inputSchema or {"type": "object", "properties": {}},
    }


def mcp_result_to_string(result):
    """将 MCP CallToolResult 转换为纯文本

    Args:
        result: mcp.types.CallToolResult

    Returns:
        str: 结果文本
    """
    if result.isError:
        return f"MCP工具错误: {_extract_text(result.content)}"
    return _extract_text(result.content)


def _extract_text(content_list):
    """从 content 列表提取文本"""
    texts = []
    for item in (content_list or []):
        if hasattr(item, 'text'):
            texts.append(item.text)
        else:
            texts.append(str(item))
    return "\n".join(texts) if texts else "(无输出)"


def parse_mcp_tool_name(tool_name):
    """解析 MCP 工具名，提取 server_name 和 actual_name

    Args:
        tool_name: "mcp__{server}__{actual_name}"

    Returns:
        (server_name, actual_name) or (None, None) if not MCP tool
    """
    if not tool_name.startswith("mcp__"):
        return None, None
    parts = tool_name.split("__", 2)
    if len(parts) == 3:
        return parts[1], parts[2]
    return None, None
