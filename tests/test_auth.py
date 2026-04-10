"""
api/auth.py 单元测试 — Token 认证与 CORS 配置
"""

import json
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app(api_token="", cors_origins=None):
    """创建带认证配置的测试 app"""
    app = FastAPI()

    config = {"api_token": api_token, "cors_origins": cors_origins or ["*"]}

    with patch("api.auth._load_config", return_value=config):
        from api.auth import setup_auth
        setup_auth(app)

    @app.get("/api/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/public")
    async def public_endpoint():
        return {"status": "ok"}

    return app


class TestNoAuth:
    """无 token 时所有请求通过"""

    def test_api_accessible(self):
        client = TestClient(_make_app(api_token=""))
        resp = client.get("/api/test")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_public_accessible(self):
        client = TestClient(_make_app(api_token=""))
        resp = client.get("/public")
        assert resp.status_code == 200


class TestWithAuth:
    """有 token 时需要 Bearer 认证"""

    def test_api_without_token_rejected(self):
        client = TestClient(_make_app(api_token="secret123"))
        resp = client.get("/api/test")
        assert resp.status_code == 401
        assert "Unauthorized" in resp.json()["message"]

    def test_api_with_wrong_token_rejected(self):
        client = TestClient(_make_app(api_token="secret123"))
        resp = client.get("/api/test", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 401

    def test_api_with_correct_token_passes(self):
        client = TestClient(_make_app(api_token="secret123"))
        resp = client.get("/api/test", headers={"Authorization": "Bearer secret123"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_public_path_no_auth_needed(self):
        client = TestClient(_make_app(api_token="secret123"))
        resp = client.get("/public")
        assert resp.status_code == 200
