# Nutrition assistant agent for meal plan generation.

import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


_CUISINE_LABELS = {
    "international": "International (Western / Mediterranean / Asian fusion)",
    "north_indian":  "North Indian (roti, dal, paneer, rice-based dishes)",
    "south_indian":  "South Indian (idli, dosa, sambar, rice-based dishes)",
}

MEAL_SLOTS = ["breakfast", "mid_morning", "lunch", "afternoon_break", "dinner", "post_dinner"]


def generate_full_day_plan(state: dict) -> dict:
    """
    Generate a complete full-day meal plan (6 slots) with a specific cuisine type.

    Expected state keys:
        - calorie_target (int)
        - protein_target (int)
        - weight (float)
        - age (int)
        - gender (str)
        - weight_goal (str)
        - target_weight_change_kg (float)
        - target_timeline_weeks (int)
        - cuisine_type (str) — 'international' | 'north_indian' | 'south_indian'

    Returns state with added keys:
        - full_day_meals: list of 6 meal dicts
        - daily_summary: str
        - nutrition_tips: list[str]
        - ai_nutrition_generated: bool
    """
    calorie_target = state.get("calorie_target", 2000)
    protein_target = state.get("protein_target", 150)
    weight         = state.get("weight", 70)
    age            = state.get("age", 25)
    gender         = state.get("gender", "male")
    weight_goal    = state.get("weight_goal", "maintain")
    target_change  = state.get("target_weight_change_kg", 0)
    target_weeks   = state.get("target_timeline_weeks", 12)
    cuisine_type   = state.get("cuisine_type", "international")
    cuisine_label  = _CUISINE_LABELS.get(cuisine_type, cuisine_type)

    prompt = f"""You are an expert dietitian AI. Generate a healthy, balanced full-day meal plan.

**User Profile:**
- Age: {age} years | Weight: {weight} kg | Gender: {gender}
- Goal: {weight_goal.upper()} ({target_change} kg over {target_weeks} weeks)
- Daily calorie target: {calorie_target} kcal | Protein target: {protein_target} g

**Cuisine Style:** {cuisine_label}

Create a 6-meal plan covering exactly these slots in order:
1. breakfast (8:00 AM)
2. mid_morning (10:30 AM)
3. lunch (1:00 PM)
4. afternoon_break (4:00 PM)
5. dinner (7:30 PM)
6. post_dinner (9:00 PM)

Requirements:
- Total calories across all 6 meals must be close to {calorie_target} kcal
- Total protein across all 6 meals must be close to {protein_target} g
- All dishes must match the {cuisine_label} style
- Include realistic portion sizes and macro breakdown

Respond ONLY with valid JSON in this exact structure:
{{
    "meals": [
        {{
            "meal_type": "breakfast",
            "meal_name": "Name of dish",
            "description": "Brief 1-line description",
            "ingredients": ["ingredient1", "ingredient2"],
            "calories": 450,
            "protein_g": 25,
            "carbs_g": 55,
            "fat_g": 12
        }},
        {{
            "meal_type": "mid_morning",
            "meal_name": "Name of dish",
            "description": "Brief 1-line description",
            "ingredients": ["ingredient1"],
            "calories": 150,
            "protein_g": 8,
            "carbs_g": 18,
            "fat_g": 4
        }},
        {{
            "meal_type": "lunch",
            "meal_name": "Name of dish",
            "description": "Brief 1-line description",
            "ingredients": ["ingredient1", "ingredient2"],
            "calories": 550,
            "protein_g": 40,
            "carbs_g": 60,
            "fat_g": 15
        }},
        {{
            "meal_type": "afternoon_break",
            "meal_name": "Name of dish",
            "description": "Brief 1-line description",
            "ingredients": ["ingredient1"],
            "calories": 180,
            "protein_g": 6,
            "carbs_g": 25,
            "fat_g": 5
        }},
        {{
            "meal_type": "dinner",
            "meal_name": "Name of dish",
            "description": "Brief 1-line description",
            "ingredients": ["ingredient1", "ingredient2"],
            "calories": 500,
            "protein_g": 35,
            "carbs_g": 50,
            "fat_g": 14
        }},
        {{
            "meal_type": "post_dinner",
            "meal_name": "Name of dish",
            "description": "Brief 1-line description",
            "ingredients": ["ingredient1"],
            "calories": 100,
            "protein_g": 3,
            "carbs_g": 12,
            "fat_g": 3
        }}
    ],
    "daily_summary": "One sentence summary of this meal plan and how it supports the user's goals.",
    "tips": ["tip1", "tip2", "tip3"]
}}
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional dietitian AI. Always respond with valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2500,
            response_format={"type": "json_object"}
        )
        ai_response = chat_completion.choices[0].message.content
        plan = json.loads(ai_response)

        state["full_day_meals"]       = plan.get("meals", [])
        state["daily_summary"]        = plan.get("daily_summary", "")
        state["nutrition_tips"]       = plan.get("tips", [])
        state["ai_nutrition_generated"] = True

    except Exception as e:
        state["full_day_meals"]       = []
        state["daily_summary"]        = ""
        state["nutrition_tips"]       = [f"AI generation failed: {str(e)}"]
        state["ai_nutrition_generated"] = False

    return state


def nutrition_agent(state: dict):
    """
    AI-powered nutrition agent that generates personalized meal plans.
    """
    
    # Extract relevant data from state
    calorie_target = state.get("calorie_target", 2000)
    protein_target = state.get("protein_target", 150)
    current_calories = state.get("total_daily_calories", 0)
    current_protein = state.get("total_daily_protein", 0)
    weight = state.get("weight", 70)
    age = state.get("age", 25)
    gender = state.get("gender", "male")
    
    # Weight goals
    weight_goal = state.get("weight_goal", "maintain")
    target_weight_change = state.get("target_weight_change_kg", 0)
    target_timeline = state.get("target_timeline_weeks", 12)
    
    # Calculate deficits/surplus
    calorie_deficit = calorie_target - current_calories
    protein_deficit = protein_target - current_protein
    
    # Get user's current behavior patterns
    sleep_hours = state.get("sleep_hours", 7)
    exercise_duration = state.get("exercise_duration", 0)
    exercise_type = state.get("exercise_type", "none")
    hydration_score = state.get("hydration_score", 50)
    
    # Budget constraint (can be passed from user profile)
    budget_per_meal = state.get("budget_per_meal", 10)
    
    # Build prompt for Groq LLM
    prompt = f"""You are an expert nutrition AI assistant. Generate a personalized meal plan based on the following user data:

**User Profile:**
- Age: {age} years
- Current Weight: {weight} kg
- Gender: {gender}
- Weight Goal: {weight_goal.upper()}
- Daily calorie target: {calorie_target} kcal
- Daily protein target: {protein_target}g

**Current Status:**
- Calories consumed today: {current_calories} kcal
- Protein consumed today: {current_protein}g
- Calorie remaining: {calorie_deficit} kcal
- Protein remaining: {protein_deficit}g
- Sleep: {sleep_hours} hours
- Exercise: {exercise_duration} min of {exercise_type}
- Hydration score: {hydration_score}%

**Constraints:**
- Budget per meal: ${budget_per_meal}
- Focus on whole foods and balanced macros

**Task:**
Generate 2-3 meal/snack suggestions for the rest of the day that:
1. Fill the calorie and protein gaps
2. Are budget-friendly (under ${budget_per_meal} per meal)
3. Balance macros (protein, carbs, healthy fats)
4. Consider the user's activity level and sleep quality
5. **Support the weight {weight_goal} goal** - adjust portions and macro ratios accordingly
6. Include portion sizes and macro breakdown

Provide your response in JSON format:
{{
    "meal_suggestions": [
        {{
            "meal_name": "Name",
            "ingredients": ["ingredient1", "ingredient2"],
            "calories": 450,
            "protein_g": 30,
            "carbs_g": 40,
            "fat_g": 15,
            "estimated_cost": 8,
            "reasoning": "Why this meal fits the user's needs"
        }}
    ],
    "daily_summary": "Brief summary of recommendations",
    "tips": ["tip1", "tip2"]
}}
"""
    
    try:
        # Call Groq LLM
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional nutritionist AI. Always respond with valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile", #groq/compound # Fast and powerful model
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Parse LLM response
        ai_response = chat_completion.choices[0].message.content
        nutrition_plan = json.loads(ai_response)
        
        # Add to state
        state["nutrition_plan"] = nutrition_plan
        state["meal_suggestions"] = nutrition_plan.get("meal_suggestions", [])
        state["nutrition_tips"] = nutrition_plan.get("tips", [])
        state["nutrition_summary"] = nutrition_plan.get("daily_summary", "")
        
        # Calculate total suggested calories and protein
        total_suggested_calories = sum(
            meal.get("calories", 0) for meal in state["meal_suggestions"]
        )
        total_suggested_protein = sum(
            meal.get("protein_g", 0) for meal in state["meal_suggestions"]
        )
        
        state["suggested_calories"] = total_suggested_calories
        state["suggested_protein"] = total_suggested_protein
        
        # Add AI reasoning flag
        state["ai_nutrition_generated"] = True
        
    except Exception as e:
        # Fallback if AI fails
        state["nutrition_plan"] = {
            "error": f"AI nutrition generation failed: {str(e)}",
            "fallback": True
        }
        state["meal_suggestions"] = []
        state["nutrition_tips"] = [
            "Focus on lean protein sources",
            f"Aim for {protein_deficit}g more protein today",
            "Stay hydrated and eat whole foods"
        ]
        state["ai_nutrition_generated"] = False
    
    return state
