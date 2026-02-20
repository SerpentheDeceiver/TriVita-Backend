"""
Sleep AI Insights route — GET /sleep/ai-insights?uid=
Generates personalised, LLM-powered sleep insights for the user:
  • ai_advice      - 2–3 sentences of personalised advice
  • root_cause     - why their sleep is what it is today
  • trend_analysis - 7-day pattern summary
  • tips           - list of 5 refreshable actionable tips
"""
from __future__ import annotations

import json
import os
import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from groq import AsyncGroq

from app.mcp import get_mcp_client

router = APIRouter(prefix="/sleep", tags=["Sleep AI Insights"])


@router.get("/ai-insights")
async def get_sleep_ai_insights(uid: str = Query(..., description="Firebase UID")):
    """
    Return AI-generated sleep insights for a user based on today's log
    and 7-day history.
    """
    try:
        mcp = await get_mcp_client()

        # Fetch profile, today's log, and 7-day trends concurrently
        profile, today_log, trends = await asyncio.gather(
            mcp.get_user_profile(uid),
            mcp.get_today_health_log(uid),
            mcp.get_health_trends(uid, days=7),
        )

        # Also pull the last 7 individual sleep records for detailed trend analysis
        await mcp.ensure_connected()
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor = mcp._db["daily_logs"].find(
            {"firebase_uid": uid, "date": {"$gte": start_date}},
            {"sleep": 1, "date": 1, "_id": 0},
        ).sort("date", 1)
        last_7_days = await cursor.to_list(length=7)

        # Build a readable sleep history string
        sleep_records = []
        for log in last_7_days:
            s = log.get("sleep") or {}
            if s.get("hours") is not None:
                sleep_records.append({
                    "date":      log.get("date", "?"),
                    "hours":     s.get("hours"),
                    "bed_time":  s.get("bed_time", "?"),
                    "wake_time": s.get("wake_time", "?"),
                })

        history_str = (
            "\n".join(
                f"  • {r['date']}: {r['hours']}h  (bed {r['bed_time']}, "
                f"wake {r['wake_time']})"
                for r in sleep_records
            )
            if sleep_records
            else "  No recent sleep records."
        )

        # Context variables
        name          = profile.get("name") or "User"
        sleep_target  = profile.get("sleep_target") or 8.0
        sleep_hours   = today_log.get("sleep_hours") or 0.0
        bed_time      = today_log.get("sleep_bed_time") or "not recorded"
        wake_time     = today_log.get("sleep_wake_time") or "not recorded"
        avg_7day      = trends.get("avg_sleep_7days")
        days_logged   = trends.get("days_logged", 0)

        deficit = round(sleep_target - sleep_hours, 1)
        deficit_str = (
            f"{deficit}h deficit"  if deficit > 0
            else f"{abs(deficit)}h surplus"  if deficit < 0
            else "exactly on target"
        )

        # Build Groq prompt
        user_prompt = (
            f"Name: {name}\n"
            f"Sleep target: {sleep_target}h/night\n"
            f"Last night: {sleep_hours}h  (bed: {bed_time}, wake: {wake_time})  [{deficit_str}]\n"
            f"7-day average: {avg_7day}h  over {days_logged} logged day(s)\n"
            f"Recent sleep log (chronological):\n{history_str}\n\n"
            "Generate personalised sleep insights."
        )

        system_prompt = (
            "You are a personal health AI with deep sleep science expertise. "
            "Be empathetic, specific, and science-backed. "
            "Return ONLY a valid JSON object with exactly these four keys:\n"
            "  \"ai_advice\"      : 2–3 sentence personalised advice for tonight.\n"
            "  \"root_cause\"     : 1–2 sentence analysis of WHY their sleep quality "
            "is what it is (irregular schedule, late bedtime, short duration, etc.).\n"
            "  \"trend_analysis\" : 2–3 sentences about the 7-day trend "
            "(improving / declining / consistent, notable patterns).\n"
            "  \"tips\"           : JSON array of exactly 5 specific, "
            "actionable sleep improvement tips (strings).\n"
            "Do NOT wrap in markdown code blocks."
        )

        groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        response = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.72,
            max_tokens=700,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        tips = result.get("tips", [])
        if isinstance(tips, list):
            tips = [str(t) for t in tips[:5]]
        else:
            tips = []

        return {
            "ai_advice":      result.get("ai_advice", ""),
            "root_cause":     result.get("root_cause", ""),
            "trend_analysis": result.get("trend_analysis", ""),
            "tips":           tips,
        }

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI response parse error: {e}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
