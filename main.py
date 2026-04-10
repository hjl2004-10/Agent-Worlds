# ============================================
# main.py - 夸父 v2.0 总控
# 职责: 启动引导 + 主循环 + FastAPI监控(5000端口)
# ============================================

import sys
import os
import time
import math
import threading
import signal
import atexit
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from tools.loader import save_npc
from core.drive import drive
from core import state_bus
from core.lock import npcs_lock
from body.npc import WalkMode
from tools import llm_client as llm, io
from env import time as world_time

# ========== 配置区 ==========
# NPC_FILES 现在动态扫描 data/individuals/ 目录
# 时间参数现在从 world_time 动态获取，不再硬编码

# ========== 全局状态 ==========
npcs = []
current_tick = 0
last_event = ""

# 事件历史队列 (最近100条)
event_history: list[dict] = []
EVENT_HISTORY_MAX = 100


def push_event(event_type: str, npc: str, detail: str):
    """添加事件到历史队列"""
    from env import time as world_time
    info = world_time.get_time_info()
    event = {
        "tick": current_tick,
        "time": info["time_str"],
        "date": f"{info['month']}月{info['day']}日",
        "type": event_type,
        "npc": npc,
        "detail": detail,
    }
    event_history.append(event)
    if len(event_history) > EVENT_HISTORY_MAX:
        event_history.pop(0)


def _load_scene_config():
    from env import map as map_module

    scene_file = map_module.get_scene_path() / 'scene.hjl'
    return io.read_hjl(str(scene_file)) or {}


def _direction_to_angle(direction: str, fallback: float = 0.0) -> float:
    mapping = {
        "right": 0.0,
        "down": math.pi / 2,
        "left": math.pi,
        "up": -math.pi / 2,
    }
    if not direction:
        return fallback
    return mapping.get(str(direction).lower(), fallback)


def _apply_scene_spawns(scene_data):
    """对没有保存坐标的 NPC 使用 spawn_points 出生点

    如果 NPC 的 scene_positions 里已有当前场景的坐标，说明上次在这个场景
    退出时保存过位置，应该保留而不是覆盖。
    """
    from tools.loader_l1 import _get_current_scene_key
    scene_key = _get_current_scene_key()

    spawns = scene_data.get("spawn_points", {}) if scene_data else {}
    if not isinstance(spawns, dict):
        return

    normalized = {
        str(name).lower(): spawn
        for name, spawn in spawns.items()
        if isinstance(spawn, dict)
    }
    default_spawn = normalized.get("default")
    player_spawn = normalized.get("player") or default_spawn

    for npc in npcs:
        # 如果 NPC 在当前场景已有保存的坐标，跳过 (保留上次退出的位置)
        scene_positions = npc.memory.get('scene_positions', {})
        if scene_key in scene_positions:
            continue

        spawn = normalized.get(npc.name.lower())
        if spawn is None and npc.is_player:
            spawn = player_spawn
        if not spawn:
            continue

        npc.x = float(spawn.get("x", npc.x))
        npc.y = float(spawn.get("y", npc.y))
        npc.walk_direction = _direction_to_angle(spawn.get("direction"), npc.walk_direction)


def _reset_scene_runtime(scene_data=None, apply_spawns=True):
    from core.social.social_l1 import reset_runtime_state, set_npcs_ref

    drive.reset_counter()
    reset_runtime_state()

    for npc in npcs:
        npc.is_talking = False
        npc.ban_target_uuid = None
        npc.god_controlled = False
        npc.god_move_direction = None
        npc.walk_mode = WalkMode.IDLE
        npc.walk_mode_tick = 0
        npc.walk_target = None
        npc.walk_target_name = None

    if apply_spawns:
        _apply_scene_spawns(scene_data or _load_scene_config())

    set_npcs_ref(npcs)


def reset_world_state():
    """重置世界相关的运行时状态 (世界切换时调用)"""
    global current_tick, npcs

    from core.social import social_l1
    from env import map as map_module
    from tools.loader import load_npcs_for_world, save_npc
    from tools.task import load_tasks
    from tools.timer import load_timers

    # ① 先安全结束所有活跃对话任务，保存旧 NPC 数据
    from core.social.conversation_task import clear_all as clear_all_tasks
    clear_all_tasks()

    for npc in npcs:
        if npc.memory.get('ram_buffer'):
            print(f"[WorldSwitch] 保存 {npc.name} 的对话记录")
            social_l1.finalize_conversation_if_needed(npc)
        save_npc(npc, f"{npc.name.lower()}.hjl")

    # ② 重置对话系统运行态
    social_l1.reset_runtime_state()

    # ②a 清理微信对话状态 (上下文和输入队列，绑定保留)
    from core.wechat import wechat_l1 as wechat_l1_module
    wechat_l1_module.cleanup_all_wechat_state()

    # ③ 重置主循环 tick
    current_tick = 0

    # ④ 重置驱动系统的内部计数器
    drive.reset_counter()

    # ⑤ 加载新世界的 NPC
    npcs = load_npcs_for_world(map_module._current_world)
    load_tasks(map_module._current_world)
    load_timers(map_module._current_world)
    _reset_scene_runtime(_load_scene_config(), apply_spawns=True)
    print(f"[Main] 加载 {len(npcs)} 个NPC: {[n.name for n in npcs]}")

    # ⑥ 更新所有模块的 NPC 引用
    from core.social.social_l1 import set_npcs_ref
    set_npcs_ref(npcs)

    # ⑦ 刷新 API 和 dispatcher 的引用 (npcs 被重新赋值了)
    _init_api_state()
    from core import dispatcher
    dispatcher.init(npcs, _find_npc, _build_npc_config_payload)

    print("[Main] 世界状态已重置")


def _find_npc(npc_name: str):
    for npc in npcs:
        if npc.name.lower() == npc_name.lower():
            return npc
    return None


def _build_npc_config_payload(npc):
    return {
        "name": npc.name,
        "sprite_id": npc.sprite_id,
        "description": npc.memory.get('rom_personality', ''),
        "prompt": npc.memory.get('rom_prompt', []),
        "tools_prompt": npc.memory.get('rom_tools_prompt', ''),
        "extra_prompt": npc.memory.get('rom_extra_prompt', ''),
        "tools": npc.memory.get('rom_tools', []),
        "skills": npc.memory.get('rom_skills', []),
        "mcp_servers": npc.memory.get('mcp_servers', []),
        "groups": npc.memory.get('rom_groups', []),
        "llm": {
            "channel": npc.llm_channel,
            "model": npc.llm_model
        },
        "behavior": {
            "base_initiative": npc.initiative,
            "walk_idle": npc.walk_idle_duration,
            "walk_random": npc.walk_random_duration,
            "walk_linear": npc.walk_linear_duration,
            "no_collision": npc.memory.get('no_collision', False)
        },
        "is_player": npc.is_player,
        "enabled": npc.enabled
    }


def _dispatch_state_command(command_type: str, payload: dict):
    from core.dispatcher import dispatch
    return dispatch(command_type, payload)

state_bus.register_dispatcher(_dispatch_state_command)

# ========== FastAPI 监控 ==========
app = FastAPI(title="夸父", version="2.0")

# CORS + Token 认证
from api.auth import setup_auth
setup_auth(app)

# ========== API 路由注册 (从 api/ 子模块加载) ==========
from api import register_all_routers
from api import _state as api_state

register_all_routers(app)

# 注入全局状态引用到 api._state (延迟到 boot 之后在下方 boot() 中调用)
# 这里先定义辅助函数供 api._state 使用
def _init_api_state():
    api_state.init({
        "npcs": npcs,
        "get_tick": lambda: current_tick,
        "get_last_event": lambda: last_event,
        "get_event_history": lambda: event_history,
        "push_event": push_event,
        "find_npc": _find_npc,
        "build_npc_config": _build_npc_config_payload,
        "load_scene_config": _load_scene_config,
        "reset_world_state": reset_world_state,
        "reset_scene_runtime": _reset_scene_runtime,
    })


# ========== 以下路由已迁移到 api/ 子模块 ==========
# 保留占位注释，便于 git diff 追踪
# 原 60+ 路由已拆分为:
#   api/status.py      - 状态/地图/事件
#   api/god.py          - 上帝模式
#   api/npc.py          - NPC 管理
#   api/conversation.py - 对话系统
#   api/tools_api.py    - 工具/技能/MCP/市场
#   api/world.py        - 世界/场景
#   api/tasks.py        - 任务/定时器
#   api/mailbox.py      - 邮箱/表单
#   api/misc.py         - LLM渠道/精灵图


# 静态文件 (前端 - React SPA)
_main_dir = os.path.dirname(os.path.abspath(__file__))
static_dist_path = os.path.join(_main_dir, "static", "dist")
static_src_path = os.path.join(_main_dir, "static")

# 优先使用构建后的 dist 目录
if os.path.exists(static_dist_path):
    # 挂载静态资源目录
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dist_path, "assets")), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(static_dist_path, "index.html"))

    # SPA fallback - 未匹配的路由返回 index.html
    # ⚠️ 必须排除 /api/ 路径！否则 {path:path} 会拦截参数化的 API 路由
    #    （如 /api/mailbox/{player_name}），返回 index.html 而不是 JSON
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API 路由绝不走 SPA fallback
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": f"API not found: /{full_path}"}
            )

        file_path = os.path.join(static_dist_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dist_path, "index.html"))

elif os.path.exists(static_src_path):
    # 开发模式: 使用源目录 (需要配合 Vite dev server)
    app.mount("/static", StaticFiles(directory=static_src_path), name="static")

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(static_src_path, "index.html"))


# ========== 系统函数 ==========
def boot():
    """系统引导"""
    global npcs

    print("=" * 50)
    print("AI_OS v2.0")
    print("=" * 50)

    io.ensure_data_dir()
    llm.init()

    # 初始化 MCP 客户端事件循环
    from tools import mcp_client
    mcp_client.init()
    # 初始化 MCP 进程管理器
    from tools import mcp_manager
    mcp_manager.init()
    from env import map as map_module
    map_module.init()
    world_time.init()  # 初始化时间系统

    # 初始化工具工作目录
    from tools.tool import set_workdir, add_allowed_dir
    from pathlib import Path
    project_root = Path(__file__).parent
    workspace_path = project_root / "workspace"
    workspace_path.mkdir(exist_ok=True)
    set_workdir(str(workspace_path))

    # 初始化内置浏览器工具
    from tools import browser as browser_module
    browser_module.init(str(workspace_path))

    # 初始化市场模块
    from tools import marketplace as marketplace_module
    marketplace_module.init(str(project_root))

    # 额外允许访问的目录 (skill 引导文件、数据目录等)
    add_allowed_dir(str(project_root / "data" / "skills"))
    add_allowed_dir(str(project_root / "data" / "individuals"))

    # 加载运行时状态 (当前世界/场景)
    from env import map as map_module
    map_module.init()  # 先初始化运行时状态

    # 加载当前世界的 NPC (按 world_id 过滤)
    from tools.loader import load_npcs_for_world
    npcs = load_npcs_for_world(map_module._current_world)
    print(f"[Boot] 加载 {len(npcs)} 个NPC: {[n.name for n in npcs]}")

    # 加载地点注册表
    map_module.load_locations()

    # 加载障碍物数据
    map_module.load_obstacles()

    # 加载地图瓦片数据
    map_module.load_tiles()

    # 设置 NPC 引用 (供工具系统使用)
    from core.social.social_l1 import set_npcs_ref
    set_npcs_ref(npcs)

    # 加载任务池
    from tools.task import load_tasks
    load_tasks(map_module._current_world)

    # 加载定时器池
    from tools.timer import load_timers
    load_timers(map_module._current_world)
    _reset_scene_runtime(_load_scene_config(), apply_spawns=True)

    # 初始化邮箱系统
    from tools.mailbox import init as mailbox_init
    mailbox_init()

    # 注入全局状态到 API 路由模块
    _init_api_state()

    # 注入全局引用到命令分发器
    from core import dispatcher
    dispatcher.init(npcs, _find_npc, _build_npc_config_payload)

    # QQ Bot Gateway 延迟启动 (在 qq_chat 首次调用时才连接)

    # 微信 iLink: 恢复绑定 + 启动消息轮询
    from core.wechat import wechat as wechat_module
    from core.wechat import wechat_l1 as wechat_l1_module
    wechat_l1_module.restore_bindings_from_npcs(npcs)
    wechat_module.start_polling()


def loop():
    """Main loop"""
    global current_tick, last_event, _shutdown_requested

    print("[Loop] Start")

    from core.social import social
    from tools.timer_l1 import check_timers

    try:
        while current_tick < world_time.get_day_ticks() * 100:  # 100天
            state_bus.process_all()

            if _shutdown_requested:
                print("[Loop] Shutdown requested, stopping current loop")
                break

            current_tick += 1
            world_time.set_tick(current_tick)

            with npcs_lock:
                drive.update_all(npcs)
                check_timers(current_tick, npcs)

            state_bus.process_all()

            # 推进所有活跃对话 (非阻塞)
            social.tick_all()

            sleep_remaining = world_time.get_tick_interval()
            while sleep_remaining > 0 and not _shutdown_requested:
                sleep_chunk = min(0.1, sleep_remaining)
                time.sleep(sleep_chunk)
                sleep_remaining -= sleep_chunk
                state_bus.process_all()
                # 在等待期间也推进对话 (提高响应速度)
                social.tick_all()

    except KeyboardInterrupt:
        print("\n[Loop] Interrupted")


_shutdown_done = False


def shutdown():
    """关闭保存 (幂等，可安全多次调用)"""
    global _shutdown_done
    if _shutdown_done:
        return
    _shutdown_done = True

    print("[Shutdown] 保存中...")
    state_bus.process_all()

    # 停止微信轮询
    from core.wechat import wechat as wechat_module
    wechat_module.stop_polling()

    # 强制结束所有活跃对话任务
    from core.social import social_l1
    from core.social.conversation_task import clear_all as clear_all_tasks
    clear_all_tasks()

    # 确保 ram_buffer 被正确转换为 hdd_history
    for npc in npcs:
        if npc.memory.get('ram_buffer'):
            print(f"[Shutdown] 保存 {npc.name} 的对话记录")
            social_l1.finalize_conversation_if_needed(npc)

    # 保存世界时间
    world_time.save()

    # 保存所有 NPC
    for npc in npcs:
        save_npc(npc, f"{npc.name.lower()}.hjl")

    # 保存任务池
    from tools.task import save_tasks
    save_tasks()

    # 保存定时器池
    from tools.timer import save_timers
    save_timers()

    # 关闭内置浏览器
    from tools import browser as browser_module
    browser_module.shutdown()

    # 关闭 MCP 连接
    from tools import mcp_client
    mcp_client.shutdown()

    print("[Shutdown] 完成")
    state_bus.process_all()


def start_server():
    """启动监控服务"""
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="warning")


# ========== 信号处理 ==========
_shutdown_requested = False


def _signal_handler(signum, frame):
    """信号处理器 - 设置标志位，让主循环优雅退出"""
    global _shutdown_requested
    if _shutdown_requested:
        # 第二次 Ctrl+C，强制退出
        print("\n[Shutdown] 强制退出")
        sys.exit(1)
    _shutdown_requested = True
    print(f"\n[Signal] 收到信号 {signum}，准备优雅退出...")


def _register_signal_handlers():
    """注册信号处理器"""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    # Windows 不支持 SIGQUIT
    try:
        signal.signal(signal.SIGQUIT, _signal_handler)
    except AttributeError:
        pass
    # atexit 作为最后保障
    atexit.register(shutdown)


# ========== 入口 ==========
if __name__ == "__main__":
    _register_signal_handlers()

    try:
        boot()

        # 启动监控线程
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        print("[Server] http://localhost:5000")

        # 主循环
        loop()
    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt")
    finally:
        shutdown()
