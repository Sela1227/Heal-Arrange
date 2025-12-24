# -*- coding: utf-8 -*-
"""
設備服務 - 故障回報與管理
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.equipment import Equipment, EquipmentStatus, EquipmentLog
from ..models.user import User


def get_all_equipment(db: Session) -> List[Equipment]:
    """取得所有設備"""
    return db.query(Equipment).filter(Equipment.is_active == True).all()


def get_equipment_by_location(db: Session, location: str) -> List[Equipment]:
    """取得特定位置的設備"""
    return db.query(Equipment).filter(
        Equipment.location == location,
        Equipment.is_active == True
    ).all()


def report_failure(
    db: Session,
    equipment_id: int,
    reported_by: int,
    description: str = None
) -> EquipmentLog:
    """回報設備故障"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        return None
    
    # 更新設備狀態
    equipment.status = EquipmentStatus.BROKEN.value
    equipment.updated_at = datetime.utcnow()
    
    # 建立日誌
    log = EquipmentLog(
        equipment_id=equipment_id,
        action="report_failure",
        old_status=equipment.status,
        new_status=EquipmentStatus.BROKEN.value,
        description=description or "設備故障",
        operator_id=reported_by,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log


def report_repair(
    db: Session,
    equipment_id: int,
    reported_by: int,
    description: str = None
) -> EquipmentLog:
    """回報設備修復"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        return None
    
    old_status = equipment.status
    equipment.status = EquipmentStatus.NORMAL.value
    equipment.updated_at = datetime.utcnow()
    
    log = EquipmentLog(
        equipment_id=equipment_id,
        action="repair",
        old_status=old_status,
        new_status=EquipmentStatus.NORMAL.value,
        description=description or "設備已修復",
        operator_id=reported_by,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log


def get_broken_equipment(db: Session) -> List[Equipment]:
    """取得所有故障設備"""
    return db.query(Equipment).filter(
        Equipment.status == EquipmentStatus.BROKEN.value,
        Equipment.is_active == True
    ).all()


def get_equipment_logs(db: Session, equipment_id: int = None, limit: int = 50) -> List[EquipmentLog]:
    """取得設備日誌"""
    query = db.query(EquipmentLog)
    if equipment_id:
        query = query.filter(EquipmentLog.equipment_id == equipment_id)
    return query.order_by(EquipmentLog.created_at.desc()).limit(limit).all()


def create_equipment(
    db: Session,
    name: str,
    location: str,
    equipment_type: str = None,
    description: str = None
) -> Equipment:
    """建立設備"""
    equipment = Equipment(
        name=name,
        location=location,
        equipment_type=equipment_type,
        description=description,
        status=EquipmentStatus.NORMAL.value,
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def init_default_equipment(db: Session) -> int:
    """初始化預設設備（依檢查站）"""
    from ..models.exam import Exam
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    count = 0
    
    for exam in exams:
        # 檢查是否已有該位置的設備
        existing = db.query(Equipment).filter(Equipment.location == exam.exam_code).first()
        if not existing:
            equipment = Equipment(
                name=f"{exam.name}主機",
                location=exam.exam_code,
                equipment_type="檢查設備",
                description=f"{exam.name}檢查站設備",
                status=EquipmentStatus.NORMAL.value,
            )
            db.add(equipment)
            count += 1
    
    db.commit()
    return count
