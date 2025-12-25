# -*- coding: utf-8 -*-
"""
PDF 報表服務 - 使用 reportlab 產生 PDF 報表
"""

from datetime import date, datetime
from typing import List, Dict
from io import BytesIO
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..models.patient import Patient
from ..models.user import User
from ..models.tracking import PatientTracking, CoordinatorAssignment, TrackingStatus


def register_chinese_font():
    """註冊中文字型"""
    font_paths = [
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    
    for font_path in font_paths:
        try:
            import os
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                return 'Chinese'
        except Exception:
            continue
    return 'Helvetica'


CHINESE_FONT = register_chinese_font()


def create_daily_report_pdf(
    db: Session,
    target_date: date,
    summary: Dict,
    station_stats: List[Dict],
    coordinator_stats: List[Dict]
) -> bytes:
    """產生每日報表 PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName=CHINESE_FONT, fontSize=18, alignment=1, spaceAfter=12)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontName=CHINESE_FONT, fontSize=14, spaceBefore=12, spaceAfter=6)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName=CHINESE_FONT, fontSize=10)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontName=CHINESE_FONT, fontSize=8, textColor=colors.grey)
    
    content = []
    
    # 標題
    content.append(Paragraph(f"高檢病人動態系統 - 每日報表", title_style))
    content.append(Paragraph(f"報表日期：{target_date.strftime('%Y年%m月%d日')}", normal_style))
    content.append(Paragraph(f"產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", small_style))
    content.append(Spacer(1, 0.5*cm))
    
    # 摘要統計
    content.append(Paragraph("每日摘要", subtitle_style))
    summary_data = [
        ['項目', '數值'],
        ['總病人數', str(summary['patients']['total'])],
        ['已完成', str(summary['patients']['completed'])],
        ['進行中', str(summary['patients']['in_progress'])],
        ['未開始', str(summary['patients']['not_started'])],
        ['完成率', f"{summary['patients']['completion_rate']}%"],
    ]
    summary_table = Table(summary_data, colWidths=[6*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    content.append(summary_table)
    content.append(Spacer(1, 0.5*cm))
    
    # 檢查站統計
    content.append(Paragraph("檢查站統計", subtitle_style))
    station_data = [['檢查站', '代碼', '完成數', '等候中', '檢查中']]
    for stat in station_stats:
        station_data.append([stat['exam_name'], stat['exam_code'], str(stat['completed']), str(stat['waiting']), str(stat['in_exam'])])
    station_table = Table(station_data, colWidths=[4*cm, 2*cm, 2*cm, 2*cm, 2*cm])
    station_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    content.append(station_table)
    content.append(Spacer(1, 0.5*cm))
    
    # 病人列表
    content.append(Paragraph("病人詳細列表", subtitle_style))
    patients = db.query(Patient).filter(Patient.exam_date == target_date, Patient.is_active == True).all()
    patient_data = [['病歷號', '姓名', '狀態', '位置', '個管師']]
    for patient in patients:
        tracking = db.query(PatientTracking).filter(PatientTracking.patient_id == patient.id, PatientTracking.exam_date == target_date).first()
        assignment = db.query(CoordinatorAssignment).filter(CoordinatorAssignment.patient_id == patient.id, CoordinatorAssignment.exam_date == target_date, CoordinatorAssignment.is_active == True).first()
        coordinator_name = "-"
        if assignment:
            coord = db.query(User).filter(User.id == assignment.coordinator_id).first()
            if coord:
                coordinator_name = coord.display_name or "-"
        status_map = {'waiting': '等候中', 'in_exam': '檢查中', 'completed': '已完成'}
        status = '未開始'
        location = '-'
        if tracking:
            status = status_map.get(tracking.current_status, tracking.current_status)
            location = tracking.current_location or '-'
        patient_data.append([patient.chart_no, patient.name, status, location, coordinator_name])
    patient_table = Table(patient_data, colWidths=[3*cm, 3*cm, 2.5*cm, 3*cm, 3*cm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F59E0B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    content.append(patient_table)
    
    # 頁尾
    content.append(Spacer(1, 1*cm))
    content.append(Paragraph("彰濱秀傳醫院 高級健檢中心 - Heal-Arrange 系統自動產生", small_style))
    
    doc.build(content)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def create_patient_list_pdf(db: Session, target_date: date) -> bytes:
    """產生病人清單 PDF（適合列印）"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    
    title_style = ParagraphStyle('Title', fontName=CHINESE_FONT, fontSize=16, alignment=1, spaceAfter=12)
    content = []
    content.append(Paragraph(f"病人清單 - {target_date.strftime('%Y年%m月%d日')}", title_style))
    content.append(Spacer(1, 0.3*cm))
    
    patients = db.query(Patient).filter(Patient.exam_date == target_date, Patient.is_active == True).order_by(Patient.chart_no).all()
    data = [['#', '病歷號', '姓名', '檢查項目', '報到', '完成']]
    for i, patient in enumerate(patients, 1):
        exam_list = patient.notes or '-'
        if len(exam_list) > 20:
            exam_list = exam_list[:20] + '...'
        data.append([str(i), patient.chart_no, patient.name, exam_list, '☐', '☐'])
    
    table = Table(data, colWidths=[1*cm, 2.5*cm, 2.5*cm, 6*cm, 1.5*cm, 1.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), CHINESE_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    content.append(table)
    content.append(Spacer(1, 0.5*cm))
    content.append(Paragraph(f"共 {len(patients)} 位病人", ParagraphStyle('Footer', fontName=CHINESE_FONT, fontSize=10, alignment=2)))
    
    doc.build(content)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
