def sleep_agent(state: dict):
    # Sleep analysis agent.
    sleep_hours = state.get("sleep_hours", 0)
    sleep_quality = state.get("sleep_quality", "good")
    interruptions = state.get("sleep_interruptions", 0)
    feeling_on_wake = state.get("feeling_on_wake", "neutral")
    bed_time = state.get("bed_time", "")
    wake_time = state.get("wake_time", "")
    dream_recall = state.get("dream_recall", False)
    
    # Calculate sleep score based on multiple factors
    base_score = 0
    
    # Sleep duration (40% weight)
    if sleep_hours >= 7 and sleep_hours <= 9:
        base_score += 40
    elif sleep_hours >= 6 or sleep_hours <= 10:
        base_score += 30
    else:
        base_score += 15
    
    # Sleep quality (30% weight)
    quality_scores = {"excellent": 30, "good": 25, "fair": 15, "poor": 5}
    base_score += quality_scores.get(sleep_quality, 15)
    
    # Interruptions (15% weight)
    if interruptions == 0:
        base_score += 15
    elif interruptions <= 2:
        base_score += 10
    else:
        base_score += 3
    
    # Feeling on wake (15% weight)
    feeling_scores = {"refreshed": 15, "neutral": 10, "groggy": 5, "exhausted": 0}
    base_score += feeling_scores.get(feeling_on_wake, 5)
    
    # Calculate sleep deficit
    recommended_sleep = 7.5  # Average recommended sleep
    deficit = max(0, recommended_sleep - sleep_hours)
    
    # Update state
    state["sleep_score"] = base_score
    state["sleep_deficit"] = round(deficit, 1)
    state["sleep_quality"] = sleep_quality
    state["sleep_interruptions"] = interruptions
    state["feeling_on_wake"] = feeling_on_wake
    state["bed_time"] = bed_time
    state["wake_time"] = wake_time
    state["dream_recall"] = dream_recall
    
    return state
