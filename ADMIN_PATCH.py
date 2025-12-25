# -*- coding: utf-8 -*-
"""
管理後台路由 - QR Code 管理功能
========================================
請將以下程式碼加入現有的 admin.py 檔案末尾
========================================
"""

# 請在 admin.py 開頭加入以下 import:
# from ..models.tracking import PatientTracking

# ======================
# QR Code 報到管理
# ======================

"""
將以下程式碼加入 admin.py 的路由部分：

@router.get("/qrcodes", response_class=HTMLResponse)
async def admin_qrcodes(
    request: Request,
    exam_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    '''QR Code 報到管理頁面'''
    from ..models.tracking import PatientTracking
    
    if exam_date:
        try:
            target_date = date.fromisoformat(exam_date)
        except:
            target_date = date.today()
    else:
        target_date = date.today()
    
    # 取得病人列表
    patients = db.query(Patient).filter(
        Patient.exam_date == target_date,
        Patient.is_active == True
    ).all()
    
    # 檢查報到狀態
    patient_list = []
    for patient in patients:
        tracking = db.query(PatientTracking).filter(
            PatientTracking.patient_id == patient.id,
            PatientTracking.exam_date == target_date
        ).first()
        
        patient_list.append({
            "patient": patient,
            "checked_in": tracking is not None,
            "tracking": tracking,
        })
    
    return templates.TemplateResponse("admin/qrcodes.html", {
        "request": request,
        "user": current_user,
        "exam_date": target_date,
        "patients": patient_list,
    })
"""

# 完整的 admin.py 補充路由程式碼
QRCODE_ROUTE_CODE = '''
@router.get("/qrcodes", response_class=HTMLResponse)
async def admin_qrcodes(
    request: Request,
    exam_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """QR Code 報到管理頁面"""
    from ..models.tracking import PatientTracking
    
    if exam_date:
        try:
            target_date = date.fromisoformat(exam_date)
        except:
            target_date = date.today()
    else:
        target_date = date.today()
    
    patients = db.query(Patient).filter(
        Patient.exam_date == target_date,
        Patient.is_active == True
    ).all()
    
    patient_list = []
    for patient in patients:
        tracking = db.query(PatientTracking).filter(
            PatientTracking.patient_id == patient.id,
            PatientTracking.exam_date == target_date
        ).first()
        
        patient_list.append({
            "patient": patient,
            "checked_in": tracking is not None,
            "tracking": tracking,
        })
    
    return templates.TemplateResponse("admin/qrcodes.html", {
        "request": request,
        "user": current_user,
        "exam_date": target_date,
        "patients": patient_list,
    })
'''
