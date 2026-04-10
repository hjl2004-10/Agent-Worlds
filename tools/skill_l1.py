# ============================================
# tools/skill_l1.py - Skill 业务层
# 职责: 个体作用域，解析单个 NPC 的 Skill 配置
# ============================================

import os
import json
import shutil
from tools.skill_l2 import merge_tool_lists, concat_prompts, build_skill_summary, build_tool_skill_map


def load_skill_data(skills_dir, skill_name):
    """读取单个 Skill 的定义和提示词

    Returns:
        dict: {"name", "description", "tools", "prompt", "mcp_server"}
        None: 如果 skill 不存在
    """
    skill_dir = os.path.join(skills_dir, skill_name)
    hjl_path = os.path.join(skill_dir, "skill.hjl")

    if not os.path.exists(hjl_path):
        print(f"⚠️ [Skill] 未找到 skill: {skill_name} ({hjl_path})")
        return None

    # 读取 skill.hjl
    with open(hjl_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 读取 prompt.md
    prompt_file = config.get("prompt_file", "prompt.md")
    prompt_path = os.path.join(skill_dir, prompt_file)
    prompt_text = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_text = f.read()

    return {
        "name": config.get("name", skill_name),
        "description": config.get("description", ""),
        "tools": config.get("tools", []),
        "prompt": prompt_text,
        "mcp_server": config.get("mcp_server", None),
    }


def resolve(skills_dir, skill_names, extra_tools=None, extra_prompt=""):
    """解析 Skill 列表，合并工具，按需分离提示词

    Returns:
        (merged_tools, summary_prompt, skill_prompts, tool_skill_map, mcp_servers)

        - merged_tools: 去重合并的工具名列表
        - summary_prompt: 技能摘要 + extra_prompt（给初始 prompt 用）
        - skill_prompts: {skill_name: prompt_text} 完整提示词（按需注入用）
        - tool_skill_map: {tool_name: skill_name} 反向映射
        - mcp_servers: MCP 服务器配置列表
    """
    all_tool_lists = []
    skills_meta = []       # 用于生成摘要
    skill_prompts = {}     # skill_name → 完整 prompt
    mcp_servers = []

    for skill_name in skill_names:
        skill_data = load_skill_data(skills_dir, skill_name)
        if skill_data is None:
            continue

        all_tool_lists.append(skill_data["tools"])
        skills_meta.append({
            "name": skill_data["name"],
            "description": skill_data["description"],
            "tools": skill_data["tools"],
        })

        # 完整 prompt 单独存储，不塞进初始提示词
        if skill_data["prompt"]:
            skill_prompts[skill_data["name"]] = skill_data["prompt"]

        if skill_data["mcp_server"]:
            mcp_servers.append(skill_data["mcp_server"])

    # 追加 NPC 自身的 extra tools
    if extra_tools:
        all_tool_lists.append(extra_tools)

    merged_tools = merge_tool_lists(*all_tool_lists) if all_tool_lists else []

    # 生成摘要 prompt（技能列表 + extra_prompt）
    summary = build_skill_summary(skills_meta)
    if extra_prompt:
        summary = concat_prompts(summary, extra_prompt) if summary else extra_prompt

    # 构建工具→技能的反向映射
    tool_skill_map = build_tool_skill_map(skills_meta)

    return merged_tools, summary, skill_prompts, tool_skill_map, mcp_servers


def write_skill(skills_dir, name, config_data, prompt_text):
    """写入 Skill 定义文件 (skill.hjl + prompt.md)

    Args:
        skills_dir: skills 根目录
        name: skill 名称
        config_data: {"name", "description", "tools", "mcp_server"}
        prompt_text: prompt.md 内容
    """
    skill_dir = os.path.join(skills_dir, name)
    os.makedirs(skill_dir, exist_ok=True)

    hjl = {
        "name": config_data["name"],
        "description": config_data["description"],
        "tools": config_data["tools"],
        "prompt_file": "prompt.md",
        "mcp_server": config_data.get("mcp_server"),
    }
    with open(os.path.join(skill_dir, "skill.hjl"), 'w', encoding='utf-8') as f:
        json.dump(hjl, f, indent=2, ensure_ascii=False)

    with open(os.path.join(skill_dir, "prompt.md"), 'w', encoding='utf-8') as f:
        f.write(prompt_text or "")


def remove_skill(skills_dir, name):
    """删除 Skill 目录"""
    skill_dir = os.path.join(skills_dir, name)
    if os.path.isdir(skill_dir):
        shutil.rmtree(skill_dir)
