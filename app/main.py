# -*- coding: utf-8 -*-
"""
高檢病人動態系統 - FastAPI 入口
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

from .config import settings
from .database import init_db
from .routers import auth, home, admin
from .routers import dispatcher, coordinator
from .routers import equipment


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期"""
    print(f"🚀 {settings.APP_NAME} {settings.APP_VERSION} 啟動中...")
    init_db()
    yield
    print("👋 應用程式關閉")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


# =====================
# 自定義異常處理 - 未登入自動跳轉
# =====================

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    處理 HTTP 異常：
    - 401 未授權 → 跳轉登入頁
    - 403 無權限 → 跳轉登入頁
    - 其他 → 顯示錯誤頁
    """
    # API 請求返回 JSON
    if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # 401 未授權 - 跳轉登入（session 過期或未登入）
    if exc.status_code == 401:
        next_url = request.url.path
        return RedirectResponse(
            url=f"/auth/login?next={next_url}",
            status_code=302
        )
    
    # 403 無權限 - 跳轉登入頁並提示
    if exc.status_code == 403:
        next_url = request.url.path
        return RedirectResponse(
            url=f"/auth/login?msg=no_permission&next={next_url}",
            status_code=302
        )
    
    # 404 找不到頁面 - 顯示友好錯誤頁
    if exc.status_code == 404:
        templates = Jinja2Templates(directory="app/templates")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_title": "找不到頁面",
                "error_message": "您要找的頁面不存在或已被移除",
            },
            status_code=404
        )
    
    # 500 伺服器錯誤
    if exc.status_code == 500:
        templates = Jinja2Templates(directory="app/templates")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 500,
                "error_title": "系統錯誤",
                "error_message": "系統發生錯誤，請稍後再試",
            },
            status_code=500
        )
    
    # 其他錯誤
    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": exc.status_code,
            "error_title": "發生錯誤",
            "error_message": str(exc.detail) if exc.detail else "請稍後再試",
        },
        status_code=exc.status_code
    )


# =====================
# 全局異常處理（捕捉未預期錯誤）
# =====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """處理所有未預期的異常"""
    # API 請求返回 JSON
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # 顯示錯誤頁面
    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 500,
            "error_title": "系統錯誤",
            "error_message": "系統發生未預期的錯誤，請稍後再試",
        },
        status_code=500
    )


# =====================
# 靜態檔案
# =====================

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    print(f"⚠️ Static directory not found: {static_dir}")


# =====================
# 註冊路由
# =====================

app.include_router(home.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dispatcher.router)
app.include_router(coordinator.router)
app.include_router(equipment.router)
