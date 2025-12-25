# -*- coding: utf-8 -*-
"""
檢查項目模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from ..database import Base


# 預設檢查項目
DEFAULT_EXAMS = [
    {"exam_code": "REG", "name": "報到櫃檯", "duration_minutes": 5, "location": "大廳"},
    {"exam_code": "PHY", "name": "一般體檢", "duration_minutes": 15, "location": "體檢室"},
    {"exam_code": "BLOOD", "name": "抽血站", "duration_minutes": 10, "location": "抽血室"},
    {"exam_code": "XRAY", "name": "X光室", "duration_minutes": 10, "location": "X光室"},
    {"exam_code": "US", "name": "超音波", "duration_minutes": 20, "location": "超音波室"},
    {"exam_code": "CT", "name": "電腦斷層", "duration_minutes": 30, "location": "CT室"},
    {"exam_code": "MRI", "name": "磁振造影", "duration_minutes": 45, "location": "MRI室"},
    {"exam_code": "ENDO", "name": "內視鏡室", "duration_minutes": 30, "location": "內視鏡室"},
    {"exam_code": "CARDIO", "name": "心電圖室", "duration_minutes": 15, "location": "心電圖室"},
    {"exam_code": "CONSULT", "name": "醫師諮詢", "duration_minutes": 15, "location": "諮詢室"},
]


class Exam(Base):
    """檢查項目"""
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    
    # 欄位映射：程式用 duration_minutes，資料庫用 duration_min
    duration_minutes = Column("duration_min", Integer, default=15)
    
    location = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Exam {self.exam_code}: {self.name}>"
