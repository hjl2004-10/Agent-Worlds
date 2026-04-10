"""
HJL Schema 校验单元测试
"""

import pytest


class TestGetNested:
    """嵌套字典取值"""

    def test_simple_key(self):
        from tools.loader_l1 import _get_nested
        assert _get_nested({"a": 1}, "a") == 1

    def test_nested_key(self):
        from tools.loader_l1 import _get_nested
        assert _get_nested({"header": {"name": "Alice"}}, "header.name") == "Alice"

    def test_missing_key(self):
        from tools.loader_l1 import _get_nested
        assert _get_nested({"header": {}}, "header.name") is None

    def test_missing_parent(self):
        from tools.loader_l1 import _get_nested
        assert _get_nested({}, "header.name") is None

    def test_non_dict_parent(self):
        from tools.loader_l1 import _get_nested
        assert _get_nested({"header": "not_a_dict"}, "header.name") is None


class TestSetNested:
    """嵌套字典设值"""

    def test_simple_key(self):
        from tools.loader_l1 import _set_nested
        d = {}
        _set_nested(d, "a", 1)
        assert d == {"a": 1}

    def test_nested_key(self):
        from tools.loader_l1 import _set_nested
        d = {}
        _set_nested(d, "header.name", "Alice")
        assert d == {"header": {"name": "Alice"}}

    def test_existing_parent(self):
        from tools.loader_l1 import _set_nested
        d = {"header": {"uuid": "alice"}}
        _set_nested(d, "header.name", "Alice")
        assert d["header"]["uuid"] == "alice"
        assert d["header"]["name"] == "Alice"

    def test_deep_nesting(self):
        from tools.loader_l1 import _set_nested
        d = {}
        _set_nested(d, "a.b.c", 42)
        assert d["a"]["b"]["c"] == 42


class TestValidateIndividualHjl:
    """INDIVIDUAL 类型 HJL 校验"""

    def test_valid_full_data(self):
        from tools.loader_l1 import validate_individual_hjl
        data = {
            "header": {"uuid": "alice", "name": "Alice"},
            "position": {"modern:office": {"x": 100, "y": 200}},
            "sprite": {"id": "Adam"},
            "attributes": {
                "description": "测试人设",
                "prompt": [],
                "base_initiative": 3,
                "skills": [],
                "tools": [],
                "groups": [],
                "enabled": True,
            },
            "memory": {"history": []},
        }
        warnings = validate_individual_hjl(data, "alice.hjl")
        assert len(warnings) == 0

    def test_missing_name_warns(self):
        from tools.loader_l1 import validate_individual_hjl
        data = {"header": {"uuid": "alice"}}
        warnings = validate_individual_hjl(data, "alice.hjl")
        assert any("header.name" in w for w in warnings)

    def test_fills_missing_defaults(self):
        from tools.loader_l1 import validate_individual_hjl
        data = {"header": {"name": "Alice"}}
        warnings = validate_individual_hjl(data, "alice.hjl")
        # 应该自动填入默认值
        assert data.get("sprite", {}).get("id") == "Adam"
        assert data.get("attributes", {}).get("description") == ""
        assert data.get("memory", {}).get("history") == []
        assert data.get("attributes", {}).get("enabled") is True
        # uuid 应自动生成
        assert data["header"]["uuid"] == "alice"
        # 应该有填补警告
        assert len(warnings) > 0

    def test_non_dict_data(self):
        from tools.loader_l1 import validate_individual_hjl
        warnings = validate_individual_hjl("not a dict", "bad.hjl")
        assert any("不是 dict" in w for w in warnings)

    def test_wrong_type_warns(self):
        from tools.loader_l1 import validate_individual_hjl
        data = {"header": {"name": 123}}  # name 应为 str
        warnings = validate_individual_hjl(data, "bad.hjl")
        assert any("类型错误" in w for w in warnings)

    def test_minimal_data_gets_filled(self):
        """最小数据 (只有 header.name) 经校验后能正常加载"""
        from tools.loader_l1 import validate_individual_hjl
        data = {"header": {"name": "Minimal"}}
        validate_individual_hjl(data, "minimal.hjl")
        # 所有必要结构都应存在
        assert isinstance(data.get("attributes"), dict)
        assert isinstance(data.get("memory"), dict)
        assert isinstance(data.get("position"), dict)
        assert isinstance(data.get("sprite"), dict)
