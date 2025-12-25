# -*- coding: utf-8 -*-
"""
QR Code 自助報到服務
產生病人專屬 QR Code，支援掃碼報到
"""

import hashlib
import secrets
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Tuple
from io import BytesIO
from sqlalchemy.orm import Session

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from ..models.patient import Patient
from ..models.tracking import PatientTracking, TrackingHistory, TrackingStatus, TrackingAction
from ..config import settings


def generate_checkin_token(patient_id: int, exam_date: date) -> str:
    """
    產生病人報到專用 Token
    格式：{patient_id}-{date}-{hash}
    """
    # 建立簽名資料
    data = f"{patient_id}:{exam_date.isoformat()}:{settings.SECRET_KEY}"
    
    # 產生 hash（取前 12 碼）
    hash_value = hashlib.sha256(data.encode()).hexdigest()[:12]
    
    # 組合 token
    token = f"{patient_id}-{exam_date.strftime('%Y%m%d')}-{hash_value}"
    
    return token


def verify_checkin_token(token: str) -> Tuple[bool, Optional[int], Optional[date]]:
    """
    驗證報到 Token
    
    Returns:
        (is_valid, patient_id, exam_date)
    """
    try:
        parts = token.split('-')
        if len(parts) != 3:
            return False, None, None
        
        patient_id = int(parts[0])
        exam_date = datetime.strptime(parts[1], '%Y%m%d').date()
        provided_hash = parts[2]
        
        # 重新計算 hash 驗證
        data = f"{patient_id}:{exam_date.isoformat()}:{settings.SECRET_KEY}"
        expected_hash = hashlib.sha256(data.encode()).hexdigest()[:12]
        
        if provided_hash != expected_hash:
            return False, None, None
        
        return True, patient_id, exam_date
        
    except Exception:
        return False, None, None


def generate_checkin_url(patient_id: int, exam_date: date, base_url: str) -> str:
    """產生報到 URL"""
    token = generate_checkin_token(patient_id, exam_date)
    return f"{base_url}/checkin/{token}"


def generate_qrcode_image(url: str, size: int = 10) -> bytes:
    """
    產生 QR Code 圖片
    
    Args:
        url: 要編碼的 URL
        size: QR Code 大小 (box_size)
    
    Returns:
        PNG 圖片的 bytes
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_M,
        box_size=size,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer.getvalue()


def get_patient_qrcode(db: Session, patient_id: int, exam_date: date, base_url: str) -> Optional[bytes]:
    """
    取得病人的報到 QR Code
    
    Returns:
        PNG 圖片的 bytes，如果病人不存在則返回 None
    """
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.exam_date == exam_date,
        Patient.is_active == True
    ).first()
    
    if not patient:
        return None
    
    url = generate_checkin_url(patient_id, exam_date, base_url)
    return generate_qrcode_image(url)


def process_checkin(db: Session, token: str) -> Dict:
    """
    處理報到請求
    
    Returns:
        {
            "success": bool,
            "message": str,
            "patient": Patient or None,
            "already_checked_in": bool
        }
    """
    # 驗證 token
    is_valid, patient_id, exam_date = verify_checkin_token(token)
    
    if not is_valid:
        return {
            "success": False,
            "message": "無效的報到連結",
            "patient": None,
            "already_checked_in": False,
        }
    
    # 檢查日期
    today = date.today()
    if exam_date != today:
        if exam_date < today:
            return {
                "success": False,
                "message": f"此報到連結已過期（檢查日期：{exam_date}）",
                "patient": None,
                "already_checked_in": False,
            }
        else:
            return {
                "success": False,
                "message": f"檢查日期尚未到達（預約日期：{exam_date}）",
                "patient": None,
                "already_checked_in": False,
            }
    
    # 查詢病人
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.exam_date == exam_date,
        Patient.is_active == True
    ).first()
    
    if not patient:
        return {
            "success": False,
            "message": "找不到病人資料",
            "patient": None,
            "already_checked_in": False,
        }
    
    # 檢查是否已報到
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date
    ).first()
    
    if tracking:
        # 已有追蹤記錄，表示已報到
        return {
            "success": True,
            "message": f"您已完成報到，目前狀態：{tracking.current_status}",
            "patient": patient,
            "already_checked_in": True,
            "tracking": tracking,
        }
    
    # 建立追蹤記錄（報到）
    tracking = PatientTracking(
        patient_id=patient_id,
        exam_date=exam_date,
        current_status=TrackingStatus.WAITING.value,
        current_location="REG",  # 報到櫃檯
        updated_at=datetime.utcnow(),
    )
    db.add(tracking)
    
    # 記錄歷程
    history = TrackingHistory(
        patient_id=patient_id,
        exam_date=exam_date,
        action=TrackingAction.ARRIVE.value,
        location="REG",
        status=TrackingStatus.WAITING.value,
        timestamp=datetime.utcnow(),
        notes="QR Code 自助報到",
    )
    db.add(history)
    
    db.commit()
    db.refresh(tracking)
    
    return {
        "success": True,
        "message": "報到成功！請至報到櫃檯確認",
        "patient": patient,
        "already_checked_in": False,
        "tracking": tracking,
    }


def get_patient_checkin_status(db: Session, patient_id: int, exam_date: date) -> Dict:
    """
    取得病人報到狀態
    """
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.exam_date == exam_date,
        Patient.is_active == True
    ).first()
    
    if not patient:
        return {
            "exists": False,
            "checked_in": False,
            "patient": None,
        }
    
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date
    ).first()
    
    return {
        "exists": True,
        "checked_in": tracking is not None,
        "patient": patient,
        "tracking": tracking,
    }


def generate_batch_qrcodes(
    db: Session, 
    exam_date: date, 
    base_url: str
) -> list:
    """
    批次產生當日所有病人的 QR Code 資訊
    
    Returns:
        [{"patient": Patient, "token": str, "url": str}, ...]
    """
    patients = db.query(Patient).filter(
        Patient.exam_date == exam_date,
        Patient.is_active == True
    ).all()
    
    result = []
    for patient in patients:
        token = generate_checkin_token(patient.id, exam_date)
        url = generate_checkin_url(patient.id, exam_date, base_url)
        
        result.append({
            "patient": patient,
            "token": token,
            "url": url,
        })
    
    return result
