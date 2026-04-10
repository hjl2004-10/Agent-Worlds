"""
浏览器工具 - 原子层 (L2)
快照解析、元素提取等纯计算函数
"""


def parse_ax_tree(node, depth=0, ref_counter=None):
    """
    将 Playwright accessibility snapshot 转为文本格式

    类似 @playwright/mcp 的 snapshot 输出格式:
    - ref=1 button "搜索"
    - ref=2 textbox "请输入关键词"

    Returns:
        (str, dict): (格式化文本, {ref_id: node} 映射)
    """
    if ref_counter is None:
        ref_counter = [0]

    lines = []
    ref_map = {}

    if not node:
        return "", ref_map

    role = node.get("role", "")
    name = node.get("name", "")

    # 跳过无意义节点
    skip_roles = {"none", "generic", "presentation"}

    # 有交互意义的节点才分配 ref
    interactive_roles = {
        "link", "button", "textbox", "checkbox", "radio",
        "combobox", "menuitem", "tab", "option", "searchbox",
        "slider", "spinbutton", "switch", "menuitemcheckbox",
        "menuitemradio", "treeitem"
    }

    if role and role not in skip_roles:
        ref_counter[0] += 1
        ref_id = ref_counter[0]
        ref_map[ref_id] = node

        indent = "  " * depth

        # 构建显示行
        parts = [f"{indent}"]
        if role in interactive_roles:
            parts.append(f"[ref={ref_id}]")
        parts.append(role)
        if name:
            # 截断过长的名称
            display_name = name[:80] + "..." if len(name) > 80 else name
            parts.append(f'"{display_name}"')

        # 附加状态
        value = node.get("value", "")
        if value:
            parts.append(f'value="{value}"')
        if node.get("checked"):
            parts.append("[checked]")
        if node.get("disabled"):
            parts.append("[disabled]")
        if node.get("expanded") is not None:
            parts.append(f'[{"expanded" if node["expanded"] else "collapsed"}]')

        lines.append(" ".join(parts))

    # 递归子节点
    for child in node.get("children", []):
        child_text, child_refs = parse_ax_tree(child, depth + 1, ref_counter)
        if child_text:
            lines.append(child_text)
        ref_map.update(child_refs)

    return "\n".join(lines), ref_map


def find_node_by_ref(ref_map, ref_id):
    """根据 ref 编号查找节点"""
    return ref_map.get(ref_id)


def build_selector_from_node(node):
    """
    从 ax node 构建 Playwright selector
    优先用 role + name 定位
    """
    role = node.get("role", "")
    name = node.get("name", "")

    if role and name:
        return f'role={role}[name="{name}"]'
    elif role:
        return f'role={role}'
    elif name:
        return f'text="{name}"'
    return None


def truncate_snapshot(text, max_lines=200):
    """截断过长的快照文本"""
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + f"\n... (共 {len(lines)} 行，已截断)"
