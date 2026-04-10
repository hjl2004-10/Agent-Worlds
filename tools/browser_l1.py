"""
浏览器工具 - 业务层 (L1)
浏览器实例管理 + 工具 handler 实现
"""
import asyncio
import os
import threading
from pathlib import Path

from tools import browser_l2

# ========== 全局浏览器实例 ==========

_browser = None          # playwright Browser (共享)
_playwright = None       # playwright 实例
_pages = {}              # {npc_name: Page}
_ref_maps = {}           # {npc_name: {ref_id: node}} 最近一次快照的引用映射
_lock = threading.Lock()
_loop = None             # asyncio 事件循环 (浏览器操作都在这里)
_loop_thread = None


def _ensure_loop():
    """确保浏览器专用的 asyncio 事件循环在运行"""
    global _loop, _loop_thread
    if _loop is not None and _loop.is_running():
        return

    def _run_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    _loop = asyncio.new_event_loop()
    _loop_thread = threading.Thread(target=_run_loop, args=(_loop,), daemon=True)
    _loop_thread.start()


def _run_async(coro):
    """在浏览器事件循环中执行异步操作，同步等待结果"""
    _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=60)


async def _get_browser():
    """获取或创建全局浏览器实例"""
    global _browser, _playwright
    if _browser and _browser.is_connected():
        return _browser

    from playwright.async_api import async_playwright
    _playwright = await async_playwright().start()

    from tools.browser import HEADLESS, BROWSER_TYPE
    launch_args = {"headless": HEADLESS}

    if BROWSER_TYPE == "chromium":
        _browser = await _playwright.chromium.launch(**launch_args)
    elif BROWSER_TYPE == "firefox":
        _browser = await _playwright.firefox.launch(**launch_args)
    elif BROWSER_TYPE == "webkit":
        _browser = await _playwright.webkit.launch(**launch_args)
    else:
        _browser = await _playwright.chromium.launch(**launch_args)

    print(f"[Browser] 🌐 浏览器已启动 (headless={HEADLESS}, type={BROWSER_TYPE})")
    return _browser


async def _get_page(npc_name):
    """获取 NPC 专属的页面，没有则创建"""
    if npc_name in _pages:
        page = _pages[npc_name]
        if not page.is_closed():
            return page

    browser = await _get_browser()
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="zh-CN",
    )
    page = await context.new_page()
    _pages[npc_name] = page
    return page


async def _close_page(npc_name):
    """关闭 NPC 的页面"""
    if npc_name in _pages:
        page = _pages.pop(npc_name)
        if not page.is_closed():
            await page.close()
        _ref_maps.pop(npc_name, None)


async def _take_snapshot(npc_name):
    """获取当前页面的可访问性快照"""
    page = await _get_page(npc_name)
    snapshot = await page.accessibility.snapshot()
    if not snapshot:
        return "页面为空或无法获取快照", {}

    text, ref_map = browser_l2.parse_ax_tree(snapshot)
    _ref_maps[npc_name] = ref_map
    text = browser_l2.truncate_snapshot(text)
    return text, ref_map


# ========== 工具 Handler ==========

def tool_browser_open(input_obj: dict, npc, context) -> str:
    """打开 URL 并返回页面快照"""
    url = input_obj.get("url", "")
    if not url:
        return "错误: 请提供 url 参数"

    # 补全 http
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    npc_name = npc.name if hasattr(npc, 'name') else str(npc)

    try:
        async def _do():
            page = await _get_page(npc_name)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await page.title()
            snapshot_text, _ = await _take_snapshot(npc_name)
            return title, page.url, snapshot_text

        title, final_url, snapshot = _run_async(_do())
        print(f"🌐 [{npc_name}] 打开: {final_url}")

        return f"已打开: {final_url}\n标题: {title}\n\n页面快照:\n{snapshot}"

    except Exception as e:
        return f"打开 {url} 失败: {str(e)}"


def tool_browser_click(input_obj: dict, npc, context) -> str:
    """点击页面元素"""
    ref = input_obj.get("ref")
    selector = input_obj.get("selector", "")
    npc_name = npc.name if hasattr(npc, 'name') else str(npc)

    try:
        async def _do():
            page = await _get_page(npc_name)

            if ref is not None:
                # 通过 ref 编号定位
                ref_map = _ref_maps.get(npc_name, {})
                node = browser_l2.find_node_by_ref(ref_map, int(ref))
                if not node:
                    return f"错误: ref={ref} 不存在，请先调用 browser_snapshot 获取最新快照"
                sel = browser_l2.build_selector_from_node(node)
                if not sel:
                    return f"错误: ref={ref} 无法构建选择器"
            elif selector:
                sel = selector
            else:
                return "错误: 请提供 ref (元素编号) 或 selector"

            await page.locator(sel).first.click(timeout=10000)
            # 等待页面稳定
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
            snapshot_text, _ = await _take_snapshot(npc_name)
            return f"已点击\n\n页面快照:\n{snapshot_text}"

        return _run_async(_do())

    except Exception as e:
        return f"点击失败: {str(e)}"


def tool_browser_type(input_obj: dict, npc, context) -> str:
    """在输入框中输入文字"""
    ref = input_obj.get("ref")
    selector = input_obj.get("selector", "")
    text = input_obj.get("text", "")
    submit = input_obj.get("submit", False)
    npc_name = npc.name if hasattr(npc, 'name') else str(npc)

    if not text:
        return "错误: 请提供 text 参数"

    try:
        async def _do():
            page = await _get_page(npc_name)

            if ref is not None:
                ref_map = _ref_maps.get(npc_name, {})
                node = browser_l2.find_node_by_ref(ref_map, int(ref))
                if not node:
                    return f"错误: ref={ref} 不存在"
                sel = browser_l2.build_selector_from_node(node)
                if not sel:
                    return f"错误: ref={ref} 无法构建选择器"
            elif selector:
                sel = selector
            else:
                return "错误: 请提供 ref 或 selector"

            locator = page.locator(sel).first
            await locator.fill(text, timeout=10000)

            if submit:
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("domcontentloaded", timeout=10000)

            snapshot_text, _ = await _take_snapshot(npc_name)
            return f"已输入: {text}" + (" (已提交)" if submit else "") + f"\n\n页面快照:\n{snapshot_text}"

        return _run_async(_do())

    except Exception as e:
        return f"输入失败: {str(e)}"


def tool_browser_screenshot(input_obj: dict, npc, context) -> str:
    """截取当前页面截图"""
    filename = input_obj.get("filename", "screenshot.png")
    npc_name = npc.name if hasattr(npc, 'name') else str(npc)

    # 确保文件名安全
    filename = Path(filename).name  # 去掉路径部分
    if not filename.endswith(".png"):
        filename += ".png"

    from tools.browser import SCREENSHOT_DIR
    save_path = SCREENSHOT_DIR / filename

    try:
        async def _do():
            page = await _get_page(npc_name)
            await page.screenshot(path=str(save_path))
            return str(save_path)

        result_path = _run_async(_do())
        print(f"📸 [{npc_name}] 截图: {result_path}")
        return f"截图已保存: {filename}"

    except Exception as e:
        return f"截图失败: {str(e)}"


def tool_browser_snapshot(input_obj: dict, npc, context) -> str:
    """获取当前页面的可访问性快照"""
    npc_name = npc.name if hasattr(npc, 'name') else str(npc)

    try:
        async def _do():
            page = await _get_page(npc_name)
            url = page.url
            title = await page.title()
            snapshot_text, _ = await _take_snapshot(npc_name)
            return url, title, snapshot_text

        url, title, snapshot = _run_async(_do())
        return f"URL: {url}\n标题: {title}\n\n{snapshot}"

    except Exception as e:
        return f"获取快照失败: {str(e)}"


def tool_browser_close(input_obj: dict, npc, context) -> str:
    """关闭浏览器页面"""
    npc_name = npc.name if hasattr(npc, 'name') else str(npc)

    try:
        _run_async(_close_page(npc_name))
        print(f"🌐 [{npc_name}] 浏览器页面已关闭")
        return "浏览器页面已关闭"
    except Exception as e:
        return f"关闭失败: {str(e)}"


# ========== 生命周期 ==========

def shutdown():
    """关闭所有浏览器资源"""
    global _browser, _playwright

    async def _do_shutdown():
        global _browser, _playwright
        # 关闭所有页面
        for name in list(_pages.keys()):
            await _close_page(name)
        # 关闭浏览器
        if _browser:
            await _browser.close()
            _browser = None
        if _playwright:
            await _playwright.stop()
            _playwright = None

    if _loop and _loop.is_running():
        try:
            future = asyncio.run_coroutine_threadsafe(_do_shutdown(), _loop)
            future.result(timeout=10)
        except Exception:
            pass

    print("[Browser] 浏览器资源已清理")
