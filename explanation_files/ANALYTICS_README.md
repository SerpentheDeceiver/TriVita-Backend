# Analytics Feature - Multi-Day Health Trends

## Overview
The Analytics page provides comprehensive multi-day trend analysis for Sleep, Hydration, and Nutrition habits. Users can analyze data from 1 to 7 days to identify patterns and track progress.

## Features

### 📊 Analytics Page Components

#### 1. Analysis Type Selection
Choose which health aspect to analyze:
- **Sleep** - Sleep patterns, quality, and deficit tracking
- **Hydration** - Water intake, hydration status, and compliance
- **Nutrition** - Calorie and macro nutrient trends

#### 2. Time Period Selection
Analyze different time spans:
- 1 Day - Single day snapshot
- 2 Days - Short-term comparison
- 3 Days - 3-day trend
- 4 Days - Mid-week analysis
- 5 Days - Weekday pattern
- 6 Days - Extended period
- 7 Days (Full Week) - Complete weekly overview

### 📈 Sleep Analytics

#### Summary Metrics (Top Row)
1. **Average Sleep** - Mean hours of sleep across selected days
2. **Average Score** - Overall sleep quality score (0-100)
3. **Total Deficit** - Cumulative sleep deficit in hours
4. **Good Nights** - Count of nights with score ≥ 70

#### Daily Breakdown
Each day displays:
- Sleep hours and quality rating
- Sleep score and interruption count
- Sleep deficit and feeling on wake
- Bed time and wake time

**Example Insights:**
```
Day 5 (Friday):
- 6.0h sleep, Poor quality
- Score: 45/100
- 3 interruptions
- Feeling: Groggy
- Deficit: 1.5h
→ Indicates need for earlier bed time
```

### 💧 Hydration Analytics

#### Summary Metrics (Top Row)
1. **Avg Water Intake** - Mean daily water consumption (ml)
2. **Avg Hydration Score** - Mean hydration percentage
3. **Avg Deficit** - Average shortfall from target (ml)
4. **Optimal Days** - Days with score ≥ 90%

#### Daily Breakdown
Each day displays:
- Water intake and hydration status
- Hydration score and caffeine intake
- Recommended target and deficit
- Personalized hydration advice

**Example Insights:**
```
7-Day Average: 2,186ml/day
Target: 2,400ml/day
Deficit: 214ml/day

Day 5 shows critical hydration (1,600ml)
→ Suggestion: Set hourly water reminders
```

### 🍽️ Nutrition Analytics

#### Summary Metrics (Top Row)
1. **Avg Calories** - Mean daily calorie intake
2. **Avg Protein** - Mean daily protein consumption (g)
3. **Avg Carbs** - Mean daily carbohydrate intake (g)
4. **Avg Fat** - Mean daily fat consumption (g)

#### Daily Breakdown
Each day displays:
- Actual vs target calories (with delta)
- Actual vs target protein (with delta)
- Carbohydrates and fat totals
- Meal count and budget per meal

**Example Insights:**
```
Weekly Average: 2,036 kcal/day
Target: 2,100 kcal/day
Deficit: -64 kcal/day

Day 5 (Friday): 2,200 kcal (+100 from target)
Day 7 (Sunday): 1,950 kcal (-150 from target)
→ Good weekly balance
```

## Usage Flow

### Step 1: Navigate to Analytics
Click **📊 Analytics** in the navbar

### Step 2: Configure Analysis
In the sidebar:
1. Select **Analysis Type** (Sleep/Hydration/Nutrition)
2. Choose **Time Period** (1-7 days)
3. Click **📊 Run Multi-Day Analysis**

### Step 3: Review Results
The main panel displays:
- Summary metrics at the top
- Daily breakdown in expandable sections
- Trend insights and patterns

### Step 4: Interpret Data
Look for:
- **Consistency** - Are metrics stable or fluctuating?
- **Compliance** - Meeting targets most days?
- **Patterns** - Weekday vs weekend differences?
- **Problem Days** - Which days need improvement?

## Data Source

Analytics reads from `tests/weekly_logs/day1` through `day7`:
```
weekly_logs/
  day1/  (Monday - Feb 17)
    profile.json
    sleep.json
    hydration.json
    nutrition.json
  
  day2/  (Tuesday - Feb 18)
    ...
  
  day7/  (Sunday - Feb 23)
    ...
```

Each day contains realistic sample data with variations to demonstrate:
- Good days (high scores, met targets)
- Poor days (low scores, deficits)
- Weight progress (72.0kg → 71.2kg over 7 days)
- Different activity levels and patterns

## Sample Week Overview

### Sleep Trends
```
Day 1 (Mon): 7.5h ⭐ Good
Day 2 (Tue): 6.5h ⚠️ Fair
Day 3 (Wed): 8.0h ⭐⭐ Excellent
Day 4 (Thu): 7.0h ⭐ Good
Day 5 (Fri): 6.0h ❌ Poor (late night)
Day 6 (Sat): 9.0h ⭐⭐ Excellent (catch-up)
Day 7 (Sun): 8.5h ⭐ Good

Average: 7.5h (Optimal)
Total Deficit: 2.0h
```

### Hydration Trends
```
Day 1: 2,200ml ⭐ (Light Yellow)
Day 2: 1,800ml ⚠️ (Yellow)
Day 3: 2,500ml ⭐⭐ (Pale)
Day 4: 2,100ml ⭐ (Light Yellow)
Day 5: 1,600ml ❌ (Dark Yellow)
Day 6: 2,800ml ⭐⭐ (Pale)
Day 7: 2,300ml ⭐ (Light Yellow)

Average: 2,186ml/day
Target: ~2,400ml/day
Compliance: 5/7 days optimal
```

### Nutrition Trends
```
Day 1: 2,050 kcal (140g protein) ⭐
Day 2: 2,030 kcal (122g protein) ⭐
Day 3: 2,000 kcal (142g protein) ⭐
Day 4: 1,980 kcal (124g protein) ⭐
Day 5: 2,200 kcal (105g protein) ⚠️ (cheat day)
Day 6: 2,040 kcal (156g protein) ⭐⭐
Day 7: 1,950 kcal (126g protein) ⭐

Average: 2,036 kcal/day
Target: 2,100 kcal/day
Protein: 131g/day (Excellent)
```

## Insights & Recommendations

### Sleep Pattern Analysis
**Observation:** Friday shows poor sleep (6.0h, score 45)
**Causes:** Late bed time (00:30), 3 interruptions
**Action:** Implement wind-down routine by 22:00 on weeknights

### Hydration Pattern Analysis
**Observation:** Friday critical hydration (1,600ml)
**Causes:** High caffeine (250mg), busy schedule
**Action:** Pre-fill water bottles in morning, set reminders

### Nutrition Pattern Analysis
**Observation:** Friday calorie spike (2,200 kcal), low protein
**Causes:** Social eating (burger & fries)
**Action:** Plan ahead for social meals, choose protein-rich options

## Technical Details

### Multi-Day Analysis Process
```python
# For each day in selected range:
1. Load profile.json (weight, goals, activity level)
2. Load relevant log (sleep/hydration/nutrition)
3. Run through health graph pipeline
4. Store result with day_number

# Aggregate results:
5. Calculate averages across all days
6. Count optimal vs suboptimal days
7. Display summary + daily breakdown
```

### Graph Pipeline
Each day's data flows through:
```
log_context → profile → specific_agent → analytics
```

For example, Sleep analysis:
```
log_context_agent → profile_agent → sleep_agent → analytics_agent
```

### Performance
- **7-day analysis**: ~2-3 seconds (reads 7 files, runs 7 graph invocations)
- **Single-day**: <1 second
- **Data size**: ~2KB per day per log type

## Future Enhancements

### Phase 1 - Visualizations
- [ ] Line charts for trends (matplotlib/plotly)
- [ ] Bar charts for day-by-day comparison
- [ ] Pie charts for macro distribution
- [ ] Progress bars for target compliance

### Phase 2 - Advanced Analytics
- [ ] Week-over-week comparison
- [ ] Statistical insights (std dev, outliers)
- [ ] Correlation analysis (sleep vs activity)
- [ ] Predictive modeling (trend forecasting)

### Phase 3 - Custom Reports
- [ ] PDF export with charts
- [ ] Email weekly summaries
- [ ] Goal achievement badges
- [ ] Shareability (coach/doctor access)

### Phase 4 - Smart Insights
- [ ] AI-generated recommendations
- [ ] Pattern detection (e.g., "Low sleep on Fridays")
- [ ] Anomaly alerts
- [ ] Personalized intervention suggestions

## Troubleshooting

### "Error loading day X"
**Cause:** Missing log file for that day
**Solution:** Ensure all required JSON files exist in `weekly_logs/dayX/`

### Empty analysis results
**Cause:** No data in session state
**Solution:** Click "Run Multi-Day Analysis" button first

### Incorrect metrics
**Cause:** Stale session state
**Solution:** Refresh page or re-run analysis

## Best Practices

### For Users
1. **Run weekly analysis** every Sunday to review the week
2. **Compare 3-day periods** to identify short-term patterns
3. **Use single-day view** to investigate specific problem days
4. **Track progress** by comparing week-over-week averages

### For Developers
1. **Validate data** before running graph (check file existence)
2. **Handle missing fields** gracefully (use .get() with defaults)
3. **Cache results** in session state to avoid re-computation
4. **Log errors** for debugging multi-day analysis issues

## Related Documentation
- [NAVBAR_UI_README.md](NAVBAR_UI_README.md) - Overall UI restructure
- [MULTI_DAY_ANALYTICS_README.md](MULTI_DAY_ANALYTICS_README.md) - Analytics agent details
- Sample data: `tests/weekly_logs/day1-7/`

---

**Analytics Feature Version:** 1.0
**Last Updated:** February 17, 2026
**Supported Time Periods:** 1-7 days
**Supported Analysis Types:** Sleep, Hydration, Nutrition
