"""
io / io_l1 单元测试 — HJL 文件读写
"""

import json
import os
import tempfile
import pytest


class TestLoadJsonFile:
    """JSON 文件加载"""

    def test_load_valid_json(self, tmp_path):
        from tools.io_l1 import load_json_file
        f = tmp_path / "test.hjl"
        f.write_text('{"header": {"name": "Alice"}}', encoding='utf-8')
        result = load_json_file(str(f))
        assert result == {"header": {"name": "Alice"}}

    def test_load_nonexistent_file(self):
        from tools.io_l1 import load_json_file
        result = load_json_file("/nonexistent/path/test.hjl")
        assert result is None

    def test_load_invalid_json(self, tmp_path):
        from tools.io_l1 import load_json_file
        f = tmp_path / "bad.hjl"
        f.write_text("{invalid json}", encoding='utf-8')
        result = load_json_file(str(f))
        assert result is None

    def test_load_unicode(self, tmp_path):
        from tools.io_l1 import load_json_file
        f = tmp_path / "cn.hjl"
        data = {"header": {"name": "拾荒者阿灰"}}
        f.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        result = load_json_file(str(f))
        assert result["header"]["name"] == "拾荒者阿灰"

    def test_load_empty_file(self, tmp_path):
        from tools.io_l1 import load_json_file
        f = tmp_path / "empty.hjl"
        f.write_text("", encoding='utf-8')
        result = load_json_file(str(f))
        assert result is None  # JSONDecodeError


class TestSaveJsonFile:
    """JSON 文件保存"""

    def test_save_and_reload(self, tmp_path):
        from tools.io_l1 import load_json_file, save_json_file
        f = str(tmp_path / "out.hjl")
        data = {"header": {"name": "Bob"}, "attributes": {"description": "测试"}}
        assert save_json_file(f, data) is True
        loaded = load_json_file(f)
        assert loaded == data

    def test_save_unicode_preserved(self, tmp_path):
        from tools.io_l1 import save_json_file
        f = str(tmp_path / "cn.hjl")
        data = {"name": "哨兵林七"}
        save_json_file(f, data)
        with open(f, 'r', encoding='utf-8') as fh:
            raw = fh.read()
        assert "哨兵林七" in raw  # ensure_ascii=False 保留中文

    def test_save_creates_readable_json(self, tmp_path):
        from tools.io_l1 import save_json_file
        f = str(tmp_path / "formatted.hjl")
        save_json_file(f, {"a": 1})
        with open(f, 'r') as fh:
            raw = fh.read()
        assert "\n" in raw  # indent=2 产生多行


class TestEnsureDirectory:
    """目录创建"""

    def test_create_new_dir(self, tmp_path):
        from tools.io_l1 import ensure_directory
        new_dir = str(tmp_path / "newdir" / "subdir")
        result = ensure_directory(new_dir)
        assert result is True
        assert os.path.isdir(new_dir)

    def test_existing_dir(self, tmp_path):
        from tools.io_l1 import ensure_directory
        result = ensure_directory(str(tmp_path))
        assert result is False  # 已存在


class TestIoReadWriteHjl:
    """io.py 高层接口 (路径解析)"""

    def test_full_path_roundtrip(self, tmp_path):
        from tools import io
        f = str(tmp_path / "test.hjl")
        data = {"header": {"uuid": "test_001", "name": "Test"}}
        io.write_hjl(f, data)
        loaded = io.read_hjl(f)
        assert loaded == data

    def test_write_creates_parent_dir(self, tmp_path):
        from tools import io
        f = str(tmp_path / "sub" / "deep" / "test.hjl")
        io.write_hjl(f, {"test": True})
        assert os.path.exists(f)
