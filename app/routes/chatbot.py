"""
AI Health Assistant Chatbot Routes
POST /chatbot/chat
GET  /chatbot/greeting/{firebase_uid}
GET  /chatbot/history/{firebase_uid}
DELETE /chatbot/history/{firebase_uid}
POST /chatbot/quick-ask/{firebase_uid}
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from app.agents.chatbot_agent import (
    HealthAssistantChatbot,
    get_user_context_from_db,
    analyze_health_sentiment,
)
from app.db.mongo import get_users_collection
from motor.motor_asyncio import AsyncIOMotorCollection

router = APIRouter(prefix="/chatbot", tags=["AI Assistant"])


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str
    firebase_uid: str


class ChatResponse(BaseModel):
    response: str
    timestamp: str
    conversation_id: str
    context_summary: Optional[Dict[str, Any]] = None


class ConversationStats(BaseModel):
    total_messages: int
    user_messages: int
    assistant_messages: int
    conversation_started: Optional[str]
    last_message: Optional[str]


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    body: ChatMessage,
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    """
    Send a message to the AI health assistant and get a personalised response.

    The assistant has access to:
    - User profile (name, age, weight, targets)
    - Today's health logs (sleep, hydration, nutrition)
    - Conversation memory (last 20 messages)
    - 7-day health trends
    """
    try:
        # Ensure user exists
        user = await users_col.find_one({"firebase_uid": body.firebase_uid})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Build full context via MCP
        user_context = await get_user_context_from_db(body.firebase_uid)

        # Run chatbot
        chatbot  = HealthAssistantChatbot(user_id=body.firebase_uid)
        response = await chatbot.chat(body.message, user_context)
        stats    = await chatbot.get_memory_summary()

        return ChatResponse(
            response=response,
            timestamp=datetime.now().isoformat(),
            conversation_id=body.firebase_uid,
            context_summary={
                "user_name":             user_context.get("name"),
                "messages_in_session":   stats["total_messages"],
                "health_data_available": {
                    "sleep_today":     user_context.get("recent_sleep_hours") is not None,
                    "hydration_today": user_context.get("recent_hydration_ml") is not None,
                    "nutrition_today": user_context.get("recent_calories") is not None,
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[/chatbot/chat] {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


@router.get("/greeting/{firebase_uid}")
async def get_personalized_greeting(
    firebase_uid: str,
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    """Return a time-based greeting enriched with health sentiment."""
    try:
        user_context = await get_user_context_from_db(firebase_uid)
        name = user_context.get("name", "there")

        hour = datetime.now().hour
        if hour < 12:
            greeting_text = f"Good morning, {name}! 🌅"
        elif hour < 17:
            greeting_text = f"Good afternoon, {name}! ☀️"
        else:
            greeting_text = f"Good evening, {name}! 🌙"

        health_status = analyze_health_sentiment(user_context)

        # Contextual suggestion
        if not user_context.get("recent_sleep_hours"):
            suggestion = "Don't forget to log your sleep from last night!"
        elif not user_context.get("recent_hydration_ml"):
            suggestion = "How about starting with a glass of water? 💧"
        elif not user_context.get("meals_today"):
            suggestion = "Ready to log your first meal of the day? 🍽️"
        else:
            suggestion = "You're doing great! Keep up the healthy habits! 💪"

        return {
            "greeting":      greeting_text,
            "health_status": health_status,
            "suggestion":    suggestion,
            "context": {
                "has_sleep_data":     user_context.get("recent_sleep_hours") is not None,
                "has_hydration_data": user_context.get("recent_hydration_ml") is not None,
                "meals_logged":       user_context.get("meals_today", 0),
            },
        }
    except Exception as e:
        print(f"[/chatbot/greeting] {e}")
        raise HTTPException(status_code=500, detail=f"Greeting failed: {e}")


@router.get("/history/{firebase_uid}", response_model=ConversationStats)
async def get_conversation_history(firebase_uid: str):
    """Return conversation statistics for a user."""
    try:
        chatbot = HealthAssistantChatbot(user_id=firebase_uid)
        stats   = await chatbot.get_memory_summary()
        return ConversationStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History fetch failed: {e}")


@router.delete("/history/{firebase_uid}")
async def clear_conversation_history(firebase_uid: str):
    """Clear conversation memory so the next chat starts fresh."""
    try:
        chatbot = HealthAssistantChatbot(user_id=firebase_uid)
        await chatbot.clear_memory()           # ← fixed: was missing await
        return {
            "message":      "Conversation history cleared",
            "firebase_uid": firebase_uid,
            "timestamp":    datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear failed: {e}")


@router.post("/quick-ask/{firebase_uid}")
async def quick_health_question(
    firebase_uid: str,
    question_type: str,
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    """
    Fire a pre-defined health question without typing.
    question_type: sleep | hydration | nutrition | progress
    """
    questions = {
        "sleep":      "How has my sleep been this week? Any insights?",
        "hydration":  "Am I staying hydrated? How's my water intake?",
        "nutrition":  "How's my nutrition looking today?",
        "progress":   "How am I doing with my health goals overall?",
    }
    q = questions.get(question_type)
    if not q:
        raise HTTPException(status_code=400, detail="Invalid question_type")

    return await chat_with_assistant(
        ChatMessage(message=q, firebase_uid=firebase_uid), users_col
    )
