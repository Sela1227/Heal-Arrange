# -*- coding: utf-8 -*-
"""
病人模型
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text
from ..database import Base


class Patient(Base):
    """病人"""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    chart_no = Column(String(20), nullable=False, index=True)  # 病歷號
    name = Column(String(100), nullable=False)
    
    # 基本資料
    gender = Column(String(10), nullable=True)
    birthday = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # 檢查相關
    exam_date = Column(Date, nullable=False, index=True)
    exam_list = Column(Text, nullable=True)  # 檢查項目，逗號分隔
    
    # VIP 等級
    vip_level = Column(Integer, default=0)
    
    # 備註
    notes = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Patient {self.chart_no}: {self.name}>"
