# -*- coding: utf-8 -*-
"""
追蹤服務 - 病人位置與狀態管理
"""

from datetime import datetime, date
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.patient import Patient
from ..models.user import User
from ..models.tracking import (
    CoordinatorAssignment,
    PatientTracking,
    TrackingHistory,
    TrackingStatus,
    TrackingAction,
)
from ..models.exam import Exam


def get_today_patients(db: Session, exam_date: date = None) -> List[Patient]:
    """取得指定日期的所有病人"""
    if exam_date is None:
        exam_date = date.today()
    
    return db.query(Patient).filter(
        Patient.exam_date == exam_date,
        Patient.is_active == True
    ).all()


def get_patient_with_tracking(db: Session, patient_id: int, exam_date: date = None) -> Dict:
    """取得病人及其追蹤資訊"""
    if exam_date is None:
        exam_date = date.today()
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return None
    
    # 取得追蹤資訊
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date
    ).first()
    
    # 取得指派的個管師
    assignment = db.query(CoordinatorAssignment).filter(
        CoordinatorAssignment.patient_id == patient_id,
        CoordinatorAssignment.exam_date == exam_date,
        CoordinatorAssignment.is_active == True
    ).first()
    
    coordinator = None
    if assignment:
        coordinator = db.query(User).filter(User.id == assignment.coordinator_id).first()
    
    return {
        "patient": patient,
        "tracking": tracking,
        "assignment": assignment,
        "coordinator": coordinator,
    }


def get_coordinator_patient(db: Session, coordinator_id: int, exam_date: date = None) -> Dict:
    """取得個管師負責的病人"""
    if exam_date is None:
        exam_date = date.today()
    
    assignment = db.query(CoordinatorAssignment).filter(
        CoordinatorAssignment.coordinator_id == coordinator_id,
        CoordinatorAssignment.exam_date == exam_date,
        CoordinatorAssignment.is_active == True
    ).first()
    
    if not assignment:
        return None
    
    return get_patient_with_tracking(db, assignment.patient_id, exam_date)


def assign_coordinator(
    db: Session,
    patient_id: int,
    coordinator_id: int,
    assigned_by: int,
    exam_date: date = None
) -> CoordinatorAssignment:
    """指派個管師給病人"""
    if exam_date is None:
        exam_date = date.today()
    
    # 取消該病人現有的指派
    db.query(CoordinatorAssignment).filter(
        CoordinatorAssignment.patient_id == patient_id,
        CoordinatorAssignment.exam_date == exam_date,
        CoordinatorAssignment.is_active == True
    ).update({"is_active": False})
    
    # 取消該個管師現有的指派（一對一）
    db.query(CoordinatorAssignment).filter(
        CoordinatorAssignment.coordinator_id == coordinator_id,
        CoordinatorAssignment.exam_date == exam_date,
        CoordinatorAssignment.is_active == True
    ).update({"is_active": False})
    
    # 建立新指派
    assignment = CoordinatorAssignment(
        patient_id=patient_id,
        coordinator_id=coordinator_id,
        exam_date=exam_date,
        assigned_by=assigned_by,
        is_active=True,
    )
    db.add(assignment)
    
    # 記錄歷程
    history = TrackingHistory(
        patient_id=patient_id,
        exam_date=exam_date,
        action=TrackingAction.ASSIGN.value,
        operator_id=assigned_by,
        notes=f"指派個管師 ID:{coordinator_id}",
    )
    db.add(history)
    
    db.commit()
    db.refresh(assignment)
    
    return assignment


def assign_next_station(
    db: Session,
    patient_id: int,
    next_exam_code: str,
    assigned_by: int,
    exam_date: date = None
) -> PatientTracking:
    """指派病人下一站"""
    if exam_date is None:
        exam_date = date.today()
    
    # 取得或建立追蹤記錄
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date
    ).first()
    
    if not tracking:
        tracking = PatientTracking(
            patient_id=patient_id,
            exam_date=exam_date,
            current_status=TrackingStatus.WAITING.value,
        )
        db.add(tracking)
    
    tracking.next_exam_code = next_exam_code
    tracking.updated_by = assigned_by
    tracking.updated_at = datetime.utcnow()
    
    # 記錄歷程
    history = TrackingHistory(
        patient_id=patient_id,
        exam_date=exam_date,
        action=TrackingAction.ASSIGN.value,
        operator_id=assigned_by,
        notes=f"指派下一站: {next_exam_code}",
    )
    db.add(history)
    
    db.commit()
    db.refresh(tracking)
    
    return tracking


def update_patient_status(
    db: Session,
    patient_id: int,
    new_status: str,
    location: str,
    operator_id: int,
    exam_date: date = None,
    notes: str = None
) -> PatientTracking:
    """更新病人狀態（個管師回報）"""
    if exam_date is None:
        exam_date = date.today()
    
    # 取得或建立追蹤記錄
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date
    ).first()
    
    if not tracking:
        tracking = PatientTracking(
            patient_id=patient_id,
            exam_date=exam_date,
        )
        db.add(tracking)
    
    # 判斷動作類型
    if new_status == TrackingStatus.WAITING.value:
        action = TrackingAction.ARRIVE.value
    elif new_status == TrackingStatus.IN_EXAM.value:
        action = TrackingAction.START.value
    elif new_status == TrackingStatus.COMPLETED.value:
        action = TrackingAction.COMPLETE.value
    else:
        action = TrackingAction.ARRIVE.value
    
    tracking.current_status = new_status
    tracking.current_location = location
    tracking.updated_by = operator_id
    tracking.updated_at = datetime.utcnow()
    
    # 記錄歷程
    history = TrackingHistory(
        patient_id=patient_id,
        exam_date=exam_date,
        location=location,
        status=new_status,
        action=action,
        operator_id=operator_id,
        notes=notes,
    )
    db.add(history)
    
    db.commit()
    db.refresh(tracking)
    
    return tracking


def get_station_summary(db: Session, exam_date: date = None) -> Dict[str, Dict]:
    """取得各檢查站的狀態摘要"""
    if exam_date is None:
        exam_date = date.today()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    summary = {}
    for exam in exams:
        # 統計該站的病人數
        waiting = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.current_location == exam.exam_code,
            PatientTracking.current_status == TrackingStatus.WAITING.value
        ).count()
        
        in_exam = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.current_location == exam.exam_code,
            PatientTracking.current_status == TrackingStatus.IN_EXAM.value
        ).count()
        
        # 等待前往該站的病人
        pending = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.next_exam_code == exam.exam_code,
            PatientTracking.current_location != exam.exam_code
        ).count()
        
        summary[exam.exam_code] = {
            "exam": exam,
            "waiting": waiting,
            "in_exam": in_exam,
            "pending": pending,
            "total": waiting + in_exam,
        }
    
    return summary


def get_tracking_history(db: Session, patient_id: int, exam_date: date = None) -> List[TrackingHistory]:
    """取得病人的追蹤歷程"""
    if exam_date is None:
        exam_date = date.today()
    
    return db.query(TrackingHistory).filter(
        TrackingHistory.patient_id == patient_id,
        TrackingHistory.exam_date == exam_date
    ).order_by(TrackingHistory.timestamp.desc()).all()
