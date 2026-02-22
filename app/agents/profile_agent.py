from app.services.formulas import calculate_bmr, water_target_ml, protein_target_g


def profile_agent(state: dict):
    # Profile analysis agent.
    weight = state["weight"]
    height = state["height"]
    age = state["age"]
    gender = state.get("gender", "male")
    weight_goal = state.get("weight_goal", "maintain")
    target_weight_change = state.get("target_weight_change_kg", 0)
    target_timeline = state.get("target_timeline_weeks", 12)
    activity_level = state.get("activity_level", "moderate")
    
    # Calculate BMR (Base Metabolic Rate)
    bmr = calculate_bmr(weight, height, age, gender)
    
    # Activity level multipliers (TDEE = Total Daily Energy Expenditure)
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    
    tdee = bmr * activity_multipliers.get(activity_level, 1.55)
    
    # Adjust calories based on weight goal
    # 1 kg fat = ~7700 calories
    # Safe weight loss/gain: 0.5-1 kg per week
    if weight_goal == "reduce":
        # Calculate daily calorie deficit needed
        total_calorie_deficit = target_weight_change * 7700
        daily_deficit = total_calorie_deficit / (target_timeline * 7)
        calorie_target = int(tdee - daily_deficit)
        # Safety: Don't go below 1200 calories (women) or 1500 (men)
        min_calories = 1200 if gender == "female" else 1500
        calorie_target = max(calorie_target, min_calories)
        
    elif weight_goal == "increase":
        # Calculate daily calorie surplus needed
        total_calorie_surplus = target_weight_change * 7700
        daily_surplus = total_calorie_surplus / (target_timeline * 7)
        calorie_target = int(tdee + daily_surplus)
        # Safety: Don't exceed 1000 calorie surplus per day
        calorie_target = min(calorie_target, int(tdee + 1000))
        
    else:  # maintain
        calorie_target = int(tdee)
    
    # Update protein target based on weight goal
    if weight_goal == "reduce":
        # Higher protein during weight loss to preserve muscle
        protein_multiplier = 2.2  # g per kg
    elif weight_goal == "increase":
        # Higher protein for muscle gain
        protein_multiplier = 2.0
    else:
        protein_multiplier = 1.6
    
    protein_target = int(weight * protein_multiplier)
    
    state["calorie_target"] = calorie_target
    state["water_target"] = int(water_target_ml(weight))
    state["protein_target"] = protein_target
    state["bmr"] = int(bmr)
    state["tdee"] = int(tdee)
    state["activity_level"] = activity_level
    state["weight_goal"] = weight_goal
    
    return state
