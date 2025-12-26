# 🔧 完整修復包：settings + impersonate 404 問題

## 問題原因
Phase 7 部署時 `admin.py` 被覆蓋，導致 settings 和 impersonate 路由消失。

## 📁 修復文件

```
fix-admin-complete/
└── app/
    ├── routers/
    │   └── admin.py         ← Phase 7 + settings + impersonate 完整版
    └── services/
        └── __init__.py      ← 補上 settings, impersonate import
```

## 🚀 部署步驟

### 1. 替換文件
```bash
cp app/routers/admin.py      你的專案/app/routers/admin.py
cp app/services/__init__.py  你的專案/app/services/__init__.py
```

### 2. 確認 templates 存在
確認以下文件已存在：
- `app/templates/admin/settings.html`
- `app/templates/admin/impersonate.html`

### 3. 部署
```bash
git add .
git commit -m "Fix: 完整補回 settings 和 impersonate 功能"
git push
```

## ✅ 驗證
部署後測試：
- `/admin/settings` → 200 OK
- `/admin/impersonate` → 200 OK
