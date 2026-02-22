# 🏥 TriVita Backend — API Reference

TriVita Backend is a robust FastAPI service powering the TriVita health and wellness ecosystem. It handles user profiles, health data logging, AI-driven insights, and a sophisticated notification scheduler.

## 🚀 Key Features

- **Consolidated Notification System**: Simplified 4-toggle management (Global, Sleep, Nutrition, Hydration).
- **Automated Scheduling**: Precise notification seeding and 5-minute cycle processing.
- **AI Health Insights**: Personalized sleep and hydration analysis using Groq LLM.
- **Predictive Analytics**: Machine learning models (scikit-learn) for sleep risk and weight projection.
- **Scalable Architecture**: Built with FastAPI and MongoDB (Motor/Async).

---

## 🏗️ Technical Stack

- **Framework**: FastAPI
- **Database**: MongoDB (Motor / Atlas)
- **AI/LLM**: Groq (Llama-3.3-70B)
- **ML Engine**: Scikit-Learn
- **Scheduler**: Async APScheduler
- **Push Notifications**: Firebase Admin (FCM)

---

## 📁 Project Structure

```text
Backend/
├── app/
│   ├── agents/          # AI logic (Chatbot, Nutrition)
│   ├── core/            # Config and global settings
│   ├── db/              # MongoDB connection and state helpers
│   ├── models/          # Pydantic schemas for API and DB
│   ├── routes/          # FastAPI endpoint definitions
│   ├── scheduler/       # Notification background tasks
│   ├── services/        # Business logic (FCM, scoring, formulas)
│   ├── mcp/             # Model Context Protocol (AI data access)
│   └── main.py          # Application entry point
├── .env.example         # Example environment variables
├── requirements.txt     # Python dependencies
└── README.md            # Documentation
```

---

## 🛠️ Setup & Deployment

### Local Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Create a `.env` file based on `.env.example`:
   ```env
   MONGO_URI=your_mongodb_uri
   MONGO_DB_NAME=health_ai
   GROQ_API_KEY=your_groq_key
   FIREBASE_CREDENTIALS_PATH=firebase_service_account.json
   ```

3. **Run Service**:
   ```bash
   uvicorn app.main:app --reload
   ```

### Render Deployment

- **Environment**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**: Set `MONGO_URI`, `GROQ_API_KEY`, etc. in the Render dashboard.
- **Secret Files**: Upload your Firebase service account JSON as a Secret File and set its path in `FIREBASE_CREDENTIALS_PATH`.

---

## 🔌 Core API Endpoints

### 1. Profile (`/profile`)
- `POST /profile/create`: Register user and compute personalized daily targets.
- `GET /profile/{uid}`: Retrieve full profile including targets and preferences.

### 2. Notifications (`/notifications`)
- `GET /preferences?uid=<uid>`: Fetch current toggles and scheduled times.
- `POST /preferences`: Save and sync schedule. This auto-seeds today's notification slots.
- `GET /status?uid=<uid>&date=<YYYY-MM-DD>`: Live tracker of generated/sent/resolved slots.
- `POST /register-token`: Update FCM token for push delivery.

### 3. Health Logging (`/log`)
- `POST /log/sleep`: Log sleep duration and quality.
- `POST /log/hydration`: Record water intake.
- `POST /log/nutrition`: Log meals with macro breakdown.
- `GET /log/today`: Fetch all logs and current Wellness/Sleep/Hydration scores.

### 4. AI & Analytics (`/chatbot`, `/analytics`, `/predictive`)
- `POST /chatbot/chat`: Dynamic health assistant with full contextual awareness.
- `GET /sleep/ai-insights`: Deep dive into sleep patterns and root causes.
- `GET /predictive/analysis`: ML-powered risk probability and trend clusters.

---

## 🔒 Notification Logic

TriVita uses 16 daily micro-log reminders:
- **Sleep (2)**: Wake & Bedtime.
- **Nutrition (6)**: 6 strategic meal windows.
- **Hydration (8)**: 250ml units spaced across the active day.

**Consolidated Toggles**:
The system respects 4 master flags: `global_enabled`, `sleep_enabled`, `nutrition_enabled`, and `hydration_enabled`. If a category is disabled, the scheduler skips generating those specific slots for the day.
