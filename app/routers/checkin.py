# -*- coding: utf-8 -*-
"""
病人自助報到路由
"""

from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.patient import Patient
from ..models.tracking import PatientTracking, TrackingHistory, TrackingStatus, TrackingAction
from ..services import qrcode_service
from ..services import wait_time as wait_time_service

router = APIRouter(prefix="/checkin", tags=["自助報到"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/{token}", response_class=HTMLResponse)
async def checkin_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    """自助報到頁面"""
    # 驗證 Token
    token_data = qrcode_service.verify_checkin_token(token)
    
    if not token_data:
        return templates.TemplateResponse("patient/checkin_error.html", {
            "request": request,
            "error": "無效或過期的報到連結",
            "message": "請確認 QR Code 是否正確，或聯繫服務人員",
        })
    
    patient_id = token_data["patient_id"]
    exam_date = token_data["exam_date"]
    
    # 取得病人資料
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return templates.TemplateResponse("patient/checkin_error.html", {
            "request": request,
            "error": "找不到病人資料",
            "message": "請聯繫服務人員協助",
        })
    
    # 取得追蹤狀態
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date,
    ).first()
    
    # 判斷狀態
    already_checked_in = False
    if tracking and tracking.current_status != TrackingStatus.WAITING.value:
        already_checked_in = True
    
    # 取得等候資訊
    wait_info = None
    if tracking and tracking.current_location:
        wait_info = wait_time_service.estimate_wait_time(db, tracking.current_location, exam_date)
    
    return templates.TemplateResponse("patient/checkin.html", {
        "request": request,
        "patient": patient,
        "tracking": tracking,
        "token": token,
        "already_checked_in": already_checked_in,
        "wait_info": wait_info,
        "today": date.today(),
    })


@router.post("/{token}")
async def do_checkin(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    """執行報到"""
    # 驗證 Token
    token_data = qrcode_service.verify_checkin_token(token)
    
    if not token_data:
        raise HTTPException(status_code=400, detail="無效或過期的報到連結")
    
    patient_id = token_data["patient_id"]
    exam_date = token_data["exam_date"]
    
    # 取得病人資料
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="找不到病人資料")
    
    # 取得或建立追蹤記錄
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date,
    ).first()
    
    if not tracking:
        tracking = PatientTracking(
            patient_id=patient_id,
            exam_date=exam_date,
            current_status=TrackingStatus.WAITING.value,
            current_location="REG",  # 預設在報到櫃檯
        )
        db.add(tracking)
    else:
        tracking.current_status = TrackingStatus.WAITING.value
        if not tracking.current_location:
            tracking.current_location = "REG"
    
    # 記錄歷程
    history = TrackingHistory(
        patient_id=patient_id,
        exam_date=exam_date,
        action=TrackingAction.ARRIVE.value,
        location=tracking.current_location,
        status=TrackingStatus.WAITING.value,
        notes="病人自助報到",
    )
    db.add(history)
    
    db.commit()
    
    # 重導向到成功頁面
    return RedirectResponse(url=f"/checkin/{token}/success", status_code=302)


@router.get("/{token}/success", response_class=HTMLResponse)
async def checkin_success(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    """報到成功頁面"""
    token_data = qrcode_service.verify_checkin_token(token)
    
    if not token_data:
        return templates.TemplateResponse("patient/checkin_error.html", {
            "request": request,
            "error": "無效的連結",
        })
    
    patient = db.query(Patient).filter(Patient.id == token_data["patient_id"]).first()
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == token_data["patient_id"],
        PatientTracking.exam_date == token_data["exam_date"],
    ).first()
    
    # 取得等候資訊
    wait_info = None
    if tracking and tracking.current_location:
        wait_info = wait_time_service.estimate_wait_time(
            db, tracking.current_location, token_data["exam_date"]
        )
    
    return templates.TemplateResponse("patient/checkin_success.html", {
        "request": request,
        "patient": patient,
        "tracking": tracking,
        "wait_info": wait_info,
    })


@router.get("/{token}/status", response_class=HTMLResponse)
async def checkin_status(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    """查看目前狀態（HTMX 更新）"""
    token_data = qrcode_service.verify_checkin_token(token)
    
    if not token_data:
        return HTMLResponse("<p class='text-red-500'>連結已失效</p>")
    
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == token_data["patient_id"],
        PatientTracking.exam_date == token_data["exam_date"],
    ).first()
    
    wait_info = None
    if tracking and tracking.current_location:
        wait_info = wait_time_service.estimate_wait_time(
            db, tracking.current_location, token_data["exam_date"]
        )
    
    return templates.TemplateResponse("patient/partials/status_card.html", {
        "request": request,
        "tracking": tracking,
        "wait_info": wait_info,
    })
