# -*- coding: utf-8 -*-
"""
首頁路由
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..services.auth import get_current_user, get_line_login_url

router = APIRouter(tags=["首頁"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: Session = Depends(get_db),
):
    """首頁 - 根據權限導向"""
    user = get_current_user(request, db)
    
    if not user:
        # 未登入，顯示登入頁
        return templates.TemplateResponse("login.html", {
            "request": request,
            "line_login_url": get_line_login_url(),
        })
    
    # 已登入，顯示功能入口頁
    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user,
    })


@router.get("/dashboard")
async def dashboard_redirect(
    request: Request,
    db: Session = Depends(get_db),
):
    """根據權限自動導向適當的儀表板"""
    user = get_current_user(request, db)
    
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # 根據權限優先級導向
    if user.is_admin:
        return RedirectResponse(url="/admin", status_code=302)
    elif user.is_dispatcher:
        return RedirectResponse(url="/dispatcher", status_code=302)
    elif user.is_coordinator:
        return RedirectResponse(url="/coordinator", status_code=302)
    else:
        # 待審核狀態
        return templates.TemplateResponse("pending.html", {
            "request": request,
            "user": user,
        })
