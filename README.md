# 🚀 Phase 7 部署包

## 📦 新功能

| 功能 | 說明 |
|------|------|
| 📄 PDF 報表匯出 | 每日報表、趨勢報表匯出成 PDF |
| 📊 Chart.js 圖表 | 趨勢報表視覺化（長條圖、折線圖） |
| 📏 檢查室容量管理 | 設定每站同時檢查人數上限 |
| 🧠 排程建議 | 智慧推薦下一站（依等候人數、依賴關係） |
| ⚠️ 衝突檢測 | 容量警告、設備故障、依賴關係提醒 |

---

## 📁 檔案結構

```
phase7/
├── app/
│   ├── models/
│   │   └── exam.py              ← 替換（新增 capacity 欄位）
│   │
│   ├── services/
│   │   ├── __init__.py          ← 替換
│   │   ├── pdf_report.py        ← 新增
│   │   └── scheduler.py         ← 新增
│   │
│   ├── routers/
│   │   ├── admin.py             ← 替換
│   │   ├── dispatcher.py        ← 替換
│   │   └── reports.py           ← 替換
│   │
│   └── templates/
│       ├── admin/
│       │   ├── exams.html       ← 替換（容量設定）
│       │   ├── reports.html     ← 替換（PDF 按鈕）
│       │   ├── trend.html       ← 替換（Chart.js）
│       │   └── scheduler.html   ← 新增
│       │
│       └── partials/
│           ├── station_cards.html   ← 替換（容量指示）
│           └── conflict_alert.html  ← 新增
│
├── migrations/
│   └── phase7_add_capacity.sql  ← 資料庫遷移
│
└── README.md
```

---

## 🔧 部署步驟

### Step 1：更新 requirements.txt

加入 PDF 產生套件：
```
reportlab>=4.0.0
```

### Step 2：複製檔案

> ⚠️ **資料庫遷移會自動執行**：系統啟動時會自動檢查並新增 `capacity` 欄位，無需手動操作。

```bash
# 解壓縮後
cp -r phase7/app/* app/
```

### Step 3：部署

```bash
git add .
git commit -m "Phase 7: PDF報表 + Chart.js + 容量管理 + 排程建議"
git push
```

---

## ✅ 驗證

### PDF 報表
1. 管理後台 → 統計報表
2. 點擊「📄 PDF」按鈕
3. 應該下載 PDF 檔案

### Chart.js 圖表
1. 統計報表 → 7日趨勢
2. 應該看到長條圖和折線圖

### 容量管理
1. 管理後台 → 檢查項目管理
2. 應該看到容量狀態總覽
3. 可以修改每站容量

### 排程建議
1. 管理後台 → 🧠 排程建議
2. 選擇病人後顯示下一站建議
3. 調度台也會顯示衝突警示

---

## 📊 新功能路徑

| 功能 | 路徑 |
|------|------|
| PDF 每日報表 | `/admin/reports/export/daily/pdf` |
| PDF 趨勢報表 | `/admin/reports/trend/pdf?days=7` |
| 排程建議頁面 | `/admin/scheduler` |
| 容量設定 | `/admin/exams` |

---

## 💡 使用說明

### 容量管理
- 每個檢查站可設定同時容納人數（1-20人）
- 超過 70% 顯示黃色警告
- 達到 100% 顯示紅色已滿

### 排程建議
系統會根據以下因素計算推薦分數：
1. **等候人數**：人少的站點分數高
2. **依賴關係**：例如內視鏡應在抽血後
3. **設備狀態**：故障站點分數低
4. **時間因素**：空腹檢查適合早上

### 衝突檢測
在調度台指派下一站時會提醒：
- 🔴 容量已滿
- 🛠️ 設備故障
- 📋 建議先完成其他檢查

---

## ⚠️ 注意事項

1. **PDF 字體**：如果 PDF 中文顯示方塊，需要安裝中文字體
   ```bash
   apt-get install fonts-noto-cjk
   ```

2. **Chart.js CDN**：需要網路連線才能載入圖表

3. **容量欄位**：首次部署需執行資料庫遷移

---

## 📝 待辦事項（使用者備忘）

- [ ] 病人 LINE 綁定（之後再說）
- [ ] 病人叫號推播（之後再說）
