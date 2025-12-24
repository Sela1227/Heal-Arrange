# -*- coding: utf-8 -*-
"""
首頁路由 - 依角色跳轉
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole
from ..services.auth import get_current_user

router = APIRouter(tags=["首頁"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: Session = Depends(get_db),
):
    """首頁 - 依角色跳轉"""
    user = get_current_user(request, db)
    
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # 依角色跳轉
    if user.role == UserRole.ADMIN.value:
        return RedirectResponse(url="/admin", status_code=302)
    
    elif user.role == UserRole.DISPATCHER.value:
        return RedirectResponse(url="/dispatcher", status_code=302)
    
    elif user.role == UserRole.COORDINATOR.value:
        return RedirectResponse(url="/coordinator", status_code=302)
    
    else:  # pending
        return templates.TemplateResponse("pending.html", {
            "request": request,
            "user": user,
        })


@router.get("/health")
async def health_check():
    """健康檢查（Railway 用）"""
    return {"status": "ok"}
