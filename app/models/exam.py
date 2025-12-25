# -*- coding: utf-8 -*-
"""
檢查項目模型 - 匹配實際資料庫結構
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from ..database import Base


# 預設檢查項目
DEFAULT_EXAMS = [
    {"exam_code": "REG", "name": "報到櫃檯", "duration_min": 5},
    {"exam_code": "PHY", "name": "一般體檢", "duration_min": 15},
    {"exam_code": "BLOOD", "name": "抽血站", "duration_min": 10},
    {"exam_code": "XRAY", "name": "X光室", "duration_min": 10},
    {"exam_code": "US", "name": "超音波", "duration_min": 20},
    {"exam_code": "CT", "name": "電腦斷層", "duration_min": 30},
    {"exam_code": "MRI", "name": "磁振造影", "duration_min": 45},
    {"exam_code": "ENDO", "name": "內視鏡室", "duration_min": 30},
    {"exam_code": "CARDIO", "name": "心電圖室", "duration_min": 15},
    {"exam_code": "CONSULT", "name": "醫師諮詢", "duration_min": 15},
]


class Exam(Base):
    """檢查項目"""
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    duration_min = Column(Integer, default=15)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Exam {self.exam_code}: {self.name}>"
