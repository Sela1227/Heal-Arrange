# -*- coding: utf-8 -*-
"""
設備路由 - 故障回報與管理
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole
from ..services.auth import get_current_user
from ..services import equipment as equipment_service

router = APIRouter(prefix="/equipment", tags=["設備"])
templates = Jinja2Templates(directory="app/templates")


def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    """要求登入"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if user.role == "pending":
        raise HTTPException(status_code=403, detail="帳號尚未授權")
    return user


@router.post("/report-failure")
async def report_failure(
    request: Request,
    equipment_id: int = Form(...),
    description: str = Form(None),
    redirect_url: str = Form("/dispatcher"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """回報設備故障"""
    equipment_service.report_failure(
        db=db,
        equipment_id=equipment_id,
        reported_by=current_user.id,
        description=description,
    )
    
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/report-repair")
async def report_repair(
    request: Request,
    equipment_id: int = Form(...),
    description: str = Form(None),
    redirect_url: str = Form("/admin/equipment"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """回報設備修復（僅管理員/調度員）"""
    if current_user.role not in [UserRole.ADMIN.value, UserRole.DISPATCHER.value]:
        raise HTTPException(status_code=403, detail="權限不足")
    
    equipment_service.report_repair(
        db=db,
        equipment_id=equipment_id,
        reported_by=current_user.id,
        description=description,
    )
    
    return RedirectResponse(url=redirect_url, status_code=302)


# ======================
# HTMX API - 設備狀態
# ======================

@router.get("/api/broken", response_class=HTMLResponse)
async def get_broken_equipment(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """取得故障設備列表（HTMX）"""
    broken = equipment_service.get_broken_equipment(db)
    
    return templates.TemplateResponse("partials/broken_equipment.html", {
        "request": request,
        "broken_equipment": broken,
    })
