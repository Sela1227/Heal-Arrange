# -*- coding: utf-8 -*-
"""
檢查項目模型 - Phase 7 更新：加入容量管理
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from ..database import Base


class Exam(Base):
    """檢查項目"""
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, default=15)
    location = Column(String(100), nullable=True)
    
    # Phase 7 新增：容量管理
    capacity = Column(Integer, default=5, nullable=False)  # 同時檢查人數上限
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Exam {self.exam_code}: {self.name}>"


# 預設檢查項目（含容量）
DEFAULT_EXAMS = [
    {"exam_code": "REG", "name": "報到櫃檯", "duration_minutes": 5, "location": "1F 大廳", "capacity": 3},
    {"exam_code": "PHY", "name": "一般體檢", "duration_minutes": 15, "location": "2F 體檢區", "capacity": 5},
    {"exam_code": "BLOOD", "name": "抽血站", "duration_minutes": 10, "location": "2F 檢驗科", "capacity": 4},
    {"exam_code": "XRAY", "name": "X光室", "duration_minutes": 10, "location": "1F 放射科", "capacity": 2},
    {"exam_code": "US", "name": "超音波", "duration_minutes": 20, "location": "2F 超音波室", "capacity": 3},
    {"exam_code": "CT", "name": "電腦斷層", "duration_minutes": 30, "location": "1F 影像中心", "capacity": 1},
    {"exam_code": "MRI", "name": "磁振造影", "duration_minutes": 45, "location": "1F 影像中心", "capacity": 1},
    {"exam_code": "ENDO", "name": "內視鏡室", "duration_minutes": 30, "location": "3F 內視鏡中心", "capacity": 2},
    {"exam_code": "CARDIO", "name": "心電圖室", "duration_minutes": 15, "location": "2F 心臟科", "capacity": 3},
    {"exam_code": "CONSULT", "name": "醫師諮詢", "duration_minutes": 15, "location": "2F 諮詢室", "capacity": 4},
]
