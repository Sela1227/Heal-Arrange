# -*- coding: utf-8 -*-
"""
QR Code 服務 - 病人自助報到
"""

import qrcode
import io
import base64
import hashlib
import hmac
from datetime import date, datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session

from ..config import settings
from ..models.patient import Patient


def generate_checkin_token(patient_id: int, exam_date: date) -> str:
    """
    產生報到 Token（防止偽造）
    
    格式：{patient_id}:{date}:{signature}
    """
    data = f"{patient_id}:{exam_date.isoformat()}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    return f"{patient_id}:{exam_date.isoformat()}:{signature}"


def verify_checkin_token(token: str) -> Optional[Dict]:
    """
    驗證報到 Token
    
    Returns:
        {"patient_id": int, "exam_date": date} or None
    """
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        
        patient_id = int(parts[0])
        exam_date = date.fromisoformat(parts[1])
        provided_signature = parts[2]
        
        # 驗證簽名
        data = f"{patient_id}:{exam_date.isoformat()}"
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        if provided_signature != expected_signature:
            return None
        
        # 檢查日期是否為今天
        if exam_date != date.today():
            return None
        
        return {
            "patient_id": patient_id,
            "exam_date": exam_date,
        }
    
    except Exception:
        return None


def generate_checkin_url(patient_id: int, exam_date: date, base_url: str = None) -> str:
    """產生報到 URL"""
    token = generate_checkin_token(patient_id, exam_date)
    
    if base_url is None:
        base_url = settings.LINE_REDIRECT_URI.rsplit("/", 2)[0]  # 取得 base URL
    
    return f"{base_url}/checkin/{token}"


def generate_qrcode_base64(data: str, box_size: int = 10, border: int = 2) -> str:
    """
    產生 QR Code 並回傳 Base64 編碼
    
    Args:
        data: QR Code 內容
        box_size: 每格像素大小
        border: 邊框格數
    
    Returns:
        Base64 編碼的 PNG 圖片
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 轉換為 Base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()


def generate_patient_qrcode(
    patient_id: int,
    exam_date: date,
    base_url: str = None,
) -> Dict:
    """
    產生病人報到 QR Code
    
    Returns:
        {
            "url": str,
            "qrcode_base64": str,
            "token": str,
        }
    """
    url = generate_checkin_url(patient_id, exam_date, base_url)
    qrcode_base64 = generate_qrcode_base64(url)
    token = generate_checkin_token(patient_id, exam_date)
    
    return {
        "url": url,
        "qrcode_base64": qrcode_base64,
        "token": token,
    }


def get_patient_qrcodes(
    db: Session,
    exam_date: date = None,
    base_url: str = None,
) -> list:
    """
    取得當日所有病人的 QR Code
    
    Returns:
        List of {patient, qrcode_info}
    """
    if exam_date is None:
        exam_date = date.today()
    
    patients = db.query(Patient).filter(
        Patient.exam_date == exam_date,
        Patient.is_active == True,
    ).order_by(Patient.chart_no).all()
    
    results = []
    for patient in patients:
        qrcode_info = generate_patient_qrcode(patient.id, exam_date, base_url)
        results.append({
            "patient": patient,
            "qrcode": qrcode_info,
        })
    
    return results
