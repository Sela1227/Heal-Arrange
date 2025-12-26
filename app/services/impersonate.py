# -*- coding: utf-8 -*-
"""
角色模擬服務 - 管理員可切換視角查看其他角色畫面
使用 Cookie 儲存模擬狀態
"""

import jwt
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response

from ..config import settings
from ..models.user import User, UserRole, get_role_display_name
from ..models.patient import Patient


# JWT 設定
JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"
IMPERSONATE_COOKIE_NAME = "impersonate_token"
IMPERSONATE_EXPIRATION_HOURS = 4


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
    """取得目前模擬狀態"""
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


def start_impersonation(
    request: Request,
    admin_id: int,
    target_role: str,
    target_user_id: int = None,
    target_patient_id: int = None,
) -> Dict[str, Any]:
    """
    開始模擬（回傳結果，由路由設定 Cookie）
    
    Returns:
        {
            "success": bool,
            "token": str,
            "redirect_url": str,
            "error": str or None,
        }
    """
    # 驗證角色
    valid_roles = ["dispatcher", "coordinator", "leader", "patient"]
    if target_role not in valid_roles:
        return {
            "success": False,
            "token": None,
            "redirect_url": "/admin/impersonate",
            "error": "無效的角色",
        }
    
    # 建立 Token
    token = create_impersonate_token(
        admin_id=admin_id,
        target_role=target_role,
        target_user_id=target_user_id,
        target_patient_id=target_patient_id,
    )
    
    # 決定跳轉 URL
    redirect_urls = {
        "dispatcher": "/dispatcher",
        "coordinator": "/coordinator",
        "leader": "/dispatcher",  # 組長預設去調度台
        "patient": "/patient/dashboard",
    }
    
    return {
        "success": True,
        "token": token,
        "redirect_url": redirect_urls.get(target_role, "/admin"),
        "error": None,
    }


def end_impersonation(request: Request) -> Dict[str, Any]:
    """結束模擬"""
    return {
        "success": True,
        "redirect_url": "/admin",
    }


def set_impersonate_cookie(response: Response, token: str) -> None:
    """設定模擬 Cookie"""
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


def get_impersonatable_users(db: Session, role: str) -> List[User]:
    """取得可模擬的用戶列表"""
    return db.query(User).filter(
        User.role == role,
        User.is_active == True
    ).order_by(User.display_name).all()


def get_impersonatable_patients(db: Session, exam_date: date = None) -> List[Patient]:
    """取得可模擬的病人列表"""
    if exam_date is None:
        exam_date = date.today()
    
    return db.query(Patient).filter(
        Patient.exam_date == exam_date,
        Patient.is_active == True
    ).order_by(Patient.name).all()


def get_impersonation_context(request: Request, db: Session) -> Dict[str, Any]:
    """取得模擬相關的模板上下文"""
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
                user_name = user.display_name or user.line_id
    
    return {
        "is_impersonating": True,
        "impersonate_role": status["role"],
        "impersonate_role_name": status["role_name"],
        "impersonate_user_name": user_name,
    }
