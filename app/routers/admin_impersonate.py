# -*- coding: utf-8 -*-
"""
管理後台 - 角色模擬路由
========================================
請將以下程式碼加入現有的 admin.py 檔案
========================================
"""

# 在 admin.py 開頭加入以下 import:
# from ..services import impersonate as impersonate_service
# from ..models.patient import Patient

IMPERSONATE_ROUTES = '''
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
    from ..models.patient import Patient
    
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
    
    result = impersonate_service.start_impersonation(
        request=request,
        admin_user=current_user,
        target_role=role,
        target_user_id=user_id,
        target_patient_id=patient_id,
    )
    
    if result["success"]:
        return RedirectResponse(url=result["redirect_url"], status_code=302)
    else:
        # 失敗時返回模擬頁面
        return RedirectResponse(url="/admin/impersonate?error=" + result["message"], status_code=302)


@router.post("/impersonate/end")
async def end_impersonate(
    request: Request,
    db: Session = Depends(get_db),
):
    """結束角色模擬"""
    from ..services import impersonate as impersonate_service
    
    # 不需要驗證權限，只要在模擬中就可以結束
    result = impersonate_service.end_impersonation(request)
    
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/impersonate/status")
async def get_impersonate_status(
    request: Request,
    db: Session = Depends(get_db),
):
    """取得模擬狀態 (API)"""
    from ..services import impersonate as impersonate_service
    
    return impersonate_service.get_impersonation_status(request)
'''

print("請將上述程式碼加入 admin.py")
