# -*- coding: utf-8 -*-
"""
認證路由 - LINE 登入/登出
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.auth import (
    get_line_login_url,
    exchange_code_for_token,
    get_line_profile,
    get_or_create_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["認證"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登入頁面"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "line_login_url": get_line_login_url(),
    })


@router.get("/callback")
async def line_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db),
):
    """LINE Login 回調"""
    if error:
        return RedirectResponse(url="/auth/login?error=" + error)
    
    if not code:
        return RedirectResponse(url="/auth/login?error=no_code")
    
    try:
        # 換取 token
        token_data = await exchange_code_for_token(code)
        access_token = token_data["access_token"]
        
        # 取得用戶資料
        line_profile = await get_line_profile(access_token)
        
        # 建立或更新用戶
        user = get_or_create_user(db, line_profile)
        
        # 建立 JWT
        jwt_token = create_access_token(user.id)
        
        # 設定 Cookie 並跳轉
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            max_age=60 * 60 * 24 * 7,  # 7 天
            samesite="lax",
        )
        
        return response
        
    except Exception as e:
        print(f"LINE callback error: {e}")
        return RedirectResponse(url="/auth/login?error=callback_failed")


@router.get("/logout")
async def logout(request: Request):
    """登出"""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
