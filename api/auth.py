# ============================================
# api/auth.py - API 认证中间件
# 职责: Token 认证 + CORS 配置加载
# ============================================

import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "auth.json"

# 不需要认证的路径前缀
_PUBLIC_PREFIXES = ("/", "/assets/", "/sprites/", "/static/")


def _load_config() -> dict:
    """加载认证配置"""
    if not _CONFIG_PATH.exists():
        return {"api_token": "", "cors_origins": ["*"]}
    try:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"api_token": "", "cors_origins": ["*"]}


def setup_auth(app: FastAPI):
    """配置 CORS 和 Token 认证中间件

    认证逻辑:
    - 如果 config/auth.json 中 api_token 为空字符串，则不启用认证（开发模式）
    - 如果 api_token 有值，所有 /api/* 请求必须携带 Authorization: Bearer <token>
    """
    config = _load_config()
    api_token = config.get("api_token", "")
    cors_origins = config.get("cors_origins", ["*"])

    # CORS 配置
    # 如果没有配置 token，保持宽松 CORS（开发模式）
    # 如果配置了 token，使用白名单 CORS
    if not api_token:
        cors_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Token 认证中间件（仅在 api_token 非空时启用）
    if api_token:
        @app.middleware("http")
        async def token_auth_middleware(request: Request, call_next):
            path = request.url.path

            # 非 API 路径跳过认证（静态文件、SPA 等）
            if not path.startswith("/api/"):
                return await call_next(request)

            # 检查 Authorization 头
            auth_header = request.headers.get("Authorization", "")
            if auth_header == f"Bearer {api_token}":
                return await call_next(request)

            return JSONResponse(
                status_code=401,
                content={"status": "error", "message": "Unauthorized: invalid or missing API token"}
            )

        print(f"[Auth] API Token 认证已启用 (CORS: {cors_origins})")
    else:
        print("[Auth] 开发模式: 无认证 (设置 config/auth.json 中 api_token 启用)")
