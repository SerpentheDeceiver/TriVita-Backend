import streamlit as st
import sys
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# CRITICAL: Remove this module from sys.modules to avoid import conflicts
if 'app' in sys.modules and hasattr(sys.modules['app'], '__file__'):
    if sys.modules['app'].__file__ == __file__:
        del sys.modules['app']

# Add backend directory to sys.path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.analytics_agent import analytics_agent

# Page configuration
st.set_page_config(
    page_title="Health Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #dee2e6;
    }
    .stMetric label {
        color: #495057 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #212529 !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    .stMetric [data-testid="stMetricDelta"] {
        color: #28a745 !important;
        font-weight: 500 !important;
    }
    h1, h2, h3 {
        color: #FFD700 !important;
    }
    h4, h5, h6 {
        color: #212529 !important;
    }
    .stMarkdown {
        color: #495057;
    }
    .yellow-title {
        color: #FFD700 !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown("<h1 style='color: #FFD700;'>📊 Health Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='color: #FFD700;'>Comprehensive Health Data Analysis & Predictions</h3>", unsafe_allow_html=True)
st.markdown("---")

# Load data
@st.cache_data
def load_health_data():
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_PATH = os.path.join(BASE_DIR, "data", "sample_logs.json")
    
    with open(DATA_PATH) as f:
        logs = json.load(f)
    
    return logs

# Get analytics
@st.cache_data
def get_analytics():
    return analytics_agent({})

try:
    logs = load_health_data()
    analytics_result = get_analytics()
    
    # Extract data
    analytics_data = analytics_result.get('analytics', {})
    averages = analytics_data.get('averages', {})
    trend = analytics_data.get('trend', 'stable')
    predictions = analytics_data.get('next_7_day_prediction', [])
    
    # Prepare historical data
    dates = [log["date"] for log in logs]
    sleep_hours_history = [log["sleep"]["hours"] for log in logs]
    hydration_ml = [log["hydration"]["total_ml"] for log in logs]
    calories = [log["nutrition"]["totals"]["calories"] for log in logs]
    wellness_scores = [log["scores"]["wellness"] for log in logs]
    sleep_scores = [log["scores"]["sleep"] for log in logs]
    hydration_scores = [log["scores"]["hydration"] for log in logs]
    nutrition_scores = [log["scores"]["nutrition"] for log in logs]
    
    # =====================================================
    # SECTION 1: KEY METRICS OVERVIEW
    # =====================================================
    st.markdown("<h2 style='color: #FFD700;'>📈 Key Metrics Overview</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="😴 Average Sleep",
            value=f"{averages.get('avg_sleep', 0)} hrs",
            delta=f"{averages.get('avg_sleep', 0) - 7:.1f} hrs from target"
        )
    
    with col2:
        st.metric(
            label="💧 Average Hydration",
            value=f"{averages.get('avg_hydration', 0):.0f} ml",
            delta=f"{averages.get('avg_hydration', 0) - 2000:.0f} ml from target"
        )
    
    with col3:
        st.metric(
            label="🍽️ Average Calories",
            value=f"{averages.get('avg_calories', 0):.0f} kcal"
        )
    
    with col4:
        trend_emoji = "📈" if trend == "improving" else "📉" if trend == "declining" else "➡️"
        trend_color = "normal" if trend == "improving" else "inverse" if trend == "declining" else "off"
        st.metric(
            label="💚 Wellness Trend",
            value=f"{averages.get('avg_wellness', 0):.1f}",
            delta=trend.capitalize(),
            delta_color=trend_color
        )
    
    st.markdown("---")
    
    # =====================================================
    # SECTION 2: WELLNESS SCORE ANALYSIS
    # =====================================================
    st.markdown("<h2 style='color: #FFD700;'>💚 Wellness Score Analysis</h2>", unsafe_allow_html=True)
    
    # Primary Wellness Chart
    fig_wellness = go.Figure()
    
    fig_wellness.add_trace(go.Scatter(
        x=dates,
        y=wellness_scores,
        mode='lines+markers',
        name='Wellness Score',
        line=dict(color='#2ecc71', width=4),
        marker=dict(size=10, color='#27ae60'),
        fill='tozeroy',
        fillcolor='rgba(46, 204, 113, 0.2)',
        hovertemplate='<b>%{x}</b><br>Wellness: %{y}<extra></extra>'
    ))
    
    # Add average line
    avg_wellness = averages.get('avg_wellness', 0)
    fig_wellness.add_hline(
        y=avg_wellness, 
        line_dash="dash", 
        line_color="purple",
        annotation_text=f"Average: {avg_wellness:.1f}",
        annotation_position="right"
    )
    
    fig_wellness.update_layout(
        title="Wellness Score Timeline",
        xaxis_title="Date",
        yaxis_title="Wellness Score",
        hovermode='x unified',
        height=450,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12, color='#212529')
    )
    
    st.plotly_chart(fig_wellness, width='stretch')
    
    st.markdown("---")
    
    # =====================================================
    # SECTION 3: DETAILED HEALTH METRICS
    # =====================================================
    st.markdown("<h2 style='color: #FFD700;'>📊 Detailed Health Metrics</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sleep Analysis
        st.subheader("😴 Sleep Analysis")
        
        fig_sleep = go.Figure()
        fig_sleep.add_trace(go.Scatter(
            x=dates,
            y=sleep_hours_history,
            mode='lines+markers',
            name='Sleep Hours',
            line=dict(color='#3498db', width=3),
            marker=dict(size=8),
            fill='tozeroy',
            fillcolor='rgba(52, 152, 219, 0.2)',
            hovertemplate='<b>%{x}</b><br>Sleep: %{y} hrs<extra></extra>'
        ))
        
        fig_sleep.add_hline(
            y=7, 
            line_dash="dash", 
            line_color="green",
            annotation_text="Target: 7hrs",
            annotation_position="right"
        )
        
        fig_sleep.update_layout(
            title="Daily Sleep Hours",
            xaxis_title="Date",
            yaxis_title="Hours",
            height=350,
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529')
        )
        
        st.plotly_chart(fig_sleep, width='stretch')
        
        # Sleep Score
        fig_sleep_score = go.Figure()
        fig_sleep_score.add_trace(go.Bar(
            x=dates,
            y=sleep_scores,
            name='Sleep Score',
            marker_color='#3498db',
            hovertemplate='<b>%{x}</b><br>Score: %{y}<extra></extra>'
        ))
        
        fig_sleep_score.update_layout(
            title="Sleep Quality Score",
            xaxis_title="Date",
            yaxis_title="Score",
            height=300,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529')
        )
        
        st.plotly_chart(fig_sleep_score, width='stretch')
    
    with col2:
        # Hydration Analysis
        st.subheader("💧 Hydration Analysis")
        
        fig_hydration = go.Figure()
        fig_hydration.add_trace(go.Scatter(
            x=dates,
            y=hydration_ml,
            mode='lines+markers',
            name='Water Intake',
            line=dict(color='#1abc9c', width=3),
            marker=dict(size=8),
            fill='tozeroy',
            fillcolor='rgba(26, 188, 156, 0.2)',
            hovertemplate='<b>%{x}</b><br>Water: %{y} ml<extra></extra>'
        ))
        
        fig_hydration.add_hline(
            y=2000, 
            line_dash="dash", 
            line_color="blue",
            annotation_text="Target: 2000ml",
            annotation_position="right"
        )
        
        fig_hydration.update_layout(
            title="Daily Water Intake",
            xaxis_title="Date",
            yaxis_title="Milliliters (ml)",
            height=350,
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529')
        )
        
        st.plotly_chart(fig_hydration, width='stretch')
        
        # Hydration Score
        fig_hydration_score = go.Figure()
        fig_hydration_score.add_trace(go.Bar(
            x=dates,
            y=hydration_scores,
            name='Hydration Score',
            marker_color='#1abc9c',
            hovertemplate='<b>%{x}</b><br>Score: %{y}<extra></extra>'
        ))
        
        fig_hydration_score.update_layout(
            title="Hydration Quality Score",
            xaxis_title="Date",
            yaxis_title="Score",
            height=300,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529')
        )
        
        st.plotly_chart(fig_hydration_score, width='stretch')
    
    st.markdown("---")
    
    # =====================================================
    # SECTION 4: NUTRITION & COMPREHENSIVE SCORES
    # =====================================================
    st.markdown("<h2 style='color: #FFD700;'>🍽️ Nutrition & Comprehensive Analysis</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Calories Chart
        fig_calories = go.Figure()
        fig_calories.add_trace(go.Bar(
            x=dates,
            y=calories,
            name='Calories',
            marker_color='#e74c3c',
            hovertemplate='<b>%{x}</b><br>Calories: %{y} kcal<extra></extra>'
        ))
        
        avg_calories = averages.get('avg_calories', 0)
        fig_calories.add_hline(
            y=avg_calories,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Average: {avg_calories:.0f} kcal",
            annotation_position="right"
        )
        
        fig_calories.update_layout(
            title="Daily Calorie Intake",
            xaxis_title="Date",
            yaxis_title="Calories (kcal)",
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529')
        )
        
        st.plotly_chart(fig_calories, width='stretch')
    
    with col2:
        # All Scores Radar Chart
        fig_radar = go.Figure()
        
        # Calculate average scores
        avg_scores = {
            'Sleep': sum(sleep_scores) / len(sleep_scores),
            'Hydration': sum(hydration_scores) / len(hydration_scores),
            'Nutrition': sum(nutrition_scores) / len(nutrition_scores),
            'Wellness': sum(wellness_scores) / len(wellness_scores)
        }
        
        categories = list(avg_scores.keys())
        values = list(avg_scores.values())
        
        fig_radar.add_trace(go.Scatterpolar(
            r=values + [values[0]],  # Close the radar
            theta=categories + [categories[0]],
            fill='toself',
            name='Average Scores',
            line_color='#9b59b6',
            fillcolor='rgba(155, 89, 182, 0.3)'
        ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title="Average Health Scores Overview",
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529')
        )
        
        st.plotly_chart(fig_radar, width='stretch')
    
    st.markdown("---")
    
    # =====================================================
    # SECTION 5: MULTI-METRIC COMPARISON
    # =====================================================
    st.markdown("<h2 style='color: #FFD700;'>📉 Multi-Metric Timeline</h2>", unsafe_allow_html=True)
    
    # Create comprehensive multi-line chart
    fig_multi = go.Figure()
    
    # Normalize data to 0-100 scale for comparison
    fig_multi.add_trace(go.Scatter(
        x=dates,
        y=wellness_scores,
        mode='lines+markers',
        name='Wellness',
        line=dict(color='#2ecc71', width=2),
        marker=dict(size=6)
    ))
    
    fig_multi.add_trace(go.Scatter(
        x=dates,
        y=sleep_scores,
        mode='lines+markers',
        name='Sleep',
        line=dict(color='#3498db', width=2),
        marker=dict(size=6)
    ))
    
    fig_multi.add_trace(go.Scatter(
        x=dates,
        y=hydration_scores,
        mode='lines+markers',
        name='Hydration',
        line=dict(color='#1abc9c', width=2),
        marker=dict(size=6)
    ))
    
    fig_multi.add_trace(go.Scatter(
        x=dates,
        y=nutrition_scores,
        mode='lines+markers',
        name='Nutrition',
        line=dict(color='#e74c3c', width=2),
        marker=dict(size=6)
    ))
    
    fig_multi.update_layout(
        title="All Health Metrics Comparison",
        xaxis_title="Date",
        yaxis_title="Score",
        hovermode='x unified',
        height=450,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='#212529'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig_multi, width='stretch')
    
    st.markdown("---")
    
    # =====================================================
    # SECTION 6: 7-DAY PREDICTIONS
    # =====================================================
    st.markdown("<h2 style='color: #FFD700;'>🔮 7-Day Wellness Predictions</h2>", unsafe_allow_html=True)
    
    if predictions:
        # Create prediction dates
        last_date = datetime.strptime(dates[-1], "%Y-%m-%d")
        prediction_dates = [(last_date + timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(7)]
        
        # Prediction insights
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_wellness = wellness_scores[-1]
            st.metric(
                label="Current Wellness",
                value=f"{current_wellness:.1f}",
                delta=None
            )
        
        with col2:
            avg_prediction = sum(predictions) / len(predictions)
            st.metric(
                label="Predicted Average",
                value=f"{avg_prediction:.1f}",
                delta=f"{avg_prediction - current_wellness:+.1f}"
            )
        
        with col3:
            max_prediction = max(predictions)
            st.metric(
                label="Peak Prediction",
                value=f"{max_prediction:.1f}",
                delta=f"{max_prediction - current_wellness:+.1f}"
            )
        
        with col4:
            min_prediction = min(predictions)
            st.metric(
                label="Lowest Prediction",
                value=f"{min_prediction:.1f}",
                delta=f"{min_prediction - current_wellness:+.1f}"
            )
        
        # Prediction Chart
        fig_prediction = go.Figure()
        
        # Historical data
        fig_prediction.add_trace(go.Scatter(
            x=dates,
            y=wellness_scores,
            mode='lines+markers',
            name='Historical',
            line=dict(color='#2ecc71', width=3),
            marker=dict(size=10),
            hovertemplate='<b>%{x}</b><br>Wellness: %{y}<extra></extra>'
        ))
        
        # Predicted data
        fig_prediction.add_trace(go.Scatter(
            x=prediction_dates,
            y=predictions,
            mode='lines+markers',
            name='Predicted',
            line=dict(color='#f39c12', width=3, dash='dash'),
            marker=dict(size=10, symbol='diamond'),
            hovertemplate='<b>%{x}</b><br>Predicted: %{y}<extra></extra>'
        ))
        
        # Add confidence band (simplified)
        upper_bound = [p + 5 for p in predictions]
        lower_bound = [p - 5 for p in predictions]
        
        fig_prediction.add_trace(go.Scatter(
            x=prediction_dates + prediction_dates[::-1],
            y=upper_bound + lower_bound[::-1],
            fill='toself',
            fillcolor='rgba(243, 156, 18, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            showlegend=False,
            name='Confidence Range',
            hoverinfo='skip'
        ))
        
        fig_prediction.update_layout(
            title="Wellness Score: Historical vs Predicted (Next 7 Days)",
            xaxis_title="Date",
            yaxis_title="Wellness Score",
            hovermode='x unified',
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#212529'),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        st.plotly_chart(fig_prediction, width='stretch')
        
        # Prediction Table
        st.subheader("📅 Detailed 7-Day Forecast")
        
        pred_df = pd.DataFrame({
            'Day': [f'Day {i+1}' for i in range(7)],
            'Date': prediction_dates,
            'Predicted Wellness Score': [f"{p:.2f}" for p in predictions],
            'Change from Current': [f"{p - current_wellness:+.2f}" for p in predictions],
            'Trend': ['↗️' if p > current_wellness else '↘️' if p < current_wellness else '→' for p in predictions]
        })
        
        st.dataframe(pred_df, width='stretch', hide_index=True)
        
        # Insights
        st.markdown("---")
        st.subheader("💡 AI-Generated Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if trend == "improving":
                st.success(f"""
                **✅ Excellent Progress!**
                
                Your wellness trend is **{trend}**. Keep it up!
                
                **Recommendations:**
                - Maintain your current sleep schedule ({averages.get('avg_sleep', 0):.1f} hrs average)
                - Continue your hydration habits ({averages.get('avg_hydration', 0):.0f} ml average)
                - Keep consistent with your nutrition plan
                """)
            elif trend == "declining":
                st.warning(f"""
                **⚠️ Attention Needed**
                
                Your wellness trend is **{trend}**.
                
                **Action Items:**
                - Increase sleep duration (currently {averages.get('avg_sleep', 0):.1f} hrs avg)
                - Boost water intake (currently {averages.get('avg_hydration', 0):.0f} ml avg)
                - Review and improve nutrition quality
                """)
            else:
                st.info(f"""
                **ℹ️ Steady State**
                
                Your wellness trend is **{trend}**.
                
                **To Improve:**
                - Set incremental goals for each metric
                - Focus on consistency
                - Make small, sustainable changes
                """)
        
        with col2:
            # Weekly summary
            st.info(f"""
            **📊 Weekly Summary**
            
            **Historical Averages:**
            - Sleep: {averages.get('avg_sleep', 0):.1f} hours/day
            - Hydration: {averages.get('avg_hydration', 0):.0f} ml/day
            - Calories: {averages.get('avg_calories', 0):.0f} kcal/day
            - Wellness: {averages.get('avg_wellness', 0):.1f}/100
            
            **Predicted Next Week:**
            - Avg Wellness: {avg_prediction:.1f}/100
            - Expected Change: {avg_prediction - current_wellness:+.1f} points
            """)
    
    else:
        st.warning("⚠️ No predictions available. Ensure sample_logs.json contains sufficient data.")
    
    st.markdown("---")
    
    # =====================================================
    # SECTION 7: RAW DATA
    # =====================================================
    with st.expander("📋 View Raw Analytics Data"):
        st.json(analytics_data)
    
    with st.expander("📊 View Historical Data"):
        df_history = pd.DataFrame({
            'Date': dates,
            'Sleep (hrs)': sleep_hours_history,
            'Hydration (ml)': hydration_ml,
            'Calories (kcal)': calories,
            'Sleep Score': sleep_scores,
            'Hydration Score': hydration_scores,
            'Nutrition Score': nutrition_scores,
            'Wellness Score': wellness_scores
        })
        st.dataframe(df_history, width='stretch', hide_index=True)

except FileNotFoundError:
    st.error("❌ Error: sample_logs.json not found. Please ensure the data file exists in the data/ directory.")
except json.JSONDecodeError:
    st.error("❌ Error: Invalid JSON format in sample_logs.json. Please check the file structure.")
except Exception as e:
    st.error(f"❌ An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; padding: 20px;'>
    <p><strong>Health Analytics Dashboard</strong> | Powered by AI & Data Science</p>
    <p>Data-driven insights for better health decisions</p>
</div>
""", unsafe_allow_html=True)
