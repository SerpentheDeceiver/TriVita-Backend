# Hydration AI Insights route: Patterns and advice for water intake.
from __future__ import annotations

import json
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from groq import AsyncGroq

from app.mcp import get_mcp_client

router = APIRouter(prefix="/hydration", tags=["Hydration AI Insights"])


@router.get("/ai-insights")
async def get_hydration_ai_insights(uid: str = Query(..., description="Firebase UID")):
    """
    Return AI-generated hydration insights for a user based on today's
    logged water intake entries.
    """
    try:
        mcp = await get_mcp_client()

        # Profile + today log in parallel
        import asyncio
        profile, today_log = await asyncio.gather(
            mcp.get_user_profile(uid),
            mcp.get_today_health_log(uid),
        )

        # Fetch today's hydration entries (with timestamps) directly from MongoDB
        await mcp.ensure_connected()
        today = datetime.now().strftime("%Y-%m-%d")
        log_doc = await mcp._db["daily_logs"].find_one(
            {"firebase_uid": uid, "date": today},
            {"hydration": 1, "_id": 0},
        )

        entries: list = []
        if log_doc:
            hydration = log_doc.get("hydration") or {}
            entries = hydration.get("entries") or []

        # Context variables
        name         = profile.get("name") or "User"
        water_target = profile.get("hydration_target") or 2500
        total_ml     = today_log.get("hydration_ml") or 0
        remaining    = max(0, water_target - total_ml)

        # Build readable entries string
        if entries:
            entries_str = "\n".join(
                f"  • {e.get('logged_time', '?')} — {e.get('amount_ml', '?')} ml"
                for e in entries
            )
        else:
            entries_str = "  No entries logged yet today."

        entry_count  = len(entries)
        pct_complete = round(total_ml / water_target * 100) if water_target else 0

        user_prompt = (
            f"Name: {name}\n"
            f"Daily water target: {water_target} ml\n"
            f"Total consumed today: {total_ml} ml  ({pct_complete}% of goal)\n"
            f"Remaining: {remaining} ml\n"
            f"Number of logged entries: {entry_count}\n"
            f"Water intake log (time – amount):\n{entries_str}\n\n"
            "Generate personalised hydration insights."
        )

        system_prompt = (
            "You are a personal health AI specialising in hydration science. "
            "Be empathetic, specific, and actionable. "
            "Return ONLY a valid JSON object with exactly these three keys:\n"
            "  \"ai_advice\"       : 2–3 sentence personalised hydration advice "
            "for the rest of the day or tomorrow.\n"
            "  \"timing_analysis\" : 2 sentence analysis of WHEN the user drinks "
            "water — flag risks like all-at-once intake, long gaps, "
            "or morning dehydration. If no entries, give general timing advice.\n"
            "  \"peak_time\"       : A short string (e.g. 'afternoon', '2:30 PM', "
            "'evening') describing when most water was consumed, "
            "or 'none yet' if no entries.\n"
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
            max_tokens=350,
            response_format={"type": "json_object"},
        )

        raw    = response.choices[0].message.content
        result = json.loads(raw)

        return {
            "ai_advice":       result.get("ai_advice", ""),
            "timing_analysis": result.get("timing_analysis", ""),
            "peak_time":       result.get("peak_time", ""),
        }

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI response parse error: {e}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
