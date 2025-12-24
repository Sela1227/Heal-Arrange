# -*- coding: utf-8 -*-
"""
個管師路由 - 我的病人與狀態回報
"""

from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole
from ..models.exam import Exam
from ..models.tracking import TrackingStatus
from ..services.auth import get_current_user
from ..services import tracking as tracking_service

router = APIRouter(prefix="/coordinator", tags=["個管師"])
templates = Jinja2Templates(directory="app/templates")


def require_coordinator(request: Request, db: Session = Depends(get_db)) -> User:
    """要求個管師或管理員權限"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if user.role not in [UserRole.COORDINATOR.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="需要個管師權限")
    return user


@router.get("", response_class=HTMLResponse)
async def coordinator_my_patient(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """個管師 - 我的病人頁面"""
    today = date.today()
    
    # 取得我負責的病人
    patient_info = tracking_service.get_coordinator_patient(db, current_user.id, today)
    
    # 取得所有檢查項目（用於顯示）
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    exams_dict = {e.exam_code: e for e in exams}
    
    # 取得歷程
    history = []
    if patient_info and patient_info["patient"]:
        history = tracking_service.get_tracking_history(db, patient_info["patient"].id, today)
    
    return templates.TemplateResponse("coordinator/my_patient.html", {
        "request": request,
        "user": current_user,
        "today": today,
        "patient_info": patient_info,
        "exams_dict": exams_dict,
        "history": history,
        "statuses": [
            {"value": "waiting", "label": "等候中", "icon": "⏳"},
            {"value": "in_exam", "label": "檢查中", "icon": "🔬"},
            {"value": "moving", "label": "移動中", "icon": "🚶"},
            {"value": "completed", "label": "完成", "icon": "✅"},
        ],
    })


@router.post("/update-status")
async def update_status(
    request: Request,
    status: str = Form(...),
    location: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """更新病人狀態"""
    today = date.today()
    
    # 取得我負責的病人
    patient_info = tracking_service.get_coordinator_patient(db, current_user.id, today)
    
    if not patient_info or not patient_info["patient"]:
        raise HTTPException(status_code=400, detail="您目前沒有負責的病人")
    
    # 如果沒有指定位置，使用下一站或目前位置
    if not location:
        if patient_info["tracking"]:
            location = patient_info["tracking"].next_exam_code or patient_info["tracking"].current_location
        else:
            location = "LOBBY"
    
    tracking_service.update_patient_status(
        db=db,
        patient_id=patient_info["patient"].id,
        new_status=status,
        location=location,
        operator_id=current_user.id,
        notes=notes,
    )
    
    return RedirectResponse(url="/coordinator", status_code=302)


@router.post("/arrive")
async def report_arrive(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """回報到達"""
    today = date.today()
    patient_info = tracking_service.get_coordinator_patient(db, current_user.id, today)
    
    if not patient_info or not patient_info["patient"]:
        raise HTTPException(status_code=400, detail="您目前沒有負責的病人")
    
    # 到達下一站
    location = "LOBBY"
    if patient_info["tracking"] and patient_info["tracking"].next_exam_code:
        location = patient_info["tracking"].next_exam_code
    
    tracking_service.update_patient_status(
        db=db,
        patient_id=patient_info["patient"].id,
        new_status=TrackingStatus.WAITING.value,
        location=location,
        operator_id=current_user.id,
        notes="到達",
    )
    
    return RedirectResponse(url="/coordinator", status_code=302)


@router.post("/start")
async def report_start(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """回報開始檢查"""
    today = date.today()
    patient_info = tracking_service.get_coordinator_patient(db, current_user.id, today)
    
    if not patient_info or not patient_info["patient"]:
        raise HTTPException(status_code=400, detail="您目前沒有負責的病人")
    
    location = "LOBBY"
    if patient_info["tracking"]:
        location = patient_info["tracking"].current_location or patient_info["tracking"].next_exam_code or "LOBBY"
    
    tracking_service.update_patient_status(
        db=db,
        patient_id=patient_info["patient"].id,
        new_status=TrackingStatus.IN_EXAM.value,
        location=location,
        operator_id=current_user.id,
        notes="開始檢查",
    )
    
    return RedirectResponse(url="/coordinator", status_code=302)


@router.post("/complete")
async def report_complete(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """回報完成檢查"""
    today = date.today()
    patient_info = tracking_service.get_coordinator_patient(db, current_user.id, today)
    
    if not patient_info or not patient_info["patient"]:
        raise HTTPException(status_code=400, detail="您目前沒有負責的病人")
    
    location = "LOBBY"
    if patient_info["tracking"]:
        location = patient_info["tracking"].current_location or "LOBBY"
    
    tracking_service.update_patient_status(
        db=db,
        patient_id=patient_info["patient"].id,
        new_status=TrackingStatus.WAITING.value,  # 完成後等待下一站指派
        location=location,
        operator_id=current_user.id,
        notes="完成檢查，等待下一站",
    )
    
    return RedirectResponse(url="/coordinator", status_code=302)


# ======================
# HTMX API
# ======================

@router.get("/api/notifications", response_class=HTMLResponse)
async def get_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """通知更新（HTMX）"""
    today = date.today()
    patient_info = tracking_service.get_coordinator_patient(db, current_user.id, today)
    
    notifications = []
    
    if patient_info and patient_info["tracking"]:
        tracking = patient_info["tracking"]
        # 檢查是否有新指派的下一站
        if tracking.next_exam_code and tracking.current_location != tracking.next_exam_code:
            notifications.append({
                "type": "info",
                "message": f"請前往 {tracking.next_exam_code}",
            })
    
    return templates.TemplateResponse("partials/notifications.html", {
        "request": request,
        "notifications": notifications,
    })
