# -*- coding: utf-8 -*-
"""
認證服務 - 權限檢查
"""

from typing import Optional, List
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, Permission


def get_current_user(request: Request, db: Session) -> Optional[User]:
    """從 Session 取得當前使用者"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None
    
    return user


def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    """要求登入"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    return user


def require_approved(request: Request, db: Session = Depends(get_db)) -> User:
    """要求已核准的帳號（有任何權限）"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if user.is_pending:
        raise HTTPException(status_code=403, detail="帳號尚未核准，請等待管理員審核")
    return user


# ===== 權限檢查 Dependency =====

def require_permission(*permissions: str):
    """
    建立權限檢查 Dependency
    
    使用方式：
        @router.get("/admin")
        async def admin_page(user: User = Depends(require_permission("admin"))):
            ...
        
        # 要求任一權限
        @router.get("/manage")
        async def manage_page(user: User = Depends(require_permission("admin", "dispatcher"))):
            ...
    """
    def dependency(request: Request, db: Session = Depends(get_db)) -> User:
        user = get_current_user(request, db)
        if not user:
            raise HTTPException(status_code=401, detail="請先登入")
        
        if not user.has_any_permission(*permissions):
            permission_names = {
                "admin": "管理員",
                "dispatcher": "調度員", 
                "coordinator": "個管師",
            }
            required = "、".join(permission_names.get(p, p) for p in permissions)
            raise HTTPException(
                status_code=403, 
                detail=f"需要以下任一權限：{required}"
            )
        
        return user
    
    return dependency


# ===== 便捷權限檢查函數 =====

def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """要求管理員權限"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return user


def require_dispatcher(request: Request, db: Session = Depends(get_db)) -> User:
    """要求調度員權限（管理員也可以）"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if not user.has_any_permission(Permission.DISPATCHER.value, Permission.ADMIN.value):
        raise HTTPException(status_code=403, detail="需要調度員權限")
    return user


def require_coordinator(request: Request, db: Session = Depends(get_db)) -> User:
    """要求個管師權限（管理員也可以）"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if not user.has_any_permission(Permission.COORDINATOR.value, Permission.ADMIN.value):
        raise HTTPException(status_code=403, detail="需要個管師權限")
    return user


def require_admin_or_dispatcher(request: Request, db: Session = Depends(get_db)) -> User:
    """要求管理員或調度員權限"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if not user.has_any_permission(Permission.ADMIN.value, Permission.DISPATCHER.value):
        raise HTTPException(status_code=403, detail="需要管理員或調度員權限")
    return user


# ===== 角色轉換輔助（向後兼容）=====

def migrate_role_to_permissions(user: User) -> List[str]:
    """
    將舊的 role 轉換為新的 permissions
    用於資料庫遷移
    """
    role = user.role
    
    if role == "admin":
        return [Permission.ADMIN.value, Permission.DISPATCHER.value, Permission.COORDINATOR.value]
    elif role == "dispatcher":
        return [Permission.DISPATCHER.value]
    elif role == "coordinator":
        return [Permission.COORDINATOR.value]
    else:  # pending or other
        return []
