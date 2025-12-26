# 修復 /admin/settings 和 /admin/impersonate 404

## 問題原因
`app/services/__init__.py` 缺少 settings 和 impersonate 的 import

## 修復方式
用此檔案替換 `app/services/__init__.py`

## 部署
```bash
git add app/services/__init__.py
git commit -m "Fix: 補回 settings 和 impersonate import"
git push
```
