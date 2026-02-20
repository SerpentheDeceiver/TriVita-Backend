import streamlit as st
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd

# CRITICAL: Remove this module from sys.modules to avoid import conflicts
if 'app' in sys.modules and hasattr(sys.modules['app'], '__file__'):
    if sys.modules['app'].__file__ == __file__:
        del sys.modules['app']

# Add backend directory to sys.path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.graph.health_graph import build_graph

# Page configuration
st.set_page_config(
    page_title="Health AI - Multi-Agent Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Profile"

# Navbar
st.markdown("""
<style>
.navbar {
    display: flex;
    justify-content: space-around;
    background-color: #f0f2f6;
    padding: 1rem;
    margin-bottom: 2rem;
    border-radius: 10px;
}
.nav-button {
    font-size: 1.2rem;
    font-weight: bold;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

# Navigation Buttons
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if st.button("👤 Profile", use_container_width=True, type="primary" if st.session_state.current_page == "Profile" else "secondary"):
        st.session_state.current_page = "Profile"
with col2:
    if st.button("😴 Sleep", use_container_width=True, type="primary" if st.session_state.current_page == "Sleep" else "secondary"):
        st.session_state.current_page = "Sleep"
with col3:
    if st.button("💧 Hydration", use_container_width=True, type="primary" if st.session_state.current_page == "Hydration" else "secondary"):
        st.session_state.current_page = "Hydration"
with col4:
    if st.button("🍽️ Nutrition", use_container_width=True, type="primary" if st.session_state.current_page == "Nutrition" else "secondary"):
        st.session_state.current_page = "Nutrition"
with col5:
    if st.button("📊 Analytics", use_container_width=True, type="primary" if st.session_state.current_page == "Analytics" else "secondary"):
        st.session_state.current_page = "Analytics"

st.markdown("---")

# === PROFILE PAGE ===
if st.session_state.current_page == "Profile":
    st.title("👤 Personal Profile & Health Goals")
    
    with st.sidebar:
        st.header("📝 Profile Information")
        
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age (years)", min_value=1, max_value=120, value=28, step=1)
            weight = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=72.0, step=0.1)
        with col2:
            height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=175.0, step=0.1)
            gender = st.selectbox("Gender", ["male", "female"])
        
        st.markdown("---")
        st.subheader("🎯 Weight Goals")
        
        weight_goal = st.selectbox("Goal", ["maintain", "reduce", "increase"])
        if weight_goal != "maintain":
            target_change = st.number_input(f"Target Weight Change (kg)", min_value=0.5, max_value=50.0, value=5.0, step=0.5)
            timeline = st.number_input("Timeline (weeks)", min_value=1, max_value=104, value=12, step=1)
        else:
            target_change = 0
            timeline = 0
        
        activity_level = st.selectbox("Activity Level", ["sedentary", "light", "moderate", "active", "very_active"])
        
        st.markdown("---")
        if st.button("💾 Save Profile", use_container_width=True, type="primary"):
            st.session_state.profile = {
                "age": age,
                "weight": weight,
                "height": height,
                "gender": gender,
                "weight_goal": weight_goal,
                "target_weight_change_kg": target_change,
                "target_timeline_weeks": timeline,
                "activity_level": activity_level
            }
            st.success("✅ Profile saved!")
    
    # Main content
    if 'profile' in st.session_state:
        profile = st.session_state.profile
        
        st.subheader("📊 Your Profile Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Age", f"{profile['age']} years")
        with col2:
            st.metric("Weight", f"{profile['weight']} kg")
        with col3:
            st.metric("Height", f"{profile['height']} cm")
        with col4:
            bmi = profile['weight'] / ((profile['height'] / 100) ** 2)
            st.metric("BMI", f"{bmi:.1f}")
        
        st.markdown("---")
        st.subheader("🎯 Health Goals")
        
        goal_text = {
            "maintain": "Maintain current weight",
            "reduce": f"Lose {profile['target_weight_change_kg']}kg in {profile['target_timeline_weeks']} weeks",
            "increase": f"Gain {profile['target_weight_change_kg']}kg in {profile['target_timeline_weeks']} weeks"
        }
        
        st.info(f"**Goal:** {goal_text[profile['weight_goal']]}")
        st.info(f"**Activity Level:** {profile['activity_level'].title()}")
        
        if profile['weight_goal'] != "maintain":
            weekly_change = profile['target_weight_change_kg'] / profile['target_timeline_weeks']
            st.metric("Weekly Target", f"{weekly_change:.2f} kg/week")
    else:
        st.info("👈 Please fill in your profile information in the sidebar")

# === SLEEP PAGE ===
elif st.session_state.current_page == "Sleep":
    st.title("😴 Sleep Analysis & Insights")
    
    with st.sidebar:
        st.header("📝 Sleep Log")
        
        sleep_hours = st.number_input("Sleep Hours", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
        
        col1, col2 = st.columns(2)
        with col1:
            bed_time = st.time_input("Bed Time", value=datetime.strptime("23:00", "%H:%M").time())
        with col2:
            wake_time = st.time_input("Wake Time", value=datetime.strptime("06:30", "%H:%M").time())
        
        sleep_quality = st.select_slider("Sleep Quality", options=["poor", "fair", "good", "excellent"], value="good")
        
        interruptions = st.number_input("Interruptions", min_value=0, max_value=20, value=1)
        
        col1, col2 = st.columns(2)
        with col1:
            dream_recall = st.checkbox("Dream Recall")
        with col2:
            feeling = st.selectbox("Feeling on Wake", ["refreshed", "neutral", "groggy", "exhausted"])
        
        st.markdown("---")
        if st.button("💾 Save Sleep Log", use_container_width=True, type="primary"):
            st.session_state.sleep_log = {
                "sleep_hours": sleep_hours,
                "bed_time": bed_time.strftime("%H:%M"),
                "wake_time": wake_time.strftime("%H:%M"),
                "sleep_quality": sleep_quality,
                "interruptions": interruptions,
                "dream_recall": dream_recall,
                "feeling_on_wake": feeling
            }
            st.success("✅ Sleep log saved!")
    
    # Main content
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        
        st.subheader("📊 Sleep Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Sleep Hours", f"{result.get('sleep_hours', 0)}h", 
                     delta=f"{result.get('sleep_hours', 0) - 7:.1f}h from 7h target")
        with col2:
            st.metric("Quality", result.get('sleep_quality', 'unknown').title())
        with col3:
            st.metric("Sleep Score", f"{result.get('sleep_score', 0)}/100")
        with col4:
            deficit = result.get('sleep_deficit', 0)
            st.metric("Deficit", f"{deficit}h", delta=f"{-deficit}h" if deficit > 0 else "None")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⏰ Sleep Schedule")
            st.write(f"**Bed Time:** {result.get('bed_time', 'N/A')}")
            st.write(f"**Wake Time:** {result.get('wake_time', 'N/A')}")
            st.write(f"**Interruptions:** {result.get('sleep_interruptions', 0)}")
        
        with col2:
            st.subheader("✨ Sleep Quality Indicators")
            st.write(f"**Feeling on Wake:** {result.get('feeling_on_wake', 'unknown').title()}")
            st.write(f"**Dream Recall:** {'Yes' if result.get('dream_recall', False) else 'No'}")
        
        # Sleep insights
        if result.get('sleep_deficit', 0) > 0:
            st.warning(f"⚠️ Sleep deficit: {result['sleep_deficit']} hours")
        else:
            st.success("✅ Meeting sleep requirements")
    else:
        st.info("👈 Enter your sleep data and run analysis to see insights")

# === HYDRATION PAGE ===
elif st.session_state.current_page == "Hydration":
    st.title("💧 Hydration Tracking & Analysis")
    
    with st.sidebar:
        st.header("📝 Hydration Log")
        
        water_intake = st.number_input("Total Water Intake (ml)", min_value=0, max_value=10000, value=2200, step=100)
        caffeine = st.number_input("Caffeine Intake (mg)", min_value=0, max_value=1000, value=150, step=10)
        urine_color = st.select_slider("Urine Color", options=["dark_yellow", "yellow", "light_yellow", "pale", "clear"], value="light_yellow")
        
        st.markdown("---")
        if st.button("💾 Save Hydration Log", use_container_width=True, type="primary"):
            st.session_state.hydration_log = {
                "water_intake_ml": water_intake,
                "caffeine_intake_mg": caffeine,
                "urine_color": urine_color
            }
            st.success("✅ Hydration log saved!")
    
    # Main content
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        
        st.subheader("📊 Hydration Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Hydration Score", f"{result.get('hydration_score', 0)}%")
        with col2:
            st.metric("Status", result.get('hydration_status', 'unknown').title())
        with col3:
            st.metric("Water Intake", f"{result.get('actual_water_intake', 0)} ml")
        with col4:
            st.metric("Deficit", f"{result.get('water_deficit_ml', 0)} ml")
        
        st.markdown("---")
        
        # Hydration progress bar
        st.subheader("💧 Hydration Progress")
        water_actual = result.get('actual_water_intake', 0)
        water_target = result.get('recommended_water_ml', 0)
        progress = min(water_actual / water_target, 1.0) if water_target > 0 else 0
        st.progress(progress)
        st.caption(f"{water_actual} ml / {water_target} ml (Target based on age: {result.get('age', 0)} years)")
        
        st.markdown("---")
        
        # Hydration advice
        st.subheader("💡 Hydration Advice")
        advice = result.get('hydration_advice', 'Stay hydrated!')
        if result.get('hydration_status') == "poor":
            st.error(advice)
        elif result.get('hydration_status') == "optimal":
            st.success(advice)
        else:
            st.info(advice)
    else:
        st.info("👈 Enter your hydration data and run analysis to see insights")

# === NUTRITION PAGE ===
elif st.session_state.current_page == "Nutrition":
    st.title("🍽️ AI-Powered Nutrition Planning")
    
    with st.sidebar:
        st.header("📝 Nutrition Log")
        
        total_calories = st.number_input("Total Calories (kcal)", min_value=0, max_value=10000, value=2050, step=50)
        total_protein = st.number_input("Total Protein (g)", min_value=0, max_value=500, value=140, step=5)
        total_carbs = st.number_input("Total Carbs (g)", min_value=0, max_value=1000, value=210, step=10)
        total_fat = st.number_input("Total Fat (g)", min_value=0, max_value=500, value=65, step=5)
        meal_count = st.number_input("Number of Meals", min_value=0, max_value=10, value=4, step=1)
        
        st.markdown("---")
        
        budget = st.slider("Budget per Meal (USD)", min_value=5, max_value=50, value=12, step=1)
        
        st.markdown("---")
        if st.button("💾 Save Nutrition Log", use_container_width=True, type="primary"):
            st.session_state.nutrition_log = {
                "total_calories": total_calories,
                "total_protein_g": total_protein,
                "total_carbs_g": total_carbs,
                "total_fat_g": total_fat,
                "meal_count": meal_count,
                "budget_per_meal": budget
            }
            st.success("✅ Nutrition log saved!")
    
    # Main content
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        
        st.subheader("📊 Nutrition Metrics")
        col1,col2, col3, col4 = st.columns(4)
        
        with col1:
            calories = result.get('total_daily_calories', 0)
            target = result.get('calorie_target', 0)
            st.metric("Calories", f"{calories} kcal", delta=f"{calories - target:+d} kcal")
        
        with col2:
            protein = result.get('total_daily_protein', 0)
            p_target = result.get('protein_target', 0)
            st.metric("Protein", f"{protein}g", delta=f"{protein - p_target:+.0f}g")
        
        with col3:
            st.metric("Carbs", f"{result.get('total_daily_carbs', 0)}g")
        
        with col4:
            st.metric("Fat", f"{result.get('total_daily_fat', 0)}g")
        
        st.markdown("---")
        
        # AI Meal Suggestions
        if result.get('ai_nutrition_generated', False):
            st.subheader("✨ AI-Generated Meal Suggestions")
            
            summary = result.get('nutrition_summary', '')
            if summary:
                st.info(f"**📋 Summary:** {summary}")
            
            meal_suggestions = result.get('meal_suggestions', [])
            for i, meal in enumerate(meal_suggestions, 1):
                with st.expander(f"🍽️ {meal.get('meal_name', f'Meal {i}')} - ${meal.get('estimated_cost', 0)}", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write("**Ingredients:**")
                        for ingredient in meal.get('ingredients', []):
                            st.write(f"• {ingredient}")
                        
                        st.markdown("---")
                        st.write(f"**💭 Why this meal:** {meal.get('reasoning', 'N/A')}")
                    
                    with col2:
                        st.metric("Calories", f"{meal.get('calories', 0)} kcal")
                        st.metric("Protein", f"{meal.get('protein_g', 0)}g")
                        st.metric("Carbs", f"{meal.get('carbs_g', 0)}g")
                        st.metric("Fat", f"{meal.get('fat_g', 0)}g")
                        st.metric("Cost", f"${meal.get('estimated_cost', 0)}")
            
            # Nutrition tips
            tips = result.get('nutrition_tips', [])
            if tips:
                st.markdown("---")
                st.subheader("💡 Nutrition Tips")
                for tip in tips:
                    st.success(f"✨ {tip}")
        else:
            st.warning("⚠️ AI meal suggestions not available. Please ensure your Groq API key is configured.")
    else:
        st.info("👈 Enter your nutrition data and run analysis to see AI meal suggestions")

# === ANALYTICS PAGE ===
elif st.session_state.current_page == "Analytics":
    st.title("📊 Health Analytics Dashboard")

    # ── Helper: load sample_logs + run ML agent ──────────────────────────────
    @st.cache_data
    def _load_sample_logs():
        data_path = Path(__file__).parent.parent.parent / "data" / "sample_logs.json"
        with open(data_path) as f:
            return json.load(f)

    @st.cache_data
    def _run_analytics_agent():
        from app.agents.analytics_agent import analytics_agent
        result = analytics_agent({})
        return result.get("analytics", {})

    try:
        logs = _load_sample_logs()
        analytics = _run_analytics_agent()

        df = pd.DataFrame([
            {
                "date": log["date"],
                "sleep_hours": log["sleep"]["hours"],
                "hydration_ml": log["hydration"]["total_ml"],
                "calories": log["nutrition"]["totals"]["calories"],
                "wellness": log["scores"]["wellness"],
                "sleep_score": log["scores"]["sleep"],
                "hydration_score": log["scores"]["hydration"],
                "nutrition_score": log["scores"]["nutrition"],
            }
            for log in logs
        ])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        averages   = analytics.get("averages", {})
        trend      = analytics.get("trend", "stable")
        predictions = analytics.get("next_7_day_prediction", [])
        trend_icon = "📈" if trend == "improving" else "📉" if trend == "declining" else "➡️"

        # ── SECTION 1: Key Metrics ────────────────────────────────────────────
        st.subheader("📌 Key Health Metrics")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Avg Sleep",      f"{averages.get('avg_sleep',0):.1f} h")
        with m2:
            st.metric("Avg Hydration",  f"{averages.get('avg_hydration',0):.0f} ml")
        with m3:
            st.metric("Avg Calories",   f"{averages.get('avg_calories',0):.0f} kcal")
        with m4:
            st.metric("Wellness Trend", f"{trend_icon} {trend.title()}")
        st.markdown("---")

        # ── SECTION 2: Wellness Timeline ──────────────────────────────────────
        st.subheader("🌡️ Wellness Score Timeline")
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(
            x=df["date"], y=df["wellness"],
            mode="lines+markers", name="Wellness Score",
            line=dict(color="#2ecc71", width=3), marker=dict(size=10),
        ))
        fig_w.update_layout(xaxis_title="Date", yaxis_title="Score",
                             height=320, template="plotly_dark")
        st.plotly_chart(fig_w, use_container_width=True)
        st.markdown("---")

        # ── SECTION 3: Sleep & Hydration ──────────────────────────────────────
        st.subheader("😴 Sleep & 💧 Hydration Trends")
        cs, ch = st.columns(2)
        with cs:
            fig_s = go.Figure()
            fig_s.add_trace(go.Bar(
                x=df["date"].dt.strftime("%Y-%m-%d"), y=df["sleep_hours"],
                marker_color="#9b59b6",
            ))
            fig_s.update_layout(title="Daily Sleep Hours", height=280,
                                 template="plotly_dark", showlegend=False)
            st.plotly_chart(fig_s, use_container_width=True)
        with ch:
            fig_h = go.Figure()
            fig_h.add_trace(go.Bar(
                x=df["date"].dt.strftime("%Y-%m-%d"), y=df["hydration_ml"],
                marker_color="#3498db",
            ))
            fig_h.update_layout(title="Daily Hydration (ml)", height=280,
                                 template="plotly_dark", showlegend=False)
            st.plotly_chart(fig_h, use_container_width=True)
        st.markdown("---")

        # ── SECTION 4: Calories & Radar ───────────────────────────────────────
        st.subheader("🍽️ Nutrition & Wellness Radar")
        cc, cr = st.columns(2)
        with cc:
            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(
                x=df["date"].dt.strftime("%Y-%m-%d"), y=df["calories"],
                marker_color="#e67e22",
            ))
            fig_c.update_layout(title="Daily Calories (kcal)", height=280,
                                 template="plotly_dark", showlegend=False)
            st.plotly_chart(fig_c, use_container_width=True)
        with cr:
            latest   = df.iloc[-1]
            cats     = ["Sleep", "Hydration", "Nutrition", "Wellness"]
            vals     = [float(latest["sleep_score"]), float(latest["hydration_score"]),
                        float(latest["nutrition_score"]), float(latest["wellness"])]
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(
                r=vals + [vals[0]], theta=cats + [cats[0]],
                fill="toself", line=dict(color="#2ecc71"),
            ))
            fig_r.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                title=f"Latest Day Scores ({df['date'].max().strftime('%Y-%m-%d')})",
                height=280, template="plotly_dark",
            )
            st.plotly_chart(fig_r, use_container_width=True)
        st.markdown("---")

        # ── SECTION 5: Multi-Metric Comparison ────────────────────────────────
        st.subheader("📈 Multi-Metric Score Comparison")
        fig_m = go.Figure()
        for col_name, label, color in [
            ("sleep_score",     "Sleep Score",     "#9b59b6"),
            ("hydration_score", "Hydration Score", "#3498db"),
            ("nutrition_score", "Nutrition Score", "#e67e22"),
            ("wellness",        "Wellness Score",  "#2ecc71"),
        ]:
            fig_m.add_trace(go.Scatter(
                x=df["date"], y=df[col_name],
                mode="lines+markers", name=label,
                line=dict(color=color, width=2),
            ))
        fig_m.update_layout(xaxis_title="Date", yaxis_title="Score",
                             height=320, template="plotly_dark")
        st.plotly_chart(fig_m, use_container_width=True)
        st.markdown("---")

        # ── SECTION 6: 7-Day Predictions ──────────────────────────────────────
        st.subheader("🔮 7-Day Wellness Predictions")
        last_date    = df["date"].max()
        future_dates = [last_date + timedelta(days=i + 1) for i in range(7)]

        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(
            x=df["date"], y=df["wellness"],
            mode="lines+markers", name="Historical",
            line=dict(color="#2ecc71", width=3),
        ))
        fig_p.add_trace(go.Scatter(
            x=future_dates, y=predictions,
            mode="lines+markers", name="Predicted",
            line=dict(color="#e74c3c", width=3, dash="dash"),
            marker=dict(symbol="diamond", size=10),
        ))
        upper = [p + 5 for p in predictions]
        lower = [max(0.0, p - 5) for p in predictions]
        fig_p.add_trace(go.Scatter(
            x=future_dates + future_dates[::-1],
            y=upper + lower[::-1],
            fill="toself", fillcolor="rgba(231,76,60,0.15)",
            line=dict(color="rgba(255,255,255,0)"), name="Confidence Band",
        ))
        fig_p.update_layout(xaxis_title="Date", yaxis_title="Wellness Score",
                             height=380, template="plotly_dark")
        st.plotly_chart(fig_p, use_container_width=True)

        pc1, pc2 = st.columns(2)
        with pc1:
            st.info(f"**Trend Direction:** {trend_icon} {trend.title()}")
            avg_pred = sum(predictions) / len(predictions) if predictions else 0
            st.info(f"**Avg Predicted Wellness:** {avg_pred:.1f}")
        with pc2:
            st.info(f"**Highest Predicted:** {max(predictions):.1f}")
            st.info(f"**Lowest Predicted:** {min(predictions):.1f}")
        st.markdown("---")

        # ── SECTION 7: Raw Data ────────────────────────────────────────────────
        with st.expander("📋 View Raw Log Data", expanded=False):
            st.dataframe(df.round(2), use_container_width=True)

    except FileNotFoundError:
        st.warning("⚠️ `backend/data/sample_logs.json` not found — AI analytics unavailable.")
    except Exception as _e:
        st.error(f"❌ Analytics error: {_e}")

    # ── SECTION 8: Multi-Day Trend Analysis (existing) ────────────────────────
    st.markdown("---")
    st.subheader("📅 Multi-Day Trend Analysis")

    with st.sidebar:
        st.header("📈 Analysis Settings")

        analysis_type = st.selectbox("Analysis Type", ["Sleep", "Hydration", "Nutrition"])

        num_days = st.selectbox("Time Period", [
            ("1 Day", 1),
            ("2 Days", 2),
            ("3 Days", 3),
            ("4 Days", 4),
            ("5 Days", 5),
            ("6 Days", 6),
            ("7 Days (Full Week)", 7)
        ], format_func=lambda x: x[0])

        st.markdown("---")

        if st.button("📊 Run Multi-Day Analysis", use_container_width=True, type="primary"):
            with st.spinner(f"🔄 Analyzing {num_days[1]} days of {analysis_type.lower()} data..."):
                # Load data from weekly_logs
                weekly_logs_path = Path(__file__).parent.parent / "weekly_logs"

                daily_data = []
                for day_num in range(1, num_days[1] + 1):
                    day_path = weekly_logs_path / f"day{day_num}"

                    try:
                        # Load profile
                        with open(day_path / "profile.json", "r") as f:
                            profile_data = json.load(f)

                        # Load sleep if needed
                        sleep_data = {}
                        if analysis_type in ["Sleep"]:
                            with open(day_path / "sleep.json", "r") as f:
                                sleep_data = json.load(f)

                        # Load hydration if needed
                        hydration_data = {}
                        if analysis_type in ["Hydration"]:
                            with open(day_path / "hydration.json", "r") as f:
                                hydration_data = json.load(f)

                        # Load nutrition if needed
                        nutrition_data = {}
                        if analysis_type in ["Nutrition"]:
                            with open(day_path / "nutrition.json", "r") as f:
                                nutrition_data = json.load(f)

                        # Prepare data for graph
                        data = {
                            "profile": profile_data,
                            "sleep_log": sleep_data,
                            "hydration_log": hydration_data,
                            "nutrition_log": nutrition_data
                        }

                        # Run analysis
                        graph = build_graph()
                        result = graph.invoke(data)
                        result["day_number"] = day_num
                        daily_data.append(result)

                    except Exception as e:
                        st.error(f"Error loading day {day_num}: {e}")

                st.session_state.multi_day_analysis = {
                    "type": analysis_type,
                    "days": num_days[1],
                    "data": daily_data
                }

            st.success(f"✅ {num_days[1]}-day {analysis_type.lower()} analysis complete!")

    # Display multi-day analysis results
    if 'multi_day_analysis' in st.session_state:
        analysis = st.session_state.multi_day_analysis
        analysis_type = analysis["type"]
        num_days_analyzed = analysis["days"]
        daily_data = analysis["data"]

        st.subheader(f"📈 {num_days_analyzed}-Day {analysis_type} Trends")

        # === SLEEP ANALYTICS ===
        if analysis_type == "Sleep":
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            sleep_hours = [d.get('sleep_hours', 0) for d in daily_data]
            sleep_scores = [d.get('sleep_score', 0) for d in daily_data]
            deficits = [d.get('sleep_deficit', 0) for d in daily_data]

            with col1:
                avg_sleep = sum(sleep_hours) / len(sleep_hours) if sleep_hours else 0
                st.metric("Avg Sleep", f"{avg_sleep:.1f}h")
            with col2:
                avg_score = sum(sleep_scores) / len(sleep_scores) if sleep_scores else 0
                st.metric("Avg Score", f"{avg_score:.0f}/100")
            with col3:
                total_deficit = sum(deficits)
                st.metric("Total Deficit", f"{total_deficit:.1f}h")
            with col4:
                good_nights = sum(1 for score in sleep_scores if score >= 70)
                st.metric("Good Nights", f"{good_nights}/{len(daily_data)}")

            st.markdown("---")

            # Daily breakdown
            st.subheader("📅 Daily Sleep Breakdown")
            for data in daily_data:
                day_date = data.get('date', f"Day {data.get('day_number', 0)}")

                with st.expander(f"📆 {day_date} ({data.get('day_of_week', 'Unknown')})", expanded=False):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Sleep Hours", f"{data.get('sleep_hours', 0)}h")
                        st.write(f"**Quality:** {data.get('sleep_quality', 'unknown').title()}")

                    with col2:
                        st.metric("Sleep Score", f"{data.get('sleep_score', 0)}/100")
                        st.write(f"**Interruptions:** {data.get('sleep_interruptions', 0)}")

                    with col3:
                        st.metric("Deficit", f"{data.get('sleep_deficit', 0):.1f}h")
                        st.write(f"**Feeling:** {data.get('feeling_on_wake', 'unknown').title()}")

                    st.write(f"🛏️ **Bed Time:** {data.get('bed_time', 'N/A')}")
                    st.write(f"⏰ **Wake Time:** {data.get('wake_time', 'N/A')}")

        # === HYDRATION ANALYTICS ===
        elif analysis_type == "Hydration":
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            water_intakes = [d.get('actual_water_intake', 0) for d in daily_data]
            hydration_scores = [d.get('hydration_score', 0) for d in daily_data]
            deficits = [d.get('water_deficit_ml', 0) for d in daily_data]

            with col1:
                avg_intake = sum(water_intakes) / len(water_intakes) if water_intakes else 0
                st.metric("Avg Water Intake", f"{avg_intake:.0f}ml")
            with col2:
                avg_score = sum(hydration_scores) / len(hydration_scores) if hydration_scores else 0
                st.metric("Avg Hydration Score", f"{avg_score:.0f}%")
            with col3:
                avg_deficit = sum(deficits) / len(deficits) if deficits else 0
                st.metric("Avg Deficit", f"{avg_deficit:.0f}ml")
            with col4:
                optimal_days = sum(1 for score in hydration_scores if score >= 90)
                st.metric("Optimal Days", f"{optimal_days}/{len(daily_data)}")

            st.markdown("---")

            # Daily breakdown
            st.subheader("📅 Daily Hydration Breakdown")
            for data in daily_data:
                day_date = data.get('date', f"Day {data.get('day_number', 0)}")

                with st.expander(f"📆 {day_date} ({data.get('day_of_week', 'Unknown')})", expanded=False):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Water Intake", f"{data.get('actual_water_intake', 0)}ml")
                        st.write(f"**Status:** {data.get('hydration_status', 'unknown').title()}")

                    with col2:
                        st.metric("Hydration Score", f"{data.get('hydration_score', 0)}%")
                        st.write(f"**Caffeine:** {data.get('caffeine_intake_mg', 0)}mg")

                    with col3:
                        st.metric("Target", f"{data.get('recommended_water_ml', 0)}ml")
                        st.write(f"**Deficit:** {data.get('water_deficit_ml', 0)}ml")

                    st.info(f"💡 {data.get('hydration_advice', 'Stay hydrated!')}")

        # === NUTRITION ANALYTICS ===
        elif analysis_type == "Nutrition":
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            calories = [d.get('total_daily_calories', 0) for d in daily_data]
            proteins = [d.get('total_daily_protein', 0) for d in daily_data]
            carbs = [d.get('total_daily_carbs', 0) for d in daily_data]
            fats = [d.get('total_daily_fat', 0) for d in daily_data]

            with col1:
                avg_cal = sum(calories) / len(calories) if calories else 0
                st.metric("Avg Calories", f"{avg_cal:.0f} kcal")
            with col2:
                avg_protein = sum(proteins) / len(proteins) if proteins else 0
                st.metric("Avg Protein", f"{avg_protein:.0f}g")
            with col3:
                avg_carbs = sum(carbs) / len(carbs) if carbs else 0
                st.metric("Avg Carbs", f"{avg_carbs:.0f}g")
            with col4:
                avg_fat = sum(fats) / len(fats) if fats else 0
                st.metric("Avg Fat", f"{avg_fat:.0f}g")

            st.markdown("---")

            # Daily breakdown
            st.subheader("📅 Daily Nutrition Breakdown")
            for data in daily_data:
                day_date = data.get('date', f"Day {data.get('day_number', 0)}")
                calorie_target = data.get('calorie_target', 0)
                protein_target = data.get('protein_target', 0)

                with st.expander(f"📆 {day_date} ({data.get('day_of_week', 'Unknown')})", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        actual_cal = data.get('total_daily_calories', 0)
                        delta_cal = actual_cal - calorie_target
                        st.metric("Calories", f"{actual_cal} kcal", delta=f"{delta_cal:+d} kcal")

                    with col2:
                        actual_protein = data.get('total_daily_protein', 0)
                        delta_protein = actual_protein - protein_target
                        st.metric("Protein", f"{actual_protein}g", delta=f"{delta_protein:+.0f}g")

                    with col3:
                        st.metric("Carbs", f"{data.get('total_daily_carbs', 0)}g")

                    with col4:
                        st.metric("Fat", f"{data.get('total_daily_fat', 0)}g")

                    st.write(f"🍽️ **Meals:** {data.get('meal_count', 0)}")
                    st.write(f"💰 **Budget:** ${data.get('budget_per_meal', 0)}/meal")
    else:
        st.info("👈 Select analysis type and time period, then click 'Run Multi-Day Analysis'")

# Analyze Button (always visible)
st.markdown("---")
if st.button("🚀 Run Complete Health Analysis", use_container_width=True, type="primary", key="analyze_btn"):
    if 'profile' not in st.session_state:
        st.error("❌ Please complete your profile first!")
    else:
        # Prepare data
        data = {
            "profile": st.session_state.profile,
            "sleep_log": st.session_state.get('sleep_log', {}),
            "hydration_log": st.session_state.get('hydration_log', {}),
            "nutrition_log": st.session_state.get('nutrition_log', {})
        }
        
        with st.spinner("🔄 Running AI-powered health analysis..."):
            graph = build_graph()
            result = graph.invoke(data)
            st.session_state.analysis_result = result
        
        st.success("✅ Analysis complete! Check each page for detailed insights.")
        st.balloons()
