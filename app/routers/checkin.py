# -*- coding: utf-8 -*-
"""
報到路由 - QR Code 自助報到
"""

from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.patient import Patient
from ..services import checkin as checkin_service

router = APIRouter(prefix="/checkin", tags=["報到"])
templates = Jinja2Templates(directory="app/templates")


def get_base_url(request: Request) -> str:
    """取得基礎 URL"""
    # 優先使用 X-Forwarded-Proto 和 X-Forwarded-Host
    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    return f"{proto}://{host}"


@router.get("/{token}", response_class=HTMLResponse)
async def checkin_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    """報到頁面（掃描 QR Code 後顯示）"""
    
    result = checkin_service.process_checkin(db, token)
    
    return templates.TemplateResponse("checkin/result.html", {
        "request": request,
        "success": result["success"],
        "message": result["message"],
        "patient": result.get("patient"),
        "already_checked_in": result.get("already_checked_in", False),
        "tracking": result.get("tracking"),
    })


@router.get("/api/qrcode/{patient_id}")
async def get_patient_qrcode(
    request: Request,
    patient_id: int,
    exam_date: str = None,
    db: Session = Depends(get_db),
):
    """取得病人 QR Code 圖片"""
    
    if exam_date:
        try:
            target_date = date.fromisoformat(exam_date)
        except:
            target_date = date.today()
    else:
        target_date = date.today()
    
    base_url = get_base_url(request)
    qr_image = checkin_service.get_patient_qrcode(db, patient_id, target_date, base_url)
    
    if not qr_image:
        raise HTTPException(status_code=404, detail="病人不存在")
    
    return Response(
        content=qr_image,
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename=checkin_qr_{patient_id}.png"
        }
    )


@router.get("/api/status/{patient_id}")
async def get_checkin_status(
    patient_id: int,
    exam_date: str = None,
    db: Session = Depends(get_db),
):
    """取得病人報到狀態（API）"""
    
    if exam_date:
        try:
            target_date = date.fromisoformat(exam_date)
        except:
            target_date = date.today()
    else:
        target_date = date.today()
    
    status = checkin_service.get_patient_checkin_status(db, patient_id, target_date)
    
    return {
        "patient_id": patient_id,
        "exam_date": target_date.isoformat(),
        "exists": status["exists"],
        "checked_in": status["checked_in"],
        "patient_name": status["patient"].name if status["patient"] else None,
        "current_status": status["tracking"].current_status if status.get("tracking") else None,
        "current_location": status["tracking"].current_location if status.get("tracking") else None,
    }
