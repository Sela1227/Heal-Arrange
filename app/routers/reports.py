# -*- coding: utf-8 -*-
"""
報表路由 - Phase 7 更新：加入 PDF 匯出
"""

from datetime import date, datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole
from ..models.exam import Exam
from ..services.auth import get_current_user
from ..services import stats as stats_service

router = APIRouter(prefix="/admin/reports", tags=["報表"])
templates = Jinja2Templates(directory="app/templates")


def require_admin_or_dispatcher(request: Request, db: Session = Depends(get_db)) -> User:
    """要求管理員或調度員權限"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")
    if user.role not in [UserRole.ADMIN.value, UserRole.DISPATCHER.value]:
        raise HTTPException(status_code=403, detail="需要管理員或調度員權限")
    return user


@router.get("", response_class=HTMLResponse)
async def reports_index(
    request: Request,
    target_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """報表首頁 - 今日摘要"""
    if target_date:
        try:
            report_date = date.fromisoformat(target_date)
        except:
            report_date = date.today()
    else:
        report_date = date.today()
    
    # 取得統計資料
    summary = stats_service.get_daily_summary(db, report_date)
    station_stats = stats_service.get_station_statistics(db, report_date)
    coordinator_stats = stats_service.get_coordinator_statistics(db, report_date)
    
    return templates.TemplateResponse("admin/reports.html", {
        "request": request,
        "user": current_user,
        "report_date": report_date,
        "today": date.today(),
        "summary": summary,
        "station_stats": station_stats,
        "coordinator_stats": coordinator_stats,
        "timedelta": timedelta,
    })


@router.get("/history", response_class=HTMLResponse)
async def history_query(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    exam_code: str = None,
    days: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """歷史查詢頁面"""
    # 處理日期
    if not end_date:
        end = date.today()
    else:
        try:
            end = date.fromisoformat(end_date)
        except:
            end = date.today()
    
    # 優先使用 days 參數
    if days:
        start = end - timedelta(days=days)
    elif not start_date:
        start = end - timedelta(days=7)
    else:
        try:
            start = date.fromisoformat(start_date)
        except:
            start = end - timedelta(days=7)
    
    # 取得歷史記錄
    records = stats_service.get_history_records(
        db=db,
        start_date=start,
        end_date=end,
        exam_code=exam_code if exam_code else None,
        limit=200
    )
    
    # 取得檢查項目列表
    exams = db.query(Exam).filter(Exam.is_active == True).all()
    
    return templates.TemplateResponse("admin/history.html", {
        "request": request,
        "user": current_user,
        "start_date": start,
        "end_date": end,
        "exam_code": exam_code,
        "records": records,
        "exams": exams,
    })


@router.get("/trend", response_class=HTMLResponse)
async def trend_report(
    request: Request,
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """趨勢報表（Chart.js 視覺化）"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    # 取得每日摘要
    daily_summaries = stats_service.get_date_range_summary(db, start_date, end_date)
    
    return templates.TemplateResponse("admin/trend.html", {
        "request": request,
        "user": current_user,
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "today": date.today(),
        "daily_summaries": daily_summaries,
    })


# ======================
# CSV 匯出
# ======================

@router.get("/export/daily")
async def export_daily_csv(
    target_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """匯出每日報表 CSV"""
    if target_date:
        try:
            report_date = date.fromisoformat(target_date)
        except:
            report_date = date.today()
    else:
        report_date = date.today()
    
    csv_content = stats_service.export_daily_report_csv(db, report_date)
    
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=daily_report_{report_date}.csv"
        }
    )


# ======================
# PDF 匯出
# ======================

@router.get("/export/daily/pdf")
async def export_daily_pdf(
    target_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """匯出每日報表 PDF"""
    from ..services.pdf_report import generate_daily_report_pdf
    
    if target_date:
        try:
            report_date = date.fromisoformat(target_date)
        except:
            report_date = date.today()
    else:
        report_date = date.today()
    
    try:
        pdf_content = generate_daily_report_pdf(db, report_date)
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=daily_report_{report_date}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 產生失敗: {str(e)}")


@router.get("/trend/pdf")
async def export_trend_pdf(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """匯出趨勢報表 PDF"""
    from ..services.pdf_report import generate_trend_report_pdf
    
    try:
        pdf_content = generate_trend_report_pdf(db, days)
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=trend_report_{start_date}_{end_date}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 產生失敗: {str(e)}")


# ======================
# HTMX API - 即時刷新
# ======================

@router.get("/api/summary", response_class=HTMLResponse)
async def get_summary_partial(
    request: Request,
    target_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """摘要統計（HTMX 部分更新）"""
    if target_date:
        try:
            report_date = date.fromisoformat(target_date)
        except:
            report_date = date.today()
    else:
        report_date = date.today()
    
    summary = stats_service.get_daily_summary(db, report_date)
    
    return templates.TemplateResponse("partials/report_summary.html", {
        "request": request,
        "summary": summary,
    })


@router.get("/api/stations", response_class=HTMLResponse)
async def get_stations_stats_partial(
    request: Request,
    target_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """檢查站統計（HTMX 部分更新）"""
    if target_date:
        try:
            report_date = date.fromisoformat(target_date)
        except:
            report_date = date.today()
    else:
        report_date = date.today()
    
    station_stats = stats_service.get_station_statistics(db, report_date)
    
    return templates.TemplateResponse("partials/station_stats.html", {
        "request": request,
        "station_stats": station_stats,
    })


@router.get("/api/coordinators", response_class=HTMLResponse)
async def get_coordinators_stats_partial(
    request: Request,
    target_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_dispatcher),
):
    """個管師統計（HTMX 部分更新）"""
    if target_date:
        try:
            report_date = date.fromisoformat(target_date)
        except:
            report_date = date.today()
    else:
        report_date = date.today()
    
    coordinator_stats = stats_service.get_coordinator_statistics(db, report_date)
    
    return templates.TemplateResponse("partials/coordinator_stats.html", {
        "request": request,
        "coordinator_stats": coordinator_stats,
    })
