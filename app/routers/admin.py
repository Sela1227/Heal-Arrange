# -*- coding: utf-8 -*-
"""
管理後台路由 - 支援多權限管理
"""

from datetime import date, datetime, timedelta
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
    # 用 role 欄位判斷待審核（避免 JSON 比較問題）
    pending_count = db.query(User).filter(
        User.is_active == True,
        User.role == 'pending'
    ).count()
    
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
                package_code = row.get("package_code", row.get("套餐代碼", "")).strip()
                
                if not chart_no or not name:
                    errors += 1
                    continue
                
                existing = db.query(Patient).filter(
                    Patient.chart_no == chart_no,
                    Patient.exam_date == import_date,
                ).first()
                
                if existing:
                    existing.name = name
                    existing.notes = exam_list  # 存到 notes 欄位
                    existing.package_code = package_code
                else:
                    patient = Patient(
                        chart_no=chart_no,
                        name=name,
                        notes=exam_list,  # 存到 notes 欄位
                        package_code=package_code,
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
        existing.notes = exam_list  # 存到 notes 欄位
    else:
        patient = Patient(
            chart_no=chart_no,
            name=name,
            notes=exam_list,  # 存到 notes 欄位
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
    duration_min: int = Form(15),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """新增檢查項目"""
    existing = db.query(Exam).filter(Exam.exam_code == exam_code).first()
    if existing:
        existing.name = name
        existing.duration_min = duration_min
    else:
        exam = Exam(
            exam_code=exam_code,
            name=name,
            duration_min=duration_min,
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


# ======================
# 操作日誌
# ======================

@router.get("/audit", response_class=HTMLResponse)
async def admin_audit(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    action: str = None,
    user_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """操作日誌頁面"""
    from ..services import audit as audit_service
    from ..models.audit import AuditLog
    
    # 處理日期
    today = date.today()
    if not end_date:
        end = today
    else:
        try:
            end = date.fromisoformat(end_date)
        except:
            end = today
    
    if not start_date:
        start = end - timedelta(days=7)
    else:
        try:
            start = date.fromisoformat(start_date)
        except:
            start = end - timedelta(days=7)
    
    # 查詢日誌
    logs = audit_service.get_audit_logs(
        db=db,
        start_date=start,
        end_date=end,
        action=action if action else None,
        user_id=user_id if user_id else None,
        limit=100
    )
    
    # 統計
    total_count = db.query(AuditLog).count()
    today_count = audit_service.get_audit_log_count(db, start_date=today, end_date=today)
    
    # 活躍使用者數
    from sqlalchemy import func, distinct
    unique_users = db.query(func.count(distinct(AuditLog.user_id))).filter(
        AuditLog.created_at >= datetime.combine(start, datetime.min.time()),
        AuditLog.user_id.isnot(None)
    ).scalar() or 0
    
    # 所有使用者（用於篩選）
    users = db.query(User).filter(User.is_active == True).all()
    
    return templates.TemplateResponse("admin/audit.html", {
        "request": request,
        "user": current_user,
        "logs": logs,
        "start_date": start,
        "end_date": end,
        "selected_action": action,
        "selected_user_id": user_id,
        "all_actions": audit_service.ALL_ACTIONS,
        "users": users,
        "total_count": total_count,
        "today_count": today_count,
        "unique_users": unique_users,
    })


@router.get("/audit/export")
async def export_audit_logs(
    start_date: str = None,
    end_date: str = None,
    action: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """匯出操作日誌 CSV"""
    from ..services import audit as audit_service
    
    # 處理日期
    today = date.today()
    try:
        start = date.fromisoformat(start_date) if start_date else today - timedelta(days=30)
        end = date.fromisoformat(end_date) if end_date else today
    except:
        start = today - timedelta(days=30)
        end = today
    
    csv_content = audit_service.export_audit_logs_csv(db, start_date=start, end_date=end)
    
    # 記錄操作
    audit_service.log_user_action(
        db=db,
        user=current_user,
        action="data_export",
        request=None,
        target_type="audit_log",
        details={"start_date": str(start), "end_date": str(end)}
    )
    
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_logs_{start}_{end}.csv"}
    )


# ======================
# 資料備份
# ======================

@router.get("/backup", response_class=HTMLResponse)
async def admin_backup(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """資料備份頁面"""
    from ..services import backup as backup_service
    
    summary = backup_service.get_backup_summary(db)
    
    return templates.TemplateResponse("admin/backup.html", {
        "request": request,
        "user": current_user,
        "summary": summary,
        "today": date.today(),
    })


@router.get("/backup/export/users")
async def export_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """匯出使用者 CSV"""
    from ..services import backup as backup_service
    from ..services import audit as audit_service
    
    csv_content = backup_service.export_users_csv(db)
    
    audit_service.log_user_action(
        db=db, user=current_user, action="data_export",
        target_type="users", details={"format": "csv"}
    )
    
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=users_{date.today()}.csv"}
    )


@router.get("/backup/export/patients")
async def export_patients(
    exam_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """匯出病人 CSV"""
    from ..services import backup as backup_service
    from ..services import audit as audit_service
    
    target_date = None
    if exam_date:
        try:
            target_date = date.fromisoformat(exam_date)
        except:
            pass
    
    csv_content = backup_service.export_patients_csv(db, exam_date=target_date)
    
    audit_service.log_user_action(
        db=db, user=current_user, action="data_export",
        target_type="patients", details={"format": "csv", "date": str(target_date) if target_date else "all"}
    )
    
    filename = f"patients_{target_date or 'all'}_{date.today()}.csv"
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/backup/export/exams")
async def export_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """匯出檢查項目 CSV"""
    from ..services import backup as backup_service
    from ..services import audit as audit_service
    
    csv_content = backup_service.export_exams_csv(db)
    
    audit_service.log_user_action(
        db=db, user=current_user, action="data_export",
        target_type="exams", details={"format": "csv"}
    )
    
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=exams_{date.today()}.csv"}
    )


@router.get("/backup/export/equipment")
async def export_equipment(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """匯出設備 CSV"""
    from ..services import backup as backup_service
    from ..services import audit as audit_service
    
    csv_content = backup_service.export_equipment_csv(db)
    
    audit_service.log_user_action(
        db=db, user=current_user, action="data_export",
        target_type="equipment", details={"format": "csv"}
    )
    
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=equipment_{date.today()}.csv"}
    )


@router.get("/backup/export/tracking")
async def export_tracking(
    exam_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """匯出追蹤記錄 CSV"""
    from ..services import backup as backup_service
    from ..services import audit as audit_service
    
    target_date = None
    if exam_date:
        try:
            target_date = date.fromisoformat(exam_date)
        except:
            pass
    
    csv_content = backup_service.export_tracking_history_csv(db, exam_date=target_date)
    
    audit_service.log_user_action(
        db=db, user=current_user, action="data_export",
        target_type="tracking", details={"format": "csv", "date": str(target_date) if target_date else "all"}
    )
    
    filename = f"tracking_{target_date or 'all'}_{date.today()}.csv"
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/backup/export/full")
async def export_full_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """完整備份 JSON"""
    from ..services import backup as backup_service
    from ..services import audit as audit_service
    
    json_content = backup_service.export_all_data_json(db)
    
    audit_service.log_user_action(
        db=db, user=current_user, action="data_backup",
        details={"format": "json", "type": "full"}
    )
    
    return Response(
        content=json_content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=heal_arrange_backup_{date.today()}.json"}
    )


# ======================
# 效能儀表板
# ======================

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """效能儀表板"""
    from ..services import dashboard as dashboard_service
    
    kpi = dashboard_service.get_realtime_kpi(db)
    hourly_data = dashboard_service.get_hourly_stats(db)
    station_performance = dashboard_service.get_station_performance(db)
    coordinator_performance = dashboard_service.get_coordinator_performance(db)
    chart_data = dashboard_service.get_daily_chart_data(db, days=7)
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": current_user,
        "now": datetime.now(),
        "kpi": kpi,
        "hourly_data": hourly_data,
        "station_performance": station_performance,
        "coordinator_performance": coordinator_performance,
        "chart_data": chart_data,
    })


@router.get("/dashboard/api/kpi", response_class=HTMLResponse)
async def get_kpi_partial(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """KPI 卡片（HTMX 部分更新）"""
    from ..services import dashboard as dashboard_service
    
    kpi = dashboard_service.get_realtime_kpi(db)
    
    return templates.TemplateResponse("partials/kpi_cards.html", {
        "request": request,
        "kpi": kpi,
    })


# ===================================
# 資料庫修復端點（緊急使用）
# ===================================

@router.get("/fix-permissions", response_class=HTMLResponse)
async def fix_user_permissions(
    request: Request,
    key: str = None,
    db: Session = Depends(get_db),
):
    """
    修復用戶權限
    使用方式：訪問 /admin/fix-permissions?key=heal2025
    """
    # 簡單的安全驗證
    if key != "heal2025":
        return HTMLResponse("""
        <html>
        <head><title>權限修復</title></head>
        <body style="font-family: sans-serif; padding: 20px;">
            <h1>⚠️ 需要密鑰</h1>
            <p>請訪問: <code>/admin/fix-permissions?key=heal2025</code></p>
        </body>
        </html>
        """)
    
    # 取得所有用戶
    users = db.query(User).all()
    fixed_count = 0
    results = []
    
    for user in users:
        old_permissions = user.permissions
        old_role = user.role
        
        # 檢查是否需要修復
        needs_fix = (
            user.permissions is None or 
            user.permissions == [] or 
            user.permissions == 'null' or
            (isinstance(user.permissions, str) and user.permissions == '[]')
        )
        
        if needs_fix and user.is_active:
            # 設定預設權限
            user.permissions = ["dispatcher", "coordinator"]
            user.role = "active"
            fixed_count += 1
            results.append(f"✅ {user.display_name}: {old_permissions} → {user.permissions}")
        else:
            results.append(f"⏭️ {user.display_name}: 已有權限 {user.permissions}")
    
    db.commit()
    
    # 顯示結果
    result_html = "<br>".join(results)
    return HTMLResponse(f"""
    <html>
    <head>
        <title>權限修復結果</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }}
            .success {{ color: green; }}
            .info {{ color: blue; }}
            pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>🔧 權限修復結果</h1>
        <p class="success">已修復 <strong>{fixed_count}</strong> 個用戶</p>
        <h3>詳細結果：</h3>
        <pre>{result_html}</pre>
        <hr>
        <p><a href="/">← 返回首頁</a></p>
    </body>
    </html>
    """)
