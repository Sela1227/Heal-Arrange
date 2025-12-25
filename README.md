# 🏥 高檢病人動態系統 (Heal-Arrange) 完整技術文檔

> **版本**：v1.0  
> **最後更新**：2025-12-25  
> **開發者**：Sela (彰濱秀傳放射腫瘤科) & Claude AI  
> **部署平台**：Railway (PostgreSQL + FastAPI)

---

## 📋 目錄

1. [專案概述](#1-專案概述)
2. [系統架構](#2-系統架構)
3. [功能詳細說明](#3-功能詳細說明)
4. [程式結構](#4-程式結構)
5. [資料庫設計](#5-資料庫設計)
6. [核心子程式說明](#6-核心子程式說明)
7. [API 端點一覽](#7-api-端點一覽)
8. [部署與設定](#8-部署與設定)
9. [開發過程遇到的問題與解決方案](#9-開發過程遇到的問題與解決方案)
10. [待開發功能](#10-待開發功能)
11. [維護指南](#11-維護指南)

---

## 1. 專案概述

### 1.1 專案背景

彰化秀傳高級健檢中心需要一套即時病人追蹤與調度系統，用於：
- 追蹤病人在各檢查站的位置與狀態
- 協調個管師與病人的配對
- 監控設備狀態與故障回報
- 統計分析每日營運數據

### 1.2 系統名稱

| 項目 | 內容 |
|------|------|
| 中文名稱 | 高檢病人動態系統 |
| 英文名稱 | Heal-Arrange |
| 全稱 | Chang Bing Show Chwan High-End Checkup Patient Tracking |

### 1.3 使用者角色

| 角色 | 英文 | 人數 | 使用裝置 | 主要功能 |
|------|------|------|----------|----------|
| 管理員 | admin | 1-2 | 電腦 | 系統管理、帳號審核、所有功能 |
| 調度員 | dispatcher | 1-2 | 固定電腦 | 病人指派、即時監控、報表 |
| 個管師 | coordinator | ~15 | 手機 | 陪同病人、狀態回報 |
| 待審核 | pending | - | - | 新註冊，等待審核 |

### 1.4 權限系統

採用**多權限制**，一個用戶可同時擁有多個角色權限：

```python
permissions = ["admin", "dispatcher", "coordinator"]
```

---

## 2. 系統架構

### 2.1 技術棧

| 層級 | 技術 | 說明 |
|------|------|------|
| 後端框架 | FastAPI | Python 3.12，高效能非同步框架 |
| 資料庫 | PostgreSQL | Railway 託管，支援 JSON 欄位 |
| ORM | SQLAlchemy | 物件關聯映射 |
| 前端模板 | Jinja2 | 伺服器端渲染 |
| CSS 框架 | TailwindCSS | CDN 引入，快速樣式開發 |
| 即時更新 | HTMX | 無需 JavaScript 的 AJAX |
| 圖表 | Chart.js | 效能儀表板視覺化 |
| 認證 | LINE Login | OAuth 2.0 |
| Session | JWT Cookie | 7 天有效期 |

### 2.2 系統流程圖

```
┌─────────────┐     LINE Login      ┌─────────────┐
│   使用者    │ ──────────────────> │  LINE API   │
└─────────────┘                     └──────┬──────┘
                                           │
                                           ▼
┌─────────────┐     JWT Cookie      ┌─────────────┐
│   瀏覽器    │ <─────────────────> │   FastAPI   │
└─────────────┘                     └──────┬──────┘
                                           │
                                           ▼
                                    ┌─────────────┐
                                    │ PostgreSQL  │
                                    └─────────────┘
```

### 2.3 HTMX 即時更新機制

```html
<!-- 調度員頁面：每 5 秒刷新病人列表 -->
<div hx-get="/dispatcher/api/patients" 
     hx-trigger="every 5s" 
     hx-swap="innerHTML">
</div>

<!-- 個管師頁面：每 3 秒刷新通知 -->
<div hx-get="/coordinator/api/notifications" 
     hx-trigger="every 3s">
</div>
```

---

## 3. 功能詳細說明

### 3.1 Phase 1：基礎架構 ✅

| 功能 | 說明 |
|------|------|
| FastAPI 專案結構 | 模組化的路由、服務、模型分層 |
| PostgreSQL 連線 | Railway 託管，自動 SSL |
| SQLAlchemy ORM | 資料模型定義與關聯 |
| LINE Login 整合 | OAuth 2.0 認證流程 |
| JWT Session | Cookie-based，7 天有效 |
| Railway 部署 | Dockerfile + railway.toml |

### 3.2 Phase 2：核心追蹤功能 ✅

#### 調度員主控台 `/dispatcher`

- **今日病人列表**：顯示所有今日預約病人
- **個管師指派**：下拉選單一鍵指派
- **下一站指派**：指定病人的下一個檢查站
- **檢查站狀態卡片**：顯示每站等候/檢查中人數
- **HTMX 即時刷新**：每 5 秒自動更新

#### 個管師頁面 `/coordinator`

- **我的病人資訊**：顯示目前負責的病人
- **大按鈕狀態回報**：
  - 📍 到達（arrive）
  - 🔬 開始檢查（start）
  - ✅ 完成（complete）
- **今日歷程記錄**：該病人的操作歷史
- **通知即時更新**：每 3 秒檢查新通知

### 3.3 Phase 3：設備與資料管理 ✅

#### 設備管理 `/admin/equipment`

- 設備列表與狀態（正常/警告/故障）
- 故障回報與修復操作
- 依檢查站自動初始化設備
- 操作日誌記錄

#### 檢查項目管理 `/admin/exams`

- 新增/編輯/刪除檢查站
- 檢查時間設定
- 批次初始化 10 個預設項目

#### 病人管理 `/admin/patients`

- 手動新增病人
- CSV 批次匯入
- CSV 模板下載

### 3.4 Phase 4：故障回報系統 ✅

#### 調度員端

- 故障警示橫幅（紅色背景，即時刷新）
- 設備故障回報表單
- 檢查站卡片故障標示（紅色邊框）

#### 個管師端

- 目前位置設備回報
- 故障警示通知

#### 登入體驗優化

- 401 未授權 → 自動跳轉登入頁
- 403 無權限 → 跳轉登入頁並提示
- 通用錯誤頁面 `error.html`

### 3.5 Phase 5：統計報表 ✅

#### 報表首頁 `/admin/reports`

- 每日摘要統計卡片（總人數、完成率、設備狀態）
- 檢查站統計表
- 個管師工作統計
- 日期導航（前一天/後一天）
- CSV 匯出

#### 歷史查詢 `/admin/reports/history`

- 日期範圍篩選
- 檢查站篩選
- 操作記錄詳細列表

#### 趨勢報表 `/admin/reports/trend`

- 7/14/30 天選擇
- CSS 長條圖視覺化
- 每日詳細數據表格

### 3.6 Phase 6：進階功能 ✅

#### 操作日誌 (Audit Log)

- 記錄所有重要操作
- 包含操作者、目標、IP、User Agent
- 可查詢歷史記錄

#### 資料備份

- CSV 匯出（病人、檢查項目、設備）
- JSON 完整備份
- 一鍵下載

#### 效能儀表板

- Chart.js 圖表視覺化
- 即時 KPI 卡片
- 檢查站負載圖表

#### 等候時間預估

- 基於歷史數據計算
- 考慮目前排隊人數
- 顯示預估完成時間

---

## 4. 程式結構

### 4.1 目錄結構

```
Heal-Arrange/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口 + 異常處理
│   ├── config.py               # 環境變數設定
│   ├── database.py             # 資料庫連線與 Session
│   │
│   ├── models/                 # SQLAlchemy 資料模型
│   │   ├── __init__.py         # 模型匯出
│   │   ├── user.py             # 使用者（多權限系統）
│   │   ├── patient.py          # 病人
│   │   ├── exam.py             # 檢查項目
│   │   ├── tracking.py         # 追蹤相關（狀態、歷程、指派）
│   │   ├── equipment.py        # 設備與日誌
│   │   └── audit.py            # 操作日誌
│   │
│   ├── routers/                # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py             # LINE Login 認證
│   │   ├── home.py             # 首頁與導航
│   │   ├── admin.py            # 管理後台（含診斷端點）
│   │   ├── dispatcher.py       # 調度員功能
│   │   ├── coordinator.py      # 個管師功能
│   │   ├── equipment.py        # 設備 API
│   │   └── reports.py          # 報表功能
│   │
│   ├── services/               # 業務邏輯層
│   │   ├── __init__.py
│   │   ├── auth.py             # 認證服務（JWT、權限檢查）
│   │   ├── tracking.py         # 追蹤服務
│   │   ├── equipment.py        # 設備服務
│   │   ├── import_service.py   # CSV 匯入服務
│   │   ├── stats.py            # 統計服務
│   │   ├── audit.py            # 操作日誌服務
│   │   ├── backup.py           # 備份服務
│   │   ├── dashboard.py        # 儀表板服務
│   │   └── wait_time.py        # 等候時間預估
│   │
│   ├── templates/              # Jinja2 模板
│   │   ├── base.html           # 基礎模板（含導航）
│   │   ├── login.html          # 登入頁
│   │   ├── error.html          # 錯誤頁
│   │   ├── home.html           # 首頁
│   │   ├── admin/              # 管理後台頁面
│   │   │   ├── index.html
│   │   │   ├── users.html
│   │   │   ├── patients.html
│   │   │   ├── exams.html
│   │   │   ├── equipment.html
│   │   │   ├── reports.html
│   │   │   ├── history.html
│   │   │   ├── trend.html
│   │   │   ├── audit.html
│   │   │   ├── backup.html
│   │   │   └── dashboard.html
│   │   ├── dispatcher/
│   │   │   └── dashboard.html
│   │   ├── coordinator/
│   │   │   └── my_patient.html
│   │   └── partials/           # HTMX 部分更新模板
│   │       ├── patient_table.html
│   │       ├── station_cards.html
│   │       ├── notifications.html
│   │       ├── broken_alert.html
│   │       ├── report_summary.html
│   │       ├── station_stats.html
│   │       ├── coordinator_stats.html
│   │       └── kpi_cards.html
│   │
│   └── static/
│       └── css/
│
├── requirements.txt            # Python 依賴
├── Dockerfile                  # Docker 設定
├── railway.toml                # Railway 部署設定
└── README.md
```

### 4.2 模組職責

| 層級 | 職責 | 範例 |
|------|------|------|
| **routers/** | HTTP 請求處理、參數驗證 | 接收表單、回傳 HTML/JSON |
| **services/** | 業務邏輯、資料處理 | 權限檢查、狀態更新 |
| **models/** | 資料結構定義、ORM 映射 | SQLAlchemy 模型 |
| **templates/** | 前端呈現 | Jinja2 + TailwindCSS |

---

## 5. 資料庫設計

### 5.1 實際資料庫結構

> ⚠️ **重要**：以下為實際 PostgreSQL 資料庫欄位，程式碼中的 ORM 模型必須與此匹配

#### users 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK, 自動遞增 |
| line_id | VARCHAR(100) | LINE User ID (程式中用 `line_user_id`) |
| display_name | VARCHAR(100) | 顯示名稱 |
| picture_url | VARCHAR(500) | 頭像 URL |
| role | VARCHAR(20) | 狀態: pending/active/disabled |
| permissions | JSONB | 權限陣列: ["admin", "dispatcher"] |
| is_active | BOOLEAN | 是否啟用 |
| created_at | TIMESTAMP | 建立時間 |
| last_login_at | TIMESTAMP | 最後登入 (程式中用 `last_login`) |

#### patients 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK |
| chart_no | VARCHAR(20) | 病歷號 |
| name | VARCHAR(100) | 姓名 |
| package_code | VARCHAR(50) | 套餐代碼 |
| exam_date | DATE | 檢查日期 |
| is_active | BOOLEAN | 是否啟用 |
| is_completed | BOOLEAN | 是否完成 |
| notes | TEXT | 備註（可存檢查項目清單） |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

#### exams 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK |
| exam_code | VARCHAR(20) | 檢查代碼 (CT, MRI...) |
| name | VARCHAR(100) | 檢查名稱 |
| duration_min | INTEGER | 檢查時間（分鐘）|
| is_active | BOOLEAN | 是否啟用 |
| created_at | TIMESTAMP | 建立時間 |

#### patient_tracking 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK |
| patient_id | INTEGER | FK → patients |
| exam_date | DATE | 檢查日期 |
| current_location | VARCHAR(50) | 目前位置 |
| current_status | VARCHAR(20) | 狀態: waiting/in_exam/moving/completed |
| next_exam_code | VARCHAR(20) | 下一站代碼 |
| updated_at | TIMESTAMP | 更新時間 |
| updated_by | INTEGER | FK → users |

#### tracking_history 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK |
| patient_id | INTEGER | FK → patients |
| exam_date | DATE | 檢查日期 |
| location | VARCHAR(50) | 位置 |
| status | VARCHAR(20) | 狀態 |
| action | VARCHAR(20) | 動作: arrive/start/complete/assign |
| timestamp | TIMESTAMP | 時間戳 |
| operator_id | INTEGER | FK → users |
| notes | TEXT | 備註 |

#### coordinator_assignments 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK |
| exam_date | DATE | 檢查日期 |
| patient_id | INTEGER | FK → patients |
| coordinator_id | INTEGER | FK → users |
| assigned_at | TIMESTAMP | 指派時間 |
| assigned_by | INTEGER | FK → users |
| is_active | BOOLEAN | 是否生效 |

#### equipment 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK |
| name | VARCHAR(100) | 設備名稱 |
| location | VARCHAR(50) | 所在檢查站 |
| equipment_type | VARCHAR(50) | 設備類型 |
| description | TEXT | 說明 |
| status | VARCHAR(20) | 狀態: normal/warning/broken |
| is_active | BOOLEAN | 是否啟用 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

#### equipment_logs 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK |
| equipment_id | INTEGER | FK → equipment |
| action | VARCHAR(50) | 操作類型 |
| old_status | VARCHAR(20) | 舊狀態 |
| new_status | VARCHAR(20) | 新狀態 |
| description | TEXT | 說明 |
| operator_id | INTEGER | FK → users |
| created_at | TIMESTAMP | 時間戳 |

#### audit_logs 表

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | PK |
| user_id | INTEGER | FK → users |
| user_name | VARCHAR(100) | 操作者名稱 |
| action | VARCHAR(50) | 操作類型 |
| target_type | VARCHAR(50) | 目標類型 |
| target_id | INTEGER | 目標 ID |
| target_name | VARCHAR(100) | 目標名稱 |
| details | TEXT | 詳細資訊 (JSON) |
| ip_address | VARCHAR(50) | IP 位址 |
| user_agent | VARCHAR(255) | 瀏覽器資訊 |
| created_at | TIMESTAMP | 時間戳 |

### 5.2 預設檢查項目

| 代碼 | 名稱 | 時間 |
|------|------|------|
| REG | 報到櫃檯 | 5 分鐘 |
| PHY | 一般體檢 | 15 分鐘 |
| BLOOD | 抽血站 | 10 分鐘 |
| XRAY | X光室 | 10 分鐘 |
| US | 超音波 | 20 分鐘 |
| CT | 電腦斷層 | 30 分鐘 |
| MRI | 磁振造影 | 45 分鐘 |
| ENDO | 內視鏡室 | 30 分鐘 |
| CARDIO | 心電圖室 | 15 分鐘 |
| CONSULT | 醫師諮詢 | 15 分鐘 |

---

## 6. 核心子程式說明

### 6.1 認證服務 `services/auth.py`

```python
# JWT Token 建立
def create_access_token(user_id: int) -> str:
    """建立 7 天有效的 JWT Token"""
    
# LINE Login 流程
async def exchange_code_for_token(code: str) -> Dict:
    """用 authorization code 換取 access token"""
    
async def get_line_profile(access_token: str) -> Dict:
    """取得 LINE 使用者資料"""
    
def get_or_create_user(db: Session, line_profile: Dict) -> User:
    """取得或建立使用者，新用戶預設有 dispatcher+coordinator 權限"""

# 權限檢查 Dependency
def require_permission(*permissions: str):
    """建立權限檢查 Dependency"""
    
def require_admin(request, db) -> User:
    """要求管理員權限"""
    
def require_dispatcher(request, db) -> User:
    """要求調度員權限（管理員也可以）"""
    
def require_coordinator(request, db) -> User:
    """要求個管師權限（管理員也可以）"""
```

### 6.2 追蹤服務 `services/tracking.py`

```python
def get_today_patients(db, exam_date) -> List[Patient]:
    """取得指定日期的所有病人"""
    
def get_patient_with_tracking(db, patient_id, exam_date) -> Dict:
    """取得病人及其追蹤資訊、個管師"""
    
def get_coordinator_patient(db, coordinator_id, exam_date) -> Dict:
    """取得個管師負責的病人"""
    
def assign_coordinator(db, patient_id, coordinator_id, assigned_by) -> CoordinatorAssignment:
    """指派個管師給病人（一對一，會取消舊指派）"""
    
def assign_next_station(db, patient_id, next_exam_code, assigned_by) -> PatientTracking:
    """指派病人下一站"""
    
def update_patient_status(db, patient_id, new_status, location, operator_id, notes) -> PatientTracking:
    """更新病人狀態（個管師回報用）"""
    
def get_station_summary(db, exam_date) -> Dict[str, Dict]:
    """取得各檢查站的狀態摘要（等候/檢查中/待前往人數）"""
    
def get_tracking_history(db, patient_id, exam_date) -> List[TrackingHistory]:
    """取得病人的追蹤歷程"""
```

### 6.3 統計服務 `services/stats.py`

```python
def get_daily_summary(db, target_date) -> Dict:
    """取得每日摘要統計（病人數、完成率、設備狀態）"""
    
def get_station_statistics(db, target_date) -> List[Dict]:
    """取得各檢查站統計（完成數、等候數、設備狀態）"""
    
def get_coordinator_statistics(db, target_date) -> List[Dict]:
    """取得個管師工作統計"""
    
def get_history_records(db, start_date, end_date, exam_code, limit) -> List[Dict]:
    """取得歷史記錄"""
    
def get_date_range_summary(db, start_date, end_date) -> List[Dict]:
    """取得日期範圍內每日摘要（趨勢報表用）"""
    
def export_daily_report_csv(db, target_date) -> str:
    """匯出每日報表 CSV"""
```

### 6.4 等候時間預估 `services/wait_time.py`

```python
def estimate_station_wait_time(db, exam_code, exam_date) -> Dict:
    """預估特定檢查站的等候時間"""
    
def estimate_patient_remaining_time(db, patient_id, exam_date) -> Dict:
    """預估病人剩餘檢查時間"""
    
def get_historical_average(db, exam_code, days) -> float:
    """取得歷史平均檢查時間"""
```

### 6.5 備份服務 `services/backup.py`

```python
def export_patients_csv(db, exam_date) -> str:
    """匯出病人資料 CSV"""
    
def export_exams_csv(db) -> str:
    """匯出檢查項目 CSV"""
    
def export_equipment_csv(db) -> str:
    """匯出設備資料 CSV"""
    
def export_full_backup_json(db) -> str:
    """匯出完整備份 JSON"""
```

---

## 7. API 端點一覽

### 7.1 認證相關

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/auth/login` | 登入頁面 |
| GET | `/auth/line-login` | 導向 LINE Login |
| GET | `/auth/callback` | LINE 回調處理 |
| GET | `/auth/logout` | 登出 |

### 7.2 管理後台 `/admin`

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/admin` | 管理後台首頁 |
| GET | `/admin/users` | 帳號管理 |
| POST | `/admin/users/{id}/role` | 更新角色 |
| POST | `/admin/users/{id}/permissions` | 更新權限 |
| GET | `/admin/patients` | 病人管理 |
| POST | `/admin/patients/import` | CSV 匯入 |
| POST | `/admin/patients/add` | 新增病人 |
| GET | `/admin/exams` | 檢查項目管理 |
| POST | `/admin/exams/init` | 初始化預設項目 |
| GET | `/admin/equipment` | 設備管理 |
| POST | `/admin/equipment/init` | 初始化設備 |
| GET | `/admin/audit` | 操作日誌 |
| GET | `/admin/backup` | 備份管理 |
| GET | `/admin/dashboard` | 效能儀表板 |
| GET | `/admin/check-line?key=heal2025` | LINE 設定診斷 |
| GET | `/admin/fix-permissions?key=heal2025` | 權限修復 |

### 7.3 調度員 `/dispatcher`

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/dispatcher` | 調度員主控台 |
| POST | `/dispatcher/assign-coordinator` | 指派個管師 |
| POST | `/dispatcher/assign-station` | 指派下一站 |
| POST | `/dispatcher/report-equipment-failure` | 回報故障 |
| GET | `/dispatcher/api/patients` | 病人列表 (HTMX) |
| GET | `/dispatcher/api/stations` | 檢查站狀態 (HTMX) |

### 7.4 個管師 `/coordinator`

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/coordinator` | 我的病人頁面 |
| POST | `/coordinator/arrive` | 回報到達 |
| POST | `/coordinator/start` | 回報開始檢查 |
| POST | `/coordinator/complete` | 回報完成 |
| POST | `/coordinator/report-equipment-failure` | 回報故障 |
| GET | `/coordinator/api/notifications` | 通知更新 (HTMX) |

### 7.5 報表 `/admin/reports`

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/admin/reports` | 報表首頁 |
| GET | `/admin/reports/history` | 歷史查詢 |
| GET | `/admin/reports/trend` | 趨勢報表 |
| GET | `/admin/reports/export/daily` | 匯出 CSV |

---

## 8. 部署與設定

### 8.1 Railway 環境變數

```env
# 資料庫（Railway 自動提供）
DATABASE_URL=postgresql://...

# LINE Login 設定
LINE_CHANNEL_ID=你的_LINE_Channel_ID
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
LINE_REDIRECT_URI=https://你的網域/auth/callback

# 應用程式密鑰
SECRET_KEY=隨機產生的密鑰字串

# 選用
APP_NAME=高檢病人動態系統
APP_VERSION=1.0.0
```

### 8.2 LINE Developers Console 設定

1. 建立 LINE Login Channel
2. 設定 Callback URL：`https://你的網域/auth/callback`
3. **重要**：將 Channel 狀態改為 **Published**（發布）
4. 記錄 Channel ID 和 Channel Secret

### 8.3 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 8.4 railway.toml

```toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 10
```

---

## 9. 開發過程遇到的問題與解決方案

### 9.1 LINE Login 只有擁有者能登入

**問題**：其他人登入時顯示「無法正常執行！」錯誤

**原因**：LINE Channel 還在「Developing」模式

**解決方案**：
1. 登入 LINE Developers Console
2. 找到 LINE Login Channel
3. 點擊「Publish」發布

**經驗**：排查 LINE Login 問題時，**優先檢查 Channel 狀態**

---

### 9.2 資料庫欄位名稱不匹配

**問題**：部署後所有頁面 500 錯誤，日誌顯示 `column patients.gender does not exist`

**原因**：ORM 模型定義的欄位與實際資料庫不一致

**解決方案**：
1. 查詢實際資料庫結構
2. 修正 ORM 模型匹配實際欄位
3. 使用 SQLAlchemy 的 `Column("實際欄位名", ...)` 語法處理名稱差異

```python
# 程式中用 line_user_id，資料庫欄位是 line_id
line_user_id = Column("line_id", String(100), ...)

# 程式中用 last_login，資料庫欄位是 last_login_at  
last_login = Column("last_login_at", DateTime, ...)

# 程式中用 duration_min，不是 duration_minutes
duration_min = Column(Integer, default=15)
```

**經驗**：部署新功能前，先確認資料庫實際結構

---

### 9.3 Jinja2 模板 timedelta 未定義

**問題**：報表頁面錯誤 `'timedelta' is undefined`

**原因**：模板中使用 `timedelta` 但未傳入

**解決方案**：在路由中傳入 timedelta

```python
from datetime import timedelta

return templates.TemplateResponse("admin/reports.html", {
    "request": request,
    ...
    "timedelta": timedelta,  # 加入這行
})
```

---

### 9.4 station_cards.html 迭代錯誤

**問題**：檢查站卡片只顯示單個字母

**原因**：`get_station_summary()` 返回 dict，模板直接迭代取得字串

**解決方案**：

```html
<!-- 錯誤 -->
{% for station in station_summary %}

<!-- 正確 -->
{% for exam_code, station in station_summary.items() %}
```

---

### 9.5 401/403 顯示醜陋錯誤

**問題**：未登入時顯示 JSON 錯誤訊息

**解決方案**：在 `main.py` 加入全域異常處理

```python
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    if exc.status_code == 401:
        return RedirectResponse(url="/auth/login")
    if exc.status_code == 403:
        return RedirectResponse(url="/auth/login?msg=no_permission")
    ...
```

---

### 9.6 用戶權限為空無法使用功能

**問題**：現有用戶 permissions 欄位為空，無法使用功能

**解決方案**：建立修復端點

```python
@router.get("/fix-permissions")
async def fix_user_permissions(request, key, db):
    if key != "heal2025":
        return "需要密鑰"
    
    for user in db.query(User).all():
        if not user.permissions and user.is_active:
            user.permissions = ["dispatcher", "coordinator"]
            user.role = "active"
    db.commit()
```

訪問 `/admin/fix-permissions?key=heal2025` 即可修復

---

### 9.7 HTMX 刷新導致閃爍

**問題**：頁面頻繁刷新造成視覺閃爍

**解決方案**：
1. 調整刷新間隔（調度員 5 秒、個管師 3 秒）
2. 使用 `hx-swap="innerHTML"` 只更新內容
3. 避免整頁刷新

---

## 10. 待開發功能

### 10.1 Phase 7（建議）

- [ ] **LINE 推播通知**
  - 叫號提醒（輪到某病人時通知個管師）
  - 設備故障通知管理員

- [ ] **病人自助報到**
  - QR Code 掃描報到
  - 顯示等候時間

- [ ] **進階排程**
  - OR-Tools 排程優化整合
  - 檢查室容量管理
  - 衝突檢測與建議

### 10.2 Phase 8（建議）

- [ ] **進階報表**
  - PDF 報表匯出
  - 更多圖表類型
  - 自訂報表

- [ ] **多語言支援**
  - 繁體中文
  - 英文
  - 簡體中文

### 10.3 其他優化

- [ ] 單元測試
- [ ] 效能優化（快取、索引）
- [ ] 完整 API 文檔（OpenAPI）
- [ ] 自動備份排程

---

## 11. 維護指南

### 11.1 常用診斷端點

| 端點 | 說明 |
|------|------|
| `/health` | 健康檢查 |
| `/admin/check-line?key=heal2025` | LINE 設定診斷 |
| `/admin/fix-permissions?key=heal2025` | 權限修復 |

### 11.2 日誌查看

Railway Dashboard → Deployments → 選擇部署 → Logs

### 11.3 資料庫管理

Railway Dashboard → Database → Data → 執行 SQL

### 11.4 常見問題快速排查

| 問題 | 排查順序 |
|------|----------|
| LINE 登入失敗 | 1. Channel 狀態 → 2. Callback URL → 3. 程式碼 |
| 500 錯誤 | 1. 查看日誌 → 2. 檢查資料庫欄位 → 3. 模型定義 |
| 權限不足 | 1. 檢查 permissions 欄位 → 2. 執行 fix-permissions |
| 頁面空白 | 1. 瀏覽器 Console → 2. 網路請求 → 3. 伺服器日誌 |

### 11.5 版本更新流程

1. 本地修改程式碼
2. 測試功能
3. 推送到 GitHub
4. Railway 自動部署
5. 檢查日誌確認正常
6. 測試主要功能

---

## 📞 聯繫資訊

**開發者**：Sela  
**單位**：彰濱秀傳醫院 放射腫瘤科  
**系統**：高檢病人動態系統 (Heal-Arrange)

---

> 本文檔最後更新：2025-12-25  
> 文檔版本：v1.0
