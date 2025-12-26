# -*- coding: utf-8 -*-
"""
排程優化服務 - OR-Tools 排程建議 + 衝突檢測
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.patient import Patient
from ..models.exam import Exam
from ..models.tracking import PatientTracking, TrackingStatus


def get_exam_dependencies() -> Dict[str, List[str]]:
    """
    取得檢查項目的依賴關係
    某些檢查必須在其他檢查之前完成
    
    Returns:
        {exam_code: [must_be_after_these_exams]}
    """
    return {
        # 內視鏡需要空腹，應該排在抽血之後
        'ENDO': ['BLOOD'],
        # CT/MRI 通常排在後面
        'CT': ['BLOOD', 'US'],
        'MRI': ['BLOOD', 'US'],
        # 醫師諮詢應該最後
        'CONSULT': ['PHY', 'BLOOD', 'XRAY', 'US', 'CT', 'MRI', 'ENDO', 'CARDIO'],
    }


def get_exam_conflicts() -> List[Tuple[str, str]]:
    """
    取得互斥的檢查項目（不能同時進行）
    
    Returns:
        [(exam1, exam2), ...] 不能同時進行的檢查對
    """
    return [
        # 這些通常不會衝突，但可以根據實際情況設定
        # ('CT', 'MRI'),  # 如果只有一台大型設備
    ]


def detect_schedule_conflicts(
    db: Session,
    patient_id: int,
    exam_date: date = None,
) -> List[Dict]:
    """
    檢測病人排程衝突
    
    Returns:
        [{"type": str, "message": str, "severity": str}, ...]
    """
    if exam_date is None:
        exam_date = date.today()
    
    conflicts = []
    
    # 取得病人資料
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient or not patient.exam_list:
        return conflicts
    
    # 解析檢查項目
    exam_codes = [e.strip() for e in patient.exam_list.split(',') if e.strip()]
    
    # 取得檢查項目詳細資料
    exams = db.query(Exam).filter(Exam.exam_code.in_(exam_codes)).all()
    exam_dict = {e.exam_code: e for e in exams}
    
    # 取得目前追蹤狀態
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date,
    ).first()
    
    # 1. 檢查依賴關係
    dependencies = get_exam_dependencies()
    completed_exams = set()  # 已完成的檢查
    
    # TODO: 從歷史記錄取得已完成的檢查
    
    for exam_code in exam_codes:
        if exam_code in dependencies:
            required = dependencies[exam_code]
            missing = [r for r in required if r in exam_codes and r not in completed_exams]
            if missing:
                conflicts.append({
                    "type": "dependency",
                    "exam_code": exam_code,
                    "message": f"{exam_code} 建議在 {', '.join(missing)} 之後進行",
                    "severity": "warning",
                })
    
    # 2. 檢查容量衝突
    for exam_code in exam_codes:
        exam = exam_dict.get(exam_code)
        if not exam:
            continue
        
        # 檢查該站目前等候人數
        waiting_count = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.current_location == exam_code,
            PatientTracking.current_status.in_([
                TrackingStatus.WAITING.value,
                TrackingStatus.IN_EXAM.value,
            ])
        ).count()
        
        # 取得容量限制
        capacity = getattr(exam, 'capacity', None) or 5  # 預設容量 5
        
        if waiting_count >= capacity:
            conflicts.append({
                "type": "capacity",
                "exam_code": exam_code,
                "message": f"{exam.name} 目前已滿（{waiting_count}/{capacity}人）",
                "severity": "error",
            })
        elif waiting_count >= capacity * 0.8:
            conflicts.append({
                "type": "capacity",
                "exam_code": exam_code,
                "message": f"{exam.name} 接近滿載（{waiting_count}/{capacity}人）",
                "severity": "warning",
            })
    
    # 3. 檢查設備狀態
    from ..models.equipment import Equipment, EquipmentStatus
    
    for exam_code in exam_codes:
        broken_equipment = db.query(Equipment).filter(
            Equipment.location == exam_code,
            Equipment.status == EquipmentStatus.BROKEN.value,
            Equipment.is_active == True,
        ).first()
        
        if broken_equipment:
            conflicts.append({
                "type": "equipment",
                "exam_code": exam_code,
                "message": f"{exam_code} 設備故障中（{broken_equipment.name}）",
                "severity": "error",
            })
    
    return conflicts


def suggest_next_station(
    db: Session,
    patient_id: int,
    exam_date: date = None,
) -> List[Dict]:
    """
    建議病人下一站
    
    Returns:
        [{"exam_code": str, "exam_name": str, "score": int, "reason": str}, ...]
        按照推薦分數排序（高分優先）
    """
    if exam_date is None:
        exam_date = date.today()
    
    # 取得病人資料
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient or not patient.exam_list:
        return []
    
    # 解析檢查項目
    all_exams = [e.strip() for e in patient.exam_list.split(',') if e.strip()]
    
    # 取得已完成的檢查
    from ..models.tracking import TrackingHistory
    completed_history = db.query(TrackingHistory).filter(
        TrackingHistory.patient_id == patient_id,
        TrackingHistory.exam_date == exam_date,
        TrackingHistory.action == 'complete',
    ).all()
    completed_exams = set(h.location for h in completed_history if h.location)
    
    # 取得目前位置
    tracking = db.query(PatientTracking).filter(
        PatientTracking.patient_id == patient_id,
        PatientTracking.exam_date == exam_date,
    ).first()
    current_location = tracking.current_location if tracking else None
    
    # 過濾出尚未完成的檢查
    remaining_exams = [e for e in all_exams if e not in completed_exams and e != current_location]
    
    if not remaining_exams:
        return []
    
    # 取得檢查項目詳細資料
    exams = db.query(Exam).filter(Exam.exam_code.in_(remaining_exams)).all()
    exam_dict = {e.exam_code: e for e in exams}
    
    # 取得依賴關係
    dependencies = get_exam_dependencies()
    
    suggestions = []
    
    for exam_code in remaining_exams:
        exam = exam_dict.get(exam_code)
        if not exam:
            continue
        
        score = 100
        reasons = []
        
        # 1. 檢查依賴是否滿足
        if exam_code in dependencies:
            required = dependencies[exam_code]
            missing = [r for r in required if r in all_exams and r not in completed_exams]
            if missing:
                score -= 50  # 依賴未滿足，大幅降低分數
                reasons.append(f"建議先完成 {', '.join(missing)}")
        
        # 2. 檢查等候人數
        waiting_count = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.current_location == exam_code,
            PatientTracking.current_status == TrackingStatus.WAITING.value,
        ).count()
        
        in_exam_count = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.current_location == exam_code,
            PatientTracking.current_status == TrackingStatus.IN_EXAM.value,
        ).count()
        
        total_waiting = waiting_count + in_exam_count
        
        if total_waiting == 0:
            score += 30
            reasons.append("目前無人等候")
        elif total_waiting <= 2:
            score += 15
            reasons.append(f"等候人數少（{total_waiting}人）")
        elif total_waiting >= 5:
            score -= 20
            reasons.append(f"等候人數多（{total_waiting}人）")
        
        # 3. 檢查設備狀態
        from ..models.equipment import Equipment, EquipmentStatus
        
        broken = db.query(Equipment).filter(
            Equipment.location == exam_code,
            Equipment.status == EquipmentStatus.BROKEN.value,
            Equipment.is_active == True,
        ).first()
        
        if broken:
            score -= 100  # 設備故障，不建議
            reasons.append("設備故障中")
        
        # 4. 檢查時間（早上適合空腹檢查）
        current_hour = datetime.now().hour
        if exam_code in ['ENDO', 'US'] and current_hour < 10:
            score += 10
            reasons.append("適合早上空腹進行")
        
        # 5. CONSULT 應該最後
        if exam_code == 'CONSULT':
            remaining_non_consult = [e for e in remaining_exams if e != 'CONSULT']
            if remaining_non_consult:
                score -= 40
                reasons.append("建議其他檢查完成後再諮詢")
        
        suggestions.append({
            "exam_code": exam_code,
            "exam_name": exam.name,
            "score": max(0, score),
            "reason": "；".join(reasons) if reasons else "可立即前往",
            "waiting_count": total_waiting,
            "duration_minutes": exam.duration_minutes,
        })
    
    # 按分數排序
    suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    return suggestions


def optimize_daily_schedule(
    db: Session,
    exam_date: date = None,
) -> Dict:
    """
    優化當日排程（使用簡單啟發式演算法）
    
    Returns:
        {
            "suggestions": [...],
            "bottlenecks": [...],
            "estimated_completion_time": str,
        }
    """
    if exam_date is None:
        exam_date = date.today()
    
    # 取得當日所有病人
    patients = db.query(Patient).filter(
        Patient.exam_date == exam_date,
        Patient.is_active == True,
    ).all()
    
    # 取得所有檢查站
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    exam_dict = {e.exam_code: e for e in exams}
    
    # 統計各站需求
    station_demand = {}
    for exam in exams:
        station_demand[exam.exam_code] = {
            "name": exam.name,
            "duration": exam.duration_minutes,
            "capacity": getattr(exam, 'capacity', 1) or 1,
            "total_needed": 0,
            "completed": 0,
            "waiting": 0,
        }
    
    for patient in patients:
        if not patient.exam_list:
            continue
        for code in patient.exam_list.split(','):
            code = code.strip()
            if code in station_demand:
                station_demand[code]['total_needed'] += 1
    
    # 統計目前進度
    for code in station_demand:
        # 等候中
        waiting = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.current_location == code,
            PatientTracking.current_status == TrackingStatus.WAITING.value,
        ).count()
        station_demand[code]['waiting'] = waiting
        
        # 已完成（從歷史記錄）
        from ..models.tracking import TrackingHistory
        completed = db.query(TrackingHistory).filter(
            TrackingHistory.exam_date == exam_date,
            TrackingHistory.location == code,
            TrackingHistory.action == 'complete',
        ).count()
        station_demand[code]['completed'] = completed
    
    # 找出瓶頸
    bottlenecks = []
    for code, data in station_demand.items():
        remaining = data['total_needed'] - data['completed']
        if remaining <= 0:
            continue
        
        # 預估完成時間
        capacity = data['capacity']
        duration = data['duration']
        estimated_minutes = (remaining / capacity) * duration
        
        if estimated_minutes > 120:  # 超過 2 小時
            bottlenecks.append({
                "exam_code": code,
                "exam_name": data['name'],
                "remaining": remaining,
                "estimated_minutes": int(estimated_minutes),
                "severity": "high" if estimated_minutes > 180 else "medium",
                "suggestion": f"建議增加人手或設備",
            })
    
    # 排序瓶頸
    bottlenecks.sort(key=lambda x: x['estimated_minutes'], reverse=True)
    
    # 整體預估完成時間
    if bottlenecks:
        max_minutes = bottlenecks[0]['estimated_minutes']
        estimated_completion = datetime.now() + timedelta(minutes=max_minutes)
        estimated_completion_time = estimated_completion.strftime('%H:%M')
    else:
        estimated_completion_time = "已完成或無資料"
    
    return {
        "station_demand": station_demand,
        "bottlenecks": bottlenecks,
        "estimated_completion_time": estimated_completion_time,
        "total_patients": len(patients),
    }


def get_capacity_status(db: Session, exam_date: date = None) -> List[Dict]:
    """
    取得各檢查站容量狀態
    """
    if exam_date is None:
        exam_date = date.today()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    status_list = []
    for exam in exams:
        capacity = getattr(exam, 'capacity', None) or 5
        
        # 目前在該站的人數
        current_count = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.current_location == exam.exam_code,
            PatientTracking.current_status.in_([
                TrackingStatus.WAITING.value,
                TrackingStatus.IN_EXAM.value,
            ])
        ).count()
        
        # 正在檢查中
        in_exam = db.query(PatientTracking).filter(
            PatientTracking.exam_date == exam_date,
            PatientTracking.current_location == exam.exam_code,
            PatientTracking.current_status == TrackingStatus.IN_EXAM.value,
        ).count()
        
        utilization = round(current_count / capacity * 100) if capacity > 0 else 0
        
        status_list.append({
            "exam_code": exam.exam_code,
            "exam_name": exam.name,
            "capacity": capacity,
            "current_count": current_count,
            "in_exam": in_exam,
            "waiting": current_count - in_exam,
            "utilization": utilization,
            "status": "full" if utilization >= 100 else "busy" if utilization >= 70 else "normal",
        })
    
    return status_list
