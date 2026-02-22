# Context agent to process raw logs.

def log_context_agent(state: dict):
    """
    Processes separate daily logs and routes information to specialized health agents.
    """
    
    # Extract profile data
    profile = state.get("profile", {})
    state["user_id"] = profile.get("user_id", "unknown")
    state["user_name"] = profile.get("name", "User")
    state["age"] = profile.get("age", 25)
    state["weight"] = profile.get("weight", 70)
    state["height"] = profile.get("height", 170)
    state["gender"] = profile.get("gender", "male")
    state["weight_goal"] = profile.get("weight_goal", "maintain")
    state["target_weight_change_kg"] = profile.get("target_weight_change_kg", 0)
    state["target_timeline_weeks"] = profile.get("target_timeline_weeks", 12)
    state["activity_level"] = profile.get("activity_level", "moderate")
    
    # Extract sleep log data
    sleep_log = state.get("sleep_log", {})
    state["date"] = sleep_log.get("date", "")
    state["day_of_week"] = sleep_log.get("day_of_week", "")
    state["sleep_hours"] = sleep_log.get("sleep_hours", 0)
    state["sleep_quality"] = sleep_log.get("sleep_quality", "unknown")
    state["bed_time"] = sleep_log.get("bed_time", "")
    state["wake_time"] = sleep_log.get("wake_time", "")
    state["sleep_interruptions"] = sleep_log.get("interruptions", 0)
    state["dream_recall"] = sleep_log.get("dream_recall", False)
    state["feeling_on_wake"] = sleep_log.get("feeling_on_wake", "unknown")
    
    # Extract hydration log data
    hydration_log = state.get("hydration_log", {})
    state["actual_water_intake"] = hydration_log.get("water_intake_ml", 0)
    state["water_logs"] = hydration_log.get("water_logs", [])
    state["caffeine_intake_mg"] = hydration_log.get("caffeine_intake_mg", 0)
    state["urine_color"] = hydration_log.get("urine_color", "unknown")
    
    # Extract nutrition log data
    nutrition_log = state.get("nutrition_log", {})
    state["meals"] = nutrition_log.get("meals", [])
    state["total_daily_calories"] = nutrition_log.get("total_calories", 0)
    state["total_daily_protein"] = nutrition_log.get("total_protein_g", 0)
    state["total_daily_carbs"] = nutrition_log.get("total_carbs_g", 0)
    state["total_daily_fat"] = nutrition_log.get("total_fat_g", 0)
    state["meal_count"] = nutrition_log.get("meal_count", 0)
    state["budget_per_meal"] = nutrition_log.get("budget_per_meal", 10)
    
    # Store original logs for reference
    state["original_logs"] = {
        "sleep": sleep_log,
        "hydration": hydration_log,
        "nutrition": nutrition_log
    }
    
    return state
