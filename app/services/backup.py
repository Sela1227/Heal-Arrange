# -*- coding: utf-8 -*-
"""
備份服務 - 資料匯出與備份
"""

from datetime import datetime, date
from typing import Dict, List
from sqlalchemy.orm import Session
import json
import csv
import io

from ..models.user import User
from ..models.patient import Patient
from ..models.exam import Exam
from ..models.equipment import Equipment, EquipmentLog
from ..models.tracking import PatientTracking, TrackingHistory, CoordinatorAssignment


def export_users_csv(db: Session) -> str:
    """匯出使用者資料"""
    users = db.query(User).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'LINE ID', '顯示名稱', '角色', '權限', '是否啟用', '建立時間', '最後登入'])
    
    for u in users:
        permissions = ','.join(u.permissions) if u.permissions else ''
        writer.writerow([
            u.id,
            u.line_user_id,
            u.display_name,
            u.role,
            permissions,
            '是' if u.is_active else '否',
            u.created_at.strftime('%Y-%m-%d %H:%M:%S') if u.created_at else '',
            u.last_login.strftime('%Y-%m-%d %H:%M:%S') if u.last_login else '',
        ])
    
    return output.getvalue()


def export_patients_csv(db: Session, exam_date: date = None) -> str:
    """匯出病人資料"""
    query = db.query(Patient)
    if exam_date:
        query = query.filter(Patient.exam_date == exam_date)
    patients = query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '病歷號', '姓名', '檢查日期', '檢查項目', 'VIP等級', '是否啟用'])
    
    for p in patients:
        writer.writerow([
            p.id,
            p.chart_no,
            p.name,
            p.exam_date.strftime('%Y-%m-%d') if p.exam_date else '',
            p.exam_list or '',
            p.vip_level,
            '是' if p.is_active else '否',
        ])
    
    return output.getvalue()


def export_exams_csv(db: Session) -> str:
    """匯出檢查項目資料"""
    exams = db.query(Exam).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '代碼', '名稱', '時間(分)', '位置', '是否啟用'])
    
    for e in exams:
        writer.writerow([
            e.id,
            e.exam_code,
            e.name,
            e.duration_minutes,
            e.location or '',
            '是' if e.is_active else '否',
        ])
    
    return output.getvalue()


def export_equipment_csv(db: Session) -> str:
    """匯出設備資料"""
    equipment = db.query(Equipment).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '名稱', '位置', '類型', '狀態', '是否啟用'])
    
    for e in equipment:
        writer.writerow([
            e.id,
            e.name,
            e.location,
            e.equipment_type or '',
            e.status,
            '是' if e.is_active else '否',
        ])
    
    return output.getvalue()


def export_tracking_history_csv(db: Session, exam_date: date = None) -> str:
    """匯出追蹤歷程"""
    query = db.query(TrackingHistory)
    if exam_date:
        query = query.filter(TrackingHistory.exam_date == exam_date)
    history = query.order_by(TrackingHistory.timestamp.desc()).all()
    
    # 取得病人和使用者資訊
    patient_ids = list(set(h.patient_id for h in history))
    patients = {p.id: p for p in db.query(Patient).filter(Patient.id.in_(patient_ids)).all()}
    
    operator_ids = list(set(h.operator_id for h in history if h.operator_id))
    operators = {u.id: u for u in db.query(User).filter(User.id.in_(operator_ids)).all()}
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '時間', '檢查日期', '病人', '病歷號', '動作', '位置', '狀態', '操作者', '備註'])
    
    for h in history:
        patient = patients.get(h.patient_id)
        operator = operators.get(h.operator_id) if h.operator_id else None
        writer.writerow([
            h.id,
            h.timestamp.strftime('%Y-%m-%d %H:%M:%S') if h.timestamp else '',
            h.exam_date.strftime('%Y-%m-%d') if h.exam_date else '',
            patient.name if patient else '',
            patient.chart_no if patient else '',
            h.action,
            h.location or '',
            h.status or '',
            operator.display_name if operator else '',
            h.notes or '',
        ])
    
    return output.getvalue()


def export_all_data_json(db: Session) -> str:
    """匯出所有資料為 JSON（完整備份）"""
    data = {
        "export_time": datetime.utcnow().isoformat(),
        "users": [],
        "patients": [],
        "exams": [],
        "equipment": [],
        "tracking_history": [],
    }
    
    # 使用者
    for u in db.query(User).all():
        data["users"].append({
            "id": u.id,
            "line_user_id": u.line_user_id,
            "display_name": u.display_name,
            "picture_url": u.picture_url,
            "permissions": u.permissions,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        })
    
    # 病人
    for p in db.query(Patient).all():
        data["patients"].append({
            "id": p.id,
            "chart_no": p.chart_no,
            "name": p.name,
            "exam_date": p.exam_date.isoformat() if p.exam_date else None,
            "exam_list": p.exam_list,
            "vip_level": p.vip_level,
            "is_active": p.is_active,
        })
    
    # 檢查項目
    for e in db.query(Exam).all():
        data["exams"].append({
            "id": e.id,
            "exam_code": e.exam_code,
            "name": e.name,
            "duration_minutes": e.duration_minutes,
            "location": e.location,
            "is_active": e.is_active,
        })
    
    # 設備
    for e in db.query(Equipment).all():
        data["equipment"].append({
            "id": e.id,
            "name": e.name,
            "location": e.location,
            "equipment_type": e.equipment_type,
            "status": e.status,
            "is_active": e.is_active,
        })
    
    # 追蹤歷程（最近 30 天）
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=30)
    for h in db.query(TrackingHistory).filter(TrackingHistory.timestamp >= cutoff).all():
        data["tracking_history"].append({
            "id": h.id,
            "patient_id": h.patient_id,
            "exam_date": h.exam_date.isoformat() if h.exam_date else None,
            "action": h.action,
            "location": h.location,
            "status": h.status,
            "operator_id": h.operator_id,
            "notes": h.notes,
            "timestamp": h.timestamp.isoformat() if h.timestamp else None,
        })
    
    return json.dumps(data, ensure_ascii=False, indent=2)


def get_backup_summary(db: Session) -> Dict:
    """取得備份摘要資訊"""
    return {
        "users": db.query(User).count(),
        "patients": db.query(Patient).count(),
        "exams": db.query(Exam).count(),
        "equipment": db.query(Equipment).count(),
        "tracking_history": db.query(TrackingHistory).count(),
        "equipment_logs": db.query(EquipmentLog).count(),
    }
