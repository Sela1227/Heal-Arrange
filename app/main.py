# -*- coding: utf-8 -*-
"""
高檢病人動態系統 - FastAPI 入口
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from .config import settings
from .database import init_db
from .routers import auth, home, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期"""
    # 啟動時
    print(f"🚀 {settings.APP_NAME} {settings.APP_VERSION} 啟動中...")
    init_db()
    yield
    # 關閉時
    print("👋 應用程式關閉")


# 建立應用程式
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# 靜態檔案
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 註冊路由
app.include_router(home.router)
app.include_router(auth.router)
app.include_router(admin.router)

# TODO: Phase 2 加入
# from .routers import dispatcher, coordinator
# app.include_router(dispatcher.router)
# app.include_router(coordinator.router)
