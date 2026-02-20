"""
AI Health Assistant Chatbot with MCP Integration
Uses in-process MCP client for memory management and database access.
Uses Groq LLM (llama-3.3-70b-versatile) for conversational AI.
"""
import os
from datetime import datetime
from typing import List, Dict, Any
from groq import Groq
from dotenv import load_dotenv
from app.mcp import get_mcp_client

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class HealthAssistantChatbot:
    """AI Health Assistant with MCP-based memory and contextual awareness."""

    def __init__(self, user_id: str):
        self.user_id   = user_id
        self.model     = "llama-3.3-70b-versatile"
        self.max_history = 20
        self._mcp = None

    async def _get_mcp(self):
        if self._mcp is None:
            self._mcp = await get_mcp_client()
        return self._mcp

    # ──────────────────────────────────────────────────────────────────────
    # System prompt
    # ──────────────────────────────────────────────────────────────────────

    def get_system_prompt(self, ctx: Dict[str, Any]) -> str:
        name   = ctx.get("name", "there")
        age    = ctx.get("age", "unknown")
        gender = ctx.get("gender", "")
        weight = ctx.get("weight")
        height = ctx.get("height")
        goal   = ctx.get("weight_goal", "maintain health")

        # Today
        sleep_h      = ctx.get("recent_sleep_hours")
        hydration_ml = ctx.get("recent_hydration_ml")
        calories     = ctx.get("recent_calories")
        protein_g    = ctx.get("recent_protein")
        meals        = ctx.get("meals_today", 0)

        # Targets
        cal_target  = ctx.get("calorie_target",   2000)
        hyd_target  = ctx.get("hydration_target", 2500)
        sleep_target= ctx.get("sleep_target",      8.0)

        # Trends
        avg_sleep  = ctx.get("avg_sleep_7days")
        avg_hyd    = ctx.get("avg_hydration_7days")
        avg_cal    = ctx.get("avg_calories_7days")
        days_logged= ctx.get("days_logged", 0)

        def _fmt(val, unit=""):
            return f"{val}{unit}" if val is not None else "Not logged yet"

        return f"""You are TriVita AI, a compassionate and intelligent health assistant. You're speaking with {name}.

USER PROFILE:
- Name: {name}
- Age: {age} years old  |  Gender: {gender}
- Weight: {_fmt(weight, ' kg')}  |  Height: {_fmt(height, ' cm')}
- Health Goal: {goal}

TODAY'S DATA:
- Sleep: {_fmt(sleep_h, ' hrs')} (Target: {sleep_target} hrs)
- Hydration: {_fmt(hydration_ml, ' ml')} (Target: {hyd_target} ml)
- Calories: {_fmt(calories, ' kcal')} (Target: {cal_target} kcal)
- Protein: {_fmt(protein_g, ' g')}
- Meals logged: {meals}

7-DAY AVERAGES ({days_logged} days tracked):
- Avg sleep: {_fmt(avg_sleep, ' hrs')}
- Avg hydration: {_fmt(avg_hyd, ' ml')}
- Avg calories: {_fmt(avg_cal, ' kcal')}

YOUR PERSONALITY:
- Warm, empathetic, encouraging — celebrate wins, comfort during struggles
- Conversational and friendly; use their name naturally (not every message)
- Provide actionable advice grounded in their actual numbers above
- Ask thoughtful follow-ups to understand their needs
- Use emojis sparingly but appropriately
- Keep responses concise: 2–4 sentences typically; expand only if they ask

YOUR CAPABILITIES:
- Analyse sleep, hydration, and nutrition patterns from the data above
- Give personalised health recommendations based on real numbers
- Motivate and support their wellness journey
- Explain health concepts in plain language
- Remember context from earlier in THIS conversation

HARD RULES:
- Always reference their real data when it is relevant
- If they haven't logged data, gently encourage them to do so
- Never diagnose — suggest a healthcare professional for medical concerns
- Be honest when you lack information

Respond naturally as their trusted health companion."""

    # ──────────────────────────────────────────────────────────────────────
    # Memory via MCP
    # ──────────────────────────────────────────────────────────────────────

    async def _add_to_memory(self, role: str, content: str):
        mcp = await self._get_mcp()
        await mcp.store_message(self.user_id, role, content)

    async def _get_history(self) -> List[Dict[str, str]]:
        mcp = await self._get_mcp()
        history = await mcp.get_conversation_history(self.user_id, self.max_history)
        return [{"role": m["role"], "content": m["content"]} for m in history]

    async def clear_memory(self):
        mcp = await self._get_mcp()
        await mcp.clear_history(self.user_id)

    # ──────────────────────────────────────────────────────────────────────
    # Chat
    # ──────────────────────────────────────────────────────────────────────

    async def chat(self, user_message: str, user_context: Dict[str, Any]) -> str:
        """Process a user message and return the AI response."""
        try:
            # 1. Save user message to memory
            await self._add_to_memory("user", user_message)

            # 2. Build message list: system + history + (history already includes current user msg)
            history = await self._get_history()
            messages = [
                {"role": "system", "content": self.get_system_prompt(user_context)},
                *history,
            ]

            # 3. Call Groq
            resp = groq_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                top_p=0.9,
                stream=False,
            )
            assistant_msg = resp.choices[0].message.content

            # 4. Save assistant reply to memory
            await self._add_to_memory("assistant", assistant_msg)

            return assistant_msg

        except Exception as e:
            print(f"[Chatbot] Error: {e}")
            return "I'm having a little trouble right now. Could you try again? 🤔"

    async def get_memory_summary(self) -> Dict[str, Any]:
        mcp = await self._get_mcp()
        history = await mcp.get_conversation_history(self.user_id)
        return {
            "total_messages":      len(history),
            "user_messages":       sum(1 for m in history if m["role"] == "user"),
            "assistant_messages":  sum(1 for m in history if m["role"] == "assistant"),
            "conversation_started":history[0]["timestamp"] if history else None,
            "last_message":        history[-1]["timestamp"] if history else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Context builder (called by the route)
# ─────────────────────────────────────────────────────────────────────────────

async def get_user_context_from_db(
    firebase_uid: str,
    users_collection=None,   # kept for signature compatibility
    logs_collection=None,    # kept for signature compatibility
) -> Dict[str, Any]:
    """Fetch full user context via MCP and flatten into a single dict."""
    try:
        mcp = await get_mcp_client()
        data = await mcp.get_full_user_context(firebase_uid)

        context: Dict[str, Any] = {}

        # Profile fields
        context.update(data.get("profile", {}))

        # Today's log → prefixed keys expected by the system prompt
        today = data.get("today", {})
        context.update({
            "recent_sleep_hours":  today.get("sleep_hours"),
            "recent_hydration_ml": today.get("hydration_ml"),
            "recent_calories":     today.get("calories"),
            "recent_protein":      today.get("protein_g"),
            "meals_today":         today.get("meals_count", 0),
        })

        # Trends
        context.update(data.get("trends", {}))

        return context

    except Exception as e:
        print(f"[Chatbot] Error fetching context: {e}")
        return {}


def analyze_health_sentiment(user_context: Dict[str, Any]) -> str:
    """Return a short health-status string for the greeting endpoint."""
    sleep        = user_context.get("recent_sleep_hours")
    hydration    = user_context.get("recent_hydration_ml")
    hyd_target   = user_context.get("hydration_target")

    tags = []
    if sleep:
        tags.append("well-rested" if sleep >= 7 else "a bit tired")
    if hydration and hyd_target:
        tags.append(
            "well-hydrated" if hydration >= hyd_target
            else "needing some water" if hydration < hyd_target * 0.5
            else None
        )
    tags = [t for t in tags if t]

    return f"You're looking {' and '.join(tags)} today!" if tags else "How are you feeling today?"
