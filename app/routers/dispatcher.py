# -*- coding: utf-8 -*-
"""
調度員路由 - Phase 7 更新：加入衝突提醒與排程建議
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
from ..models.equipment import Equipment, EquipmentLog, EquipmentStatus
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
        
        # Phase 7: 加入衝突檢測
        from ..services.scheduler import detect_schedule_conflicts, suggest_next_station
        info['conflicts'] = detect_schedule_conflicts(db, p.id, today)
        info['suggestions'] = suggest_next_station(db, p.id, today)[:3]  # 前 3 個建議
        
        patient_list.append(info)
    
    # 取得各站摘要
    station_summary = tracking_service.get_station_summary(db, today)
    
    # 取得所有專員
    coordinators = db.query(User).filter(
        User.role == UserRole.COORDINATOR.value,
        User.is_active == True
    ).all()
    
    # 取得所有檢查項目
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    exams_dict = {e.exam_code: e for e in exams}
    
    # 取得故障設備
    broken_equipment = db.query(Equipment).filter(
        Equipment.status == EquipmentStatus.BROKEN.value,
        Equipment.is_active == True
    ).all()
    broken_locations = {eq.location for eq in broken_equipment}
    
    # 取得所有設備（用於回報）
    all_equipment = db.query(Equipment).filter(Equipment.is_active == True).all()
    
    # 統計
    total_patients = len(patients)
    completed = sum(1 for p in patient_list if p["tracking"] and p["tracking"].current_status == "completed")
    in_progress = sum(1 for p in patient_list if p["tracking"] and p["tracking"].current_status in ["waiting", "in_exam", "moving"])
    not_started = total_patients - completed - in_progress
    
    # Phase 7: 取得容量狀態
    from ..services.scheduler import get_capacity_status, optimize_daily_schedule
    capacity_status = get_capacity_status(db, today)
    optimization = optimize_daily_schedule(db, today)
    
    return templates.TemplateResponse("dispatcher/dashboard.html", {
        "request": request,
        "user": current_user,
        "today": today,
        "patient_list": patient_list,
        "station_summary": station_summary,
        "coordinators": coordinators,
        "exams": exams,
        "exams_dict": exams_dict,
        "broken_equipment": broken_equipment,
        "broken_locations": broken_locations,
        "all_equipment": all_equipment,
        "capacity_status": {c['exam_code']: c for c in capacity_status},
        "optimization": optimization,
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
    """指派專員給病人"""
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
    # Phase 7: 檢查容量
    from ..services.scheduler import get_capacity_status
    
    today = date.today()
    capacity_status = get_capacity_status(db, today)
    station_status = next((c for c in capacity_status if c['exam_code'] == exam_code), None)
    
    # 如果已滿，仍然允許指派但會警告（在前端處理）
    
    tracking_service.assign_next_station(
        db=db,
        patient_id=patient_id,
        next_exam_code=exam_code,
        assigned_by=current_user.id,
    )
    
    return RedirectResponse(url="/dispatcher", status_code=302)


@router.post("/report-equipment-failure")
async def report_equipment_failure(
    request: Request,
    equipment_id: int = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """回報設備故障"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if equipment:
        old_status = equipment.status
        equipment.status = EquipmentStatus.BROKEN.value
        
        log = EquipmentLog(
            equipment_id=equipment_id,
            action="report_failure",
            old_status=old_status,
            new_status=EquipmentStatus.BROKEN.value,
            description=description or "調度員回報故障",
            operator_id=current_user.id,
        )
        db.add(log)
        db.commit()
    
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
        
        # Phase 7: 加入衝突檢測
        from ..services.scheduler import detect_schedule_conflicts, suggest_next_station
        info['conflicts'] = detect_schedule_conflicts(db, p.id, today)
        info['suggestions'] = suggest_next_station(db, p.id, today)[:3]
        
        patient_list.append(info)
    
    coordinators = db.query(User).filter(
        User.role == UserRole.COORDINATOR.value,
        User.is_active == True
    ).all()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    # 取得容量狀態
    from ..services.scheduler import get_capacity_status
    capacity_status = get_capacity_status(db, today)
    
    return templates.TemplateResponse("partials/patient_table.html", {
        "request": request,
        "patient_list": patient_list,
        "coordinators": coordinators,
        "exams": exams,
        "capacity_status": {c['exam_code']: c for c in capacity_status},
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
    
    # 取得故障設備
    broken_equipment = db.query(Equipment).filter(
        Equipment.status == EquipmentStatus.BROKEN.value,
        Equipment.is_active == True
    ).all()
    broken_locations = {eq.location for eq in broken_equipment}
    
    return templates.TemplateResponse("partials/station_cards.html", {
        "request": request,
        "station_summary": station_summary,
        "broken_locations": broken_locations,
    })


@router.get("/api/broken-equipment", response_class=HTMLResponse)
async def get_broken_equipment_partial(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """故障設備列表（HTMX 部分更新）"""
    broken_equipment = db.query(Equipment).filter(
        Equipment.status == EquipmentStatus.BROKEN.value,
        Equipment.is_active == True
    ).all()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    exams_dict = {e.exam_code: e for e in exams}
    
    return templates.TemplateResponse("partials/broken_alert.html", {
        "request": request,
        "broken_equipment": broken_equipment,
        "exams_dict": exams_dict,
    })


# ======================
# Phase 7: 排程建議 API
# ======================

@router.get("/api/suggestions/{patient_id}", response_class=HTMLResponse)
async def get_patient_suggestions(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """取得病人的下一站建議"""
    from ..services.scheduler import suggest_next_station, detect_schedule_conflicts
    
    today = date.today()
    suggestions = suggest_next_station(db, patient_id, today)
    conflicts = detect_schedule_conflicts(db, patient_id, today)
    
    html_parts = []
    
    # 衝突警示
    if conflicts:
        html_parts.append('<div class="bg-yellow-50 border border-yellow-200 rounded p-2 mb-2 text-xs">')
        for c in conflicts:
            icon = '🔴' if c['severity'] == 'error' else '🟡'
            html_parts.append(f'<div>{icon} {c["message"]}</div>')
        html_parts.append('</div>')
    
    # 建議列表
    if suggestions:
        html_parts.append('<div class="space-y-1">')
        for i, s in enumerate(suggestions[:5]):
            score_color = 'text-green-600' if s['score'] >= 80 else 'text-yellow-600' if s['score'] >= 50 else 'text-red-600'
            html_parts.append(f'''
            <div class="flex justify-between items-center p-1 bg-gray-50 rounded text-xs">
                <span>{s["exam_code"]} - {s["exam_name"]}</span>
                <span class="{score_color} font-bold">{s["score"]}分</span>
            </div>
            ''')
        html_parts.append('</div>')
    else:
        html_parts.append('<div class="text-gray-400 text-xs">已完成所有檢查</div>')
    
    return HTMLResponse(content=''.join(html_parts))
