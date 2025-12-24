# -*- coding: utf-8 -*-
"""
調度員路由 - 病人總覽與指派
"""

from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole
from ..models.patient import Patient
from ..models.exam import Exam
from ..models.tracking import PatientTracking, CoordinatorAssignment
from ..services.auth import get_current_user
from ..services import tracking as tracking_service

router = APIRouter(prefix="/dispatcher", tags=["調度員"])
templates = Jinja2Templates(directory="app/templates")


def require_dispatcher(request: Request, db: Session = Depends(get_db)) -> User:
    """要求調度員或管理員權限"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if user.role not in [UserRole.DISPATCHER.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="需要調度員權限")
    return user


@router.get("", response_class=HTMLResponse)
async def dispatcher_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """調度員主控台"""
    today = date.today()
    
    # 取得今日病人
    patients = tracking_service.get_today_patients(db, today)
    
    # 取得各病人的追蹤資訊
    patient_list = []
    for p in patients:
        info = tracking_service.get_patient_with_tracking(db, p.id, today)
        patient_list.append(info)
    
    # 取得各站摘要
    station_summary = tracking_service.get_station_summary(db, today)
    
    # 取得所有個管師
    coordinators = db.query(User).filter(
        User.role == UserRole.COORDINATOR.value,
        User.is_active == True
    ).all()
    
    # 取得所有檢查項目
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    # 統計
    total_patients = len(patients)
    completed = sum(1 for p in patient_list if p["tracking"] and p["tracking"].current_status == "completed")
    in_progress = sum(1 for p in patient_list if p["tracking"] and p["tracking"].current_status in ["waiting", "in_exam", "moving"])
    not_started = total_patients - completed - in_progress
    
    return templates.TemplateResponse("dispatcher/dashboard.html", {
        "request": request,
        "user": current_user,
        "today": today,
        "patient_list": patient_list,
        "station_summary": station_summary,
        "coordinators": coordinators,
        "exams": exams,
        "stats": {
            "total": total_patients,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
        }
    })


@router.post("/assign-coordinator")
async def assign_coordinator(
    request: Request,
    patient_id: int = Form(...),
    coordinator_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """指派個管師給病人"""
    tracking_service.assign_coordinator(
        db=db,
        patient_id=patient_id,
        coordinator_id=coordinator_id,
        assigned_by=current_user.id,
    )
    
    return RedirectResponse(url="/dispatcher", status_code=302)


@router.post("/assign-station")
async def assign_station(
    request: Request,
    patient_id: int = Form(...),
    exam_code: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """指派病人下一站"""
    tracking_service.assign_next_station(
        db=db,
        patient_id=patient_id,
        next_exam_code=exam_code,
        assigned_by=current_user.id,
    )
    
    return RedirectResponse(url="/dispatcher", status_code=302)


# ======================
# HTMX 部分更新 API
# ======================

@router.get("/api/patients", response_class=HTMLResponse)
async def get_patients_partial(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """病人列表（HTMX 部分更新）"""
    today = date.today()
    patients = tracking_service.get_today_patients(db, today)
    
    patient_list = []
    for p in patients:
        info = tracking_service.get_patient_with_tracking(db, p.id, today)
        patient_list.append(info)
    
    coordinators = db.query(User).filter(
        User.role == UserRole.COORDINATOR.value,
        User.is_active == True
    ).all()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    return templates.TemplateResponse("partials/patient_table.html", {
        "request": request,
        "patient_list": patient_list,
        "coordinators": coordinators,
        "exams": exams,
    })


@router.get("/api/stations", response_class=HTMLResponse)
async def get_stations_partial(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """檢查站狀態（HTMX 部分更新）"""
    today = date.today()
    station_summary = tracking_service.get_station_summary(db, today)
    
    return templates.TemplateResponse("partials/station_cards.html", {
        "request": request,
        "station_summary": station_summary,
    })
