# -*- coding: utf-8 -*-
"""
高檢病人動態系統 - FastAPI 入口
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    print(f"⚠️ Static directory not found: {static_dir}")

# 註冊路由
app.include_router(home.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dispatcher.router)
app.include_router(coordinator.router)
app.include_router(equipment.router)
