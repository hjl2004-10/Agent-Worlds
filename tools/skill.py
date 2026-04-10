# ============================================
# tools/skill.py - Skill 总控层
# 职责: 配置持有、接口定义
# ============================================

import os
from tools import skill_l1

# ========== 配置 ==========
SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "skills")

# Skill 缓存 (避免重复读磁盘)
SKILL_CACHE = {}


def resolve_skills_for_npc(attrs):
    """接口: 给定 NPC 的 attributes dict，解析 skills 字段

    Args:
        attrs: HJL 的 attributes 节点

    Returns:
        (tools_list, summary_prompt, skill_prompts, tool_skill_map, mcp_servers)

        - tools_list: 去重合并的工具名列表
        - summary_prompt: 技能摘要（初始 prompt 用，不含完整说明）
        - skill_prompts: {skill_name: prompt_text} 按需注入用
        - tool_skill_map: {tool_name: skill_name} 反向映射
        - mcp_servers: MCP 服务器配置列表
    """
    skill_names = attrs.get("skills", [])
    extra_tools = attrs.get("tools", [])
    extra_prompt = attrs.get("tools_prompt", "")

    return skill_l1.resolve(
        SKILLS_DIR,
        skill_names,
        extra_tools=extra_tools,
        extra_prompt=extra_prompt,
    )


def get_all_skills():
    """列出所有可用 Skill（供前端/调试）"""
    skills = []
    if not os.path.isdir(SKILLS_DIR):
        return skills

    for name in sorted(os.listdir(SKILLS_DIR)):
        skill_dir = os.path.join(SKILLS_DIR, name)
        if os.path.isdir(skill_dir):
            data = skill_l1.load_skill_data(SKILLS_DIR, name)
            if data:
                skills.append({
                    "name": data["name"],
                    "description": data["description"],
                    "tools": data["tools"],
                    "has_mcp": data["mcp_server"] is not None,
                })
    return skills


def get_skill(name):
    """获取单个 Skill 的完整数据（含 prompt 文本）"""
    data = skill_l1.load_skill_data(SKILLS_DIR, name)
    if not data:
        return None
    return {
        "name": data["name"],
        "description": data["description"],
        "tools": data["tools"],
        "prompt_text": data["prompt"],
        "has_mcp": data["mcp_server"] is not None,
        "mcp_server": data["mcp_server"],
    }


def create_skill(name, description, tools, prompt_text="", mcp_server=None):
    """创建新 Skill"""
    skill_dir = os.path.join(SKILLS_DIR, name)
    if os.path.exists(skill_dir):
        return {"status": "error", "message": f"技能 '{name}' 已存在"}

    skill_l1.write_skill(SKILLS_DIR, name, {
        "name": name,
        "description": description,
        "tools": tools,
        "mcp_server": mcp_server,
    }, prompt_text)

    return {"status": "ok", "message": f"技能 '{name}' 已创建"}


def update_skill(name, description=None, tools=None, prompt_text=None, mcp_server=None):
    """更新已有 Skill"""
    existing = skill_l1.load_skill_data(SKILLS_DIR, name)
    if not existing:
        return {"status": "error", "message": f"技能 '{name}' 不存在"}

    config = {
        "name": name,
        "description": description if description is not None else existing["description"],
        "tools": tools if tools is not None else existing["tools"],
        "mcp_server": mcp_server if mcp_server is not None else existing["mcp_server"],
    }
    new_prompt = prompt_text if prompt_text is not None else existing["prompt"]

    skill_l1.write_skill(SKILLS_DIR, name, config, new_prompt)
    return {"status": "ok", "message": f"技能 '{name}' 已更新"}


def delete_skill(name):
    """删除 Skill"""
    skill_dir = os.path.join(SKILLS_DIR, name)
    if not os.path.isdir(skill_dir):
        return {"status": "error", "message": f"技能 '{name}' 不存在"}

    skill_l1.remove_skill(SKILLS_DIR, name)
    return {"status": "ok", "message": f"技能 '{name}' 已删除"}
