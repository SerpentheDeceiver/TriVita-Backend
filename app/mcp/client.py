# MCP Client for Health Assistant Chatbot with direct MongoDB access.
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
import os


class MCPHealthClient:
    """In-process MCP client: conversation memory + MongoDB health data."""

    def __init__(self):
        # key: firebase_uid  →  list of {"role", "content", "timestamp"}
        self._conversation_store: Dict[str, List[Dict]] = {}
        self._lock = asyncio.Lock()
        self._db_client: Optional[AsyncIOMotorClient] = None
        self._db = None

    # Connection

    async def connect(self):
        """Initialize MongoDB connection using validated settings (no localhost fallback)."""
        if self._db_client is None:
            from app.core.config import settings
            self._db_client = AsyncIOMotorClient(settings.MONGO_URI)
            self._db = self._db_client[settings.MONGO_DB_NAME]

    async def ensure_connected(self):
        if self._db_client is None:
            await self.connect()

    # Conversation memory

    async def get_conversation_history(
        self, user_id: str, limit: int = 20
    ) -> List[Dict[str, str]]:
        """MCP Tool: get-conversation-history"""
        async with self._lock:
            history = self._conversation_store.get(user_id, [])
            return history[-limit:] if len(history) > limit else list(history)

    async def store_message(self, user_id: str, role: str, content: str):
        """MCP Tool: store-conversation-message"""
        async with self._lock:
            if user_id not in self._conversation_store:
                self._conversation_store[user_id] = []
            self._conversation_store[user_id].append({
                "role":      role,
                "content":   content,
                "timestamp": datetime.now().isoformat(),
            })
            # Trim to last 40 entries to avoid unbounded growth
            if len(self._conversation_store[user_id]) > 40:
                self._conversation_store[user_id] = \
                    self._conversation_store[user_id][-40:]

    async def clear_history(self, user_id: str):
        """MCP Tool: clear-conversation-history"""
        async with self._lock:
            self._conversation_store[user_id] = []

    # User profile

    async def get_user_profile(self, firebase_uid: str) -> Dict[str, Any]:
        """MCP Tool: get-user-profile"""
        await self.ensure_connected()
        try:
            user = await self._db["users"].find_one(
                {"firebase_uid": firebase_uid}, {"_id": 0}
            )
            if not user:
                return {}
            targets = user.get("targets") or {}
            return {
                "name":             user.get("name"),
                "age":              user.get("age"),
                "gender":           user.get("gender"),
                "weight":           user.get("weight_kg"),
                "height":           user.get("height_cm"),
                "weight_goal":      user.get("goal"),
                "activity_level":   user.get("activity_level"),
                "calorie_target":   targets.get("calorie_target"),
                "hydration_target": targets.get("water_target_ml"),
                "sleep_target":     targets.get("sleep_target_hours"),
                "protein_target":   targets.get("protein_target_g"),
            }
        except Exception as e:
            print(f"[MCP] get_user_profile error: {e}")
            return {}

    # Today's health log

    async def get_today_health_log(self, firebase_uid: str) -> Dict[str, Any]:
        """MCP Tool: get-today-health-log"""
        await self.ensure_connected()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log = await self._db["daily_logs"].find_one(
                {"firebase_uid": firebase_uid, "date": today}, {"_id": 0}
            )
            if not log:
                return {}
            sleep     = log.get("sleep") or {}
            hydration = log.get("hydration") or {}
            nutrition = log.get("nutrition") or {}
            totals    = nutrition.get("totals") or {}
            return {
                "sleep_hours":     sleep.get("hours"),
                "sleep_bed_time":  sleep.get("bed_time"),
                "sleep_wake_time": sleep.get("wake_time"),
                "hydration_ml":    hydration.get("total_ml"),
                "calories":        totals.get("calories"),
                "protein_g":       totals.get("protein"),
                "carbs_g":         totals.get("carbs"),
                "fat_g":           totals.get("fat"),
                "meals_count":     len(nutrition.get("entries") or []),
            }
        except Exception as e:
            print(f"[MCP] get_today_health_log error: {e}")
            return {}

    # 7-day health trends

    async def get_health_trends(
        self, firebase_uid: str, days: int = 7
    ) -> Dict[str, Any]:
        """MCP Tool: get-health-trends"""
        await self.ensure_connected()
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            cursor = self._db["daily_logs"].find(
                {"firebase_uid": firebase_uid, "date": {"$gte": start_date}},
                {"sleep": 1, "hydration": 1, "nutrition": 1, "_id": 0},
            ).sort("date", 1)
            recent_logs = await cursor.to_list(length=days)

            def _vals(key_path):
                """Safely extract nested values from a list of log dicts."""
                results = []
                for log in recent_logs:
                    obj = log
                    for k in key_path:
                        obj = (obj or {}).get(k)
                    if obj is not None:
                        results.append(obj)
                return results

            def _avg(lst):
                return round(sum(lst) / len(lst), 1) if lst else None

            return {
                "avg_sleep_7days":     _avg(_vals(["sleep", "hours"])),
                "avg_hydration_7days": _avg(_vals(["hydration", "total_ml"])),
                "avg_calories_7days":  _avg(_vals(["nutrition", "totals", "calories"])),
                "avg_protein_7days":   _avg(_vals(["nutrition", "totals", "protein"])),
                "days_logged":         len(recent_logs),
            }
        except Exception as e:
            print(f"[MCP] get_health_trends error: {e}")
            return {}

    # Full context composite

    async def get_full_user_context(self, firebase_uid: str) -> Dict[str, Any]:
        """MCP Tool: get-full-user-context"""
        profile = await self.get_user_profile(firebase_uid)
        today   = await self.get_today_health_log(firebase_uid)
        trends  = await self.get_health_trends(firebase_uid)
        return {"profile": profile, "today": today, "trends": trends}

    # Lifecycle

    async def close(self):
        if self._db_client:
            self._db_client.close()
            self._db_client = None
            self._db = None


# Singleton accessor

_mcp_client: Optional[MCPHealthClient] = None


async def get_mcp_client() -> MCPHealthClient:
    """Return (or lazily create) the singleton MCPHealthClient."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPHealthClient()
        await _mcp_client.connect()
    return _mcp_client
