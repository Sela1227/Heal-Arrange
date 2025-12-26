# -*- coding: utf-8 -*-
"""
main.py 需要新增以下內容
在現有的 router import 後面加入：
"""

# 在 import 區域新增：
from .routers import checkin, qrcode

# 在 app.include_router() 區域新增：
app.include_router(checkin.router)
app.include_router(qrcode.router)
