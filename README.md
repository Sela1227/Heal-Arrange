# 🚀 Phase 6 部署包

## 📦 包含內容

### 需要 **替換** 的檔案
- `app/main.py` - 加入新路由

### 需要 **新增** 的檔案

```
app/
├── services/
│   ├── __init__.py         ← 替換（加入新模組）
│   ├── line_notify.py      ← 新增
│   ├── wait_time.py        ← 新增
│   ├── qrcode_service.py   ← 新增
│   └── tracking.py         ← 替換（整合推播）
│
├── routers/
│   ├── __init__.py         ← 替換（加入新模組）
│   ├── checkin.py          ← 新增
│   └── qrcode.py           ← 新增
│
├── templates/
│   ├── patient/            ← 新增整個資料夾
│   │   ├── checkin.html
│   │   ├── checkin_success.html
│   │   ├── checkin_error.html
│   │   └── partials/
│   │       └── status_card.html
│   │
│   ├── admin/
│   │   ├── index.html          ← 替換（新增 QR Code 入口）
│   │   ├── qrcode_list.html    ← 新增
│   │   ├── qrcode_print.html   ← 新增
│   │   └── qrcode_single.html  ← 新增
│   │
│   └── partials/
│       └── station_cards.html  ← 替換（含等候時間）
│
└── config.py               ← 替換（新增 LINE 推播設定）
```

---

## 🔧 部署步驟

### Step 1：更新 requirements.txt

在你的 `requirements.txt` 加入：

```
qrcode[pil]==7.4.2
Pillow>=9.0.0
```

### Step 2：複製檔案

解壓縮後，將 `app/` 資料夾內的檔案複製到你的專案：

```bash
# 在你的專案根目錄執行
cp -r phase6-deploy/app/* app/
```

或手動複製：
1. `app/main.py` → 替換
2. `app/config.py` → 替換
3. `app/services/*` → 複製所有檔案
4. `app/routers/*` → 複製所有檔案
5. `app/templates/patient/` → 整個資料夾複製
6. `app/templates/admin/*.html` → 複製
7. `app/templates/partials/station_cards.html` → 替換

### Step 3：確認環境變數

Railway 環境變數應包含：

```
LINE_CHANNEL_ACCESS_TOKEN=GTpcOYr8HV9J+KsrP2EMGD052BJq25iNeKmqJ1PZYBObZPfFAZQ14fl7luFkjs38nsENEIXiyweHJYK2k3TqGkUXskTAGtOmzENdGxsvKkqR0A6N+4UHRSSwkHD2O4lqrpLkfMdT3LiOxMvr5UNouwdB04t89/1O/w1cDnyilFU=
```

### Step 4：部署

```bash
git add .
git commit -m "Phase 6: QR Code 報到 + LINE 推播 + 等候時間"
git push
```

---

## ✅ 驗證

部署成功後：

1. **QR Code 管理**
   - 進入管理後台
   - 點擊「📱 QR Code 管理」
   - 應該能看到當日病人列表

2. **自助報到**
   - 點擊任一病人的「檢視」
   - 用手機掃描 QR Code
   - 應該能看到報到頁面

3. **LINE 推播**（需要專員先加入官方帳號好友）
   - 調度台指派專員給病人
   - 專員應收到 LINE 通知

---

## 📱 新功能說明

### QR Code 報到
- 路徑：`/admin/qrcode`
- 功能：產生、列印病人報到 QR Code
- 病人掃碼後可自助報到

### 等候時間預估
- 顯示在調度台的檢查站卡片
- 根據等候人數 × 平均檢查時間計算

### LINE 推播
- 專員被指派病人時收到通知
- 下一站指派時收到通知
- 使用 LINE Messaging API Flex Message

---

## ⚠️ 注意事項

1. **LINE 推播需要專員加入官方帳號**
   - 專員需先加入 Messaging API 對應的官方帳號為好友
   - 否則無法收到推播

2. **QR Code 只在當天有效**
   - 每天的 QR Code Token 都不同
   - 隔天掃描會顯示「過期」

3. **等候時間是預估值**
   - 根據歷史數據計算
   - 實際時間可能有差異
