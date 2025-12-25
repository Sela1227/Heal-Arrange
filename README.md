# Phase 7 功能更新 - PDF 報表 & QR Code 報到

## 📦 包含檔案

```
phase7-features/
├── app/
│   ├── main.py                      # 更新版（含 checkin 路由）
│   ├── services/
│   │   ├── pdf_report.py            # 新增：PDF 報表服務
│   │   └── checkin.py               # 新增：QR Code 報到服務
│   ├── routers/
│   │   ├── reports.py               # 更新版（含 PDF 匯出）
│   │   └── checkin.py               # 新增：報到路由
│   └── templates/
│       ├── admin/
│       │   └── qrcodes.html         # 新增：QR Code 管理頁
│       └── checkin/
│           └── result.html          # 新增：報到結果頁
├── requirements.txt                  # 更新版（含新依賴）
├── ADMIN_PATCH.py                   # admin.py 需加入的程式碼
└── README.md                        # 本檔案
```

## 🚀 部署步驟

### 1. 更新 requirements.txt

新增以下依賴：
```
reportlab==4.0.8
qrcode[pil]==7.4.2
pillow==10.2.0
```

### 2. 複製新檔案

```bash
# 複製服務檔案
cp app/services/pdf_report.py   your-project/app/services/
cp app/services/checkin.py      your-project/app/services/

# 複製路由檔案
cp app/routers/reports.py       your-project/app/routers/
cp app/routers/checkin.py       your-project/app/routers/

# 複製模板檔案
mkdir -p your-project/app/templates/checkin
cp app/templates/admin/qrcodes.html    your-project/app/templates/admin/
cp app/templates/checkin/result.html   your-project/app/templates/checkin/

# 更新 main.py
cp app/main.py your-project/app/
```

### 3. 修改 admin.py

在 `app/routers/admin.py` 末尾加入以下程式碼：

```python
# ======================
# QR Code 報到管理
# ======================

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
```

### 4. 更新 services/__init__.py

加入：
```python
from . import pdf_report
from . import checkin
```

### 5. 更新管理後台首頁

在 `admin/index.html` 加入 QR Code 管理連結：

```html
<!-- QR Code 管理 -->
<a href="/admin/qrcodes" 
   class="bg-white rounded-xl shadow p-6 hover:shadow-lg transition group">
    <div class="flex items-center mb-4">
        <div class="text-4xl mr-4 group-hover:scale-110 transition">📱</div>
        <div>
            <h3 class="font-bold text-lg text-gray-800">QR Code 報到</h3>
            <p class="text-sm text-gray-500">產生與列印報到 QR Code</p>
        </div>
    </div>
</a>
```

### 6. 更新報表頁面

在 `admin/reports.html` 加入 PDF 匯出按鈕：

```html
<a href="/admin/reports/export/pdf?target_date={{ report_date }}"
   class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm">
    📄 匯出 PDF
</a>
```

## ✨ 新功能說明

### PDF 報表匯出

- **每日報表 PDF**: `/admin/reports/export/pdf?target_date=2025-01-01`
- **趨勢報表 PDF**: `/admin/reports/export/trend-pdf?days=7`

### QR Code 自助報到

- **管理頁面**: `/admin/qrcodes`
- **單一 QR Code 圖片**: `/checkin/api/qrcode/{patient_id}?exam_date=2025-01-01`
- **報到頁面**: `/checkin/{token}`（掃描 QR Code 後顯示）
- **報到狀態 API**: `/checkin/api/status/{patient_id}`

### 報到流程

1. 管理員在 `/admin/qrcodes` 列印病人 QR Code
2. 病人掃描 QR Code
3. 系統自動建立追蹤記錄，狀態設為「等候中」，位置設為「REG」（報到櫃檯）
4. 病人看到報到成功頁面

## 🔒 安全機制

- QR Code Token 包含 SHA256 簽名，無法偽造
- Token 與病人 ID、檢查日期、SECRET_KEY 綁定
- 只能在檢查當天報到
- 過期或未來的 Token 會被拒絕

## 📝 注意事項

1. 確保 `SECRET_KEY` 環境變數已設定（用於 Token 簽名）
2. PDF 報表使用英文標題（避免中文字型問題）
3. QR Code 圖片為 PNG 格式
4. 列印功能使用瀏覽器內建列印對話框
