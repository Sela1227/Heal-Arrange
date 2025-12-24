# -*- coding: utf-8 -*-
"""
管理後台路由
"""

from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import csv
import io

from ..database import get_db
from ..models.user import User, UserRole
from ..models.patient import Patient
from ..models.exam import Exam, DEFAULT_EXAMS
from ..services.auth import get_current_user, require_role

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
    # 統計資料
    user_count = db.query(User).count()
    pending_count = db.query(User).filter(User.role == UserRole.PENDING.value).count()
    today = date.today()
    patient_count = db.query(Patient).filter(Patient.exam_date == today).count()
    
    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "user": current_user,
        "user_count": user_count,
        "pending_count": pending_count,
        "patient_count": patient_count,
    })


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
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": current_user,
        "users": users,
        "roles": [r.value for r in UserRole],
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
    
    # 不能修改自己的角色
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
        # 解析日期
        import_date = date.fromisoformat(exam_date)
        
        # 讀取 CSV
        content = await file.read()
        text = content.decode("utf-8-sig")  # 支援 BOM
        reader = csv.DictReader(io.StringIO(text))
        
        imported = 0
        errors = []
        
        for row in reader:
            try:
                chart_no = row.get("病歷號", "").strip()
                name = row.get("姓名", "").strip()
                package = row.get("套餐代碼", "").strip()
                
                if not chart_no or not name:
                    errors.append(f"跳過：缺少病歷號或姓名")
                    continue
                
                # 檢查是否已存在
                existing = db.query(Patient).filter(
                    Patient.chart_no == chart_no,
                    Patient.exam_date == import_date,
                ).first()
                
                if existing:
                    # 更新
                    existing.name = name
                    existing.package_code = package
                else:
                    # 新增
                    patient = Patient(
                        chart_no=chart_no,
                        name=name,
                        package_code=package,
                        exam_date=import_date,
                    )
                    db.add(patient)
                
                imported += 1
                
            except Exception as e:
                errors.append(f"錯誤：{e}")
        
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/patients?imported={imported}&errors={len(errors)}",
            status_code=302,
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"匯入失敗：{e}")


@router.get("/patients/template")
async def download_template():
    """下載 CSV 範本"""
    from fastapi.responses import Response
    
    content = "病歷號,姓名,套餐代碼\nA001,王小明,CT,MRI,US,XRAY\nA002,李大華,BLOOD,GFS,CFS\n"
    
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=patient_template.csv"},
    )


# ======================
# 檢查項目初始化
# ======================

@router.post("/exams/init")
async def init_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """初始化預設檢查項目"""
    for exam_data in DEFAULT_EXAMS:
        existing = db.query(Exam).filter(Exam.exam_code == exam_data["exam_code"]).first()
        if not existing:
            exam = Exam(**exam_data)
            db.add(exam)
    
    db.commit()
    
    return RedirectResponse(url="/admin", status_code=302)
