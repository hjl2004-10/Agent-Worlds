# ============================================
# tools/skill_l2.py - Skill 原子层
# 职责: 纯合并/拼接逻辑，无状态
# ============================================


def merge_tool_lists(*tool_lists):
    """去重合并多个工具列表，保持首次出现的顺序"""
    seen = set()
    merged = []
    for tool_list in tool_lists:
        for tool in tool_list:
            if tool not in seen:
                seen.add(tool)
                merged.append(tool)
    return merged


def concat_prompts(*prompts):
    """拼接多段提示词，空段跳过，用分隔线隔开"""
    non_empty = [p.strip() for p in prompts if p and p.strip()]
    return "\n\n---\n\n".join(non_empty)


def build_skill_summary(skills_data):
    """生成技能摘要（只有名字+描述+工具列表，不含完整 prompt）

    Args:
        skills_data: [{"name": "programmer", "description": "...", "tools": [...]}]

    Returns:
        str: 摘要文本
    """
    if not skills_data:
        return ""

    lines = ["【已装备技能】"]
    for s in skills_data:
        tools_str = ", ".join(s["tools"]) if s["tools"] else "无"
        lines.append(f"- {s['name']}: {s['description']} (工具: {tools_str})")
    lines.append("")
    lines.append("使用以上工具时，系统会自动提供详细使用指南。")
    return "\n".join(lines)


def build_tool_skill_map(skills_data):
    """构建 tool_name → skill_name 的反向映射（自动展开 @工具组）

    Args:
        skills_data: [{"name": "programmer", "tools": ["read_file", "@file"]}]

    Returns:
        dict: {"read_file": "programmer", "write_file": "programmer", ...}
    """
    from tools.tool import expand_tool_groups

    mapping = {}
    for s in skills_data:
        # 先展开工具组 (@file → [read_file, write_file, edit_text])
        expanded = expand_tool_groups(s.get("tools", []))
        for tool in expanded:
            mapping[tool] = s["name"]
    return mapping
