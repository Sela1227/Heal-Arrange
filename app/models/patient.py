# -*- coding: utf-8 -*-
"""
病人模型
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text
from ..database import Base


class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    chart_no = Column(String(50), nullable=False, index=True)  # 病歷號
    name = Column(String(100), nullable=False)  # 姓名
    
    # 套餐/檢查項目（逗號分隔，如 "CT,MRI,US,XRAY"）
    package_code = Column(String(500), nullable=True)
    
    # 檢查日期
    exam_date = Column(Date, nullable=False, index=True)
    
    # 狀態
    is_active = Column(Boolean, default=True)  # 當日是否啟用
    is_completed = Column(Boolean, default=False)  # 是否全部完成
    
    # 備註
    notes = Column(Text, nullable=True)
    
    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Patient {self.chart_no} {self.name}>"
    
    @property
    def exam_list(self) -> list:
        """取得檢查項目清單"""
        if not self.package_code:
            return []
        return [code.strip() for code in self.package_code.split(",") if code.strip()]
    
    @property
    def exam_count(self) -> int:
        """檢查項目數量"""
        return len(self.exam_list)
