# -*- coding: utf-8 -*-
"""
統計服務 - 報表與數據分析
修正：duration_minutes → duration_min
更新：個管師 → 專員
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models.patient import Patient
from ..models.user import User, UserRole
from ..models.exam import Exam
from ..models.tracking import PatientTracking, TrackingHistory, CoordinatorAssignment, TrackingStatus
from ..models.equipment import Equipment, EquipmentLog, EquipmentStatus


def get_daily_summary(db: Session, target_date: date = None) -> Dict:
    """取得每日摘要統計"""
    if target_date is None:
        target_date = date.today()
    
    # 病人統計
    total_patients = db.query(Patient).filter(
        Patient.exam_date == target_date,
        Patient.is_active == True
    ).count()
    
    # 追蹤統計
    completed = db.query(PatientTracking).filter(
        PatientTracking.exam_date == target_date,
        PatientTracking.current_status == TrackingStatus.COMPLETED.value
    ).count()
    
    in_progress = db.query(PatientTracking).filter(
        PatientTracking.exam_date == target_date,
        PatientTracking.current_status.in_([
            TrackingStatus.WAITING.value,
            TrackingStatus.IN_EXAM.value,
            TrackingStatus.MOVING.value
        ])
    ).count()
    
    not_started = total_patients - completed - in_progress
    
    # 設備統計
    total_equipment = db.query(Equipment).filter(Equipment.is_active == True).count()
    broken_equipment = db.query(Equipment).filter(
        Equipment.status == EquipmentStatus.BROKEN.value,
        Equipment.is_active == True
    ).count()
    
    # 專員統計（原個管師）
    active_coordinators = db.query(CoordinatorAssignment).filter(
        CoordinatorAssignment.exam_date == target_date,
        CoordinatorAssignment.is_active == True
    ).count()
    
    return {
        "date": target_date,
        "patients": {
            "total": total_patients,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "completion_rate": round(completed / total_patients * 100, 1) if total_patients > 0 else 0,
        },
        "equipment": {
            "total": total_equipment,
            "broken": broken_equipment,
            "operational": total_equipment - broken_equipment,
        },
        "coordinators": {
            "active": active_coordinators,
        }
    }


def get_station_statistics(db: Session, target_date: date = None) -> List[Dict]:
    """取得各檢查站統計"""
    if target_date is None:
        target_date = date.today()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    stats = []
    
    for exam in exams:
        # 該站完成的檢查數
        completed_count = db.query(TrackingHistory).filter(
            TrackingHistory.exam_date == target_date,
            TrackingHistory.location == exam.exam_code,
            TrackingHistory.action == 'complete'
        ).count()
        
        # 目前等待中
        waiting_count = db.query(PatientTracking).filter(
            PatientTracking.exam_date == target_date,
            PatientTracking.current_location == exam.exam_code,
            PatientTracking.current_status == TrackingStatus.WAITING.value
        ).count()
        
        # 目前檢查中
        in_exam_count = db.query(PatientTracking).filter(
            PatientTracking.exam_date == target_date,
            PatientTracking.current_location == exam.exam_code,
            PatientTracking.current_status == TrackingStatus.IN_EXAM.value
        ).count()
        
        # 設備狀態
        equipment = db.query(Equipment).filter(
            Equipment.location == exam.exam_code,
            Equipment.is_active == True
        ).first()
        
        equipment_status = "normal"
        if equipment:
            equipment_status = equipment.status
        
        # 修正：使用 duration_min 而非 duration_minutes
        duration = getattr(exam, 'duration_min', None) or getattr(exam, 'duration_minutes', 15)
        
        stats.append({
            "exam_code": exam.exam_code,
            "exam_name": exam.name,
            "completed": completed_count,
            "waiting": waiting_count,
            "in_exam": in_exam_count,
            "equipment_status": equipment_status,
            "duration_minutes": duration,  # 保持 API 輸出一致
        })
    
    return stats


def get_coordinator_statistics(db: Session, target_date: date = None) -> List[Dict]:
    """取得專員工作統計（含組長）"""
    if target_date is None:
        target_date = date.today()
    
    # 專員和組長都可以當專員用
    coordinators = db.query(User).filter(
        User.role.in_([UserRole.COORDINATOR.value, UserRole.LEADER.value]),
        User.is_active == True
    ).all()
    
    stats = []
    
    for coord in coordinators:
        # 今日指派的病人數
        assignments = db.query(CoordinatorAssignment).filter(
            CoordinatorAssignment.coordinator_id == coord.id,
            CoordinatorAssignment.exam_date == target_date
        ).count()
        
        # 目前負責的病人
        current_assignment = db.query(CoordinatorAssignment).filter(
            CoordinatorAssignment.coordinator_id == coord.id,
            CoordinatorAssignment.exam_date == target_date,
            CoordinatorAssignment.is_active == True
        ).first()
        
        current_patient = None
        current_status = "空閒"
        if current_assignment:
            patient = db.query(Patient).filter(Patient.id == current_assignment.patient_id).first()
            tracking = db.query(PatientTracking).filter(
                PatientTracking.patient_id == current_assignment.patient_id,
                PatientTracking.exam_date == target_date
            ).first()
            
            if patient:
                current_patient = patient.name
                if tracking:
                    if tracking.current_status == TrackingStatus.COMPLETED.value:
                        current_status = "已完成"
                    elif tracking.current_status == TrackingStatus.IN_EXAM.value:
                        current_status = "檢查中"
                    else:
                        current_status = "進行中"
                else:
                    current_status = "進行中"
        
        # 操作次數
        operations = db.query(TrackingHistory).filter(
            TrackingHistory.exam_date == target_date,
            TrackingHistory.operator_id == coord.id
        ).count()
        
        stats.append({
            "id": coord.id,
            "name": coord.display_name,
            "total_assignments": assignments,
            "current_patient": current_patient,
            "current_status": current_status,
            "operations": operations,
        })
    
    return stats


def get_history_records(
    db: Session,
    start_date: date,
    end_date: date,
    patient_id: int = None,
    exam_code: str = None,
    limit: int = 100
) -> List[Dict]:
    """取得歷史記錄"""
    query = db.query(TrackingHistory).filter(
        TrackingHistory.exam_date >= start_date,
        TrackingHistory.exam_date <= end_date
    )
    
    if patient_id:
        query = query.filter(TrackingHistory.patient_id == patient_id)
    
    if exam_code:
        query = query.filter(TrackingHistory.location == exam_code)
    
    records = query.order_by(TrackingHistory.timestamp.desc()).limit(limit).all()
    
    # 取得相關資料
    patient_ids = list(set(r.patient_id for r in records))
    patients = {p.id: p for p in db.query(Patient).filter(Patient.id.in_(patient_ids)).all()} if patient_ids else {}
    
    operator_ids = list(set(r.operator_id for r in records if r.operator_id))
    operators = {u.id: u for u in db.query(User).filter(User.id.in_(operator_ids)).all()} if operator_ids else {}
    
    result = []
    for r in records:
        patient = patients.get(r.patient_id)
        operator = operators.get(r.operator_id) if r.operator_id else None
        
        result.append({
            "id": r.id,
            "timestamp": r.timestamp,
            "exam_date": r.exam_date,
            "patient_name": patient.name if patient else "?",
            "patient_chart_no": patient.chart_no if patient else "?",
            "action": r.action,
            "location": r.location,
            "status": r.status,
            "operator_name": operator.display_name if operator else "-",
            "notes": r.notes,
        })
    
    return result


def get_date_range_summary(db: Session, start_date: date, end_date: date) -> List[Dict]:
    """取得日期範圍內每日摘要"""
    summaries = []
    current = start_date
    
    while current <= end_date:
        summary = get_daily_summary(db, current)
        summaries.append(summary)
        current += timedelta(days=1)
    
    return summaries


def export_daily_report_csv(db: Session, target_date: date = None) -> str:
    """匯出每日報表 CSV"""
    if target_date is None:
        target_date = date.today()
    
    # 取得資料
    patients = db.query(Patient).filter(
        Patient.exam_date == target_date,
        Patient.is_active == True
    ).all()
    
    # 更新：個管師 → 專員
    lines = ["病歷號,姓名,檢查項目,狀態,位置,專員,最後更新"]
    
    for patient in patients:
        tracking = db.query(PatientTracking).filter(
            PatientTracking.patient_id == patient.id,
            PatientTracking.exam_date == target_date
        ).first()
        
        assignment = db.query(CoordinatorAssignment).filter(
            CoordinatorAssignment.patient_id == patient.id,
            CoordinatorAssignment.exam_date == target_date,
            CoordinatorAssignment.is_active == True
        ).first()
        
        coordinator_name = "-"
        if assignment:
            coord = db.query(User).filter(User.id == assignment.coordinator_id).first()
            if coord:
                coordinator_name = coord.display_name
        
        status = "未開始"
        location = "-"
        updated = "-"
        
        if tracking:
            status = tracking.current_status
            location = tracking.current_location or "-"
            updated = tracking.updated_at.strftime("%H:%M") if tracking.updated_at else "-"
        
        lines.append(f"{patient.chart_no},{patient.name},{patient.exam_list or '-'},{status},{location},{coordinator_name},{updated}")
    
    return "\n".join(lines)
