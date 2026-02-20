# Health AI - Multi-Day Analytics Update

## 🎯 What's New

The Health AI system now supports **multi-day analytics** for a single user, enabling trend analysis and pattern detection across multiple days.

## ✨ Key Features Implemented

### 1. **Single User, Multi-Day Tracking**
- Logs are designed for tracking a **single user's health journey** over time
- Day-wise analytics for individual days
- Combined analytics for 3-day periods and weekly summaries

### 2. **Automated Water Suggestions** 
- Water intake is **NO longer an input**
- System automatically calculates recommended water intake based on:
  - Age (with age-based adjustments)
  - Weight
  - Activity level

### 3. **New Agents**

#### **Log & Context Agent**
- Processes daily intake logs
- Extracts user profile, meals, exercise, sleep data
- Prepares data for downstream agents

#### **Multi-Day Analytics Agent**
- Combines multiple days of analysis
- Calculates period averages and totals
- Detects trends (improving/declining/stable)
- Identifies problem days
- Generates comprehensive insights

### 4. **Enhanced Analytics**

#### Day-Wise Analysis Includes:
- Overall health score (0-100)
- Sleep analysis with deficit tracking
- Hydration score with automated recommendations
- Calorie and protein tracking
- Exercise and activity metrics
- Personalized daily insights

#### Multi-Day Analysis Includes:
- **Period Averages**: Sleep, hydration, steps, exercise, nutrition
- **Period Totals**: Cumulative metrics across all days
- **Trend Detection**: Comparing first half vs second half
- **Problem Day Analysis**: Days with sleep deficit, poor hydration, low activity
- **Consistency Score**: Overall adherence to healthy habits
- **Day-by-Day Breakdown**: Quick reference for each day

## 📊 Sample Output

### 3-Day Analysis for John Smith (Feb 14-16, 2026)

```
Overall Score: 77/100 (GOOD)
Trend: DECLINING (-14.0 points)

Period Averages:
- Sleep: 7.3 hours/night
- Hydration: 82% average score  
- Activity: 7,900 steps/day
- Exercise: 35 min/day
- Nutrition: 2,163 kcal/day, 108g protein/day

Problem Days: 
- 1/3 days with sleep deficit
- 1/3 days with poor hydration
- 1/3 days with low activity
- Consistency Score: 66%

Daily Breakdown:
- Day 1 (Friday): 87/100 - Energetic, good habits
- Day 2 (Saturday): 50/100 - Lazy day, poor choices
- Day 3 (Sunday): 96/100 - Motivated, excellent recovery
```

## 🗂️ File Structure

```
backend/
├── app/
│   ├── agents/
│   │   ├── log_context_agent.py         # NEW: Processes daily logs
│   │   ├── analytics_agent.py           # NEW: Day-wise analytics
│   │   ├── multi_day_analytics_agent.py # NEW: Multi-day analytics
│   │   ├── hydration_agent.py           # UPDATED: Auto water suggestion
│   │   ├── profile_agent.py
│   │   └── sleep_agent.py
│   ├── graph/
│   │   └── health_graph.py              # UPDATED: New agent flow
│   ├── main.py                           # UPDATED: Multi-day endpoint
│   └── ...
├── test_data/                            # NEW: Sample data folder
│   ├── user1_day1.json                   # Day 1: Good habits
│   ├── user1_day2.json                   # Day 2: Poor habits  
│   ├── user1_day3.json                   # Day 3: Excellent habits
│   ├── daily_logs_sample.json
│   ├── daily_logs_sample_2.json
│   ├── daily_logs_sample_3.json
│   └── README.md
├── test_analysis.py                      # Single-day testing
└── test_multi_day_analysis.py           # NEW: Multi-day testing
```

## 🚀 How to Use

### Test Scripts

```bash
# Test single-day analysis (3 different users)
python test_analysis.py

# Test multi-day analysis (1 user, 3 days)
python test_multi_day_analysis.py
```

### FastAPI Endpoints

```bash
# Start server
uvicorn app.main:app --reload

# Single-day analysis
POST /analyze
Body: {user_profile, daily_logs}

# Multi-day analysis  
POST /analyze/multi-day
Body: {days: [day1, day2, day3, ...]}

# Legacy endpoint (backward compatible)
POST /analyze/legacy
Body: {age, weight, height, gender, sleep_hours, water_intake}
```

## 🎨 Data Format

### Single Day
```json
{
  "user_profile": {
    "user_id": "user001",
    "name": "John Smith",
    "age": 28,
    "weight": 72,
    "height": 175,
    "gender": "male"
  },
  "daily_logs": {
    "date": "2026-02-14",
    "day_of_week": "Friday",
    "sleep": {
      "hours": 7.5,
      "quality": "good",
      "bed_time": "23:00",
      "wake_time": "06:30"
    },
    "meals": [...],
    "exercise": {...},
    "water_intake_ml": 2200,
    "steps": 8500,
    "mood": "energetic"
  }
}
```

### Multi-Day Request
```json
{
  "days": [
    {user_profile, daily_logs},
    {user_profile, daily_logs},
    {user_profile, daily_logs}
  ]
}
```

## 📈 Agent Flow

```
User Input (Daily Logs)
    ↓
Log & Context Agent ─→ Extract profile, meals, sleep, exercise
    ↓
Profile Agent ─→ Calculate BMR, water target, protein target
    ↓
Sleep Agent ─→ Analyze sleep quality, calculate deficit
    ↓
Hydration Agent ─→ Auto-suggest water based on age/weight
    ↓
Analytics Agent ─→ Generate day insights, overall score
    ↓
[For Multi-Day]
    ↓
Multi-Day Analytics Agent ─→ Trends, averages, consistency
```

## 💡 Key Insights Generated

1. **Sleep Patterns**: Average hours, deficit tracking, quality trends
2. **Hydration Habits**: Auto-calculated needs vs actual intake
3. **Activity Levels**: Step counts, exercise frequency, consistency
4. **Nutrition Balance**: Calorie targets, protein intake, meal patterns
5. **Health Trends**: Improving/declining patterns over time
6. **Consistency Scoring**: Adherence to healthy habits
7. **Problem Day Detection**: Specific days needing attention

## 🎯 Next Steps

Potential enhancements:
- Weekly summaries (7 days)
- Monthly trends and comparisons
- Goal setting and tracking
- Personalized recommendations based on trends
- Export reports as PDF
- Integration with wearables for automatic logging
- AI-powered meal suggestions based on deficits

## 📝 Testing the System

Run the multi-day test to see all features in action:

```bash
python test_multi_day_analysis.py
```

This will show:
- ✅ Day-by-day analysis for 3 consecutive days
- ✅ Combined 3-day period analytics
- ✅ Trend detection
- ✅ Problem day identification
- ✅ Comprehensive insights and recommendations
