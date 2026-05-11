# ============================================
# env/time_l1.py - 世界时间系统业务层
# 职责: 个体作用域、流程组装
# ============================================

import env.time_l2 as l2


def calc_time_str(tick, start_year, start_month, start_day, start_hour, start_minute, time_scale, tick_interval):
    """
    计算当前游戏时间字符串

    Returns:
        str: 时间字符串 "HH:MM"
    """
    info = calc_time_info(tick, start_year, start_month, start_day, start_hour, start_minute, time_scale, tick_interval)
    return info['time_str']


def calc_time_info(tick, start_year, start_month, start_day, start_hour, start_minute, time_scale, tick_interval):
    """
    计算详细时间信息

    Returns:
        dict: {year, month, day, hour, minute, time_str, period}
    """
    # 计算经过的游戏分钟数
    elapsed_minutes = l2.tick_to_game_minutes(tick, time_scale, tick_interval)

    # 加到起始时间上
    total_minutes = start_hour * 60 + start_minute + elapsed_minutes

    # 计算经过了多少天
    days_passed = total_minutes // (24 * 60)
    remaining_minutes = total_minutes % (24 * 60)

    # 计算小时和分钟
    hour = remaining_minutes // 60
    minute = remaining_minutes % 60

    # 计算新日期
    year, month, day = l2.add_days(start_year, start_month, start_day, days_passed)

    time_str = f"{hour:02d}:{minute:02d}"
    period = l2.get_period(hour)
    period_key = l2.get_period_key(hour)

    return {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "time_str": time_str,
        "period": period,
        "period_key": period_key,
    }
