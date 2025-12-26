# -*- coding: utf-8 -*-
"""
角色模擬服務 - 管理員可切換視角查看其他角色畫面
使用 Cookie 儲存模擬狀態（與專案的 JWT 認證方式一致）
"""

import json
import jwt
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response

from ..config import settings
from ..models.user import User, UserRole
from ..models.patient import Patient


# JWT 設定（與 auth.py 一致）
JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"
IMPERSONATE_COOKIE_NAME = "impersonate_token"
IMPERSONATE_EXPIRATION_HOURS = 4  # 模擬 4 小時後過期


# 角色顯示名稱對照（個管師 → 專員）
ROLE_DISPLAY_NAMES = {
    "admin": "管理員",
    "dispatcher": "調度員",
    "coordinator": "專員",  # 原本是「個管師」
    "patient": "病人",
    "pending": "待審核",
}


def get_role_display_name(role: str) -> str:
    """取得角色顯示名稱"""
    return ROLE_DISPLAY_NAMES.get(role, role)


def create_impersonate_token(
    admin_id: int,
    target_role: str,
    target_user_id: int = None,
    target_patient_id: int = None,
) -> str:
    """建立模擬 Token"""
    payload = {
        "admin_id": admin_id,
        "role": target_role,
        "user_id": target_user_id,
        "patient_id": target_patient_id,
        "started_at": datetime.utcnow().isoformat(),
        "exp": datetime.utcnow() + timedelta(hours=IMPERSONATE_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_impersonate_token(token: str) -> Optional[Dict]:
    """解碼模擬 Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_impersonation_status(request: Request) -> Dict[str, Any]:
    """
    從 Cookie 取得目前模擬狀態
    
    Returns:
        {
            "is_impersonating": bool,
            "role": str or None,
            "role_name": str or None,
            "user_id": int or None,
            "patient_id": int or None,
            "started_at": str or None,
            "admin_id": int or None,
        }
    """
    token = request.cookies.get(IMPERSONATE_COOKIE_NAME)
    
    if not token:
        return {
            "is_impersonating": False,
            "role": None,
            "role_name": None,
            "user_id": None,
            "patient_id": None,
            "started_at": None,
            "admin_id": None,
        }
    
    payload = decode_impersonate_token(token)
    
    if not payload:
        return {
            "is_impersonating": False,
            "role": None,
            "role_name": None,
            "user_id": None,
            "patient_id": None,
            "started_at": None,
            "admin_id": None,
        }
    
    role = payload.get("role")
    
    return {
        "is_impersonating": True,
        "role": role,
        "role_name": get_role_display_name(role),
        "user_id": payload.get("user_id"),
        "patient_id": payload.get("patient_id"),
        "started_at": payload.get("started_at"),
        "admin_id": payload.get("admin_id"),
    }


def set_impersonate_cookie(
    response: Response,
    admin_id: int,
    target_role: str,
    target_user_id: int = None,
    target_patient_id: int = None,
) -> None:
    """設定模擬 Cookie"""
    token = create_impersonate_token(
        admin_id=admin_id,
        target_role=target_role,
        target_user_id=target_user_id,
        target_patient_id=target_patient_id,
    )
    
    response.set_cookie(
        key=IMPERSONATE_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=IMPERSONATE_EXPIRATION_HOURS * 3600,
        samesite="lax",
    )


def clear_impersonate_cookie(response: Response) -> None:
    """清除模擬 Cookie"""
    response.delete_cookie(key=IMPERSONATE_COOKIE_NAME)


def get_effective_user(request: Request, db: Session) -> tuple:
    """
    取得有效用戶（考慮模擬狀態）
    
    用於替換原本的 get_current_user，讓各頁面自動支援模擬
    
    Returns:
        (user, patient, is_impersonating)
        - user: User 物件（調度員/專員）或 None
        - patient: Patient 物件（病人角色）或 None  
        - is_impersonating: 是否在模擬中
    """
    status = get_impersonation_status(request)
    
    if not status["is_impersonating"]:
        # 正常狀態，使用原本的認證
        from ..services.auth import get_current_user
        user = get_current_user(request, db)
        return user, None, False
    
    # 模擬中
    role = status["role"]
    
    if role == "patient":
        # 模擬病人
        patient_id = status["patient_id"]
        if patient_id:
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            return None, patient, True
        return None, None, True
    
    else:
        # 模擬調度員或專員
        user_id = status["user_id"]
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            return user, None, True
        return None, None, True


def get_impersonatable_users(db: Session, role: str) -> list:
    """
    取得可模擬的用戶列表
    
    Args:
        db: 資料庫 session
        role: 角色類型 (dispatcher/coordinator)
    
    Returns:
        用戶列表
    """
    return db.query(User).filter(
        User.role == role,
        User.is_active == True
    ).order_by(User.display_name).all()


def get_impersonatable_patients(db: Session, exam_date: date = None) -> list:
    """
    取得可模擬的病人列表（當日）
    
    Args:
        db: 資料庫 session
        exam_date: 檢查日期（預設今日）
    
    Returns:
        病人列表
    """
    if exam_date is None:
        exam_date = date.today()
    
    return db.query(Patient).filter(
        Patient.exam_date == exam_date,
        Patient.is_active == True
    ).order_by(Patient.name).all()


def get_impersonation_context(request: Request, db: Session) -> Dict[str, Any]:
    """
    取得模擬相關的模板上下文
    用於在 base.html 中顯示模擬提示條
    
    Returns:
        {
            "is_impersonating": bool,
            "impersonate_role": str,
            "impersonate_role_name": str,
            "impersonate_user_name": str,
        }
    """
    status = get_impersonation_status(request)
    
    if not status["is_impersonating"]:
        return {
            "is_impersonating": False,
            "impersonate_role": None,
            "impersonate_role_name": None,
            "impersonate_user_name": None,
        }
    
    # 取得被模擬者名稱
    user_name = "未知"
    
    if status["role"] == "patient":
        patient_id = status["patient_id"]
        if patient_id:
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if patient:
                user_name = patient.name
    else:
        user_id = status["user_id"]
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user_name = user.display_name or user.line_user_id
    
    return {
        "is_impersonating": True,
        "impersonate_role": status["role"],
        "impersonate_role_name": status["role_name"],
        "impersonate_user_name": user_name,
    }
