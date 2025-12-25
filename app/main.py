# -*- coding: utf-8 -*-
"""
高檢病人動態系統 - FastAPI 入口
Phase 7: 包含 PDF 報表匯出、QR Code 自助報到
"""

import os
from datetime import timedelta
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
from .routers import equipment, reports
from .routers import checkin  # 新增：QR Code 報到


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


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    
    if request.url.path.startswith("/checkin/") and exc.status_code == 404:
        templates = Jinja2Templates(directory="app/templates")
        return templates.TemplateResponse("error.html", {
            "request": request, "error_code": 404,
            "error_title": "找不到頁面", "error_message": "報到連結無效或已過期",
        }, status_code=404)
    
    if exc.status_code == 401:
        return RedirectResponse(url=f"/auth/login?next={request.url.path}", status_code=302)
    
    if exc.status_code == 403:
        return RedirectResponse(url=f"/auth/login?msg=no_permission&next={request.url.path}", status_code=302)
    
    templates = Jinja2Templates(directory="app/templates")
    titles = {404: "找不到頁面", 500: "系統錯誤"}
    msgs = {404: "您要找的頁面不存在或已被移除", 500: "系統發生錯誤，請稍後再試"}
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_code": exc.status_code,
        "error_title": titles.get(exc.status_code, "發生錯誤"),
        "error_message": msgs.get(exc.status_code, str(exc.detail) if exc.detail else "請稍後再試"),
    }, status_code=exc.status_code)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ 未預期錯誤：{exc}")
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse("error.html", {
        "request": request, "error_code": 500,
        "error_title": "系統錯誤", "error_message": "系統發生未預期的錯誤，請稍後再試",
    }, status_code=500)


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["timedelta"] = timedelta

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}

app.include_router(home.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dispatcher.router)
app.include_router(coordinator.router)
app.include_router(equipment.router)
app.include_router(reports.router)
app.include_router(checkin.router)
