# -*- coding: utf-8 -*-
"""
角色模擬服務 - 管理員可切換視角查看其他角色畫面
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from starlette.requests import Request

from ..models.user import User, UserRole
from ..models.patient import Patient


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


def start_impersonation(
    request: Request,
    admin_user: User,
    target_role: str,
    target_user_id: int = None,
    target_patient_id: int = None,
) -> Dict[str, Any]:
    """
    開始角色模擬
    
    Args:
        request: HTTP 請求（用於存取 session）
        admin_user: 原始管理員用戶
        target_role: 目標角色 (dispatcher/coordinator/patient)
        target_user_id: 目標用戶 ID（調度員/專員）
        target_patient_id: 目標病人 ID（病人角色）
    
    Returns:
        {"success": bool, "message": str, "redirect_url": str}
    """
    # 驗證管理員權限
    if admin_user.role != UserRole.ADMIN.value:
        return {
            "success": False,
            "message": "只有管理員可以使用角色模擬功能",
            "redirect_url": None,
        }
    
    # 驗證目標角色
    valid_roles = ["dispatcher", "coordinator", "patient"]
    if target_role not in valid_roles:
        return {
            "success": False,
            "message": f"無效的角色：{target_role}",
            "redirect_url": None,
        }
    
    # 設定 session
    request.session["impersonating"] = True
    request.session["impersonate_role"] = target_role
    request.session["impersonate_user_id"] = target_user_id
    request.session["impersonate_patient_id"] = target_patient_id
    request.session["original_admin_id"] = admin_user.id
    request.session["impersonate_started_at"] = datetime.utcnow().isoformat()
    
    # 決定跳轉 URL
    redirect_urls = {
        "dispatcher": "/dispatcher",
        "coordinator": "/coordinator",
        "patient": "/patient/dashboard",
    }
    
    return {
        "success": True,
        "message": f"已開始模擬 {get_role_display_name(target_role)}",
        "redirect_url": redirect_urls.get(target_role, "/"),
    }


def end_impersonation(request: Request) -> Dict[str, Any]:
    """
    結束角色模擬
    
    Returns:
        {"success": bool, "message": str}
    """
    if not request.session.get("impersonating"):
        return {
            "success": False,
            "message": "目前沒有在模擬中",
        }
    
    # 清除模擬相關 session
    keys_to_remove = [
        "impersonating",
        "impersonate_role",
        "impersonate_user_id",
        "impersonate_patient_id",
        "original_admin_id",
        "impersonate_started_at",
    ]
    
    for key in keys_to_remove:
        request.session.pop(key, None)
    
    return {
        "success": True,
        "message": "已結束模擬，返回管理員身份",
    }


def get_impersonation_status(request: Request) -> Dict[str, Any]:
    """
    取得目前模擬狀態
    
    Returns:
        {
            "is_impersonating": bool,
            "role": str or None,
            "role_name": str or None,
            "user_id": int or None,
            "patient_id": int or None,
            "started_at": str or None,
        }
    """
    if not request.session.get("impersonating"):
        return {
            "is_impersonating": False,
            "role": None,
            "role_name": None,
            "user_id": None,
            "patient_id": None,
            "started_at": None,
        }
    
    role = request.session.get("impersonate_role")
    
    return {
        "is_impersonating": True,
        "role": role,
        "role_name": get_role_display_name(role),
        "user_id": request.session.get("impersonate_user_id"),
        "patient_id": request.session.get("impersonate_patient_id"),
        "started_at": request.session.get("impersonate_started_at"),
        "original_admin_id": request.session.get("original_admin_id"),
    }


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
