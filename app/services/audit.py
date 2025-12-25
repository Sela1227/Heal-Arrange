# -*- coding: utf-8 -*-
"""
操作日誌服務 - 記錄與查詢操作日誌
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from ..models.audit import AuditLog, AuditAction, ACTION_LABELS
from ..models.user import User


def log_action(
    db: Session,
    action: str,
    user_id: int = None,
    user_name: str = None,
    target_type: str = None,
    target_id: int = None,
    target_name: str = None,
    details: dict = None,
    ip_address: str = None,
    user_agent: str = None,
) -> AuditLog:
    """記錄操作日誌"""
    log = AuditLog(
        user_id=user_id,
        user_name=user_name,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def log_user_action(
    db: Session,
    user: User,
    action: str,
    request = None,
    target_type: str = None,
    target_id: int = None,
    target_name: str = None,
    details: dict = None,
):
    """方便的日誌記錄函數（自動從 User 和 Request 取得資訊）"""
    ip_address = None
    user_agent = None
    
    if request:
        # 嘗試取得 IP
        ip_address = request.client.host if request.client else None
        # 嘗試從 headers 取得真實 IP（如果有 proxy）
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        # 取得 User-Agent
        user_agent = request.headers.get("user-agent", "")[:255]
    
    return log_action(
        db=db,
        action=action,
        user_id=user.id if user else None,
        user_name=user.display_name if user else None,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def get_audit_logs(
    db: Session,
    start_date: date = None,
    end_date: date = None,
    action: str = None,
    user_id: int = None,
    target_type: str = None,
    limit: int = 100,
    offset: int = 0,
) -> List[AuditLog]:
    """查詢操作日誌"""
    query = db.query(AuditLog)
    
    if start_date:
        query = query.filter(AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.filter(AuditLog.created_at <= datetime.combine(end_date, datetime.max.time()))
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    
    return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()


def get_audit_log_count(
    db: Session,
    start_date: date = None,
    end_date: date = None,
    action: str = None,
    user_id: int = None,
) -> int:
    """取得日誌數量"""
    query = db.query(AuditLog)
    
    if start_date:
        query = query.filter(AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.filter(AuditLog.created_at <= datetime.combine(end_date, datetime.max.time()))
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    return query.count()


def get_recent_logs(db: Session, limit: int = 20) -> List[AuditLog]:
    """取得最近的操作日誌"""
    return db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).all()


def get_user_activity(db: Session, user_id: int, days: int = 7) -> List[AuditLog]:
    """取得使用者近期活動"""
    start_date = datetime.utcnow() - timedelta(days=days)
    return db.query(AuditLog).filter(
        AuditLog.user_id == user_id,
        AuditLog.created_at >= start_date
    ).order_by(desc(AuditLog.created_at)).all()


def get_daily_stats(db: Session, target_date: date = None) -> Dict:
    """取得每日操作統計"""
    if target_date is None:
        target_date = date.today()
    
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    
    logs = db.query(AuditLog).filter(
        AuditLog.created_at >= start,
        AuditLog.created_at <= end
    ).all()
    
    # 按類型統計
    action_counts = {}
    for log in logs:
        action_counts[log.action] = action_counts.get(log.action, 0) + 1
    
    # 按使用者統計
    user_counts = {}
    for log in logs:
        if log.user_name:
            user_counts[log.user_name] = user_counts.get(log.user_name, 0) + 1
    
    return {
        "date": target_date,
        "total": len(logs),
        "by_action": action_counts,
        "by_user": user_counts,
    }


def export_audit_logs_csv(
    db: Session,
    start_date: date = None,
    end_date: date = None,
) -> str:
    """匯出操作日誌為 CSV"""
    logs = get_audit_logs(db, start_date=start_date, end_date=end_date, limit=10000)
    
    lines = ["時間,操作者,操作類型,對象類型,對象名稱,IP位址"]
    
    for log in logs:
        action_label = ACTION_LABELS.get(log.action, log.action)
        line = f"{log.created_at.strftime('%Y-%m-%d %H:%M:%S')},{log.user_name or '-'},{action_label},{log.target_type or '-'},{log.target_name or '-'},{log.ip_address or '-'}"
        lines.append(line)
    
    return "\n".join(lines)


# 所有可用的操作類型（供 UI 篩選使用）
ALL_ACTIONS = [
    {"value": a.value, "label": ACTION_LABELS.get(a.value, a.value)}
    for a in AuditAction
]
