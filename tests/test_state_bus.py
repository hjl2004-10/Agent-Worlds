"""
core/state_bus.py 单元测试 — 命令队列与事件分发
"""

import pytest
from unittest.mock import MagicMock


class TestStateBus:
    """state_bus 命令队列"""

    def setup_method(self):
        """每个测试前重置 state_bus 状态"""
        from core import state_bus
        # 清空队列
        while not state_bus._queue.empty():
            state_bus._queue.get_nowait()
        state_bus._dispatcher = None

    def test_submit_without_wait(self):
        from core import state_bus
        result = state_bus.submit("test_cmd", {"key": "value"})
        assert result["status"] == "queued"

    def test_process_with_dispatcher(self):
        from core import state_bus
        handler = MagicMock(return_value={"status": "ok"})
        state_bus.register_dispatcher(handler)
        state_bus.submit("do_thing", {"data": 1})
        count = state_bus.process_all()
        assert count == 1
        handler.assert_called_once_with("do_thing", {"data": 1})

    def test_process_without_dispatcher(self):
        from core import state_bus
        state_bus.submit("ignored", {})
        count = state_bus.process_all()
        assert count == 0

    def test_process_empty_queue(self):
        from core import state_bus
        handler = MagicMock()
        state_bus.register_dispatcher(handler)
        count = state_bus.process_all()
        assert count == 0
        handler.assert_not_called()

    def test_multiple_commands(self):
        from core import state_bus
        handler = MagicMock(return_value={"status": "ok"})
        state_bus.register_dispatcher(handler)
        state_bus.submit("cmd1", {"a": 1})
        state_bus.submit("cmd2", {"b": 2})
        state_bus.submit("cmd3", {"c": 3})
        count = state_bus.process_all()
        assert count == 3

    def test_process_limit(self):
        from core import state_bus
        handler = MagicMock(return_value={"status": "ok"})
        state_bus.register_dispatcher(handler)
        state_bus.submit("cmd1", {})
        state_bus.submit("cmd2", {})
        state_bus.submit("cmd3", {})
        count = state_bus.process_all(limit=2)
        assert count == 2
        # 第三个还在队列里
        count2 = state_bus.process_all()
        assert count2 == 1

    def test_submit_with_wait(self):
        """同步等待模式"""
        import threading
        from core import state_bus

        def delayed_process():
            import time
            time.sleep(0.05)
            state_bus.process_all()

        handler = MagicMock(return_value={"status": "ok", "msg": "done"})
        state_bus.register_dispatcher(handler)

        t = threading.Thread(target=delayed_process)
        t.start()
        result = state_bus.submit("wait_cmd", {"x": 1}, wait=True, timeout=5.0)
        t.join()

        assert result["status"] == "ok"
        assert result["msg"] == "done"

    def test_dispatcher_exception_handled(self):
        from core import state_bus

        def bad_handler(cmd_type, payload):
            raise RuntimeError("boom")

        state_bus.register_dispatcher(bad_handler)
        state_bus.submit("fail", {})
        count = state_bus.process_all()  # 不应抛出异常
        assert count == 1
