# -*- coding: utf-8 -*-
"""
管理後台路由 - 支援多權限管理
"""

from datetime import date
from typing import List
from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import csv
import io

from ..database import get_db
from ..models.user import User, Permission, ALL_PERMISSIONS
from ..models.patient import Patient
from ..models.exam import Exam, DEFAULT_EXAMS
from ..models.equipment import Equipment, EquipmentLog, EquipmentStatus
from ..services.auth import get_current_user, require_admin

router = APIRouter(prefix="/admin", tags=["管理後台"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def admin_index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """管理後台首頁"""
    user_count = db.query(User).count()
    pending_count = db.query(User).filter(
        User.is_active == True,
        User.permissions == []  # JSON 空陣列
    ).count()
    
    # 也檢查 permissions 為 null 的情況
    pending_null = db.query(User).filter(
        User.is_active == True,
        User.permissions.is_(None)
    ).count()
    pending_count += pending_null
    
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
# 帳號管理（多權限版本）
# ======================

@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """帳號管理頁面"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": current_user,
        "users": users,
        "all_permissions": ALL_PERMISSIONS,
    })


@router.post("/users/{user_id}/permissions")
async def update_user_permissions(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """更新使用者權限"""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的權限")
    
    # 從表單取得選中的權限
    form_data = await request.form()
    new_permissions = form_data.getlist("permissions")
    
    # 驗證權限值
    valid_permissions = [p["value"] for p in ALL_PERMISSIONS]
    new_permissions = [p for p in new_permissions if p in valid_permissions]
    
    # 更新權限
    target_user.set_permissions(new_permissions)
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/{user_id}/toggle")
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """啟用/停用使用者"""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能停用自己")
    
    target_user.is_active = not target_user.is_active
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """快速核准使用者（給予個管師權限）"""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    # 預設給予個管師權限
    target_user.add_permission(Permission.COORDINATOR.value)
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/{user_id}/grant-all")
async def grant_all_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """給予所有權限"""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的權限")
    
    all_perms = [p["value"] for p in ALL_PERMISSIONS]
    target_user.set_permissions(all_perms)
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/{user_id}/revoke-all")
async def revoke_all_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """撤銷所有權限"""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的權限")
    
    target_user.set_permissions([])
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=302)


# ======================
# 以下為原有功能（病人、檢查項目、設備管理）
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
    
    return templates.TemplateResponse("admin/exams.html", {
        "request": request,
        "user": current_user,
        "exams": exams,
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
    
    db.commit()
    return RedirectResponse(url="/admin/exams", status_code=302)


@router.post("/exams/add")
async def add_exam(
    request: Request,
    exam_code: str = Form(...),
    name: str = Form(...),
    duration_minutes: int = Form(15),
    location: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """新增檢查項目"""
    existing = db.query(Exam).filter(Exam.exam_code == exam_code).first()
    if existing:
        existing.name = name
        existing.duration_minutes = duration_minutes
        existing.location = location
    else:
        exam = Exam(
            exam_code=exam_code,
            name=name,
            duration_minutes=duration_minutes,
            location=location,
        )
        db.add(exam)
    
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
