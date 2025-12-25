# -*- coding: utf-8 -*-
"""
效能儀表板服務 - KPI 計算與監控
"""

from datetime import datetime, date, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.patient import Patient
from ..models.user import User
from ..models.exam import Exam
from ..models.tracking import PatientTracking, TrackingHistory, TrackingStatus, CoordinatorAssignment
from ..models.equipment import Equipment, EquipmentStatus, EquipmentLog


def get_realtime_kpi(db: Session) -> Dict:
    """取得即時 KPI"""
    today = date.today()
    now = datetime.utcnow()
    
    # 今日病人統計
    total_patients = db.query(Patient).filter(
        Patient.exam_date == today,
        Patient.is_active == True
    ).count()
    
    completed = db.query(PatientTracking).filter(
        PatientTracking.exam_date == today,
        PatientTracking.current_status == TrackingStatus.COMPLETED.value
    ).count()
    
    in_progress = db.query(PatientTracking).filter(
        PatientTracking.exam_date == today,
        PatientTracking.current_status.in_([
            TrackingStatus.WAITING.value,
            TrackingStatus.IN_EXAM.value,
            TrackingStatus.MOVING.value
        ])
    ).count()
    
    not_started = total_patients - completed - in_progress
    
    # 完成率
    completion_rate = round(completed / total_patients * 100, 1) if total_patients > 0 else 0
    
    # 設備狀態
    total_equipment = db.query(Equipment).filter(Equipment.is_active == True).count()
    broken_equipment = db.query(Equipment).filter(
        Equipment.status == EquipmentStatus.BROKEN.value,
        Equipment.is_active == True
    ).count()
    
    # 個管師工作狀態
    active_coordinators = db.query(CoordinatorAssignment).filter(
        CoordinatorAssignment.exam_date == today,
        CoordinatorAssignment.is_active == True
    ).count()
    
    total_coordinators = db.query(User).filter(
        User.is_active == True,
        User.permissions.contains(["coordinator"])
    ).count()
    
    # 今日操作次數
    today_start = datetime.combine(today, datetime.min.time())
    operations_today = db.query(TrackingHistory).filter(
        TrackingHistory.exam_date == today
    ).count()
    
    return {
        "timestamp": now.isoformat(),
        "patients": {
            "total": total_patients,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "completion_rate": completion_rate,
        },
        "equipment": {
            "total": total_equipment,
            "broken": broken_equipment,
            "operational": total_equipment - broken_equipment,
            "health_rate": round((total_equipment - broken_equipment) / total_equipment * 100, 1) if total_equipment > 0 else 100,
        },
        "coordinators": {
            "active": active_coordinators,
            "total": total_coordinators,
            "utilization": round(active_coordinators / total_coordinators * 100, 1) if total_coordinators > 0 else 0,
        },
        "operations": {
            "today": operations_today,
        }
    }


def get_hourly_stats(db: Session, target_date: date = None) -> List[Dict]:
    """取得每小時統計（用於圖表）"""
    if target_date is None:
        target_date = date.today()
    
    hourly = []
    for hour in range(7, 18):  # 07:00 - 17:00
        start_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour))
        end_time = start_time + timedelta(hours=1)
        
        # 該小時的完成數
        completed = db.query(TrackingHistory).filter(
            TrackingHistory.exam_date == target_date,
            TrackingHistory.action == 'complete',
            TrackingHistory.timestamp >= start_time,
            TrackingHistory.timestamp < end_time
        ).count()
        
        # 該小時的開始數
        started = db.query(TrackingHistory).filter(
            TrackingHistory.exam_date == target_date,
            TrackingHistory.action == 'start',
            TrackingHistory.timestamp >= start_time,
            TrackingHistory.timestamp < end_time
        ).count()
        
        hourly.append({
            "hour": hour,
            "label": f"{hour:02d}:00",
            "completed": completed,
            "started": started,
        })
    
    return hourly


def get_station_performance(db: Session, target_date: date = None) -> List[Dict]:
    """取得各檢查站效能"""
    if target_date is None:
        target_date = date.today()
    
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    results = []
    for exam in exams:
        # 完成數
        completed = db.query(TrackingHistory).filter(
            TrackingHistory.exam_date == target_date,
            TrackingHistory.location == exam.exam_code,
            TrackingHistory.action == 'complete'
        ).count()
        
        # 目前等候
        waiting = db.query(PatientTracking).filter(
            PatientTracking.exam_date == target_date,
            PatientTracking.current_location == exam.exam_code,
            PatientTracking.current_status == TrackingStatus.WAITING.value
        ).count()
        
        # 目前檢查中
        in_exam = db.query(PatientTracking).filter(
            PatientTracking.exam_date == target_date,
            PatientTracking.current_location == exam.exam_code,
            PatientTracking.current_status == TrackingStatus.IN_EXAM.value
        ).count()
        
        # 計算平均處理時間
        avg_time = exam.duration_minutes  # 預設
        
        # 設備狀態
        equipment = db.query(Equipment).filter(
            Equipment.location == exam.exam_code,
            Equipment.is_active == True
        ).first()
        equipment_status = equipment.status if equipment else "normal"
        
        results.append({
            "exam_code": exam.exam_code,
            "exam_name": exam.name,
            "completed": completed,
            "waiting": waiting,
            "in_exam": in_exam,
            "avg_time": avg_time,
            "equipment_status": equipment_status,
            "throughput": completed,  # 吞吐量
        })
    
    # 按完成數排序
    results.sort(key=lambda x: x["completed"], reverse=True)
    
    return results


def get_coordinator_performance(db: Session, target_date: date = None) -> List[Dict]:
    """取得個管師效能"""
    if target_date is None:
        target_date = date.today()
    
    coordinators = db.query(User).filter(
        User.is_active == True
    ).all()
    
    # 篩選有 coordinator 權限的
    coordinators = [c for c in coordinators if c.permissions and 'coordinator' in c.permissions]
    
    results = []
    for coord in coordinators:
        # 今日指派數
        assignments = db.query(CoordinatorAssignment).filter(
            CoordinatorAssignment.coordinator_id == coord.id,
            CoordinatorAssignment.exam_date == target_date
        ).count()
        
        # 操作次數
        operations = db.query(TrackingHistory).filter(
            TrackingHistory.exam_date == target_date,
            TrackingHistory.operator_id == coord.id
        ).count()
        
        # 目前狀態
        current = db.query(CoordinatorAssignment).filter(
            CoordinatorAssignment.coordinator_id == coord.id,
            CoordinatorAssignment.exam_date == target_date,
            CoordinatorAssignment.is_active == True
        ).first()
        
        status = "空閒"
        if current:
            tracking = db.query(PatientTracking).filter(
                PatientTracking.patient_id == current.patient_id,
                PatientTracking.exam_date == target_date
            ).first()
            if tracking:
                if tracking.current_status == TrackingStatus.IN_EXAM.value:
                    status = "檢查中"
                elif tracking.current_status == TrackingStatus.WAITING.value:
                    status = "等候中"
                elif tracking.current_status == TrackingStatus.COMPLETED.value:
                    status = "已完成"
                else:
                    status = "進行中"
        
        results.append({
            "id": coord.id,
            "name": coord.display_name,
            "assignments": assignments,
            "operations": operations,
            "status": status,
            "is_busy": current is not None,
        })
    
    # 按操作數排序
    results.sort(key=lambda x: x["operations"], reverse=True)
    
    return results


def get_weekly_trend(db: Session) -> List[Dict]:
    """取得一週趨勢"""
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    
    daily = []
    current = start_date
    while current <= end_date:
        # 病人數
        patients = db.query(Patient).filter(
            Patient.exam_date == current,
            Patient.is_active == True
        ).count()
        
        # 完成數
        completed = db.query(PatientTracking).filter(
            PatientTracking.exam_date == current,
            PatientTracking.current_status == TrackingStatus.COMPLETED.value
        ).count()
        
        # 完成率
        rate = round(completed / patients * 100, 1) if patients > 0 else 0
        
        daily.append({
            "date": current.isoformat(),
            "label": current.strftime("%m/%d"),
            "weekday": ["一", "二", "三", "四", "五", "六", "日"][current.weekday()],
            "patients": patients,
            "completed": completed,
            "completion_rate": rate,
        })
        
        current += timedelta(days=1)
    
    return daily


def get_daily_chart_data(db: Session, days: int = 7) -> Dict:
    """取得每日圖表資料（Chart.js 格式）"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    labels = []
    patients_data = []
    completed_data = []
    rate_data = []
    
    current = start_date
    while current <= end_date:
        labels.append(current.strftime("%m/%d"))
        
        patients = db.query(Patient).filter(
            Patient.exam_date == current,
            Patient.is_active == True
        ).count()
        
        completed = db.query(PatientTracking).filter(
            PatientTracking.exam_date == current,
            PatientTracking.current_status == TrackingStatus.COMPLETED.value
        ).count()
        
        rate = round(completed / patients * 100, 1) if patients > 0 else 0
        
        patients_data.append(patients)
        completed_data.append(completed)
        rate_data.append(rate)
        
        current += timedelta(days=1)
    
    return {
        "labels": labels,
        "datasets": {
            "patients": patients_data,
            "completed": completed_data,
            "completion_rate": rate_data,
        }
    }
