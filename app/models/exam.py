# -*- coding: utf-8 -*-
"""
檢查項目模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from ..database import Base


class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_code = Column(String(50), unique=True, nullable=False, index=True)  # CT, MRI, US...
    name = Column(String(100), nullable=False)  # 檢查名稱
    
    duration_min = Column(Integer, default=30)  # 預估時間（分鐘）
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Exam {self.exam_code} {self.name}>"


# 預設檢查項目資料
DEFAULT_EXAMS = [
    {"exam_code": "BLOOD", "name": "抽血檢驗", "duration_min": 10},
    {"exam_code": "XRAY", "name": "X光檢查", "duration_min": 10},
    {"exam_code": "US", "name": "超音波", "duration_min": 20},
    {"exam_code": "CT", "name": "電腦斷層", "duration_min": 30},
    {"exam_code": "MRI", "name": "核磁共振", "duration_min": 45},
    {"exam_code": "GFS", "name": "胃鏡", "duration_min": 30},
    {"exam_code": "CFS", "name": "大腸鏡", "duration_min": 45},
    {"exam_code": "BONE", "name": "骨密度", "duration_min": 15},
    {"exam_code": "EKG", "name": "心電圖", "duration_min": 10},
    {"exam_code": "ECHO", "name": "心臟超音波", "duration_min": 30},
]
