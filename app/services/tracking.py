# -*- coding: utf-8 -*-
"""
追蹤服務 - 病人位置與狀態管理（整合 LINE 推播）
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
from ..config import settings


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
    
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date
    ).first()
    
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
    """取得專員負責的病人"""
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


async def assign_coordinator(
    db: Session,
    patient_id: int,
    coordinator_id: int,
    assigned_by: int,
    exam_date: date = None,
    send_notification: bool = True,
) -> CoordinatorAssignment:
    """指派專員給病人（含 LINE 推播）"""
    if exam_date is None:
        exam_date = date.today()
    
    # 取消該病人現有的指派
    db.query(CoordinatorAssignment).filter(
        CoordinatorAssignment.patient_id == patient_id,
        CoordinatorAssignment.exam_date == exam_date,
        CoordinatorAssignment.is_active == True
    ).update({"is_active": False})
    
    # 取消該專員現有的指派（一對一）
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
        notes=f"指派專員 ID:{coordinator_id}",
    )
    db.add(history)
    
    db.commit()
    db.refresh(assignment)
    
    # 發送 LINE 推播通知
    if send_notification and settings.NOTIFY_ON_ASSIGNMENT:
        await _send_assignment_notification(db, patient_id, coordinator_id)
    
    return assignment


async def assign_next_station(
    db: Session,
    patient_id: int,
    next_exam_code: str,
    assigned_by: int,
    exam_date: date = None,
    send_notification: bool = True,
) -> PatientTracking:
    """指派病人下一站（含 LINE 推播）"""
    if exam_date is None:
        exam_date = date.today()
    
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
    
    # 發送 LINE 推播通知
    if send_notification and settings.NOTIFY_ON_NEXT_STATION:
        await _send_next_station_notification(db, patient_id, next_exam_code, exam_date)
    
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
    """更新病人狀態"""
    if exam_date is None:
        exam_date = date.today()
    
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
    """取得各檢查站的狀態摘要（含等候時間）"""
    if exam_date is None:
        exam_date = date.today()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    summary = {}
    for exam in exams:
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
        
        pending = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.next_exam_code == exam.exam_code,
            PatientTracking.current_location != exam.exam_code
        ).count()
        
        # 計算預估等候時間
        avg_duration = exam.duration_min if hasattr(exam, 'duration_min') else 15
        estimated_wait = waiting * avg_duration
        if in_exam > 0:
            estimated_wait += avg_duration // 2
        
        summary[exam.exam_code] = {
            "exam": exam,
            "waiting": waiting,
            "in_exam": in_exam,
            "pending": pending,
            "total": waiting + in_exam,
            "estimated_wait": estimated_wait,
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


# =====================
# LINE 推播通知（內部函數）
# =====================

async def _send_assignment_notification(db: Session, patient_id: int, coordinator_id: int):
    """發送指派通知給專員"""
    try:
        from ..services import line_notify
        
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        coordinator = db.query(User).filter(User.id == coordinator_id).first()
        
        if not patient or not coordinator or not coordinator.line_id:
            return
        
        messages = line_notify.create_assignment_notification(
            patient_name=patient.name,
            patient_chart_no=patient.chart_no,
            exam_list=patient.exam_list,
        )
        
        await line_notify.send_push_message(coordinator.line_id, messages)
    
    except Exception as e:
        print(f"發送指派通知失敗: {e}")


async def _send_next_station_notification(
    db: Session,
    patient_id: int,
    next_exam_code: str,
    exam_date: date,
):
    """發送下一站通知給專員"""
    try:
        from ..services import line_notify
        from ..services import wait_time as wait_time_service
        
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        exam = db.query(Exam).filter(Exam.exam_code == next_exam_code).first()
        
        # 取得專員
        assignment = db.query(CoordinatorAssignment).filter(
            CoordinatorAssignment.patient_id == patient_id,
            CoordinatorAssignment.exam_date == exam_date,
            CoordinatorAssignment.is_active == True
        ).first()
        
        if not assignment:
            return
        
        coordinator = db.query(User).filter(User.id == assignment.coordinator_id).first()
        
        if not patient or not coordinator or not coordinator.line_id:
            return
        
        # 取得等候時間
        wait_info = wait_time_service.estimate_wait_time(db, next_exam_code, exam_date)
        estimated_wait = wait_info["estimated_wait"] if wait_info else None
        
        station_name = exam.name if exam else next_exam_code
        
        messages = line_notify.create_next_station_notification(
            patient_name=patient.name,
            station_name=station_name,
            estimated_wait=estimated_wait,
        )
        
        await line_notify.send_push_message(coordinator.line_id, messages)
    
    except Exception as e:
        print(f"發送下一站通知失敗: {e}")
