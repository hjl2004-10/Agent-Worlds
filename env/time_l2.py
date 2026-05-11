# ============================================
# env/time_l2.py - 世界时间系统原子层
# 职责: 原子逻辑、纯计算、无状态
# ============================================


def tick_to_game_minutes(tick, time_scale, tick_interval):
    """
    将tick转换为游戏分钟数

    公式: tick * tick_interval * time_scale / 60
    例如: 1 tick = 0.5秒现实 * 60倍 = 30秒游戏 = 0.5分钟游戏

    Args:
        tick: tick数
        time_scale: 时间加速倍率
        tick_interval: tick间隔(秒)

    Returns:
        int: 游戏分钟数
    """
    real_seconds = tick * tick_interval
    game_seconds = real_seconds * time_scale
    game_minutes = game_seconds / 60
    return int(game_minutes)


def minutes_to_hm(total_minutes):
    """
    将总分钟数转换为小时和分钟 (24小时制循环)

    Args:
        total_minutes: 总分钟数

    Returns:
        tuple: (hour, minute)
    """
    total_minutes = total_minutes % (24 * 60)
    hour = total_minutes // 60
    minute = total_minutes % 60
    return (hour, minute)


def get_period(hour):
    """
    根据小时获取时段描述

    Args:
        hour: 小时 (0-23)

    Returns:
        str: 时段描述
    """
    if 5 <= hour < 8:
        return "清晨"
    elif 8 <= hour < 12:
        return "上午"
    elif 12 <= hour < 14:
        return "中午"
    elif 14 <= hour < 18:
        return "下午"
    elif 18 <= hour < 20:
        return "傍晚"
    elif 20 <= hour < 23:
        return "晚上"
    else:
        return "深夜"


def get_period_key(hour):
    """返回时段的 i18n key，供前端翻译"""
    if 5 <= hour < 8:
        return "dawn"
    elif 8 <= hour < 12:
        return "morning"
    elif 12 <= hour < 14:
        return "noon"
    elif 14 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 20:
        return "dusk"
    elif 20 <= hour < 23:
        return "evening"
    else:
        return "night"


def is_leap_year(year):
    """判断是否为闰年"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def days_in_month(year, month):
    """获取指定月份的天数"""
    if month in [1, 3, 5, 7, 8, 10, 12]:
        return 31
    elif month in [4, 6, 9, 11]:
        return 30
    elif month == 2:
        return 29 if is_leap_year(year) else 28


def add_days(year, month, day, days_to_add):
    """
    日期加法

    Args:
        year, month, day: 起始日期
        days_to_add: 要添加的天数

    Returns:
        tuple: (new_year, new_month, new_day)
    """
    current_day = day + days_to_add

    while current_day > days_in_month(year, month):
        current_day -= days_in_month(year, month)
        month += 1
        if month > 12:
            month = 1
            year += 1

    return (year, month, current_day)
