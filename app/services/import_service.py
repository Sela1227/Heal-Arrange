# -*- coding: utf-8 -*-
"""
病人匯入服務 - CSV/Excel 批量匯入
"""

import csv
import io
from datetime import date
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session

from ..models.patient import Patient


def parse_csv_content(content: str) -> Tuple[List[Dict], List[str]]:
    """
    解析 CSV 內容
    
    預期格式（有標題行）:
    chart_no,name,gender,birthday,phone,exam_list,vip_level,notes
    
    Returns:
        (patients_data, errors)
    """
    patients = []
    errors = []
    
    try:
        reader = csv.DictReader(io.StringIO(content))
        
        for i, row in enumerate(reader, start=2):  # 從第2行開始（第1行是標題）
            try:
                # 必填欄位檢查
                chart_no = row.get('chart_no', '').strip()
                name = row.get('name', '').strip()
                
                if not chart_no:
                    errors.append(f"第 {i} 行：缺少病歷號")
                    continue
                if not name:
                    errors.append(f"第 {i} 行：缺少姓名")
                    continue
                
                patient_data = {
                    'chart_no': chart_no,
                    'name': name,
                    'gender': row.get('gender', '').strip() or None,
                    'birthday': row.get('birthday', '').strip() or None,
                    'phone': row.get('phone', '').strip() or None,
                    'exam_list': row.get('exam_list', '').strip() or None,
                    'vip_level': int(row.get('vip_level', 0) or 0),
                    'notes': row.get('notes', '').strip() or None,
                }
                
                patients.append(patient_data)
                
            except Exception as e:
                errors.append(f"第 {i} 行：{str(e)}")
    
    except Exception as e:
        errors.append(f"CSV 解析錯誤：{str(e)}")
    
    return patients, errors


def import_patients_for_date(
    db: Session,
    patients_data: List[Dict],
    exam_date: date
) -> Tuple[int, int, List[str]]:
    """
    匯入病人資料
    
    Returns:
        (created_count, updated_count, errors)
    """
    created = 0
    updated = 0
    errors = []
    
    for data in patients_data:
        try:
            chart_no = data['chart_no']
            
            # 檢查是否已存在
            existing = db.query(Patient).filter(
                Patient.chart_no == chart_no,
                Patient.exam_date == exam_date
            ).first()
            
            if existing:
                # 更新
                existing.name = data['name']
                existing.gender = data.get('gender')
                existing.birthday = data.get('birthday')
                existing.phone = data.get('phone')
                existing.exam_list = data.get('exam_list')
                existing.vip_level = data.get('vip_level', 0)
                existing.notes = data.get('notes')
                updated += 1
            else:
                # 新增
                patient = Patient(
                    chart_no=chart_no,
                    name=data['name'],
                    gender=data.get('gender'),
                    birthday=data.get('birthday'),
                    phone=data.get('phone'),
                    exam_date=exam_date,
                    exam_list=data.get('exam_list'),
                    vip_level=data.get('vip_level', 0),
                    notes=data.get('notes'),
                    is_active=True,
                )
                db.add(patient)
                created += 1
        
        except Exception as e:
            errors.append(f"病歷號 {data.get('chart_no', '?')}：{str(e)}")
    
    db.commit()
    return created, updated, errors


def get_csv_template() -> str:
    """取得 CSV 範本"""
    return """chart_no,name,gender,birthday,phone,exam_list,vip_level,notes
A12345678,王小明,M,1980-01-15,0912345678,"CT,MRI,US",0,
A23456789,李小華,F,1990-05-20,0923456789,"CT,ECHO",1,VIP客戶
A34567890,張大同,M,1975-12-01,0934567890,"MRI,XR",0,需輪椅"""


def clear_patients_for_date(db: Session, exam_date: date) -> int:
    """清除指定日期的病人資料"""
    count = db.query(Patient).filter(Patient.exam_date == exam_date).delete()
    db.commit()
    return count
