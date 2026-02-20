def hydration_agent(state: dict):
    """
    Analyzes hydration based on automatically calculated water needs.
    Water target is calculated based on age, weight, height, and activity level.
    
    Formula: Base water need = 30-35ml per kg of body weight, adjusted for age
    """
    # Get actual water intake from logs
    actual_intake = state.get("actual_water_intake", 0)
    age = state.get("age", 25)
    weight = state.get("weight", 70)
    height = state.get("height", 170)
    activity_level = state.get("activity_level", "moderate")
    caffeine_intake = state.get("caffeine_intake_mg", 0)
    urine_color = state.get("urine_color", "light_yellow")
    
    # Calculate base water requirement (ml per kg)
    # Age-based water requirement
    if age < 18:
        ml_per_kg = 35  # Youth need more water per kg
    elif age < 30:
        ml_per_kg = 35
    elif age < 55:
        ml_per_kg = 33
    else:
        ml_per_kg = 30  # Seniors need slightly less
    
    # Calculate base water need
    base_water = ml_per_kg * weight
    
    # Activity level adjustment
    activity_multipliers = {
        "sedentary": 1.0,
        "light": 1.1,
        "moderate": 1.2,
        "active": 1.3,
        "very_active": 1.4
    }
    activity_multiplier = activity_multipliers.get(activity_level, 1.2)
    
    # Caffeine adjustment (caffeine is dehydrating)
    caffeine_adjustment = min(caffeine_intake * 1.5, 500)  # Max 500ml adjustment
    
    # Calculate recommended water intake
    recommended_water = int(base_water * activity_multiplier + caffeine_adjustment)
    
    # Calculate hydration score
    percent = int((actual_intake / recommended_water) * 100) if recommended_water > 0 else 0
    
    # Urine color adjustment to score
    urine_scores = {
        "clear": 5,  # May be over-hydrated
        "pale": 0,   # Optimal
        "light_yellow": 0,  # Optimal
        "yellow": -10,  # Need more water
        "dark_yellow": -20  # Dehydrated
    }
    urine_adjustment = urine_scores.get(urine_color, 0)
    
    final_score = max(0, min(100, percent + urine_adjustment))
    
    state["hydration_score"] = final_score
    state["recommended_water_ml"] = recommended_water
    state["actual_water_intake"] = actual_intake
    state["water_deficit_ml"] = max(0, recommended_water - actual_intake)
    state["age"] = age  # Pass through for display
    
    # Hydration status based on score
    if final_score >= 90:
        state["hydration_status"] = "optimal"
        state["hydration_advice"] = "Excellent hydration! Keep it up."
    elif final_score >= 75:
        state["hydration_status"] = "good"
        state["hydration_advice"] = f"Good hydration. Drink {state['water_deficit_ml']}ml more to reach optimal."
    elif final_score >= 50:
        state["hydration_status"] = "moderate"
        state["hydration_advice"] = f"Increase water intake. You need {state['water_deficit_ml']}ml more."
    else:
        state["hydration_status"] = "poor"
        state["hydration_advice"] = f"⚠️ Critical: Drink {state['water_deficit_ml']}ml more water today!"
    
    return state
