# -*- coding: utf-8 -*-
"""
QR Code 管理路由 - 給管理員列印病人報到 QR Code
"""

from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole
from ..models.patient import Patient
from ..services.auth import get_current_user
from ..services import qrcode_service

router = APIRouter(prefix="/admin/qrcode", tags=["QR Code 管理"])
templates = Jinja2Templates(directory="app/templates")


def require_admin_or_dispatcher(request: Request, db: Session = Depends(get_db)) -> User:
    """要求管理員或調度員權限"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if user.role not in [UserRole.ADMIN.value, UserRole.DISPATCHER.value, UserRole.LEADER.value]:
        raise HTTPException(status_code=403, detail="權限不足")
    return user


@router.get("", response_class=HTMLResponse)
async def qrcode_list(
    request: Request,
    target_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """QR Code 列表頁面"""
    if target_date:
        try:
            exam_date = date.fromisoformat(target_date)
        except:
            exam_date = date.today()
    else:
        exam_date = date.today()
    
    # 取得當日病人
    patients = db.query(Patient).filter(
        Patient.exam_date == exam_date,
        Patient.is_active == True,
    ).order_by(Patient.chart_no).all()
    
    # 取得 base URL
    base_url = str(request.base_url).rstrip("/")
    
    return templates.TemplateResponse("admin/qrcode_list.html", {
        "request": request,
        "user": current_user,
        "patients": patients,
        "exam_date": exam_date,
        "today": date.today(),
        "base_url": base_url,
    })


@router.get("/print", response_class=HTMLResponse)
async def print_qrcodes(
    request: Request,
    target_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """列印 QR Code 頁面（全部）"""
    if target_date:
        try:
            exam_date = date.fromisoformat(target_date)
        except:
            exam_date = date.today()
    else:
        exam_date = date.today()
    
    base_url = str(request.base_url).rstrip("/")
    qrcodes = qrcode_service.get_patient_qrcodes(db, exam_date, base_url)
    
    return templates.TemplateResponse("admin/qrcode_print.html", {
        "request": request,
        "qrcodes": qrcodes,
        "exam_date": exam_date,
    })


@router.get("/patient/{patient_id}", response_class=HTMLResponse)
async def single_qrcode(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """單一病人 QR Code 頁面"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="找不到病人")
    
    base_url = str(request.base_url).rstrip("/")
    qrcode_info = qrcode_service.generate_patient_qrcode(
        patient.id, patient.exam_date, base_url
    )
    
    return templates.TemplateResponse("admin/qrcode_single.html", {
        "request": request,
        "user": current_user,
        "patient": patient,
        "qrcode": qrcode_info,
    })


@router.get("/patient/{patient_id}/image")
async def qrcode_image(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
):
    """取得 QR Code 圖片（PNG）"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="找不到病人")
    
    base_url = str(request.base_url).rstrip("/")
    url = qrcode_service.generate_checkin_url(patient.id, patient.exam_date, base_url)
    
    # 產生 QR Code
    import qrcode
    import io
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename=qrcode_{patient.chart_no}.png"
        }
    )
