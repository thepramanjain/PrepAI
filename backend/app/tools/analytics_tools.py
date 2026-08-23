"""
app/tools/analytics_tools.py

Analytics-related tools for the agentic AI layer.

All analytics are computed by Python/MongoDB (Phase 8 service).
GPT-4o only interprets results — it does NOT calculate statistics.
"""

from typing import Any

from app.services.analytics_service import (
    get_full_analytics,
    get_score_trend,
    get_category_performance,
    get_topic_performance,
    get_strengths,
    get_weaknesses,
    get_improvement,
)


def get_analytics_tool(user_id: str) -> dict[str, Any]:
    """
    Return the full analytics dashboard for the user.

    Args:
        user_id: Authenticated user (injected by backend).
    """
    return get_full_analytics(user_id_str=user_id)


def get_score_trend_tool(user_id: str) -> dict[str, Any]:
    """
    Return chronological score data for all evaluated interviews.

    Args:
        user_id: Authenticated user (injected by backend).
    """
    trend = get_score_trend(user_id_str=user_id)
    # Limit to last 20 entries to control token usage
    return {"score_trend": trend[-20:], "total_entries": len(trend)}


def get_category_performance_tool(user_id: str) -> dict[str, Any]:
    """
    Return average scores per evaluation category.

    Args:
        user_id: Authenticated user (injected by backend).
    """
    return get_category_performance(user_id_str=user_id)


def get_topic_performance_tool(user_id: str) -> dict[str, Any]:
    """
    Return topic-level performance data.

    Args:
        user_id: Authenticated user (injected by backend).
    """
    topics = get_topic_performance(user_id_str=user_id, limit=15)
    return {"topics": topics, "count": len(topics)}


def get_strengths_tool(user_id: str) -> dict[str, Any]:
    """
    Return the user's top identified strengths.

    Args:
        user_id: Authenticated user (injected by backend).
    """
    strengths = get_strengths(user_id_str=user_id, top_n=10)
    return {"strengths": strengths, "count": len(strengths)}


def get_weaknesses_tool(user_id: str) -> dict[str, Any]:
    """
    Return the user's top identified weaknesses.

    Args:
        user_id: Authenticated user (injected by backend).
    """
    weaknesses = get_weaknesses(user_id_str=user_id, top_n=10)
    return {"weaknesses": weaknesses, "count": len(weaknesses)}


def get_improvement_tool(user_id: str) -> dict[str, Any]:
    """
    Analyze whether the user is improving, declining, or stable.

    Args:
        user_id: Authenticated user (injected by backend).
    """
    return get_improvement(user_id_str=user_id)
