# 🏥 Health AI - Multi-Agent Health Monitoring System

A multi-agent AI system for personalized health monitoring using LangGraph to orchestrate specialized health agents. This system analyzes your profile, sleep patterns, and hydration levels to provide comprehensive health insights.

---

## 📋 Table of Contents

- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Agent Logic](#agent-logic)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Future Enhancements](#future-enhancements)

---

## 🛠️ Tech Stack

### **Backend**
- **Python 3.14** - Core programming language
- **FastAPI** - RESTful API framework (optional, for production)
- **LangGraph 1.0.8** - Multi-agent orchestration framework
- **LangChain Core 1.2.13** - Agent workflow foundation
- **Pydantic 2.12.5** - Data validation and schemas

### **Frontend (Testing)**
- **Streamlit 1.54.0** - Interactive web dashboard for testing agents
- **Altair 6.0.0** - Data visualization

### **Data Processing**
- **Pandas 2.3.3** - Data manipulation
- **NumPy 2.4.2** - Numerical computations

### **Future Frontend**
- **Flutter** - Cross-platform mobile app (planned)
- **MCP (Model Context Protocol)** - For agent communication

---

## 🏗️ Architecture

### **Multi-Agent Pipeline**

```
┌─────────────┐
│ User Input  │
│ (Age, etc.) │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Profile Agent   │ ◄─── Calculates BMR, Water Target, Protein Target
│  (Node 1)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Sleep Agent    │ ◄─── Analyzes Sleep Quality & Deficit
│   (Node 2)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Hydration Agent  │ ◄─── Calculates Hydration Score
│   (Node 3)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Final Results   │
│  (All Metrics)   │
└──────────────────┘
```

### **State Management**

All agents share a common **state dictionary** that flows through the pipeline:

```python
state = {
    # User Inputs
    "age": 25,
    "weight": 70,
    "height": 170,
    "gender": "male",
    "sleep_hours": 7,
    "water_intake": 2000,
    
    # Agent Outputs (added progressively)
    "calorie_target": 1730,      # From Profile Agent
    "water_target": 2450,        # From Profile Agent
    "protein_target": 84,        # From Profile Agent
    "sleep_score": 90,           # From Sleep Agent
    "sleep_deficit": 0,          # From Sleep Agent
    "hydration_score": 81        # From Hydration Agent
}
```

---

## ⚙️ How It Works

### **1. LangGraph Orchestration**

The system uses **LangGraph's StateGraph** to create a directed acyclic graph (DAG) of agents:

```python
# app/graph/health_graph.py
def build_graph():
    builder = StateGraph(dict)
    
    # Add agent nodes
    builder.add_node("profile", profile_agent)
    builder.add_node("sleep", sleep_agent)
    builder.add_node("hydration", hydration_agent)
    
    # Define execution flow
    builder.set_entry_point("profile")
    builder.add_edge("profile", "sleep")
    builder.add_edge("sleep", "hydration")
    
    return builder.compile()
```

**Key Concepts:**
- **Nodes**: Each agent is a node that processes the state
- **Edges**: Define the execution order (Profile → Sleep → Hydration)
- **State**: A shared dictionary that accumulates data as it flows through agents

### **2. Sequential Processing**

Each agent:
1. Receives the current state
2. Performs its calculations
3. Adds results to the state
4. Returns the updated state to the next agent

---

## 🧠 Agent Logic

### **👤 Profile Agent** (`app/agents/profile_agent.py`)

**Purpose:** Calculate personalized health targets based on user profile

**Inputs:**
- `weight` (kg)
- `height` (cm)
- `age` (years)
- `gender` (male/female)

**Logic:**

#### 1. **BMR (Basal Metabolic Rate)** - Mifflin-St Jeor Equation
```python
# app/services/formulas.py
def calculate_bmr(weight, height, age, gender="male"):
    if gender == "male":
        # BMR for males
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        # BMR for females
        return 10 * weight + 6.25 * height - 5 * age - 161
```

**Example:**
- Male, 70kg, 170cm, 25 years old
- BMR = 10(70) + 6.25(170) - 5(25) + 5 = **1730 kcal/day**

#### 2. **Water Target**
```python
def water_target_ml(weight):
    return weight * 35  # 35ml per kg of body weight
```

**Example:**
- 70kg → **2450 ml/day**

#### 3. **Protein Target**
```python
def protein_target_g(weight):
    return weight * 1.2  # 1.2g per kg (moderate activity)
```

**Example:**
- 70kg → **84 g/day**

**Outputs:**
- `calorie_target`: Daily calorie needs
- `water_target`: Daily water intake goal (ml)
- `protein_target`: Daily protein requirement (g)

---

### **😴 Sleep Agent** (`app/agents/sleep_agent.py`)

**Purpose:** Analyze sleep quality and calculate sleep deficit

**Inputs:**
- `sleep_hours` (hours slept last night)

**Logic:**
```python
def sleep_agent(state: dict):
    sleep_hours = state.get("sleep_hours", 0)
    
    if sleep_hours >= 7:
        score = 90          # Excellent sleep
        deficit = 0
    else:
        score = 50          # Insufficient sleep
        deficit = 7 - sleep_hours  # Hours short of recommended
    
    state["sleep_score"] = score
    state["sleep_deficit"] = deficit
    
    return state
```

**Sleep Score Interpretation:**
- **90**: Getting ≥7 hours (optimal sleep)
- **50**: Getting <7 hours (sleep deprived)

**Example:**
- 6 hours slept → Score: **50**, Deficit: **1 hour**
- 8 hours slept → Score: **90**, Deficit: **0 hours**

**Outputs:**
- `sleep_score`: 0-100 quality score
- `sleep_deficit`: Hours needed to reach 7-hour target

---

### **💧 Hydration Agent** (`app/agents/hydration_agent.py`)

**Purpose:** Calculate hydration percentage based on intake vs target

**Inputs:**
- `water_intake` (ml consumed today)
- `water_target` (ml goal from Profile Agent)

**Logic:**
```python
def hydration_agent(state: dict):
    intake = state.get("water_intake", 0)
    target = state.get("water_target", 2000)
    
    # Calculate percentage, cap at 100%
    percent = int((intake / target) * 100) if target > 0 else 0
    state["hydration_score"] = min(percent, 100)
    
    return state
```

**Formula:**
```
Hydration Score = (Water Intake / Water Target) × 100
```

**Example:**
- Intake: 1500ml, Target: 2450ml
- Score: (1500 / 2450) × 100 = **61%**

**Hydration Levels:**
- **100%+**: Fully hydrated ✅
- **75-99%**: Good hydration 👍
- **50-74%**: Moderate - drink more ⚠️
- **<50%**: Dehydrated - urgent 🚨

**Outputs:**
- `hydration_score`: 0-100% of daily target

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI endpoints (future)
│   ├── schemas.py              # Pydantic models (future)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── profile_agent.py    # 👤 Profile calculations
│   │   ├── sleep_agent.py      # 😴 Sleep analysis
│   │   └── hydration_agent.py  # 💧 Hydration tracking
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   └── health_graph.py     # 🔄 LangGraph orchestration
│   │
│   └── services/
│       ├── __init__.py
│       └── formulas.py         # 📐 Health calculation formulas
│
├── streamlit_test/
│   └── app.py                  # 🖥️ Streamlit testing dashboard
│
├── requirements.txt            # 📦 Python dependencies
└── README.md                   # 📖 This file
```

---

## 🚀 Setup & Installation

### **Prerequisites**
- Python 3.10 or higher
- pip (Python package manager)

### **Installation Steps**

1. **Clone the repository**
```powershell
git clone <your-repo-url>
cd health-ai/backend
```

2. **Create virtual environment**
```powershell
python -m venv venv
```

3. **Activate virtual environment**
```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# Linux/Mac
source venv/bin/activate
```

4. **Install dependencies**
```powershell
pip install -r requirements.txt
```

5. **Create package structure** (if not already present)
```powershell
# Ensure __init__.py files exist in all subdirectories
```

---

## 💻 Usage

### **Option 1: Streamlit Dashboard (Recommended for Testing)**

Launch the interactive web dashboard:

```powershell
streamlit run streamlit_test/app.py
```

**Access:** http://localhost:8501

**Features:**
- 📝 Input health data via sidebar
- 📊 View comprehensive analysis
- 🔍 Inspect individual agent outputs
- 📈 Track progress with visual indicators

### **Option 2: FastAPI Server (Future)**

```powershell
uvicorn app.main:app --reload
```

**Access:** http://localhost:8000/docs

### **Option 3: Python Script**

```python
from app.graph.health_graph import build_graph

# Create the graph
graph = build_graph()

# Define input state
initial_state = {
    "age": 25,
    "weight": 70,
    "height": 170,
    "gender": "male",
    "sleep_hours": 7,
    "water_intake": 2000
}

# Run the multi-agent system
result = graph.invoke(initial_state)

# Access results
print(f"Calorie Target: {result['calorie_target']} kcal")
print(f"Hydration Score: {result['hydration_score']}%")
print(f"Sleep Score: {result['sleep_score']}")
```

---

## 📊 Example Use Case

### **User Profile:**
- Name: John Doe
- Age: 28 years
- Weight: 75 kg
- Height: 175 cm
- Gender: Male

### **Daily Data:**
- Sleep: 6.5 hours
- Water: 1800 ml

### **System Analysis:**

#### **Profile Agent Results:**
- 🔥 **Calorie Target:** 1,818 kcal/day
- 💧 **Water Target:** 2,625 ml/day
- 🥩 **Protein Target:** 90 g/day

#### **Sleep Agent Results:**
- 😴 **Sleep Score:** 50 (Insufficient)
- ⏰ **Sleep Deficit:** 0.5 hours
- 💡 **Recommendation:** Get 30 more minutes of sleep

#### **Hydration Agent Results:**
- 💧 **Hydration Score:** 69%
- 📉 **Status:** Moderate - drink more water
- 🥤 **Remaining:** 825 ml (≈3 glasses)

---

## 🔮 Future Enhancements

### **Planned Features:**

1. **Additional Agents:**
   - 🍎 Nutrition Agent (calorie tracking, macros)
   - 🏃 Exercise Agent (activity level monitoring)
   - ❤️ Heart Health Agent (HR, BP tracking)
   - 🧘 Stress Agent (mental health assessment)

2. **Advanced Features:**
   - Historical data tracking
   - Trend analysis and predictions
   - Personalized recommendations using LLMs
   - Integration with wearables (Fitbit, Apple Watch)

3. **Frontend:**
   - Flutter mobile app
   - MCP integration for real-time agent communication
   - Data visualization dashboards
   - Notification system for health reminders

4. **Backend:**
   - User authentication
   - Database integration (PostgreSQL)
   - RESTful API endpoints
   - Data persistence and history

5. **AI Enhancements:**
   - LLM-powered health insights
   - Natural language interaction
   - Anomaly detection
   - Predictive health alerts

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

[Your License Here]

---

## 📞 Contact

For questions or support, please [create an issue](your-repo-issues-url).

---

## 🙏 Acknowledgments

- **LangGraph** - For the multi-agent framework
- **Streamlit** - For rapid prototyping
- **Mifflin-St Jeor** - For the BMR formula

---

**Built with ❤️ using LangGraph and Python**
