# 🚀 Phase 6：通知與自助報到

## 📋 功能列表

### 6.1 LINE 推播通知 🔔
- 專員被指派病人時收到通知
- 下一站指派時收到通知（含預估等候時間）
- 設備故障提醒
- 使用 LINE Messaging API Flex Message

### 6.2 等候時間預估 ⏱️
- 根據等候人數 × 平均檢查時間計算
- 顯示在調度台檢查站卡片
- 顯示在自助報到頁面

### 6.3 病人自助報到 📱
- QR Code 生成與列印
- 病人掃碼自助報到
- 防偽造 Token 機制（HMAC 簽名）
- 報到成功顯示等候資訊

---

## 📁 檔案清單

```
phase6/
├── README.md
├── requirements_additions.txt    # 新增依賴
├── main_update.py               # main.py 更新說明
│
├── app/
│   ├── config.py                # 新增 LINE_CHANNEL_ACCESS_TOKEN
│   │
│   ├── services/
│   │   ├── __init__.py          # 更新匯出
│   │   ├── line_notify.py       # 🆕 LINE 推播服務
│   │   ├── wait_time.py         # 🆕 等候時間預估
│   │   ├── qrcode_service.py    # 🆕 QR Code 生成
│   │   └── tracking.py          # 更新：整合推播
│   │
│   ├── routers/
│   │   ├── __init__.py          # 更新匯出
│   │   ├── checkin.py           # 🆕 自助報到路由
│   │   └── qrcode.py            # 🆕 QR Code 管理路由
│   │
│   └── templates/
│       ├── admin/
│       │   ├── index.html       # 更新：新增 QR Code 入口
│       │   ├── qrcode_list.html # 🆕 QR Code 列表
│       │   ├── qrcode_print.html # 🆕 列印頁面
│       │   └── qrcode_single.html # 🆕 單一 QR Code
│       │
│       ├── patient/
│       │   ├── checkin.html     # 🆕 報到頁面
│       │   ├── checkin_success.html # 🆕 報到成功
│       │   ├── checkin_error.html # 🆕 報到錯誤
│       │   └── partials/
│       │       └── status_card.html # 🆕 狀態卡片
│       │
│       └── partials/
│           └── station_cards.html # 更新：含等候時間
```

---

## 🔧 安裝步驟

### 1. 新增依賴

在 `requirements.txt` 加入：
```
qrcode[pil]==7.4.2
Pillow>=9.0.0
```

### 2. 設定環境變數

在 Railway 新增：
```
LINE_CHANNEL_ACCESS_TOKEN=你的長期 Token
NOTIFY_ON_ASSIGNMENT=true
NOTIFY_ON_NEXT_STATION=true
NOTIFY_ON_EQUIPMENT_FAILURE=true
```

### 3. 複製檔案

```bash
# 複製服務
cp phase6/app/services/*.py app/services/

# 複製路由
cp phase6/app/routers/checkin.py app/routers/
cp phase6/app/routers/qrcode.py app/routers/

# 複製模板
cp -r phase6/app/templates/patient app/templates/
cp phase6/app/templates/admin/qrcode_*.html app/templates/admin/
cp phase6/app/templates/admin/index.html app/templates/admin/
cp phase6/app/templates/partials/station_cards.html app/templates/partials/
```

### 4. 更新 main.py

加入新路由：
```python
from .routers import checkin, qrcode

app.include_router(checkin.router)
app.include_router(qrcode.router)
```

### 5. 更新 services/__init__.py

```python
from . import line_notify
from . import wait_time
from . import qrcode_service
```

### 6. 更新 routers/__init__.py

```python
from . import checkin
from . import qrcode
```

### 7. 部署

```bash
git add .
git commit -m "Phase 6: LINE 推播 + 等候時間 + QR Code 報到"
git push
```

---

## 🔑 LINE Messaging API 設定

### 取得 Channel Access Token

1. 進入 [LINE Developers Console](https://developers.line.biz/)
2. 選擇你的 Provider
3. 選擇 Messaging API Channel（如果沒有需要新建）
4. 在 **Messaging API** 頁籤
5. 往下找到 **Channel access token (long-lived)**
6. 點擊 **Issue** 產生 Token
7. 複製 Token 設定到 Railway 環境變數

### 注意事項
- LINE Login 和 Messaging API 是兩個不同的 Channel
- 如果使用同一個 Channel，需要在 LINE Developers 啟用 Messaging API
- Channel Access Token 需要是 **long-lived** 版本

---

## 📱 使用方式

### QR Code 管理

1. 管理後台 → 📱 QR Code 管理
2. 選擇日期查看當日病人
3. 點擊「列印全部」一次列印所有 QR Code
4. 或點擊單一病人檢視/下載

### 病人自助報到

1. 病人收到印有 QR Code 的報到單
2. 用手機掃描 QR Code
3. 確認個人資料無誤後點擊「確認報到」
4. 系統顯示等候資訊

### LINE 推播

- 專員被指派病人 → 收到 LINE 通知
- 病人被指派下一站 → 專員收到通知
- 設備故障 → 相關人員收到通知

---

## ⚙️ 設定說明

| 環境變數 | 說明 | 預設值 |
|---------|------|--------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API Token | （必填） |
| `NOTIFY_ON_ASSIGNMENT` | 指派時發送通知 | true |
| `NOTIFY_ON_NEXT_STATION` | 下一站指派時通知 | true |
| `NOTIFY_ON_EQUIPMENT_FAILURE` | 設備故障時通知 | true |

---

## 🔒 安全機制

### QR Code Token
- 使用 HMAC-SHA256 簽名
- 包含病人 ID + 日期
- 只在當天有效
- 無法偽造

### 報到流程
1. 驗證 Token 簽名
2. 檢查日期是否為今天
3. 檢查病人是否存在
4. 建立追蹤記錄

---

## 📝 版本歷史

- **Phase 1-5**: 基礎追蹤系統
- **v5**: 組長角色 + 系統設定
- **Phase 6**: LINE 推播 + 等候時間 + QR Code 報到
