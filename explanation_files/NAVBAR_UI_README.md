# Health AI - Navbar UI Restructure

## Overview
Complete restructure of the Health AI application with a navbar-based UI, separated data logs, and enhanced agent capabilities.

## Key Changes

### 1. **New Data Structure**
- **Removed**: `test_data/` folder with consolidated daily logs
- **Created**: `weekly_logs/` folder with separate log files per day

#### Data File Structure
```
tests/weekly_logs/
  day1/
    profile.json       - User profile with weight goals
    sleep.json         - Sleep patterns and quality
    hydration.json     - Water intake logs
    nutrition.json     - Meal and macro logs
    activity.json      - Exercise and mood tracking
```

### 2. **UI Restructure - Navbar Components**

#### Navigation Structure
The streamlit app now features 4 main navbar components:

1. **👤 Profile**
   - Personal information (age, weight, height, gender)
   - Weight goals (maintain/reduce/increase)
   - Target weight change and timeline
   - Activity level selection
   - BMI calculation and display

2. **😴 Sleep**
   - Sleep hours input
   - Bed time and wake time
   - Sleep quality rating
   - Interruption tracking
   - Dream recall
   - Feeling on wake
   - Advanced sleep scoring (0-100)

3. **💧 Hydration**
   - Water intake tracking
   - Age-based water target calculation
   - Caffeine intake monitoring
   - Urine color indicator
   - Hydration status and advice

4. **🍽️ Nutrition**
   - Calorie and macro tracking
   - AI-powered meal suggestions (Groq LLM)
   - Budget-aware meal planning
   - Weight goal-adjusted recommendations

### 3. **Enhanced Agents**

#### Profile Agent
- **New Features**:
  - TDEE calculation based on activity level
  - Weight goal-adjusted calorie targets
  - Protein requirements scaled by goal (2.2g/kg for weight loss, 2.0g/kg for gain)
  - Safe weight change calculations (max 1kg/week)

#### Sleep Agent
- **New Features**:
  - Multi-factor sleep scoring (duration, quality, interruptions, feeling)
  - Bed time and wake time tracking
  - Sleep quality assessment
  - Dream recall tracking
  - Sophisticated deficit calculation

#### Hydration Agent
- **New Features**:
  - Age-based water requirements (30-35ml/kg)
  - Activity level adjustments
  - Caffeine dehydration compensation
  - Urine color analysis
  - Personalized hydration advice

#### Nutrition Agent (AI)
- **New Features**:
  - Weight goal integration
  - Groq LLM-powered meal suggestions
  - Budget-aware meal planning ($5-50 per meal)
  - Macro-balanced recommendations
  - Reasoning for each meal suggestion

### 4. **Input Changes**

#### Sleep Inputs
- ✅ Sleep hours
- ✅ Bed time (HH:MM)
- ✅ Wake time (HH:MM)
- ✅ Sleep quality (poor/fair/good/excellent)
- ✅ Interruptions count
- ✅ Dream recall (yes/no)
- ✅ Feeling on wake (refreshed/neutral/groggy/exhausted)

#### Hydration Inputs
- ✅ Water intake (ml)
- ✅ Caffeine intake (mg)
- ✅ Urine color (5-point scale)
- 🤖 Water target auto-calculated based on age, weight, activity

#### Profile Inputs
- ✅ Age, weight, height, gender
- ✅ Weight goal (maintain/reduce/increase)
- ✅ Target weight change (kg)
- ✅ Timeline (weeks)
- ✅ Activity level (sedentary to very active)

### 5. **Log Context Agent Update**

The `log_context_agent.py` has been completely rewritten to:
- Process separate log files (sleep, hydration, nutrition, activity)
- Extract and route data to specialized agents
- Handle weight goal parameters
- Support flexible data structure

### 6. **Analysis Flow**

```
User Input (Sidebar) 
  ↓
Profile Agent → Calculate targets
  ↓
Sleep Agent → Score sleep quality
  ↓
Hydration Agent → Calculate water needs
  ↓
Nutrition Agent (AI) → Generate meal plans
  ↓
Analytics Agent → Comprehensive analysis
  ↓
Display Results (Main Content Area)
```

## Running the Application

### 1. **Environment Setup**
```bash
# Activate virtual environment
venv\Scripts\Activate.ps1

# Ensure dependencies are installed
pip install -r requirements.txt
```

### 2. **Configure Groq API**
Create a `.env` file in the backend directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. **Start Streamlit App**
```bash
streamlit run tests\streamlit_test\app.py
```

### 4. **Usage Flow**
1. Click **👤 Profile** → Fill in personal details and weight goals → Save
2. Click **😴 Sleep** → Enter sleep data → Save
3. Click **💧 Hydration** → Enter water intake → Save
4. Click **🍽️ Nutrition** → Enter meal data → Save
5. Click **🚀 Run Complete Health Analysis** at the bottom
6. Navigate through each navbar tab to see specialized insights

## Weight Goal Calculations

### Weight Loss (Reduce)
- Calorie deficit = (target_kg × 7700) / (timeline_weeks × 7)
- Daily calories = TDEE - calorie_deficit
- Minimum: 1200 kcal (female) / 1500 kcal (male)
- Protein: 2.2g/kg (muscle preservation)

### Weight Gain (Increase)
- Calorie surplus = (target_kg × 7700) / (timeline_weeks × 7)
- Daily calories = TDEE + calorie_surplus
- Maximum: TDEE + 1000 kcal (safe bulking)
- Protein: 2.0g/kg (muscle building)

### Maintain
- Daily calories = TDEE
- Protein: 1.6g/kg (maintenance)

## Hydration Formula

```
Base Water = ml_per_kg × weight
  where ml_per_kg = 35 (age < 30)
                   33 (age 30-55)
                   30 (age > 55)

Activity Adjustment:
  - Sedentary: 1.0×
  - Light: 1.1×
  - Moderate: 1.2×
  - Active: 1.3×
  - Very Active: 1.4×

Caffeine Compensation = caffeine_mg × 1.5 (max 500ml)

Total = (Base Water × Activity) + Caffeine Compensation
```

## Sleep Scoring Algorithm

```
Total Score (0-100):
  - Duration (40%): 7-9 hours = full points
  - Quality (30%): excellent/good/fair/poor
  - Interruptions (15%): 0 = full, 2+ = minimal
  - Feeling (15%): refreshed = full, exhausted = 0
```

## Files Modified

### Created
- `tests/weekly_logs/day1/*` - New data structure
- `tests/streamlit_test/app.py` - Navbar-based UI

### Enhanced
- `app/agents/profile_agent.py` - Weight goal calculations
- `app/agents/sleep_agent.py` - Multi-factor scoring
- `app/agents/hydration_agent.py` - Age-based targets
- `app/agents/nutrition_agent.py` - Weight goal integration
- `app/agents/log_context_agent.py` - Separate log routing

### Deleted
- `tests/test_data/` - Old consolidated logs
- `app/agents/multi_day_analytics_agent.py` - Merged into analytics_agent

## Future Enhancements

1. **Multi-day Analysis** - Track trends across weekly_logs/day1, day2, etc.
2. **Goal Progress Visualization** - Charts showing weight/calorie trends
3. **Export Reports** - PDF/CSV export of analysis results
4. **Customizable Targets** - Override auto-calculated targets
5. **Integration with Wearables** - Import data from fitness trackers

## Troubleshooting

### "No module named 'app'" Error
- Ensure you're running from the backend directory
- Virtual environment must be activated

### "GROQ_API_KEY not found"
- Create `.env` file with your API key
- Restart streamlit after adding the key

### Empty Analysis Results
- Fill in Profile first (required)
- Save each section before running analysis
- Check that all agents are in the graph pipeline

## Architecture Benefits

✅ **Cleaner UI** - Navbar navigation makes each section focused
✅ **Separated Concerns** - Each agent handles specific health aspect
✅ **Flexible Data** - Separate log files allow independent tracking
✅ **Personalized** - Weight goals adjust all recommendations
✅ **AI-Powered** - Groq LLM provides intelligent meal planning
