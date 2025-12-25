# -*- coding: utf-8 -*-
"""
操作日誌模型 - 記錄所有重要操作
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class AuditAction(str, enum.Enum):
    """操作類型"""
    # 認證相關
    LOGIN = "login"
    LOGOUT = "logout"
    
    # 使用者管理
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_PERMISSION = "user_permission"
    USER_DISABLE = "user_disable"
    
    # 病人管理
    PATIENT_CREATE = "patient_create"
    PATIENT_UPDATE = "patient_update"
    PATIENT_DELETE = "patient_delete"
    PATIENT_IMPORT = "patient_import"
    
    # 追蹤操作
    ASSIGN_COORDINATOR = "assign_coordinator"
    ASSIGN_STATION = "assign_station"
    STATUS_UPDATE = "status_update"
    
    # 設備管理
    EQUIPMENT_CREATE = "equipment_create"
    EQUIPMENT_FAILURE = "equipment_failure"
    EQUIPMENT_REPAIR = "equipment_repair"
    
    # 檢查項目
    EXAM_CREATE = "exam_create"
    EXAM_UPDATE = "exam_update"
    EXAM_DELETE = "exam_delete"
    
    # 系統操作
    DATA_EXPORT = "data_export"
    DATA_BACKUP = "data_backup"
    SYSTEM_INIT = "system_init"


# 操作類型中文對照
ACTION_LABELS = {
    AuditAction.LOGIN.value: "登入系統",
    AuditAction.LOGOUT.value: "登出系統",
    AuditAction.USER_CREATE.value: "新增使用者",
    AuditAction.USER_UPDATE.value: "更新使用者",
    AuditAction.USER_PERMISSION.value: "變更權限",
    AuditAction.USER_DISABLE.value: "停用使用者",
    AuditAction.PATIENT_CREATE.value: "新增病人",
    AuditAction.PATIENT_UPDATE.value: "更新病人",
    AuditAction.PATIENT_DELETE.value: "刪除病人",
    AuditAction.PATIENT_IMPORT.value: "匯入病人",
    AuditAction.ASSIGN_COORDINATOR.value: "指派個管師",
    AuditAction.ASSIGN_STATION.value: "指派檢查站",
    AuditAction.STATUS_UPDATE.value: "狀態更新",
    AuditAction.EQUIPMENT_CREATE.value: "新增設備",
    AuditAction.EQUIPMENT_FAILURE.value: "回報故障",
    AuditAction.EQUIPMENT_REPAIR.value: "設備修復",
    AuditAction.EXAM_CREATE.value: "新增檢查項目",
    AuditAction.EXAM_UPDATE.value: "更新檢查項目",
    AuditAction.EXAM_DELETE.value: "刪除檢查項目",
    AuditAction.DATA_EXPORT.value: "資料匯出",
    AuditAction.DATA_BACKUP.value: "資料備份",
    AuditAction.SYSTEM_INIT.value: "系統初始化",
}


class AuditLog(Base):
    """操作日誌"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 操作者
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String(100), nullable=True)  # 冗餘存儲，方便查詢
    
    # 操作內容
    action = Column(String(50), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)  # user, patient, equipment...
    target_id = Column(Integer, nullable=True)
    target_name = Column(String(100), nullable=True)
    
    # 詳細資訊
    details = Column(Text, nullable=True)  # JSON 格式的詳細資料
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 關聯
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_name} @ {self.created_at}>"
    
    @property
    def action_label(self) -> str:
        """取得操作的中文標籤"""
        return ACTION_LABELS.get(self.action, self.action)
