# ============================================
# core/analyzer/analyzer_l1.py - 回复分析器业务层
# 职责: 个体作用域、流程组装
#
# 流程:
# 1. 遍历所有规则
# 2. 调用原子层匹配文本
# 3. 合并所有匹配的效果
# 4. 应用属性变更到NPC
# 5. 处理特殊标签 (如 [group:X])
# ============================================

import core.analyzer.analyzer_l2 as l2


def analyze_and_apply(npc, text, rules, bounds, listener=None):
    """
    分析文本并应用属性变更

    Args:
        npc: NPC对象 (说话者)
        text: AI回复文本
        rules: 分析规则字典
        bounds: 属性边界字典
        listener: 对话对象 (用于 group 标签绑定)

    Returns:
        dict: 实际应用的属性变更 {"initiative": +1, "groups_added": [...], ...}
    """
    applied_changes = {}

    # === 阶段1: 处理规则匹配 (数值变更) ===
    total_effects = {}

    for rule_name, rule_config in rules.items():
        patterns = rule_config.get("patterns", [])
        effect = rule_config.get("effect", {})

        # 原子层: 检查文本是否匹配该规则的任一模式
        if l2.match_patterns(text, patterns):
            print(f"[Analyzer] 匹配规则: {rule_name}")

            # 合并效果
            for attr, delta in effect.items():
                if attr not in total_effects:
                    total_effects[attr] = 0
                total_effects[attr] += delta

    # 应用数值变更
    for attr, delta in total_effects.items():
        if delta == 0:
            continue

        # 获取当前值
        old_value = get_npc_attribute(npc, attr)
        if old_value is None:
            continue

        # 计算新值
        new_value = old_value + delta

        # 应用边界限制
        if attr in bounds:
            min_val, max_val = bounds[attr]
            new_value = l2.clamp(new_value, min_val, max_val)

        # 设置新值
        set_npc_attribute(npc, attr, new_value)
        applied_changes[attr] = delta

        print(f"[Analyzer] {npc.name}.{attr}: {old_value} -> {new_value} ({'+' if delta > 0 else ''}{delta})")

    # === 阶段2: 处理特殊标签 [group:X] ===
    # group 格式变为 "关系:对象"，如 "朋友:Bob"
    group_tags = l2.extract_group_tags(text)
    if group_tags and listener:
        # 将 "朋友" 转换为 "朋友:Bob"
        bound_groups = [f"{tag}:{listener.name}" for tag in group_tags]
        added_groups = add_groups_to_npc(npc, bound_groups)
        if added_groups:
            applied_changes["groups_added"] = added_groups
            print(f"[Analyzer] {npc.name}.groups 添加: {added_groups}")

    return applied_changes


def add_groups_to_npc(npc, group_names):
    """
    将群组添加到NPC的群组列表

    Args:
        npc: NPC对象
        group_names: 要添加的群组名列表

    Returns:
        list: 实际新添加的群组名 (去重后)
    """
    # 确保 rom_groups 存在
    if 'rom_groups' not in npc.memory:
        npc.memory['rom_groups'] = []

    current_groups = npc.memory['rom_groups']
    added = []

    for group_name in group_names:
        # 去重: 只添加不存在的群组
        if group_name not in current_groups:
            current_groups.append(group_name)
            added.append(group_name)

    return added


def get_npc_attribute(npc, attr_name):
    """
    获取NPC属性值

    Args:
        npc: NPC对象
        attr_name: 属性名

    Returns:
        属性值，不存在则返回None

    扩展说明:
        添加新属性时，在此处添加对应的获取逻辑
    """
    # === 已支持的属性 ===
    if attr_name == "initiative":
        return npc.initiative

    # === [预留] 扩展属性 ===
    # if attr_name == "mood":
    #     return npc.mood
    # if attr_name == "energy":
    #     return npc.energy
    # if attr_name == "trust":
    #     return npc.trust

    return None


def set_npc_attribute(npc, attr_name, value):
    """
    设置NPC属性值

    Args:
        npc: NPC对象
        attr_name: 属性名
        value: 新值

    扩展说明:
        添加新属性时，在此处添加对应的设置逻辑
    """
    # === 已支持的属性 ===
    if attr_name == "initiative":
        npc.initiative = value
        return True

    # === [预留] 扩展属性 ===
    # if attr_name == "mood":
    #     npc.mood = value
    #     return True
    # if attr_name == "energy":
    #     npc.energy = value
    #     return True
    # if attr_name == "trust":
    #     npc.trust = value
    #     return True

    return False
