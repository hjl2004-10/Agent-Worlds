"""
浏览器工具 - 总控层 (L0)
配置 + 接口定义
"""
from pathlib import Path

# ========== 配置 ==========

HEADLESS = True                  # 无头模式 (Linux 服务器设 True)
BROWSER_TYPE = "chromium"        # chromium | firefox | webkit
SCREENSHOT_DIR = None            # 截图保存目录 (初始化时设置)


def init(workspace_path: str):
    """初始化浏览器工具配置"""
    global SCREENSHOT_DIR
    SCREENSHOT_DIR = Path(workspace_path)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def shutdown():
    """关闭浏览器资源"""
    from tools.browser_l1 import shutdown as _shutdown
    _shutdown()
