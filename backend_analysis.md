# 🏥 Health AI Backend — Full API Reference & Render Readiness Guide

> **Purpose:** Complete reference for frontend developers designing the Flutter UI and for deploying the backend to Render + MongoDB Atlas.
> **Version:** 2.0.0 · FastAPI · MongoDB (Motor) · Firebase Admin · Groq LLM · scikit-learn

---

## ✅ Render Push Readiness

| Check | Status | Action needed |
|---|---|---|
| `requirements.txt` | ✅ Present | None |
| `uvicorn` start command | ✅ Via `requirements.txt` | Set Start Command in Render dashboard |
| CORS | ✅ Open (`*`) | Tighten to Render URL before production |
| `.gitignore` | ✅ Present | Verify `.env` and `.json` are ignored |
| `.env` (local) | ⚠️ `localhost` URIs | **Replace with Atlas + secrets in Render env vars** |
| `firebase_service_account.json` | ⚠️ Secret file | **Upload contents as Render secret file or env var** |
| `GROQ_API_KEY` | ⚠️ Hard-coded in `.env` | **Move to Render env var** |
| `Procfile` | ℹ️ Not present | Render uses Start Command field instead |

### Render Start Command
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Required Environment Variables on Render

| Variable | Value |
|---|---|
| `MONGO_URI` | `mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/health_ai` |
| `MONGO_DB_NAME` | `health_ai` |
| `GROQ_API_KEY` | Your Groq key from console.groq.com |
| `FIREBASE_CREDENTIALS_PATH` | Path to uploaded service account JSON (or use inline JSON) |

> **⚠️ Important:** Never commit `firebase_service_account.json` or `.env` to Git. Add both to `.gitignore` before pushing.

---

## 🏗️ Architecture Overview

```
Flutter App (Firebase Auth)
        │
        │  firebase_uid in every request (query param or body)
        │  NO bearer tokens needed — auth is Firebase-side only
        ▼
FastAPI Backend (Render)
  ├── APScheduler  ── runs notification cycle every N minutes
  ├── MongoDB (Atlas) ── all persistent data
  ├── Firebase Admin ── FCM push notifications
  └── Groq LLM ── AI chat + sleep/hydration insights
```

### MongoDB Collections

| Collection | Purpose |
|---|---|
| `users` | User profiles, computed targets, FCM tokens, notification preferences |
| `daily_logs` | Sleep / hydration / nutrition entries + computed scores, one doc per user per date |
| `meal_plans` | AI-generated + saved meal plans |
| `nutrition_states` | (internal) notification scheduler state |

### Scoring System (runs on every log write)
Every `POST /log/*` call re-computes scores instantly and returns them:
- **Sleep score** (0–100): based on hours vs. target
- **Hydration score** (0–100): based on ml vs. target
- **Nutrition score** (0–100): based on calories vs. target ± 20%
- **Wellness score** (0–100): weighted average of all three

---

## 🔌 Complete API Reference

### Auth Pattern
**All routes use `firebase_uid` as a query/body parameter.**
Flutter reads `FirebaseAuth.instance.currentUser!.uid` and sends it with every call.

---

### 1. System

#### `GET /`
Returns app name, version, status.

#### `GET /health`
Lightweight ping. Flutter uses this to confirm backend is reachable.
```json
{ "status": "ok" }
```

---

### 2. Profile — `/profile`

#### `POST /profile/create`
Creates a new profile or returns existing one (idempotent).

**Request body:**
```json
{
  "firebase_uid": "abc123",
  "email": "user@example.com",
  "name": "Ravi Kumar",
  "age": 24,
  "weight_kg": 72.5,
  "height_cm": 175.0,
  "gender": "male",              // "male" | "female" | "other"
  "activity_level": "moderate",  // "sedentary" | "light" | "moderate" | "active" | "very_active"
  "goal": "lose",                // "lose" | "gain" | "maintain"
  "target_weight_change_kg": 5.0, // optional, kg to lose/gain
  "timeline_weeks": 12,           // optional
  "sleep_time": "10:00 PM",       // optional, preferred bed time
  "wake_time": "6:00 AM"          // optional, preferred wake time
}
```

**Response (201 Created):**
```json
{
  "status": "created",       // or "exists" if already registered
  "firebase_uid": "abc123",
  "name": "Ravi Kumar",
  "email": "user@example.com",
  "targets": {
    "calorie_target": 1800,
    "protein_target": 130,
    "water_target_ml": 2500,
    "sleep_target_hours": 8.0
  }
}
```

#### `GET /profile/{uid}`
Returns the full stored user document (includes computed targets, notification prefs, fcm_token).

**Response:**
```json
{
  "firebase_uid": "abc123",
  "name": "Ravi Kumar",
  "email": "user@example.com",
  "age": 24,
  "weight_kg": 72.5,
  "height_cm": 175.0,
  "gender": "male",
  "activity_level": "moderate",
  "goal": "lose",
  "targets": {
    "calorie_target": 1800,
    "protein_target": 130,
    "water_target_ml": 2500,
    "sleep_target_hours": 8.0
  },
  "notification_prefs": { ... },
  "fcm_token": "fcm_token_string_or_null",
  "created_at": "2026-02-20T18:00:00Z"
}
```

---

### 3. Daily Logs — `/log`

All log endpoints accept `?uid=<firebase_uid>` as query param.

#### `POST /log/sleep?uid=<uid>`
Log one sleep entry per day (409 Conflict if already logged today).

**Request body (at least one of hours / bed_time / wake_time required):**
```json
{
  "hours": 7.5,               // optional if bed+wake given
  "bed_time": "10:30 PM",    // HH:MM AM/PM or HH:MM 24hr, optional
  "wake_time": "06:00 AM",   // optional
  "entry_mode": "manual",    // "manual" | "wearable"
  "source": "flutter"        // optional label
}
```

**Response:**
```json
{
  "status": "ok",
  "sleep": {
    "hours": 7.5,
    "bed_time": "22:30",
    "wake_time": "06:00",
    "entry_mode": "manual",
    "source": "flutter",
    "logged_at": "2026-02-21T00:00:00Z"
  },
  "scores": {
    "sleep": 82,
    "hydration": 60,
    "nutrition": 75,
    "wellness": 74
  }
}
```

#### `POST /log/hydration?uid=<uid>`
Log a water intake entry.

**Request body:**
```json
{
  "amount_ml": 500,
  "estimated_time": "14:30"  // optional HH:MM, defaults to current time
}
```

**Response:**
```json
{
  "status": "ok",
  "entry": {
    "amount_ml": 500,
    "estimated_time": "14:30",
    "logged_time": "14:35"
  },
  "scores": { "sleep": 82, "hydration": 75, "nutrition": 70, "wellness": 76 }
}
```

#### `POST /log/nutrition?uid=<uid>`
Log a meal with individual food items.

**Request body:**
```json
{
  "meal_type": "breakfast",  // "breakfast"|"mid_morning"|"lunch"|"afternoon_break"|"dinner"|"post_dinner"
  "estimated_time": "08:30", // optional
  "items": [
    {
      "name": "Oats with milk",
      "cal": 350,
      "protein": 12.0,
      "carbs": 55.0,
      "fat": 7.0
    }
  ]
}
```

**Response:**
```json
{
  "status": "ok",
  "entry": {
    "meal_type": "breakfast",
    "estimated_time": "08:30",
    "logged_time": "08:35",
    "items": [...],
    "meal_calories": 350
  },
  "scores": { "sleep": 82, "hydration": 60, "nutrition": 72, "wellness": 72 }
}
```

#### `GET /log/today?uid=<uid>`
Get today's full log document with all recorded entries + latest scores.

**Response shape:**
```json
{
  "firebase_uid": "abc123",
  "date": "2026-02-21",
  "sleep": {
    "hours": 7.5,
    "bed_time": "22:30",
    "wake_time": "06:00"
  },
  "hydration": {
    "total_ml": 1500,
    "entries": [
      { "amount_ml": 500, "estimated_time": "08:00", "logged_time": "08:05" }
    ]
  },
  "nutrition": {
    "entries": [
      {
        "meal_type": "breakfast",
        "meal_calories": 350,
        "items": [...]
      }
    ],
    "totals": {
      "calories": 350,
      "protein": 12,
      "carbs": 55,
      "fat": 7
    }
  },
  "scores": { "sleep": 82, "hydration": 55, "nutrition": 72, "wellness": 70 }
}
```

#### `GET /log/{YYYY-MM-DD}?uid=<uid>`
Get log for any specific date.

---

### 4. Analytics — `/analytics`

#### `GET /analytics/weekly?uid=<uid>&week=<1-4>`
Get aggregated weekly analytics for progress charts.

- `week` omitted → rolling last 7 days
- `week=1` → days 1–7 of current month
- `week=2` → days 8–14, etc.

**Full response shape:**
```json
{
  "week_label": "Week 3",
  "date_range": "Feb 15 – Feb 21, 2026",
  "days": ["2026-02-15", "2026-02-16", "..."],
  "day_labels": ["Sat", "Sun", "..."],
  "n_days": 7,

  "sleep": {
    "daily": [
      {
        "date": "2026-02-15",
        "hours": 7.5,
        "score": 82,
        "deficit_hours": -0.5,
        "bed_hour": 22.5,
        "wake_hour": 6.0
      }
    ],
    "avg_hours": 7.2,
    "avg_score": 78.5,
    "target_hours": 8.0,
    "goal_met_days": 3,
    "trend": "improving",        // "improving"|"declining"|"stable"
    "cumulative_deficit": [-0.5, -1.0, "..."],
    "total_deficit_hours": -3.5
  },

  "hydration": {
    "daily": [
      {
        "date": "2026-02-15",
        "total_ml": 2200,
        "score": 78,
        "goal_met": false,
        "gap_ml": -300
      }
    ],
    "avg_ml": 2100,
    "avg_score": 72,
    "target_ml": 2500,
    "goal_met_days": 2,
    "completion_rate_pct": 28.6,
    "trend": "stable",
    "avg_time_blocks": [50, 120, 200, 180, 150, 100, 80, 60],
    "time_block_labels": ["6am","8am","10am","12pm","2pm","4pm","6pm","8pm"]
  },

  "nutrition": {
    "daily": [
      {
        "date": "2026-02-15",
        "calories": 1850,
        "protein": 110,
        "carbs": 200,
        "fat": 65,
        "score": 75,
        "calorie_gap": -150
      }
    ],
    "avg_calories": 1900,
    "avg_score": 74,
    "calorie_target": 2000,
    "avg_macro": {
      "protein_g": 110, "protein_pct": 25.0,
      "carbs_g": 200,   "carbs_pct": 45.5,
      "fat_g": 65,      "fat_pct": 29.5
    },
    "avg_meal_calories": {
      "breakfast": 350,
      "lunch": 600,
      "dinner": 700
    },
    "trend": "improving"
  },

  "wellness": {
    "scores": [70, 72, 76, 74, 78, 80, 75],
    "avg": 75.0,
    "trend": "improving"
  }
}
```

---

### 5. AI Chatbot — `/chatbot`

#### `POST /chatbot/chat`
Send a message and get AI response. Has access to profile, today's logs, 7-day trends, and last 20 conversation messages.

**Request body:**
```json
{
  "message": "How is my sleep this week?",
  "firebase_uid": "abc123"
}
```

**Response:**
```json
{
  "response": "Your average sleep this week is 7.2h — slightly below your 8h target...",
  "timestamp": "2026-02-21T00:00:00",
  "conversation_id": "abc123",
  "context_summary": {
    "user_name": "Ravi Kumar",
    "messages_in_session": 5,
    "health_data_available": {
      "sleep_today": true,
      "hydration_today": true,
      "nutrition_today": false
    }
  }
}
```

#### `GET /chatbot/greeting/{firebase_uid}`
Returns a time-aware, personalised greeting with health status and a contextual suggestion.

**Response:**
```json
{
  "greeting": "Good evening, Ravi! 🌙",
  "health_status": "Doing well overall",
  "suggestion": "Ready to log your first meal of the day? 🍽️",
  "context": {
    "has_sleep_data": true,
    "has_hydration_data": true,
    "meals_logged": 2
  }
}
```

#### `GET /chatbot/history/{firebase_uid}`
Returns conversation statistics.

```json
{
  "total_messages": 12,
  "user_messages": 6,
  "assistant_messages": 6,
  "conversation_started": "2026-02-21T10:00:00",
  "last_message": "2026-02-21T22:00:00"
}
```

#### `DELETE /chatbot/history/{firebase_uid}`
Clears conversation memory so next chat starts fresh.

```json
{
  "message": "Conversation history cleared",
  "firebase_uid": "abc123",
  "timestamp": "2026-02-21T00:00:00"
}
```

#### `POST /chatbot/quick-ask/{firebase_uid}?question_type=sleep`
Fire a pre-defined question without typing. `question_type`: `sleep | hydration | nutrition | progress`.

---

### 6. Meal Plan — `/meal-plan`

#### `GET /meal-plan/saved?uid=<uid>&date=<YYYY-MM-DD>`
Fetch a saved meal plan for a date (date defaults to today).

**Response (when exists):**
```json
{
  "exists": true,
  "firebase_uid": "abc123",
  "date": "2026-02-21",
  "cuisine_type": "indian",
  "meals": [
    {
      "meal_type": "breakfast",
      "name": "Poha with peanuts",
      "calories": 320,
      "protein": 10,
      "carbs": 55,
      "fat": 6,
      "items": ["Poha 1.5 cups", "Peanuts 30g", "Onion", "Green chili"]
    }
  ],
  "daily_summary": "A balanced day with 1800 kcal...",
  "targets_snapshot": { "calorie_target": 1800, "protein_target": 130 },
  "updated_at": "2026-02-21T06:00:00Z"
}
```

#### `POST /meal-plan/generate`
AI-generate a full-day meal plan (does NOT save — call `/save` after).

**Request body:**
```json
{
  "uid": "abc123",
  "cuisine_type": "indian"   // "indian"|"mediterranean"|"international"|"asian"|etc.
}
```

**Response:**
```json
{
  "uid": "abc123",
  "cuisine_type": "indian",
  "ai_generated": true,
  "meals": [
    {
      "meal_type": "breakfast",
      "name": "...",
      "calories": 320,
      "protein": 10,
      "carbs": 55,
      "fat": 6,
      "items": [...]
    }
  ],
  "daily_summary": "...",
  "tips": ["Eat more fibre", "Stay hydrated"],
  "targets_snapshot": { "calorie_target": 1800, "protein_target": 130 }
}
```

#### `POST /meal-plan/save`
Save (upsert) a generated or custom meal plan.

**Request body:** same structure as generate response, plus:
```json
{
  "uid": "abc123",
  "date": "2026-02-21",
  "meals": [...],
  "cuisine_type": "indian",
  "daily_summary": "..."
}
```

#### `GET /meal-plan?uid=<uid>` *(Legacy)*
Returns AI meal suggestions for today (no save, no cuisine preference).

---

### 7. Sleep AI Insights — `/sleep`

#### `GET /sleep/ai-insights?uid=<uid>`
LLM-powered (Groq Llama-70B) personalised sleep insights.

**Response:**
```json
{
  "ai_advice": "You slept 7.5h — just 30min short of your 8h target. Try going to bed 30 minutes earlier tonight.",
  "root_cause": "Your irregular bedtime (ranging 10:30 PM–1:00 AM) is the primary cause of your inconsistent sleep quality.",
  "trend_analysis": "Over the past 7 days your sleep has been improving — 5 out of 7 days exceeded 7h. You're on the right track.",
  "tips": [
    "Set a fixed bedtime alarm for 10:00 PM",
    "Avoid screens 1 hour before bed",
    "Keep your room temperature between 18–20°C",
    "Avoid caffeine after 2 PM",
    "Try a 10-minute wind-down stretching routine"
  ]
}
```

---

### 8. Hydration AI Insights — `/hydration`

#### `GET /hydration/ai-insights?uid=<uid>`
LLM-powered personalised hydration insights based on today's actual log entries.

**Response:**
```json
{
  "ai_advice": "You've consumed 1500ml so far — 40% of your 2500ml goal. Drink a glass every hour to catch up.",
  "timing_analysis": "All your water intake happened after 2 PM, leaving a 6-hour morning gap. This early dehydration can affect focus and energy.",
  "peak_time": "afternoon"
}
```

---

### 9. Predictive Analytics — `/predictive`

#### `GET /predictive/analysis?uid=<uid>`
Runs 4 ML models on last 30 days of data.

**Full response shape:**
```json
{
  "days_analyzed": 15,

  "sleep_risk": {
    "risk_probability": 0.62,
    "risk_percent": 62.0,
    "risk_label": "Moderate",    // "Low" | "Moderate" | "High"
    "risk_level": "moderate",
    "features": {
      "avg_sleep_3d": 6.8,
      "std_dev": 1.2,
      "cum_deficit": -8.5
    }
  },

  "sleep_clusters": {
    "scatter_points": [
      {
        "date": "2026-02-15",
        "sleep_hours": 7.0,
        "bed_time_frac": 22.5,
        "bed_time_label": "10:30 PM",
        "cluster": 0,
        "cluster_name": "Consistent Sleeper",
        "cluster_color": "#22C55E"
      }
    ],
    "cluster_counts": {
      "Consistent Sleeper": 5,
      "Sleep Deprived": 3,
      "Irregular Sleeper": 7
    }
  },

  "hydration_clusters": {
    "daily_points": [
      {
        "date": "2026-02-15",
        "total_ml": 2200,
        "avg_hour": 13.5,
        "avg_hour_label": "1:30 PM",
        "cluster": 2,
        "cluster_name": "Late Hydrator",
        "cluster_color": "#F59E0B"
      }
    ],
    "cluster_counts": {
      "Early Hydrator": 3,
      "Late Hydrator": 8,
      "Under-hydrator": 4
    }
  },

  "weight_projection": {
    "projection_points": [
      { "day": "Feb 22", "weight": 71.8 },
      { "day": "Feb 23", "weight": 71.6 }
    ],
    "weekly_change_kg": -0.35,
    "current_weight": 72.5,
    "avg_calorie_deficit": 387.5,
    "trend": "losing"              // "gaining" | "losing" | "stable"
  }
}
```

---

### 10. Notifications — `/notifications`

#### `POST /notifications/register-token`
Call on every app open to keep FCM token fresh.

```json
{ "uid": "abc123", "fcm_token": "firebase_messaging_token_here" }
```
**Response:** `{ "status": "ok", "message": "FCM token registered" }`

#### `GET /notifications/preferences?uid=<uid>`
Get notification preferences for a user.

**Response:**
```json
{
  "uid": "abc123",
  "preferences": {
    "enabled": true,
    "timezone": "Asia/Kolkata",
    "wake_time": "07:00",
    "breakfast_time": "08:00",
    "lunch_time": "13:00",
    "dinner_time": "19:30",
    "bedtime_time": "22:30",
    "hydration_interval_hours": 3.0,
    "custom_slots": []
  }
}
```

#### `POST /notifications/preferences`
Save notification preferences (auto-seeds today's notification slots).

**Request body:**
```json
{
  "uid": "abc123",
  "enabled": true,
  "timezone": "Asia/Kolkata",
  "wake_time": "07:00",
  "breakfast_time": "08:00",
  "lunch_time": "13:00",
  "dinner_time": "19:30",
  "bedtime_time": "22:30",
  "hydration_interval_hours": 3.0,
  "custom_slots": []
}
```

#### `POST /notifications/register-token`
Register/refresh FCM token (call every app open).

#### `POST /notifications/ack`
Dismiss a notification (already logged manually).
```json
{ "uid": "abc123", "slot_label": "hydration_14:00", "date": "2026-02-21" }
```

#### `POST /notifications/quick-log`
Log from notification action without opening the app.

| `notification_type` | Valid `action` values |
|---|---|
| `hydration` | `ml_250`, `ml_500`, `ml_750` |
| `wake` | `i_am_awake` |
| `bedtime` | `log_now` |
| `breakfast` / `lunch` / `dinner` | `light_meal`, `full_meal`, `skipped` |
| any | `snooze_15`, `snooze_30`, `skip`, `logged` |

#### `POST /notifications/send-test`
Sends a real FCM push to the user (for testing).
```json
{ "uid": "abc123", "notification_type": "hydration" }
```

#### `GET /notifications/status?uid=<uid>&date=<YYYY-MM-DD>`
View all notification slots and their status for a day.

---

## 🎨 Frontend Design Guidance

### Data Flow Summary

```
App open
  └─ GET /profile/{uid}          → show user name, check if setup complete
  └─ POST /notifications/register-token  → always

Dashboard page
  └─ GET /log/today?uid=         → wellness score, hydration ml, sleep hours, nutrition totals

Sleep page
  └─ POST /log/sleep?uid=

Hydration page
  └─ POST /log/hydration?uid=

Nutrition / Meal Log page
  └─ POST /log/nutrition?uid=

Meal Planner page
  └─ POST /meal-plan/generate    → generate
  └─ POST /meal-plan/save        → save
  └─ GET  /meal-plan/saved       → load saved

Progress page (Week picker)
  └─ GET /analytics/weekly?uid=&week=1-4

Progress → Sleep Analysis
  └─ Uses data already fetched from /analytics/weekly

Progress → Sleep AI Insights
  └─ GET /sleep/ai-insights?uid=

Progress → Hydration Analysis
  └─ Uses /analytics/weekly data

Progress → Hydration AI Insights
  └─ GET /hydration/ai-insights?uid=

Progress → Predictive
  └─ GET /predictive/analysis?uid=

AI Assistant page
  └─ GET /chatbot/greeting/{uid}   → on page load
  └─ POST /chatbot/chat            → each message
  └─ DELETE /chatbot/history/{uid} → clear button

Profile page → Notifications
  └─ GET /notifications/preferences?uid=
  └─ POST /notifications/preferences

Notification tap (background)
  └─ POST /notifications/quick-log
  └─ POST /notifications/ack
```

### Score Colour Guide (for UI)

| Score range | Suggested colour |
|---|---|
| 0–39 | Red `#EF4444` |
| 40–59 | Orange `#F59E0B` |
| 60–79 | Blue `#3B82F6` |
| 80–100 | Green `#22C55E` |

### Trend Strings
API returns one of: `"improving"` | `"declining"` | `"stable"` — map to ↑ ↓ → icons.

### Sleep Cluster Colours (fixed from backend)
- `#22C55E` Consistent Sleeper
- `#8B5CF6` Early Sleeper
- `#EF4444` Sleep Deprived
- `#F59E0B` Irregular Sleeper

### Hydration Cluster Colours
- `#22C55E` Early Hydrator
- `#3B82F6` Consistent Hydrator
- `#F59E0B` Late Hydrator
- `#EF4444` Under-hydrator

---

## 🚀 Deployment Checklist

### Step 1 — MongoDB Atlas
1. Create a free M0 cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a database user with read/write access
3. Whitelist `0.0.0.0/0` (allow all IPs — required for Render)
4. Copy the connection string: `mongodb+srv://<user>:<pass>@cluster.mongodb.net/health_ai`

### Step 2 — Render Deployment
1. Push backend to a GitHub repo (exclude `.env` and `firebase_service_account.json`)
2. Create a new **Web Service** on [render.com](https://render.com)
3. Connect the GitHub repo
4. Set runtime: **Python 3.11**
5. Set Build Command: `pip install -r requirements.txt`
6. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
7. Add Environment Variables (from `.env`):
   - `MONGO_URI` → Atlas URI
   - `MONGO_DB_NAME` → `health_ai`
   - `GROQ_API_KEY` → Groq key
   - `FIREBASE_CREDENTIALS_PATH` → path to service account file
8. Upload `firebase_service_account.json` as a **Secret File** at `/etc/secrets/firebase_service_account.json`
9. Set `FIREBASE_CREDENTIALS_PATH=/etc/secrets/firebase_service_account.json`
10. Deploy → copy the Render URL (e.g. `https://health-ai-backend.onrender.com`)

### Step 3 — Update Flutter
In `lib/services/api_service.dart`:
```dart
static const String baseUrl = 'https://health-ai-backend.onrender.com';
```

### Step 4 — Verify
- `GET https://health-ai-backend.onrender.com/health` → `{ "status": "ok" }`
- `GET https://health-ai-backend.onrender.com/docs` → Swagger UI with all 27 endpoints
