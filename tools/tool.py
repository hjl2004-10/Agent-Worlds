# ============================================
# tools/tool.py - 工具调用总控层 (L0)
# 职责: 配置持有、工具注册表、接口定义
#
# 支持多协议:
#   - custom: 自定义文本触发 (【工具:xxx】)
#   - anthropic: Anthropic 原生 tool_use
# ============================================

from typing import Any, Dict, List, Optional
import json
from pathlib import Path

# ========== 工具组配置 ==========
TOOL_GROUPS: Dict[str, Dict] = {}


def load_tool_groups() -> Dict[str, Dict]:
    """
    从 config/tool_groups.json 加载工具组配置

    Returns:
        Dict: 工具组配置 {"@file": {"description": "...", "tools": [...]}}
    """
    global TOOL_GROUPS
    config_path = Path(__file__).parent.parent / "config" / "tool_groups.json"
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                TOOL_GROUPS = data.get("groups", {})
                print(f"[ToolGroups] 加载 {len(TOOL_GROUPS)} 个工具组")
                return TOOL_GROUPS
    except Exception as e:
        print(f"[ToolGroups] 加载失败: {e}")
    return {}


def expand_tool_groups(tool_list: List[str]) -> List[str]:
    """
    展开工具组为具体工具列表

    Args:
        tool_list: 工具列表，可能包含 @group 形式的工具组

    Returns:
        List[str]: 展开后的工具列表 (不含重复)
    """
    if not TOOL_GROUPS:
        load_tool_groups()

    expanded = []
    for item in tool_list:
        if item.startswith("@") and item in TOOL_GROUPS:
            # 展开工具组
            group_tools = TOOL_GROUPS[item].get("tools", [])
            expanded.extend(group_tools)
        else:
            expanded.append(item)

    # 去重并保持顺序
    seen = set()
    result = []
    for t in expanded:
        if t not in seen:
            seen.add(t)
            result.append(t)

    return result


def get_tool_groups() -> Dict[str, Dict]:
    """获取所有工具组配置"""
    if not TOOL_GROUPS:
        load_tool_groups()
    return TOOL_GROUPS


def save_tool_groups(groups: Dict[str, Dict]) -> bool:
    """
    保存工具组配置到 config/tool_groups.json

    Args:
        groups: 工具组配置 {"@file": {"description": "...", "tools": [...]}}

    Returns:
        bool: 保存是否成功
    """
    global TOOL_GROUPS
    config_path = Path(__file__).parent.parent / "config" / "tool_groups.json"
    try:
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建完整配置
        data = {
            "version": "1.0",
            "groups": groups
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新内存缓存
        TOOL_GROUPS = groups
        print(f"[ToolGroups] 保存 {len(groups)} 个工具组")
        return True
    except Exception as e:
        print(f"[ToolGroups] 保存失败: {e}")
        return False

# ========== 工具注册表 ==========
# 按协议分组存储工具定义

TOOL_REGISTRY = {
    # 自定义工具协议 (文本触发)
    "custom": {
        1: {
            "name": "测试",
            "trigger": "【工具:测试】",
            "handler": None,  # 由 tool_l1._init_handlers() 初始化
            "enabled": True,
        },
        2: {
            "name": "添加群组",
            "trigger": "re:\\[group:([^\\]]+)\\]",
            "handler": None,
            "enabled": True,
        },
    },

    # Anthropic 原生工具协议
    "anthropic": {
        "read_file": {
            "description": "读取文件内容。支持: 纯文本、PDF、Word(.docx)、PPT(.pptx)、Excel(.xlsx)、CSV、图片(.png/.jpg)。文档会自动提取文本，图片返回元数据。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "start_line": {"type": "integer", "minimum": 1},
                    "end_line": {"type": "integer", "minimum": -1},
                    "max_chars": {"type": "integer", "minimum": 1, "maximum": 200000},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "write_file": {
            "description": "创建或覆写/追加文本文件",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "mode": {"type": "string", "enum": ["overwrite", "append"], "default": "overwrite"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "edit_text": {
            "description": "精确编辑文本文件: 替换/插入/删除行",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "action": {"type": "string", "enum": ["replace", "insert", "delete_range"]},
                    "find": {"type": "string"},
                    "replace": {"type": "string"},
                    "insert_after": {"type": "integer", "minimum": -1},
                    "new_text": {"type": "string"},
                    "range": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
                },
                "required": ["path", "action"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "delete_file": {
            "description": "删除指定文件 (谨慎使用，删除后无法恢复)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要删除的文件路径 (相对于 workspace 目录)"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "add_task": {
            "description": "给某人添加任务提醒，例如'给你留了文件'、'明天来找我'等",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "给谁加任务 (人名)"},
                    "hint": {"type": "string", "description": "任务提示内容 (自然语言)"},
                    "tool_hint": {"type": "string", "description": "工具使用指引，格式: '工具名: 参数'。如 'goto_location: location=酒馆' 或 'read_file: path=xxx'"},
                },
                "required": ["target", "hint"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "complete_task": {
            "description": "标记任务为已完成",
            "input_schema": {
                "type": "object",
                "properties": {
                    "hint": {"type": "string", "description": "要完成的任务提示内容 (用于匹配)"},
                },
                "required": ["hint"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "goto_location": {
            "description": "开始前往指定地点 (只是设置移动目标，需要时间移动，到达后系统会通知你)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "地点名称 (如: 酒馆, 广场, 市场)"},
                },
                "required": ["location"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "arrived_at": {
            "description": "确认已到达指定地点 (到达目的地后调用)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "地点名称"},
                },
                "required": ["location"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "end_conversation": {
            "description": "主动结束当前对话。在以下情况必须调用: 1) 你的任务已完成（如已交接给下游）2) 话题聊完了没有新内容 3) 对方说拜拜。不要在完成工作后继续闲聊，直接结束。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "farewell": {"type": "string", "description": "告别语 (如: 拜拜，下次聊~)"},
                },
                "required": ["farewell"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "edit_memory_note": {
            "description": "编辑你的个人笔记，用于记录重要信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "笔记内容"},
                    "mode": {"type": "string", "enum": ["set", "append"], "description": "set=覆盖写入(默认), append=追加到末尾"},
                },
                "required": ["content"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "send_qq_notify": {
            "description": "向管理员的 QQ 发送通知消息。重要提醒：必须实际调用此工具才能真正发送消息，不要只在回复中声称已发送。适用场景：交易完成、重要事件、需要管理员关注的情况。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "通知内容 (建议格式：【标题】详细内容)"},
                    "target": {"type": "string", "description": "目标用户OpenID (可选，默认发给管理员)"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 命令行工具 ==========
        "run_command": {
            "description": (
                "在 workspace 目录下执行命令行命令。可用于运行脚本、安装依赖、执行构建等。命令超时 30 秒。\n"
                "【重要环境信息】\n"
                "- 操作系统: Windows，请使用 Windows 命令 (dir, findstr, type 等)，不要用 Linux 命令 (ls, grep, cat, head 等)\n"
                "- Python 路径: D:\\python.exe (不要直接用 python)\n"
                "- 默认工作目录: 项目根目录 (可直接访问 data/ 等目录)\n"
                "- workspace/ 子目录可用于存放临时脚本和输出文件"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令。Windows 系统，用 dir/findstr/type 等。Python 请用 D:\\python.exe"},
                    "cwd": {"type": "string", "description": "工作目录 (可选，默认为 workspace)。用 '.' 表示项目根目录，'data/skills/xxx' 等相对路径访问项目数据"},
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 代码检查工具 ==========
        "check_syntax": {
            "description": "检查代码文件的语法错误。支持 Python (.py) 和 JavaScript/TypeScript (.js/.ts/.tsx)。编写或修改代码后建议调用此工具验证。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要检查的文件路径"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== MCP 工具 ==========
        "list_mcp_servers": {
            "description": "查看所有可用的 MCP 服务器及其状态（运行中/已停止）。用于了解有哪些外部能力可以连接，如浏览器控制、数据库等。",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "connect_mcp": {
            "description": "连接到指定的 MCP 服务器，连接成功后你将获得该服务器提供的所有工具。如果服务器未启动会自动尝试启动。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "server_name": {"type": "string", "description": "要连接的 MCP 服务器名称 (从 list_mcp_servers 获取)"},
                },
                "required": ["server_name"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 背包系统工具 ==========
        "list_attrs": {
            "description": "列出指定角色的所有属性 (查看别人时只显示公开属性，查看自己时显示全部)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标 NPC 名称 (不填则查看自己的)"},
                },
                "required": [],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "get_auth_code": {
            "description": "获取某属性的授权码 (用于修改 requires_auth: true 的敏感属性，授权码只能用一次)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "attr": {"type": "string", "description": "属性名称"},
                },
                "required": ["attr"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "read_attr": {
            "description": "读取属性值 (公共属性可看别人的，私有属性只能看自己的)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标 NPC 名称 (不填则读取自己的)"},
                    "attr": {"type": "string", "description": "属性名称"},
                },
                "required": ["attr"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "edit_attr": {
            "description": "创建或修改属性 (属性不存在时自动创建，value是数字，description是说明文字)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标 NPC 名称 (不填则操作自己的)"},
                    "attr": {"type": "string", "description": "属性名称"},
                    "value": {"type": "number", "description": "数值 (只能是数字)"},
                    "description": {"type": "string", "description": "描述文字 (可选)"},
                    "visibility": {"type": "string", "enum": ["public", "private"], "description": "可见性: public=所有人可看, private=仅自己可看 (仅创建新属性时有效，默认public)"},
                    "auth_code": {"type": "string", "description": "授权码 (敏感属性需要)"},
                },
                "required": ["attr", "value"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "modify_attr": {
            "description": "增减数值型属性 (如金币+10、生命值-5)，仅对数值有效",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标 NPC 名称 (不填则操作自己的)"},
                    "attr": {"type": "string", "description": "属性名称"},
                    "delta": {"type": "number", "description": "变化量 (正数增加，负数减少)"},
                    "auth_code": {"type": "string", "description": "授权码 (敏感属性需要)"},
                },
                "required": ["attr", "delta"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "delete_attr": {
            "description": "删除属性/物品 (物品用完后删除)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标 NPC 名称 (不填则操作自己的)"},
                    "attr": {"type": "string", "description": "属性名称"},
                    "auth_code": {"type": "string", "description": "授权码 (敏感属性需要)"},
                },
                "required": ["attr"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 定时器系统工具 ==========
        "create_timer": {
            "description": "创建定时提醒，到时间会自动提醒你做某事。120 tick = 1游戏小时，2880 tick = 1游戏天",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "定时器名称"},
                    "description": {"type": "string", "description": "提醒内容 (如: 该喝水了, 该休息了)"},
                    "interval_ticks": {"type": "integer", "description": "触发间隔 (tick数, 120=1小时, 2880=1天)", "default": 120},
                    "max_triggers": {"type": "integer", "description": "最大触发次数 (-1表示无限)", "default": -1},
                },
                "required": ["name", "description"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "remove_timer": {
            "description": "删除定时提醒",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "定时器名称"},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "list_timers": {
            "description": "列出你设置的所有定时提醒",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 主动性工具 ==========
        "modify_initiative": {
            "description": "调整自己的主动性 (正数=更想继续对话，负数=想结束对话)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "delta": {"type": "integer", "description": "变化量 (正数增加，负数减少)"},
                    "reason": {"type": "string", "description": "原因 (可选)"},
                },
                "required": ["delta"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "modify_others_initiative": {
            "description": "调整他人的主动性 (影响对方是否想继续对话)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标 NPC 名称"},
                    "delta": {"type": "integer", "description": "变化量 (正数增加，负数减少)"},
                    "reason": {"type": "string", "description": "原因 (可选)"},
                },
                "required": ["target", "delta"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 邮箱系统工具 ==========
        "send_mail": {
            "description": "向玩家发送邮件，可以发送文本、图片或文档。适合需要正式传达或留档的内容。(发送HTML应用请使用send_html_mail工具)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "邮件标题"},
                    "content": {"type": "string", "description": "邮件内容 (文本/文件路径/URL)"},
                    "content_type": {"type": "string", "enum": ["text", "image", "document"], "description": "内容类型 (默认 text，不支持html)"},
                    "to_player": {"type": "string", "description": "接收者 (默认 player)"},
                },
                "required": ["title", "content"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "send_html_mail": {
            "description": "发送HTML应用邮件，在虚拟电脑中以独立应用形式展示。支持交互式HTML(如小游戏、工具)。内容需适应固定尺寸: 手机模式393x852竖屏, 电脑模式800x600横屏。可选择: 1)推送现有HTML文件(file_path) 2)现场写HTML代码(html_content)。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "应用名称 (显示在桌面图标下)"},
                    "file_path": {"type": "string", "description": "HTML文件路径 (相对于workspace/htmls/，如: snake.html)。与html_content二选一。"},
                    "html_content": {"type": "string", "description": "HTML代码内容 (需自包含样式和脚本)。与file_path二选一。"},
                    "device_mode": {"type": "string", "enum": ["mobile", "desktop"], "description": "设备模式: mobile=393x852竖屏(默认), desktop=800x600横屏"},
                    "to_player": {"type": "string", "description": "接收者 (默认 player)"},
                },
                "required": ["title"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "send_image_mail": {
            "description": "发送图片邮件，支持文件路径、URL或base64编码的图片",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "邮件标题"},
                    "image_source": {"type": "string", "description": "图片来源: 文件路径(如 workspace:photo.jpg) 或 URL 或 base64数据"},
                    "description": {"type": "string", "description": "图片描述 (可选)"},
                    "to_player": {"type": "string", "description": "接收者 (默认 player)"},
                },
                "required": ["title", "image_source"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 内置浏览器工具 ==========
        "browser_open": {
            "description": "打开网页 URL，返回页面可访问性快照 (用于了解页面结构和可交互元素)。每个元素有 ref 编号，后续操作用 ref 定位。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "网址 (如 'baidu.com' 或 'https://www.baidu.com')"},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "browser_click": {
            "description": "点击页面元素。通过 ref 编号定位 (从 browser_open 或 browser_snapshot 获取)，或用 CSS selector。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ref": {"type": "integer", "description": "元素编号 (从快照中获取)"},
                    "selector": {"type": "string", "description": "CSS/Playwright 选择器 (备选)"},
                },
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "browser_type": {
            "description": "在输入框中输入文字。通过 ref 定位输入框。可选 submit=true 自动按回车提交。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ref": {"type": "integer", "description": "输入框的 ref 编号"},
                    "selector": {"type": "string", "description": "CSS/Playwright 选择器 (备选)"},
                    "text": {"type": "string", "description": "要输入的文字"},
                    "submit": {"type": "boolean", "description": "输入后按回车提交 (默认 false)"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "browser_screenshot": {
            "description": "截取当前页面截图，保存到 workspace 目录。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "截图文件名 (默认 screenshot.png)"},
                },
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "browser_snapshot": {
            "description": "获取当前页面的可访问性快照 (刷新元素 ref 编号)。操作前先调用此工具确认页面状态。",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "browser_close": {
            "description": "关闭浏览器页面，释放资源。完成浏览任务后调用。",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 人机交互工具 ==========
        "ask_human": {
            "description": "向用户提问并等待文字回复。这是AI获取人类意向的核心工具，会阻塞等待用户输入文字。适合需要用户决策、选择或反馈的场景。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "要问用户的问题"},
                    "context": {"type": "string", "description": "问题的背景说明 (可选)"},
                    "timeout": {"type": "integer", "description": "超时时间(秒)，默认300秒"},
                },
                "required": ["question"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== NPC 协作工具 ==========
        "invoke_npc": {
            "description": "主动调用另一个 NPC 执行任务。会向目标 NPC 发送一条指令消息，目标 NPC 收到后会执行并返回结果。适合分工协作、委派任务。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标 NPC 名称 (如 'Alex', '财务')"},
                    "message": {"type": "string", "description": "发送给目标 NPC 的指令/消息 (自然语言)"},
                    "wait": {"type": "boolean", "description": "是否等待对方回复 (默认 true)。false=发完就走，适合不需要结果的通知"},
                },
                "required": ["target", "message"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
        "create_npc": {
            "description": "动态创建一个新的 NPC 并加入世界。可指定名称、人设、技能、LLM配置等。适合按需'招人'组建团队。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "NPC 名称 (唯一标识)"},
                    "description": {"type": "string", "description": "人设描述 (性格、职责、背景)"},
                    "skills": {"type": "array", "items": {"type": "string"}, "description": "技能列表 (如 ['web-browse', 'programmer'])"},
                    "tools": {"type": "array", "items": {"type": "string"}, "description": "工具列表 (如 ['run_command', '@file'])。有 skills 时可不填"},
                    "extra_prompt": {"type": "string", "description": "额外提示词/指令 (教NPC怎么做事)"},
                    "llm_channel": {"type": "string", "description": "LLM渠道 (如 'zhipu', 'deepseek')，不填则用默认"},
                    "llm_model": {"type": "string", "description": "LLM模型 (如 'glm-5')，不填则用渠道默认"},
                    "spawn_near": {"type": "string", "description": "出生在哪个 NPC 旁边 (默认在调用者旁边)"},
                },
                "required": ["name", "description"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 知识库检索工具 ==========
        "search_knowledge": {
            "description": "从知识库中检索相关信息。支持语义搜索，返回最相关的文档片段。知识库按集合(collection)组织，不指定则搜索所有集合。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或问题 (自然语言)"},
                    "collection": {"type": "string", "description": "知识库集合名 (可选，不填则搜索所有)"},
                    "top_k": {"type": "integer", "description": "返回结果数量 (默认 5)", "default": 5},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 图片生成工具 ==========
        "image_generate": {
            "description": "调用 AI 生成图片。输入文字描述，返回图片文件路径。可选渠道: image_zhipu (智谱CogView), image_siliconflow (千问Qwen-Image，效果更好)。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "图片描述 (英文效果更好，如 'a cute cat sitting on a desk')"},
                    "size": {"type": "string", "enum": ["1024x1024", "1024x1792", "1792x1024"], "description": "图片尺寸 (默认 1024x1024)"},
                    "channel": {"type": "string", "description": "渠道名 (可选): image_zhipu 或 image_siliconflow，默认自动选择"},
                    "filename": {"type": "string", "description": "保存文件名 (可选，默认自动生成)"},
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 图片编辑工具 ==========
        "image_edit": {
            "description": "基于参考图编辑生成新图片，保持角色和风格一致性。支持1-3张参考图（多图时prompt中用'image 1','image 2','image 3'引用）。适合漫画连续格保持人物一致。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "编辑描述。多参考图时用 'image 1 character in image 2 scene' 引用不同图"},
                    "image": {"type": "string", "description": "单张参考图路径 (相对 workspace，如 'images/panel_01.png')"},
                    "images": {
                        "type": "array",
                        "description": "多张参考图路径列表 (最多3张，优先于 image 字段)。如角色正面+背面+场景",
                        "items": {"type": "string"},
                        "maxItems": 3,
                    },
                    "size": {"type": "string", "enum": ["1024x1024", "1024x1792", "1792x1024"], "description": "输出尺寸 (默认 1024x1024)"},
                    "channel": {"type": "string", "description": "渠道名 (可选，默认 image_siliconflow)"},
                    "filename": {"type": "string", "description": "保存文件名 (可选，默认自动生成)"},
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 语音合成工具 ==========
        "tts": {
            "description": "文本转语音 (TTS)。将文字合成为 mp3 语音文件，保存到 workspace/audio/ 目录。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要合成的文本内容"},
                    "voice": {"type": "string", "enum": ["alex", "anna", "bella", "benjamin", "charles", "claire", "david", "diana"], "description": "音色 (默认 alex)"},
                    "filename": {"type": "string", "description": "输出文件名 (可选，默认自动生成)"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 语音识别工具 ==========
        "asr": {
            "description": "语音识别 (ASR)。将音频文件转为文字。支持 PCM/WAV/AMR/M4A 格式，单次 ≤ 60秒。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "音频文件路径 (相对 workspace，如 'audio/recording.pcm')"},
                    "format": {"type": "string", "enum": ["pcm", "wav", "amr", "m4a"], "description": "音频格式 (默认 pcm)"},
                },
                "required": ["file"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 漫画排版工具 ==========
        "composite_image": {
            "description": "漫画排版拼图。将多张图片按布局拼成漫画页面，支持添加对话框和文字。输出到 workspace/comic/output/ 目录。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "layout": {
                        "type": "string",
                        "description": "布局格式: '2x2' (2行2列), '1x4' (1行4列), '3x2' (3行2列) 等。留空则根据图片数量自动布局",
                    },
                    "panels": {
                        "type": "array",
                        "description": "每格的内容",
                        "items": {
                            "type": "object",
                            "properties": {
                                "image": {"type": "string", "description": "图片路径 (相对 workspace，如 'comic/images/panel_01.png')"},
                                "dialogues": {
                                    "type": "array",
                                    "description": "对话框列表",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string", "description": "台词内容"},
                                            "position": {"type": "string", "enum": ["top-left", "top-right", "bottom-left", "bottom-right"], "description": "对话框位置 (默认 top-left)"},
                                            "speaker": {"type": "string", "description": "说话人名字 (可选)"},
                                        },
                                        "required": ["text"],
                                    },
                                },
                            },
                            "required": ["image"],
                        },
                    },
                    "title": {"type": "string", "description": "漫画标题 (可选，显示在顶部)"},
                    "output": {"type": "string", "description": "输出文件名 (可选，默认自动生成)"},
                },
                "required": ["panels"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 图转视频工具 ==========
        "image_to_video": {
            "description": "图片转视频。将一张图片转为5秒动态视频（AI生成动作）。异步处理，会等待生成完成。输出到 workspace/video/。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "image": {"type": "string", "description": "图片路径 (相对 workspace，如 'images/panel_01.png')"},
                    "prompt": {"type": "string", "description": "视频动作描述 (英文，如 'camera slowly pans right, character walks forward')"},
                    "image_size": {"type": "string", "enum": ["1280x720", "720x1280", "960x960"], "description": "输出分辨率 (默认 1280x720)"},
                    "filename": {"type": "string", "description": "输出文件名 (可选，默认自动生成)"},
                },
                "required": ["image", "prompt"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },

        # ========== 视频合成工具 ==========
        "make_video": {
            "description": "视频合成。将视频片段或图片+配音合成为 MP4。优先用 video 字段传视频片段，没有视频时用 image 传静态图。输出到 workspace/comic/output/。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "panels": {
                        "type": "array",
                        "description": "每格的视频/图片和音频",
                        "items": {
                            "type": "object",
                            "properties": {
                                "video": {"type": "string", "description": "视频片段路径 (优先，如 'video/clip_01.mp4')"},
                                "image": {"type": "string", "description": "静态图片路径 (无视频时降级用，如 'images/panel_01.png')"},
                                "audio": {"type": "string", "description": "音频路径 (如 'audio/voice_01.mp3')，可选，覆盖视频原声"},
                                "duration": {"type": "number", "description": "仅静态图片时有效，有音频自动按音频时长"},
                            },
                        },
                    },
                    "title": {"type": "string", "description": "视频标题 (可选，开头标题卡)"},
                    "output": {"type": "string", "description": "输出文件名 (可选，默认自动生成)"},
                    "fps": {"type": "number", "description": "帧率 (默认24)"},
                },
                "required": ["panels"],
                "additionalProperties": False,
            },
            "handler": None,
            "enabled": True,
        },
    },
}

# 工作目录 (文件操作的默认目录，也是命令执行的 cwd)
WORKDIR = None

# 允许访问的额外目录 (除 WORKDIR 外，NPC 还能读写这些路径)
ALLOWED_DIRS = []

# 项目根目录 (用于推导相对路径)
PROJECT_ROOT = None


def set_workdir(path: str):
    """设置工作目录"""
    global WORKDIR, PROJECT_ROOT
    from pathlib import Path
    WORKDIR = Path(path).resolve()
    PROJECT_ROOT = WORKDIR.parent  # workspace 的上级 = 项目根


def add_allowed_dir(path: str):
    """添加额外的允许访问目录"""
    from pathlib import Path
    resolved = Path(path).resolve()
    if resolved not in ALLOWED_DIRS:
        ALLOWED_DIRS.append(resolved)


def is_path_allowed(filepath) -> bool:
    """检查路径是否在允许范围内"""
    from pathlib import Path
    fp = Path(filepath).resolve()
    # 检查 WORKDIR
    if WORKDIR and fp.is_relative_to(WORKDIR):
        return True
    # 检查额外目录
    for d in ALLOWED_DIRS:
        if fp.is_relative_to(d):
            return True
    return False


# ========== 接口区 ==========

def get_tools_by_protocol(protocol: str) -> Dict:
    """获取指定协议的所有工具"""
    return TOOL_REGISTRY.get(protocol, {})


def get_all_protocols() -> List[str]:
    """获取所有协议名称"""
    return list(TOOL_REGISTRY.keys())


def get_anthropic_tool_definitions(npc=None) -> List[Dict]:
    """
    获取 Anthropic 格式的工具定义 (用于 API 调用)

    Args:
        npc: NPC 对象，从 npc.memory['rom_tools'] 读取该 NPC 可用的工具列表
             如果未配置或为空，返回空列表 (不推送任何工具)

    Returns:
        List[Dict]: Anthropic 格式的工具定义列表
    """
    from tools.tool_providers.providers import get_provider
    provider = get_provider("anthropic")

    # 从 NPC 配置读取可用工具列表
    if npc is None:
        allowed_tools = []
    else:
        allowed_tools = npc.memory.get('rom_tools', [])

    # 如果没有配置工具，返回空列表
    if not allowed_tools:
        return []

    # 展开工具组 (@file -> [read_file, write_file, edit_text])
    allowed_tools = expand_tool_groups(allowed_tools)

    # 构建工具定义
    tools = [
        {"name": tool_id, **tool_config}
        for tool_id, tool_config in TOOL_REGISTRY.get("anthropic", {}).items()
        if tool_config.get("enabled", True) and tool_id in allowed_tools
    ]
    return provider.get_tool_definitions(tools)


def get_task_tool_definitions(npc) -> List[Dict]:
    """
    获取任务相关的工具定义 (用于 API 调用)

    根据任务的 tool_hint 动态注入工具，而不是依赖 NPC 配置

    Args:
        npc: NPC 对象

    Returns:
        List[Dict]: Anthropic 格式的工具定义列表
    """
    from tools.tool_providers.providers import get_provider
    from tools.task import get_pending_tasks_for

    provider = get_provider("anthropic")

    # 收集任务需要的工具
    needed_tools = set()
    pending_tasks = get_pending_tasks_for(npc.name)

    for task in pending_tasks:
        tool_hint = task.get('tool_hint', '')
        if tool_hint:
            # 解析工具名 (格式: "tool_name: ...")
            tool_name = tool_hint.split(':')[0].strip()
            needed_tools.add(tool_name)

    # 如果有任务，才添加 complete_task 工具
    if pending_tasks:
        needed_tools.add('complete_task')

    if not needed_tools:
        return []

    # 构建工具定义
    tools = [
        {"name": tool_id, **tool_config}
        for tool_id, tool_config in TOOL_REGISTRY.get("anthropic", {}).items()
        if tool_config.get("enabled", True) and tool_id in needed_tools
    ]
    return provider.get_tool_definitions(tools)


# ========== 工具管理接口 ==========

def register_tool(protocol: str, tool_id: str, config: Dict):
    """
    动态注册工具

    Args:
        protocol: 协议名 ("custom" 或 "anthropic")
        tool_id: 工具ID/名称
        config: 工具配置
    """
    if protocol not in TOOL_REGISTRY:
        TOOL_REGISTRY[protocol] = {}
    TOOL_REGISTRY[protocol][tool_id] = config


def enable_tool(protocol: str, tool_id: str, enabled: bool = True):
    """启用/禁用工具"""
    if protocol in TOOL_REGISTRY and tool_id in TOOL_REGISTRY[protocol]:
        TOOL_REGISTRY[protocol][tool_id]["enabled"] = enabled


def list_all_tools() -> Dict:
    """列出所有已注册工具"""
    return {
        protocol: {
            tid: {
                "name": t.get("name", tid),
                "enabled": t.get("enabled", True),
            }
            for tid, t in tools.items()
        }
        for protocol, tools in TOOL_REGISTRY.items()
    }


# ========== 自动初始化 ==========
# 导入 tool_l1 以触发 handler 注册
import tools.tool_l1  # noqa: F401
