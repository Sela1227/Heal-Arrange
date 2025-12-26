# -*- coding: utf-8 -*-
"""
等候時間預估服務
"""

from datetime import date, datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models.exam import Exam
from ..models.tracking import PatientTracking, TrackingHistory, TrackingStatus


def estimate_wait_time(
    db: Session,
    exam_code: str,
    exam_date: date = None,
) -> Dict:
    """
    預估某檢查站的等候時間
    
    計算方式：
    1. 取得該站目前等候人數
    2. 取得該站平均檢查時間（預設或歷史數據）
    3. 預估等候時間 = 等候人數 × 平均檢查時間
    
    Returns:
        {
            "exam_code": str,
            "waiting_count": int,
            "in_exam_count": int,
            "avg_duration": int,  # 分鐘
            "estimated_wait": int,  # 分鐘
            "estimated_ready_time": datetime,
        }
    """
    if exam_date is None:
        exam_date = date.today()
    
    # 取得檢查項目資訊
    exam = db.query(Exam).filter(Exam.exam_code == exam_code).first()
    if not exam:
        return None
    
    # 統計等候人數
    waiting_count = db.query(PatientTracking).filter(
        PatientTracking.exam_date == exam_date,
        PatientTracking.current_location == exam_code,
        PatientTracking.current_status == TrackingStatus.WAITING.value,
    ).count()
    
    # 統計檢查中人數
    in_exam_count = db.query(PatientTracking).filter(
        PatientTracking.exam_date == exam_date,
        PatientTracking.current_location == exam_code,
        PatientTracking.current_status == TrackingStatus.IN_EXAM.value,
    ).count()
    
    # 取得平均檢查時間
    avg_duration = get_average_duration(db, exam_code, exam_date)
    if avg_duration is None:
        # 使用預設時間
        avg_duration = exam.duration_min if hasattr(exam, 'duration_min') else 15
    
    # 計算預估等候時間
    # 如果有人在檢查中，假設還需要一半的時間
    estimated_wait = waiting_count * avg_duration
    if in_exam_count > 0:
        estimated_wait += avg_duration // 2
    
    # 計算預估開始時間
    estimated_ready_time = datetime.now() + timedelta(minutes=estimated_wait)
    
    return {
        "exam_code": exam_code,
        "exam_name": exam.name,
        "waiting_count": waiting_count,
        "in_exam_count": in_exam_count,
        "avg_duration": avg_duration,
        "estimated_wait": estimated_wait,
        "estimated_ready_time": estimated_ready_time,
    }


def get_average_duration(
    db: Session,
    exam_code: str,
    exam_date: date = None,
    days_back: int = 7,
) -> Optional[int]:
    """
    取得某檢查站的平均檢查時間（根據歷史數據）
    
    計算方式：
    1. 找出過去 N 天該站的「開始」和「完成」記錄
    2. 計算每次檢查的時間差
    3. 取平均值
    """
    if exam_date is None:
        exam_date = date.today()
    
    start_date = exam_date - timedelta(days=days_back)
    
    # 取得該站的開始記錄
    start_records = db.query(TrackingHistory).filter(
        TrackingHistory.exam_date >= start_date,
        TrackingHistory.exam_date <= exam_date,
        TrackingHistory.location == exam_code,
        TrackingHistory.action == 'start',
    ).all()
    
    if not start_records:
        return None
    
    durations = []
    
    for start in start_records:
        # 找對應的完成記錄
        complete = db.query(TrackingHistory).filter(
            TrackingHistory.patient_id == start.patient_id,
            TrackingHistory.exam_date == start.exam_date,
            TrackingHistory.location == exam_code,
            TrackingHistory.action == 'complete',
            TrackingHistory.timestamp > start.timestamp,
        ).first()
        
        if complete:
            duration = (complete.timestamp - start.timestamp).total_seconds() / 60
            # 過濾異常值（少於 1 分鐘或超過 2 小時）
            if 1 <= duration <= 120:
                durations.append(duration)
    
    if not durations:
        return None
    
    return int(sum(durations) / len(durations))


def get_all_stations_wait_time(
    db: Session,
    exam_date: date = None,
) -> List[Dict]:
    """取得所有檢查站的等候時間預估"""
    if exam_date is None:
        exam_date = date.today()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    results = []
    for exam in exams:
        estimate = estimate_wait_time(db, exam.exam_code, exam_date)
        if estimate:
            results.append(estimate)
    
    return results


def get_patient_queue_position(
    db: Session,
    patient_id: int,
    exam_code: str,
    exam_date: date = None,
) -> Dict:
    """
    取得病人在某檢查站的排隊位置
    
    Returns:
        {
            "position": int,  # 排隊位置（1 = 下一個）
            "estimated_wait": int,  # 預估等候分鐘
            "people_ahead": int,  # 前面幾人
        }
    """
    if exam_date is None:
        exam_date = date.today()
    
    # 取得該病人的追蹤資訊
    patient_tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date,
    ).first()
    
    if not patient_tracking:
        return None
    
    # 取得所有在該站等候的病人（按到達時間排序）
    waiting_patients = db.query(PatientTracking).filter(
        PatientTracking.exam_date == exam_date,
        PatientTracking.current_location == exam_code,
        PatientTracking.current_status == TrackingStatus.WAITING.value,
    ).order_by(PatientTracking.updated_at).all()
    
    # 找出病人位置
    position = 0
    for i, p in enumerate(waiting_patients):
        if p.patient_id == patient_id:
            position = i + 1
            break
    
    if position == 0:
        return None
    
    # 取得平均時間
    exam = db.query(Exam).filter(Exam.exam_code == exam_code).first()
    avg_duration = get_average_duration(db, exam_code, exam_date)
    if avg_duration is None and exam:
        avg_duration = exam.duration_min if hasattr(exam, 'duration_min') else 15
    
    people_ahead = position - 1
    estimated_wait = people_ahead * (avg_duration or 15)
    
    # 如果有人在檢查中，加上剩餘時間
    in_exam = db.query(PatientTracking).filter(
        PatientTracking.exam_date == exam_date,
        PatientTracking.current_location == exam_code,
        PatientTracking.current_status == TrackingStatus.IN_EXAM.value,
    ).first()
    
    if in_exam:
        estimated_wait += (avg_duration or 15) // 2
    
    return {
        "position": position,
        "estimated_wait": estimated_wait,
        "people_ahead": people_ahead,
        "avg_duration": avg_duration or 15,
    }


def format_wait_time(minutes: int) -> str:
    """格式化等候時間顯示"""
    if minutes <= 0:
        return "即將開始"
    elif minutes < 5:
        return "約 5 分鐘內"
    elif minutes < 60:
        return f"約 {minutes} 分鐘"
    else:
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"約 {hours} 小時"
        else:
            return f"約 {hours} 小時 {mins} 分鐘"
