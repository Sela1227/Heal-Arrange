# -*- coding: utf-8 -*-
"""
等候時間預估服務
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.patient import Patient
from ..models.exam import Exam
from ..models.tracking import PatientTracking, TrackingHistory, TrackingStatus
from ..models.equipment import Equipment, EquipmentStatus


def get_exam_average_duration(db: Session, exam_code: str, days: int = 7) -> int:
    """
    計算檢查項目的平均實際耗時（分鐘）
    根據近 N 天的歷史記錄計算
    """
    cutoff = date.today() - timedelta(days=days)
    
    # 找出該檢查站的開始和完成記錄
    starts = db.query(TrackingHistory).filter(
        TrackingHistory.location == exam_code,
        TrackingHistory.action == 'start',
        TrackingHistory.exam_date >= cutoff
    ).all()
    
    completes = db.query(TrackingHistory).filter(
        TrackingHistory.location == exam_code,
        TrackingHistory.action == 'complete',
        TrackingHistory.exam_date >= cutoff
    ).all()
    
    # 配對計算實際耗時
    durations = []
    for start in starts:
        # 找同病人同日期的完成記錄
        for complete in completes:
            if (complete.patient_id == start.patient_id and 
                complete.exam_date == start.exam_date and
                complete.timestamp > start.timestamp):
                duration = (complete.timestamp - start.timestamp).total_seconds() / 60
                if 1 <= duration <= 120:  # 合理範圍 1-120 分鐘
                    durations.append(duration)
                break
    
    if durations:
        return int(sum(durations) / len(durations))
    
    # 沒有歷史資料，返回預設時間
    exam = db.query(Exam).filter(Exam.exam_code == exam_code).first()
    return exam.duration_min if exam else 15


def estimate_wait_time(
    db: Session,
    exam_code: str,
    exam_date: date = None
) -> Dict:
    """
    預估某檢查站的等候時間
    
    Returns:
        {
            "exam_code": "CT",
            "exam_name": "電腦斷層",
            "waiting_count": 3,
            "in_exam_count": 1,
            "avg_duration": 30,
            "estimated_wait": 45,  # 預估等候分鐘
            "status": "normal" | "busy" | "very_busy"
        }
    """
    if exam_date is None:
        exam_date = date.today()
    
    exam = db.query(Exam).filter(Exam.exam_code == exam_code).first()
    if not exam:
        return None
    
    # 目前等候人數
    waiting_count = db.query(PatientTracking).filter(
        PatientTracking.exam_date == exam_date,
        PatientTracking.current_location == exam_code,
        PatientTracking.current_status == TrackingStatus.WAITING.value
    ).count()
    
    # 目前檢查中人數
    in_exam_count = db.query(PatientTracking).filter(
        PatientTracking.exam_date == exam_date,
        PatientTracking.current_location == exam_code,
        PatientTracking.current_status == TrackingStatus.IN_EXAM.value
    ).count()
    
    # 平均檢查時間
    avg_duration = get_exam_average_duration(db, exam_code)
    
    # 預估等候時間 = 等候人數 * 平均時間 + (檢查中 ? 平均時間/2 : 0)
    estimated_wait = waiting_count * avg_duration
    if in_exam_count > 0:
        estimated_wait += avg_duration // 2  # 假設檢查中的還要一半時間
    
    # 設備狀態
    equipment = db.query(Equipment).filter(
        Equipment.location == exam_code,
        Equipment.is_active == True
    ).first()
    
    equipment_ok = True
    if equipment and equipment.status == EquipmentStatus.BROKEN.value:
        equipment_ok = False
        estimated_wait = -1  # 設備故障，無法預估
    
    # 判斷忙碌程度
    if not equipment_ok:
        status = "broken"
    elif waiting_count >= 5:
        status = "very_busy"
    elif waiting_count >= 2:
        status = "busy"
    else:
        status = "normal"
    
    return {
        "exam_code": exam_code,
        "exam_name": exam.name,
        "waiting_count": waiting_count,
        "in_exam_count": in_exam_count,
        "avg_duration": avg_duration,
        "estimated_wait": estimated_wait,
        "equipment_ok": equipment_ok,
        "status": status,
    }


def estimate_all_stations(db: Session, exam_date: date = None) -> List[Dict]:
    """預估所有檢查站的等候時間"""
    if exam_date is None:
        exam_date = date.today()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    results = []
    for exam in exams:
        estimate = estimate_wait_time(db, exam.exam_code, exam_date)
        if estimate:
            results.append(estimate)
    
    return results


def estimate_patient_remaining_time(
    db: Session,
    patient_id: int,
    exam_date: date = None
) -> Dict:
    """
    預估病人剩餘總檢查時間
    
    Returns:
        {
            "total_exams": 5,
            "completed_exams": 2,
            "remaining_exams": 3,
            "estimated_remaining": 90,  # 分鐘
            "next_station_wait": 15,
        }
    """
    if exam_date is None:
        exam_date = date.today()
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient or not patient.notes:
        return None
    
    # 解析檢查項目（從 notes 欄位讀取）
    exam_codes = [e.strip() for e in patient.notes.split(',') if e.strip()]
    total_exams = len(exam_codes)
    
    # 已完成的檢查
    completed = db.query(TrackingHistory).filter(
        TrackingHistory.patient_id == patient_id,
        TrackingHistory.exam_date == exam_date,
        TrackingHistory.action == 'complete'
    ).all()
    completed_locations = set(h.location for h in completed)
    completed_exams = len([e for e in exam_codes if e in completed_locations])
    
    # 剩餘檢查
    remaining_codes = [e for e in exam_codes if e not in completed_locations]
    remaining_exams = len(remaining_codes)
    
    # 預估剩餘時間
    estimated_remaining = 0
    for code in remaining_codes:
        estimate = estimate_wait_time(db, code, exam_date)
        if estimate and estimate["estimated_wait"] >= 0:
            estimated_remaining += estimate["estimated_wait"] + estimate["avg_duration"]
    
    # 下一站等候時間
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date
    ).first()
    
    next_station_wait = 0
    if tracking and tracking.next_exam_code:
        next_estimate = estimate_wait_time(db, tracking.next_exam_code, exam_date)
        if next_estimate and next_estimate["estimated_wait"] >= 0:
            next_station_wait = next_estimate["estimated_wait"]
    
    return {
        "total_exams": total_exams,
        "completed_exams": completed_exams,
        "remaining_exams": remaining_exams,
        "estimated_remaining": estimated_remaining,
        "next_station_wait": next_station_wait,
    }


def format_wait_time(minutes: int) -> str:
    """格式化等候時間顯示"""
    if minutes < 0:
        return "無法預估"
    if minutes == 0:
        return "無需等候"
    if minutes < 60:
        return f"約 {minutes} 分鐘"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"約 {hours} 小時"
    return f"約 {hours} 小時 {mins} 分"
