from langgraph.graph import StateGraph
from app.agents.log_context_agent import log_context_agent
from app.agents.profile_agent import profile_agent
from app.agents.sleep_agent import sleep_agent
from app.agents.hydration_agent import hydration_agent
from app.agents.nutrition_agent import nutrition_agent
from app.agents.analytics_agent import analytics_agent


def build_graph():
    """
    Builds the health analysis graph with the following flow:
    1. log_context_agent - Processes daily logs and extracts data
    2. profile_agent - Calculates health targets (BMR, water, protein)
    3. sleep_agent - Analyzes sleep quality and deficit
    4. hydration_agent - Analyzes hydration (auto-suggests water based on age)
    5. nutrition_agent - AI-powered meal plan generation (Groq LLM)
    6. analytics_agent - Provides overall day analytics
    """
    builder = StateGraph(dict)

    # Add all agents
    builder.add_node("log_context", log_context_agent)
    builder.add_node("profile", profile_agent)
    builder.add_node("sleep", sleep_agent)
    builder.add_node("hydration", hydration_agent)
    builder.add_node("nutrition", nutrition_agent)
    builder.add_node("analytics", analytics_agent)

    # Define the flow
    builder.set_entry_point("log_context")
    builder.add_edge("log_context", "profile")
    builder.add_edge("profile", "sleep")
    builder.add_edge("sleep", "hydration")
    builder.add_edge("hydration", "nutrition")
    builder.add_edge("nutrition", "analytics")

    return builder.compile()
