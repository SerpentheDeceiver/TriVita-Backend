# 🏥 TriVita

TriVita is an intelligent health and wellness platform designed to bridge the gap between data logging and actionable health improvements. Unlike traditional trackers, TriVita uses a high-frequency **Micro-Logging** approach combined with **Domain-Specific AI Agents** to provide users with real-time feedback and long-term predictive health trends.

---

# 📁 Backend Folder Structure

```
Backend/
├── app/
│   ├── agents/
│   ├── routes/
│   ├── scheduler/
│   ├── services/
│   ├── db/
│   ├── models/
│   ├── mcp/
│   ├── graph/
│   └── main.py
├── firebase_service_account.json
├── requirements.txt
└── README.md
```

---

# 🧠 app/ (Core Application Layer)

The `app/` directory contains the entire backend application logic. It is modular and separated by responsibility to ensure scalability and maintainability.

---

## 1️⃣ agents/

Contains domain-specific AI agents responsible for health intelligence.

### Responsibilities:
- Sleep analysis agent
- Hydration analysis agent
- Nutrition analysis agent
- Risk & predictive agent
- AI reasoning logic
- Prompt engineering & structured outputs

Each agent processes structured health logs and produces insights or recommendations.

---

## 2️⃣ routes/

Defines all FastAPI API endpoints.

### Responsibilities:
- Profile creation and retrieval
- Health log submission
- Notification preference management
- AI chatbot endpoint
- Predictive analytics endpoint
- Sleep insight endpoint

Each route:
- Validates input using Pydantic models
- Calls appropriate service layer logic
- Returns structured JSON responses

---

## 3️⃣ scheduler/

Handles the background notification engine.

### Responsibilities:
- Seeds 16 daily micro-log slots
- Runs every 5 minutes using APScheduler
- Checks toggle flags before sending notifications
- Tracks slot state (generated, sent, resolved, missed)
- Triggers Firebase Cloud Messaging (FCM)

This ensures consistent micro-logging reminders.

---

## 4️⃣ services/

Contains core business logic separate from routes.

### Responsibilities:
- BMR / TDEE calculation
- Hydration & sleep scoring formulas
- Wellness score computation
- Notification slot generation logic
- Firebase push notification handling
- Predictive model loading and execution

Routes call services to maintain clean architecture separation.

---

## 5️⃣ db/

Manages MongoDB interaction and persistent state.

### Responsibilities:
- MongoDB client initialization (Motor Async)
- Database connection pooling
- User document management
- Log storage
- Notification slot persistence
- Query helpers

All database operations are centralized here.

---

## 6️⃣ models/

Contains Pydantic schemas used for:

- Request validation
- Response formatting
- Database data structure consistency
- Type safety enforcement

Ensures strict API contracts and structured data flow.

---

## 7️⃣ mcp/

Implements the Model Context Protocol layer.

### Responsibilities:
- Shared health state management
- Tool-calling interface for AI agents
- Unified data access for multi-agent reasoning
- Context injection into AI prompts

Ensures all AI agents reason over the same updated health state.

---

## 8️⃣ graph/

Contains LangGraph-based AI workflow definitions.

### Responsibilities:
- Multi-agent orchestration
- Agent sequencing logic
- Cross-signal reasoning flow
- Conditional execution paths

Defines how agents collaborate within a structured reasoning pipeline.

---

## 9️⃣ main.py

Application entry point.

### Responsibilities:
- FastAPI app initialization
- Middleware configuration
- Router inclusion
- Startup & shutdown events
- Scheduler initialization
- Environment configuration loading

This file bootstraps the entire backend system.

---

# 🔐 Supporting Files

## firebase_service_account.json
- Firebase Admin SDK credentials
- Used for push notifications via FCM
- Loaded securely using environment configuration

## requirements.txt
Contains all backend dependencies:
- FastAPI
- Uvicorn
- Motor (MongoDB async driver)
- APScheduler
- Firebase Admin
- Groq SDK
- Scikit-learn
- Pandas / NumPy
- ReportLab

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

## 🏗️ Technical Stack

- **Framework**: FastAPI
- **Database**: MongoDB (Motor / Atlas)
- **AI/LLM**: Groq (Llama-3.3-70B)
- **ML Engine**: Scikit-Learn
- **Scheduler**: Async APScheduler
- **Push Notifications**: Firebase Admin (FCM)

---

# To-Note:

The TriVita Backend is a modular, AI-integrated FastAPI system that:

- Handles user profiles and health logs
- Manages a 16-slot micro-notification engine
- Executes multi-agent AI reasoning
- Computes real-time wellness scoring
- Performs predictive health analytics
- Maintains persistent health state in MongoDB