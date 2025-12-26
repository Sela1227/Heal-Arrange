# -*- coding: utf-8 -*-
"""
LINE 推播服務 - 使用 LINE Messaging API
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..config import settings


# LINE Messaging API 端點
LINE_API_ENDPOINT = "https://api.line.me/v2/bot/message"


async def send_push_message(
    user_id: str,
    messages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    推播訊息給單一用戶
    
    Args:
        user_id: LINE User ID
        messages: 訊息列表（最多 5 則）
    
    Returns:
        API 回應
    """
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        return {"success": False, "error": "未設定 LINE_CHANNEL_ACCESS_TOKEN"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LINE_API_ENDPOINT}/push",
                headers={
                    "Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": user_id,
                    "messages": messages[:5],  # 最多 5 則
                },
                timeout=10.0,
            )
            
            if response.status_code == 200:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code,
                }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


async def send_multicast_message(
    user_ids: List[str],
    messages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    推播訊息給多個用戶（最多 500 人）
    
    Args:
        user_ids: LINE User ID 列表
        messages: 訊息列表
    """
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        return {"success": False, "error": "未設定 LINE_CHANNEL_ACCESS_TOKEN"}
    
    if not user_ids:
        return {"success": False, "error": "沒有接收者"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LINE_API_ENDPOINT}/multicast",
                headers={
                    "Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": user_ids[:500],  # 最多 500 人
                    "messages": messages[:5],
                },
                timeout=10.0,
            )
            
            if response.status_code == 200:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code,
                }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


# =====================
# 訊息模板
# =====================

def create_text_message(text: str) -> Dict[str, Any]:
    """建立文字訊息"""
    return {
        "type": "text",
        "text": text,
    }


def create_flex_message(alt_text: str, contents: Dict[str, Any]) -> Dict[str, Any]:
    """建立 Flex Message"""
    return {
        "type": "flex",
        "altText": alt_text,
        "contents": contents,
    }


def create_notification_bubble(
    title: str,
    body: str,
    footer: str = None,
    color: str = "#1DB446",
) -> Dict[str, Any]:
    """建立通知氣泡"""
    contents = {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "color": "#ffffff",
                    "weight": "bold",
                    "size": "md",
                }
            ],
            "backgroundColor": color,
            "paddingAll": "15px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": body,
                    "wrap": True,
                    "size": "sm",
                }
            ],
            "paddingAll": "15px",
        },
    }
    
    if footer:
        contents["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": footer,
                    "size": "xs",
                    "color": "#888888",
                }
            ],
            "paddingAll": "10px",
        }
    
    return contents


# =====================
# 預設通知訊息
# =====================

def create_assignment_notification(
    patient_name: str,
    patient_chart_no: str,
    exam_list: str = None,
) -> List[Dict[str, Any]]:
    """建立指派通知訊息"""
    body = f"病歷號：{patient_chart_no}"
    if exam_list:
        body += f"\n檢查項目：{exam_list}"
    
    bubble = create_notification_bubble(
        title=f"📋 新病人指派：{patient_name}",
        body=body,
        footer=datetime.now().strftime("%H:%M"),
        color="#2196F3",
    )
    
    return [create_flex_message(f"新病人指派：{patient_name}", bubble)]


def create_next_station_notification(
    patient_name: str,
    station_name: str,
    estimated_wait: int = None,
) -> List[Dict[str, Any]]:
    """建立下一站通知訊息"""
    body = f"請帶領病人前往 {station_name}"
    if estimated_wait is not None:
        body += f"\n預估等候：約 {estimated_wait} 分鐘"
    
    bubble = create_notification_bubble(
        title=f"🏃 下一站指派：{patient_name}",
        body=body,
        footer=datetime.now().strftime("%H:%M"),
        color="#4CAF50",
    )
    
    return [create_flex_message(f"下一站：{station_name}", bubble)]


def create_call_notification(
    patient_name: str,
    station_name: str,
) -> List[Dict[str, Any]]:
    """建立叫號通知訊息"""
    bubble = create_notification_bubble(
        title=f"📢 輪到檢查！",
        body=f"{patient_name} 請至 {station_name} 報到",
        footer=datetime.now().strftime("%H:%M"),
        color="#FF9800",
    )
    
    return [create_flex_message(f"輪到 {patient_name} 檢查", bubble)]


def create_equipment_failure_notification(
    equipment_name: str,
    location: str,
    reporter: str = None,
) -> List[Dict[str, Any]]:
    """建立設備故障通知訊息"""
    body = f"位置：{location}\n設備：{equipment_name}"
    if reporter:
        body += f"\n回報者：{reporter}"
    
    bubble = create_notification_bubble(
        title="🔴 設備故障通知",
        body=body,
        footer=datetime.now().strftime("%H:%M"),
        color="#F44336",
    )
    
    return [create_flex_message(f"設備故障：{equipment_name}", bubble)]


def create_completion_notification(
    patient_name: str,
    completed_exams: int,
    total_exams: int,
) -> List[Dict[str, Any]]:
    """建立完成通知訊息"""
    if completed_exams >= total_exams:
        title = "🎉 檢查全部完成！"
        body = f"{patient_name} 已完成所有檢查項目"
        color = "#4CAF50"
    else:
        title = f"✅ 檢查完成 ({completed_exams}/{total_exams})"
        body = f"{patient_name} 已完成此站檢查\n請等待下一站指派"
        color = "#2196F3"
    
    bubble = create_notification_bubble(
        title=title,
        body=body,
        footer=datetime.now().strftime("%H:%M"),
        color=color,
    )
    
    return [create_flex_message(title, bubble)]
