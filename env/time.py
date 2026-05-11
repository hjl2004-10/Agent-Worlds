# ============================================
# env/time.py - 世界时间系统总控层
# 职责: 配置持有、接口定义
#
# 时间法则:
# - 现实 1 分钟 = 游戏 1 小时 (60倍加速)
# - 1 tick = 0.5 秒现实 = 30 秒游戏时间
# - 1 天 = 2880 ticks
# ============================================

import env.time_l1 as l1
from tools import io

# ========== 默认配置 (可被世界配置覆盖) ==========
DEFAULT_TIME_SCALE = 60     # 默认时间加速倍率
DEFAULT_TICK_INTERVAL = 0.5  # 默认tick间隔(秒)

# ========== 状态区 ==========
_current_tick = 0
_start_year = 2025
_start_month = 1
_start_day = 1
_start_hour = 8
_start_minute = 0
_time_scale = DEFAULT_TIME_SCALE      # 当前世界的时间加速倍率
_tick_interval = DEFAULT_TICK_INTERVAL  # 当前世界的tick间隔
_day_ticks = 2880                      # 一天的tick数


# ========== 接口区 ==========
def init():
    """从当前世界的 world.hjl 加载时间状态和参数"""
    global _current_tick, _start_year, _start_month, _start_day, _start_hour, _start_minute
    global _time_scale, _tick_interval, _day_ticks

    from env import map as map_module
    world_file = str(map_module.get_world_path() / 'world.hjl')

    data = io.read_hjl(world_file)
    if data:
        # 加载时间起点
        if 'time' in data:
            time_data = data['time']
            _start_year = time_data.get('year', 2025)
            _start_month = time_data.get('month', 1)
            _start_day = time_data.get('day', 1)
            _start_hour = time_data.get('hour', 8)
            _start_minute = time_data.get('minute', 0)
            _time_scale = time_data.get('time_scale', DEFAULT_TIME_SCALE)
            _tick_interval = time_data.get('tick_interval', DEFAULT_TICK_INTERVAL)

        # 加载世界设置
        if 'settings' in data:
            _day_ticks = data['settings'].get('day_ticks', 2880)

    _current_tick = 0
    print(f"[Time] 加载时间: {get_datetime_str()}, time_scale={_time_scale}, tick_interval={_tick_interval}")


def save():
    """保存当前时间状态到当前世界的 world.hjl"""
    info = get_time_info()

    from env import map as map_module
    world_file = str(map_module.get_world_path() / 'world.hjl')

    data = io.read_hjl(world_file) or {}

    # 更新时间部分
    data['time'] = {
        'year': info['year'],
        'month': info['month'],
        'day': info['day'],
        'hour': info['hour'],
        'minute': info['minute'],
        'time_scale': _time_scale,
        'tick_interval': _tick_interval
    }

    io.write_hjl(world_file, data)
    print(f"[Time] 保存时间: {get_datetime_str()}")


def tick():
    """推进一个tick"""
    global _current_tick
    _current_tick += 1
    return _current_tick


def get_tick():
    """获取当前tick数"""
    return _current_tick


def set_tick(tick_count):
    """设置当前tick数"""
    global _current_tick
    _current_tick = tick_count


def get_time_str():
    """
    获取当前游戏时间字符串
    格式: "HH:MM"
    """
    info = get_time_info()
    return info['time_str']


def get_date_str():
    """
    获取当前游戏日期字符串
    格式: "YYYY年MM月DD日"
    """
    info = get_time_info()
    return f"{info['year']}年{info['month']}月{info['day']}日"


def get_datetime_str():
    """
    获取完整日期时间字符串
    格式: "YYYY年MM月DD日 HH:MM"
    """
    info = get_time_info()
    return f"{info['year']}年{info['month']}月{info['day']}日 {info['time_str']}"


def get_time_info():
    """
    获取详细时间信息
    返回: {year, month, day, hour, minute, time_str, period}
    """
    return l1.calc_time_info(
        tick=_current_tick,
        start_year=_start_year,
        start_month=_start_month,
        start_day=_start_day,
        start_hour=_start_hour,
        start_minute=_start_minute,
        time_scale=_time_scale,
        tick_interval=_tick_interval
    )


def get_tick_interval():
    """获取当前世界的tick间隔 (供主循环使用)"""
    return _tick_interval


def get_day_ticks():
    """获取当前世界一天的tick数"""
    return _day_ticks


def get_time_scale():
    """获取当前世界的时间加速倍率"""
    return _time_scale
