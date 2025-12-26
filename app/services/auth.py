# -*- coding: utf-8 -*-
"""
認證服務 - LINE Login + JWT
新用戶角色由系統設定決定
"""

import httpx
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from urllib.parse import urlencode
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.user import User, UserRole


# ===================================
# JWT 設定
# ===================================

JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7


def create_access_token(user_id: int) -> str:
    """建立 JWT Token"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict]:
    """解碼 JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ===================================
# LINE Login 相關函數
# ===================================

def get_line_login_url(state: str = "default") -> str:
    """產生 LINE Login URL"""
    params = {
        "response_type": "code",
        "client_id": settings.LINE_CHANNEL_ID,
        "redirect_uri": settings.LINE_REDIRECT_URI,
        "state": state,
        "scope": "profile openid",
    }
    return f"https://access.line.me/oauth2/v2.1/authorize?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> Dict:
    """用 authorization code 換取 access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.line.me/oauth2/v2.1/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.LINE_REDIRECT_URI,
                "client_id": settings.LINE_CHANNEL_ID,
                "client_secret": settings.LINE_CHANNEL_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="LINE 認證失敗")
        
        return response.json()


async def get_line_profile(access_token: str) -> Dict:
    """取得 LINE 使用者資料"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.line.me/v2/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="無法取得 LINE 資料")
        
        return response.json()


def get_or_create_user(db: Session, line_profile: Dict) -> User:
    """取得或建立使用者（新用戶角色由系統設定決定）"""
    from ..services.settings import get_default_user_role
    
    line_user_id = line_profile.get("userId")
    display_name = line_profile.get("displayName", "未知")
    picture_url = line_profile.get("pictureUrl")
    
    # ⚠️ 使用 line_id 欄位（匹配現有資料庫）
    user = db.query(User).filter(User.line_id == line_user_id).first()
    
    if user:
        # 更新資料
        user.display_name = display_name
        if picture_url:
            user.picture_url = picture_url
        user.last_login_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user
    
    # ========================================
    # 建立新使用者 - 角色由系統設定決定
    # ========================================
    default_role = get_default_user_role(db)
    
    user = User(
        line_id=line_user_id,  # ⚠️ 使用 line_id
        display_name=display_name,
        picture_url=picture_url,
        role=default_role,
        last_login_at=datetime.utcnow(),  # ⚠️ 使用 last_login_at
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


# ===================================
# 從 Cookie 取得當前用戶
# ===================================

def get_current_user(request: Request, db: Session) -> Optional[User]:
    """從 JWT Cookie 取得當前使用者"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id = payload.get("user_id")
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


# ===================================
# 角色檢查
# ===================================

def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """要求管理員權限"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return user


def require_dispatcher(request: Request, db: Session = Depends(get_db)) -> User:
    """要求調度員權限（管理員、組長也可以）"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if not user.can_access_dispatcher():
        raise HTTPException(status_code=403, detail="需要調度員權限")
    return user


def require_coordinator(request: Request, db: Session = Depends(get_db)) -> User:
    """要求專員權限（管理員、組長也可以）"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if not user.can_access_coordinator():
        raise HTTPException(status_code=403, detail="需要專員權限")
    return user


def require_role(*roles: str):
    """動態角色檢查"""
    def dependency(request: Request, db: Session = Depends(get_db)) -> User:
        user = get_current_user(request, db)
        if not user:
            raise HTTPException(status_code=401, detail="請先登入")
        
        # 管理員可以存取所有
        if user.role == UserRole.ADMIN.value:
            return user
        
        # 組長可以存取調度員和專員
        if user.role == UserRole.LEADER.value:
            if "dispatcher" in roles or "coordinator" in roles or "leader" in roles:
                return user
        
        # 檢查具體角色
        if user.role in roles:
            return user
        
        raise HTTPException(status_code=403, detail="權限不足")
    
    return dependency
