# -*- coding: utf-8 -*-
"""
認證服務 - LINE Login + JWT
"""

from datetime import datetime, timedelta
from typing import Optional
import httpx
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status

from ..config import settings
from ..models.user import User


# ======================
# LINE Login
# ======================

def get_line_login_url(state: str = "default") -> str:
    """取得 LINE 登入 URL"""
    params = {
        "response_type": "code",
        "client_id": settings.LINE_CHANNEL_ID,
        "redirect_uri": settings.LINE_REDIRECT_URI,
        "state": state,
        "scope": "profile openid",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://access.line.me/oauth2/v2.1/authorize?{query}"


async def exchange_code_for_token(code: str) -> dict:
    """用授權碼換取 access token"""
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LINE token exchange failed: {response.text}"
            )
        
        return response.json()


async def get_line_profile(access_token: str) -> dict:
    """取得 LINE 用戶資料"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.line.me/v2/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get LINE profile"
            )
        
        return response.json()


# ======================
# JWT Token
# ======================

def create_access_token(user_id: int) -> str:
    """建立 JWT Token"""
    expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """解碼 JWT Token，回傳 user_id"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None


# ======================
# 用戶管理
# ======================

def get_or_create_user(db: Session, line_profile: dict) -> User:
    """取得或建立用戶"""
    line_id = line_profile["userId"]
    
    user = db.query(User).filter(User.line_id == line_id).first()
    
    if user:
        # 更新資料
        user.display_name = line_profile.get("displayName", user.display_name)
        user.picture_url = line_profile.get("pictureUrl")
        user.last_login_at = datetime.utcnow()
        db.commit()
        return user
    
    # 建立新用戶
    user = User(
        line_id=line_id,
        display_name=line_profile.get("displayName", "未命名"),
        picture_url=line_profile.get("pictureUrl"),
        role="pending",  # 等待管理員授權
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def get_current_user(request: Request, db: Session) -> Optional[User]:
    """從 Cookie 取得目前登入的用戶"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    user_id = decode_access_token(token)
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None
    
    return user


def require_login(request: Request, db: Session) -> User:
    """要求登入（用於依賴注入）"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="請先登入"
        )
    return user


def require_role(user: User, allowed_roles: list) -> User:
    """檢查角色權限"""
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="權限不足"
        )
    return user
