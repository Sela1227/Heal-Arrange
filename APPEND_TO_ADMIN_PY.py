# -*- coding: utf-8 -*-
"""
========================================
角色模擬路由
========================================
請將以下程式碼複製到 app/routers/admin.py 檔案的最後
========================================
"""

# ======================
# 角色模擬功能
# ======================

@router.get("/impersonate", response_class=HTMLResponse)
async def admin_impersonate(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """角色模擬選擇頁面"""
    from ..services import impersonate as impersonate_service
    
    # 取得可模擬的用戶
    dispatchers = impersonate_service.get_impersonatable_users(db, "dispatcher")
    coordinators = impersonate_service.get_impersonatable_users(db, "coordinator")
    patients = impersonate_service.get_impersonatable_patients(db)
    
    # 目前模擬狀態
    status = impersonate_service.get_impersonation_status(request)
    
    return templates.TemplateResponse("admin/impersonate.html", {
        "request": request,
        "user": current_user,
        "dispatchers": dispatchers,
        "coordinators": coordinators,
        "patients": patients,
        "impersonate_status": status,
        "today": date.today(),
    })


@router.post("/impersonate/start")
async def start_impersonate(
    request: Request,
    role: str = Form(...),
    user_id: int = Form(None),
    patient_id: int = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """開始角色模擬"""
    from ..services import impersonate as impersonate_service
    
    # 驗證目標角色
    valid_roles = ["dispatcher", "coordinator", "patient"]
    if role not in valid_roles:
        return RedirectResponse(url="/admin/impersonate?error=invalid_role", status_code=302)
    
    # 決定跳轉 URL
    redirect_urls = {
        "dispatcher": "/dispatcher",
        "coordinator": "/coordinator",
        "patient": "/patient/dashboard",
    }
    
    redirect_url = redirect_urls.get(role, "/admin")
    
    # 建立回應並設定 Cookie
    response = RedirectResponse(url=redirect_url, status_code=302)
    
    impersonate_service.set_impersonate_cookie(
        response=response,
        admin_id=current_user.id,
        target_role=role,
        target_user_id=user_id,
        target_patient_id=patient_id,
    )
    
    return response


@router.post("/impersonate/end")
async def end_impersonate(
    request: Request,
    db: Session = Depends(get_db),
):
    """結束角色模擬"""
    from ..services import impersonate as impersonate_service
    
    # 建立回應並清除 Cookie
    response = RedirectResponse(url="/admin", status_code=302)
    impersonate_service.clear_impersonate_cookie(response)
    
    return response


@router.get("/impersonate/status")
async def get_impersonate_status_api(
    request: Request,
    db: Session = Depends(get_db),
):
    """取得模擬狀態 (API)"""
    from ..services import impersonate as impersonate_service
    
    return impersonate_service.get_impersonation_status(request)
