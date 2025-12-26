# -*- coding: utf-8 -*-
"""
管理後台路由 - Phase 7 更新：加入排程建議、容量設定
+ 系統設定、角色模擬功能
"""

from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import csv
import io

from ..database import get_db
from ..models.user import User, UserRole
from ..models.patient import Patient
from ..models.exam import Exam, DEFAULT_EXAMS
from ..models.equipment import Equipment, EquipmentLog, EquipmentStatus
from ..services.auth import get_current_user, require_role
from ..services import settings as settings_service

router = APIRouter(prefix="/admin", tags=["管理後台"])
templates = Jinja2Templates(directory="app/templates")


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """要求管理員權限"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return user


@router.get("", response_class=HTMLResponse)
async def admin_index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """管理後台首頁"""
    user_count = db.query(User).count()
    pending_count = db.query(User).filter(User.role == UserRole.PENDING.value).count()
    today = date.today()
    patient_count = db.query(Patient).filter(Patient.exam_date == today).count()
    exam_count = db.query(Exam).filter(Exam.is_active == True).count()
    equipment_count = db.query(Equipment).filter(Equipment.is_active == True).count()
    broken_count = db.query(Equipment).filter(
        Equipment.status == EquipmentStatus.BROKEN.value,
        Equipment.is_active == True
    ).count()
    
    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "user": current_user,
        "user_count": user_count,
        "pending_count": pending_count,
        "patient_count": patient_count,
        "exam_count": exam_count,
        "equipment_count": equipment_count,
        "broken_count": broken_count,
    })


# ======================
# 系統設定
# ======================

@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    saved: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """系統設定頁面"""
    all_settings = settings_service.get_all_settings(db)
    default_role = settings_service.get_default_user_role(db)
    
    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "user": current_user,
        "settings": all_settings,
        "default_role": default_role,
        "saved": saved,
        "roles": [
            {"value": "pending", "label": "待審核"},
            {"value": "coordinator", "label": "專員"},
            {"value": "dispatcher", "label": "調度員"},
            {"value": "leader", "label": "組長"},
        ],
    })


@router.post("/settings/default-role")
async def update_default_role(
    request: Request,
    default_role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """更新新用戶預設角色"""
    valid_roles = ["pending", "coordinator", "dispatcher", "leader"]
    if default_role not in valid_roles:
        raise HTTPException(status_code=400, detail="無效的角色")
    
    settings_service.set_setting(db, "default_user_role", default_role, current_user.id)
    
    return RedirectResponse(url="/admin/settings?saved=1", status_code=302)


# ======================
# 帳號管理
# ======================

@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """帳號管理頁面"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    default_role = settings_service.get_default_user_role(db)
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": current_user,
        "users": users,
        "roles": [r.value for r in UserRole],
        "default_role": default_role,
    })


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """更新用戶角色"""
    if role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="無效的角色")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")
    
    target_user.role = role
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/{user_id}/toggle")
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """啟用/停用用戶"""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能停用自己")
    
    target_user.is_active = not target_user.is_active
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)


# ======================
# 病人匯入
# ======================

@router.get("/patients", response_class=HTMLResponse)
async def admin_patients(
    request: Request,
    imported: int = 0,
    errors: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """病人管理頁面"""
    today = date.today()
    patients = db.query(Patient).filter(Patient.exam_date == today).all()
    
    return templates.TemplateResponse("admin/patients.html", {
        "request": request,
        "user": current_user,
        "patients": patients,
        "today": today,
        "imported": imported,
        "errors": errors,
    })


@router.post("/patients/import")
async def import_patients(
    request: Request,
    file: UploadFile = File(...),
    exam_date: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """匯入病人 CSV"""
    try:
        import_date = date.fromisoformat(exam_date)
        content = await file.read()
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        
        imported = 0
        errors = 0
        
        for row in reader:
            try:
                chart_no = row.get("chart_no", row.get("病歷號", "")).strip()
                name = row.get("name", row.get("姓名", "")).strip()
                exam_list = row.get("exam_list", row.get("檢查項目", "")).strip()
                
                if not chart_no or not name:
                    errors += 1
                    continue
                
                existing = db.query(Patient).filter(
                    Patient.chart_no == chart_no,
                    Patient.exam_date == import_date,
                ).first()
                
                if existing:
                    existing.name = name
                    existing.exam_list = exam_list
                else:
                    patient = Patient(
                        chart_no=chart_no,
                        name=name,
                        exam_list=exam_list,
                        exam_date=import_date,
                    )
                    db.add(patient)
                
                imported += 1
                
            except Exception:
                errors += 1
        
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/patients?imported={imported}&errors={errors}",
            status_code=302,
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"匯入失敗：{e}")


@router.post("/patients/add")
async def add_patient(
    request: Request,
    chart_no: str = Form(...),
    name: str = Form(...),
    exam_list: str = Form(""),
    exam_date: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """手動新增病人"""
    import_date = date.fromisoformat(exam_date)
    
    existing = db.query(Patient).filter(
        Patient.chart_no == chart_no,
        Patient.exam_date == import_date,
    ).first()
    
    if existing:
        existing.name = name
        existing.exam_list = exam_list
    else:
        patient = Patient(
            chart_no=chart_no,
            name=name,
            exam_list=exam_list,
            exam_date=import_date,
        )
        db.add(patient)
    
    db.commit()
    return RedirectResponse(url="/admin/patients", status_code=302)


@router.post("/patients/{patient_id}/delete")
async def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """刪除病人"""
    db.query(Patient).filter(Patient.id == patient_id).delete()
    db.commit()
    return RedirectResponse(url="/admin/patients", status_code=302)


@router.get("/patients/template")
async def download_template():
    """下載 CSV 範本"""
    content = "chart_no,name,exam_list\nA001,王小明,CT,MRI,US\nA002,李大華,BLOOD,ECHO\n"
    
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=patient_template.csv"},
    )


# ======================
# 檢查項目管理
# ======================

@router.get("/exams", response_class=HTMLResponse)
async def admin_exams(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """檢查項目管理頁面"""
    exams = db.query(Exam).order_by(Exam.exam_code).all()
    
    # 取得容量狀態
    from ..services.scheduler import get_capacity_status
    capacity_list = get_capacity_status(db)
    capacity_status = {c['exam_code']: c for c in capacity_list}
    
    return templates.TemplateResponse("admin/exams.html", {
        "request": request,
        "user": current_user,
        "exams": exams,
        "capacity_status": capacity_status,
    })


@router.post("/exams/init")
async def init_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """初始化預設檢查項目"""
    count = 0
    for exam_data in DEFAULT_EXAMS:
        existing = db.query(Exam).filter(Exam.exam_code == exam_data["exam_code"]).first()
        if not existing:
            exam = Exam(**exam_data)
            db.add(exam)
            count += 1
        else:
            # 更新容量
            if 'capacity' in exam_data:
                existing.capacity = exam_data['capacity']
    
    db.commit()
    return RedirectResponse(url="/admin/exams", status_code=302)


@router.post("/exams/add")
async def add_exam(
    request: Request,
    exam_code: str = Form(...),
    name: str = Form(...),
    duration_minutes: int = Form(15),
    capacity: int = Form(5),
    location: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """新增檢查項目"""
    existing = db.query(Exam).filter(Exam.exam_code == exam_code).first()
    if existing:
        existing.name = name
        existing.duration_minutes = duration_minutes
        existing.capacity = capacity
        existing.location = location
    else:
        exam = Exam(
            exam_code=exam_code,
            name=name,
            duration_minutes=duration_minutes,
            capacity=capacity,
            location=location,
        )
        db.add(exam)
    
    db.commit()
    return RedirectResponse(url="/admin/exams", status_code=302)


@router.post("/exams/{exam_id}/capacity")
async def update_exam_capacity(
    exam_id: int,
    capacity: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """更新檢查站容量"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam:
        exam.capacity = max(1, min(20, capacity))  # 限制 1-20
        db.commit()
    return RedirectResponse(url="/admin/exams", status_code=302)


@router.post("/exams/{exam_id}/delete")
async def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """刪除檢查項目"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam:
        exam.is_active = False
        db.commit()
    return RedirectResponse(url="/admin/exams", status_code=302)


# ======================
# 設備管理
# ======================

@router.get("/equipment", response_class=HTMLResponse)
async def admin_equipment(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """設備管理頁面"""
    equipment_list = db.query(Equipment).filter(Equipment.is_active == True).all()
    logs = db.query(EquipmentLog).order_by(EquipmentLog.created_at.desc()).limit(20).all()
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    return templates.TemplateResponse("admin/equipment.html", {
        "request": request,
        "user": current_user,
        "equipment_list": equipment_list,
        "logs": logs,
        "exams": exams,
    })


@router.post("/equipment/init")
async def init_equipment(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """初始化設備（依檢查站建立）"""
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    count = 0
    
    for exam in exams:
        existing = db.query(Equipment).filter(Equipment.location == exam.exam_code).first()
        if not existing:
            equipment = Equipment(
                name=f"{exam.name}主機",
                location=exam.exam_code,
                equipment_type="檢查設備",
                status=EquipmentStatus.NORMAL.value,
            )
            db.add(equipment)
            count += 1
    
    db.commit()
    return RedirectResponse(url="/admin/equipment", status_code=302)


@router.post("/equipment/add")
async def add_equipment(
    request: Request,
    name: str = Form(...),
    location: str = Form(...),
    equipment_type: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """新增設備"""
    equipment = Equipment(
        name=name,
        location=location,
        equipment_type=equipment_type,
        status=EquipmentStatus.NORMAL.value,
    )
    db.add(equipment)
    db.commit()
    return RedirectResponse(url="/admin/equipment", status_code=302)


@router.post("/equipment/{equipment_id}/repair")
async def repair_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """修復設備"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if equipment:
        old_status = equipment.status
        equipment.status = EquipmentStatus.NORMAL.value
        
        log = EquipmentLog(
            equipment_id=equipment_id,
            action="repair",
            old_status=old_status,
            new_status=EquipmentStatus.NORMAL.value,
            description="設備已修復",
            operator_id=current_user.id,
        )
        db.add(log)
        db.commit()
    
    return RedirectResponse(url="/admin/equipment", status_code=302)


@router.post("/equipment/{equipment_id}/delete")
async def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """刪除設備"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if equipment:
        equipment.is_active = False
        db.commit()
    return RedirectResponse(url="/admin/equipment", status_code=302)


# ======================
# 角色模擬功能
# ======================

@router.get("/impersonate", response_class=HTMLResponse)
async def admin_impersonate(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """角色模擬選擇頁面"""
    from ..services import impersonate as impersonate_service
    
    dispatchers = impersonate_service.get_impersonatable_users(db, "dispatcher")
    coordinators = impersonate_service.get_impersonatable_users(db, "coordinator")
    leaders = impersonate_service.get_impersonatable_users(db, "leader")
    patients = impersonate_service.get_impersonatable_patients(db)
    
    status = impersonate_service.get_impersonation_status(request)
    
    return templates.TemplateResponse("admin/impersonate.html", {
        "request": request,
        "user": current_user,
        "dispatchers": dispatchers,
        "coordinators": coordinators,
        "leaders": leaders,
        "patients": patients,
        "impersonate_status": status,
        "today": date.today(),
    })


@router.post("/impersonate/start")
async def start_impersonate(
    request: Request,
    role: str = Form(...),
    user_id: int = Form(None),
    patient_id: int = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """開始角色模擬"""
    from ..services import impersonate as impersonate_service
    
    result = impersonate_service.start_impersonation(
        request=request,
        admin_id=current_user.id,
        target_role=role,
        target_user_id=user_id,
        target_patient_id=patient_id,
    )
    
    if not result["success"]:
        return RedirectResponse(
            url=f"/admin/impersonate?error={result['error']}",
            status_code=302
        )
    
    response = RedirectResponse(url=result["redirect_url"], status_code=302)
    impersonate_service.set_impersonate_cookie(response, result["token"])
    
    return response


@router.post("/impersonate/end")
async def end_impersonate(
    request: Request,
    db: Session = Depends(get_db),
):
    """結束角色模擬"""
    from ..services import impersonate as impersonate_service
    
    response = RedirectResponse(url="/admin", status_code=302)
    impersonate_service.clear_impersonate_cookie(response)
    
    return response


@router.get("/impersonate/status")
async def get_impersonate_status_api(
    request: Request,
    db: Session = Depends(get_db),
):
    """取得模擬狀態 (API)"""
    from ..services import impersonate as impersonate_service
    
    return impersonate_service.get_impersonation_status(request)


# ======================
# 排程建議（Phase 7 新增）
# ======================

@router.get("/scheduler", response_class=HTMLResponse)
async def scheduler_page(
    request: Request,
    patient_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """排程建議頁面"""
    from ..services.scheduler import (
        optimize_daily_schedule,
        get_capacity_status,
        suggest_next_station,
        detect_schedule_conflicts,
    )
    
    today = date.today()
    
    # 取得整體優化建議
    optimization = optimize_daily_schedule(db, today)
    
    # 取得容量狀態
    capacity_status = get_capacity_status(db, today)
    
    # 取得所有病人
    patients = db.query(Patient).filter(
        Patient.exam_date == today,
        Patient.is_active == True,
    ).all()
    
    # 如果選擇了特定病人
    selected_patient = None
    suggestions = []
    conflicts = []
    
    if patient_id:
        selected_patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if selected_patient:
            suggestions = suggest_next_station(db, patient_id, today)
            conflicts = detect_schedule_conflicts(db, patient_id, today)
    
    return templates.TemplateResponse("admin/scheduler.html", {
        "request": request,
        "user": current_user,
        "optimization": optimization,
        "capacity_status": capacity_status,
        "patients": patients,
        "selected_patient": selected_patient,
        "suggestions": suggestions,
        "conflicts": conflicts,
    })


# ======================
# HTMX API
# ======================

@router.get("/exams/api/capacity", response_class=HTMLResponse)
async def get_capacity_partial(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """容量狀態（HTMX 部分更新）"""
    from ..services.scheduler import get_capacity_status
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    capacity_list = get_capacity_status(db)
    capacity_status = {c['exam_code']: c for c in capacity_list}
    
    # 回傳容量卡片 HTML
    html_parts = []
    for exam in exams:
        if exam.is_active:
            status = capacity_status.get(exam.exam_code, {})
            utilization = status.get('utilization', 0)
            current_count = status.get('current_count', 0)
            capacity = exam.capacity or 5
            
            if utilization >= 100:
                border_class = "border-red-300 bg-red-50"
                text_class = "text-red-600"
                bar_class = "bg-red-500"
            elif utilization >= 70:
                border_class = "border-yellow-300 bg-yellow-50"
                text_class = "text-yellow-600"
                bar_class = "bg-yellow-500"
            else:
                border_class = "border-gray-200"
                text_class = "text-green-600"
                bar_class = "bg-green-500"
            
            html_parts.append(f'''
            <div class="border rounded-lg p-3 {border_class}">
                <div class="font-medium text-sm">{exam.exam_code}</div>
                <div class="text-xs text-gray-500">{exam.name}</div>
                <div class="mt-2 flex justify-between items-center">
                    <span class="text-lg font-bold">{current_count}/{capacity}</span>
                    <span class="text-xs {text_class}">{utilization}%</span>
                </div>
                <div class="mt-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div class="h-full rounded-full {bar_class}" style="width: {min(utilization, 100)}%"></div>
                </div>
            </div>
            ''')
    
    return HTMLResponse(content=''.join(html_parts))
