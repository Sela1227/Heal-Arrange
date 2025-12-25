# -*- coding: utf-8 -*-
"""
病人模型 - 匹配實際資料庫結構
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text
from ..database import Base


class Patient(Base):
    """病人"""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    chart_no = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    package_code = Column(String(50), nullable=True)  # 套餐代碼
    exam_date = Column(Date, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)  # 可用於存儲檢查項目清單
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def exam_list(self):
        """兼容性屬性：從 notes 讀取檢查項目"""
        return self.notes
    
    @exam_list.setter
    def exam_list(self, value):
        """兼容性屬性：將檢查項目寫入 notes"""
        self.notes = value
    
    def __repr__(self):
        return f"<Patient {self.chart_no}: {self.name}>"
