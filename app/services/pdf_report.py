# -*- coding: utf-8 -*-
"""
PDF 報表服務 - 使用 reportlab 產生 PDF 報表
"""

import io
from datetime import date, datetime
from typing import List, Dict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session

from .stats import get_daily_summary, get_station_statistics, get_coordinator_statistics


# 嘗試註冊中文字體（如果有的話）
def register_chinese_font():
    """註冊中文字體"""
    font_paths = [
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        'C:/Windows/Fonts/msjh.ttc',
    ]
    
    for path in font_paths:
        try:
            pdfmetrics.registerFont(TTFont('Chinese', path))
            return 'Chinese'
        except:
            continue
    
    # 如果沒有中文字體，使用 Helvetica
    return 'Helvetica'


FONT_NAME = register_chinese_font()


def generate_daily_report_pdf(db: Session, target_date: date = None) -> bytes:
    """
    產生每日報表 PDF
    
    Returns:
        PDF 檔案的 bytes
    """
    if target_date is None:
        target_date = date.today()
    
    # 取得數據
    summary = get_daily_summary(db, target_date)
    station_stats = get_station_statistics(db, target_date)
    coordinator_stats = get_coordinator_statistics(db, target_date)
    
    # 建立 PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # 標題樣式
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontName=FONT_NAME,
        fontSize=18,
        alignment=1,  # 置中
        spaceAfter=10*mm,
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontName=FONT_NAME,
        fontSize=14,
        spaceBefore=8*mm,
        spaceAfter=4*mm,
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
    )
    
    # 標題
    elements.append(Paragraph(
        f"Daily Report - {target_date.strftime('%Y-%m-%d')}",
        title_style
    ))
    elements.append(Paragraph(
        "Chang Bing Show Chwan High-End Checkup Center",
        normal_style
    ))
    elements.append(Spacer(1, 5*mm))
    
    # 摘要區塊
    elements.append(Paragraph("Summary", subtitle_style))
    
    summary_data = [
        ['Item', 'Count', 'Rate'],
        ['Total Patients', str(summary['patients']['total']), '-'],
        ['Completed', str(summary['patients']['completed']), f"{summary['patients']['completion_rate']}%"],
        ['In Progress', str(summary['patients']['in_progress']), '-'],
        ['Not Started', str(summary['patients']['not_started']), '-'],
        ['Equipment Total', str(summary['equipment']['total']), '-'],
        ['Equipment Broken', str(summary['equipment']['broken']), '-'],
    ]
    
    summary_table = Table(summary_data, colWidths=[60*mm, 40*mm, 40*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3F4F6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
    ]))
    elements.append(summary_table)
    
    # 檢查站統計
    elements.append(Paragraph("Station Statistics", subtitle_style))
    
    station_data = [['Station', 'Completed', 'Waiting', 'In Exam', 'Status']]
    for s in station_stats:
        status_text = 'OK' if s['equipment_status'] == 'normal' else 'BROKEN'
        station_data.append([
            s['exam_name'],
            str(s['completed']),
            str(s['waiting']),
            str(s['in_exam']),
            status_text,
        ])
    
    if len(station_data) > 1:
        station_table = Table(station_data, colWidths=[50*mm, 30*mm, 30*mm, 30*mm, 30*mm])
        station_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDF4')]),
        ]))
        elements.append(station_table)
    else:
        elements.append(Paragraph("No station data", normal_style))
    
    # 專員統計
    elements.append(Paragraph("Coordinator Statistics", subtitle_style))
    
    coord_data = [['Name', 'Assignments', 'Current Patient', 'Status', 'Operations']]
    for c in coordinator_stats:
        coord_data.append([
            c['name'],
            str(c['total_assignments']),
            c['current_patient'] or '-',
            c['current_status'],
            str(c['operations']),
        ])
    
    if len(coord_data) > 1:
        coord_table = Table(coord_data, colWidths=[40*mm, 25*mm, 40*mm, 30*mm, 25*mm])
        coord_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B5CF6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F3FF')]),
        ]))
        elements.append(coord_table)
    else:
        elements.append(Paragraph("No coordinator data", normal_style))
    
    # 頁尾
    elements.append(Spacer(1, 10*mm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=8,
        textColor=colors.gray,
        alignment=1,
    )
    elements.append(Paragraph(
        f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        footer_style
    ))
    
    # 建立 PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer.getvalue()


def generate_trend_report_pdf(db: Session, days: int = 7) -> bytes:
    """
    產生趨勢報表 PDF
    """
    from datetime import timedelta
    from .stats import get_date_range_summary
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    daily_summaries = get_date_range_summary(db, start_date, end_date)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontName=FONT_NAME,
        fontSize=18,
        alignment=1,
        spaceAfter=10*mm,
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontName=FONT_NAME,
        fontSize=14,
        spaceBefore=8*mm,
        spaceAfter=4*mm,
    )
    
    # 標題
    elements.append(Paragraph(
        f"Trend Report - {days} Days",
        title_style
    ))
    elements.append(Paragraph(
        f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
        ParagraphStyle('Center', alignment=1, fontName=FONT_NAME)
    ))
    elements.append(Spacer(1, 5*mm))
    
    # 統計摘要
    total_patients = sum(s['patients']['total'] for s in daily_summaries)
    total_completed = sum(s['patients']['completed'] for s in daily_summaries)
    avg_completion = round(total_completed / total_patients * 100, 1) if total_patients > 0 else 0
    
    elements.append(Paragraph("Overall Statistics", subtitle_style))
    
    overall_data = [
        ['Metric', 'Value'],
        ['Total Patients', str(total_patients)],
        ['Total Completed', str(total_completed)],
        ['Average Completion Rate', f"{avg_completion}%"],
        ['Daily Average', str(round(total_patients / days, 1))],
    ]
    
    overall_table = Table(overall_data, colWidths=[80*mm, 60*mm])
    overall_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
    ]))
    elements.append(overall_table)
    
    # 每日明細
    elements.append(Paragraph("Daily Details", subtitle_style))
    
    daily_data = [['Date', 'Total', 'Completed', 'In Progress', 'Completion %']]
    for s in daily_summaries:
        daily_data.append([
            s['date'].strftime('%m/%d'),
            str(s['patients']['total']),
            str(s['patients']['completed']),
            str(s['patients']['in_progress']),
            f"{s['patients']['completion_rate']}%",
        ])
    
    daily_table = Table(daily_data, colWidths=[30*mm, 30*mm, 30*mm, 35*mm, 35*mm])
    daily_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDF4')]),
    ]))
    elements.append(daily_table)
    
    # 頁尾
    elements.append(Spacer(1, 10*mm))
    footer_style = ParagraphStyle(
        'Footer',
        fontName=FONT_NAME,
        fontSize=8,
        textColor=colors.gray,
        alignment=1,
    )
    elements.append(Paragraph(
        f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        footer_style
    ))
    
    doc.build(elements)
    buffer.seek(0)
    
    return buffer.getvalue()
