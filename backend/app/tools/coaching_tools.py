"""
app/tools/coaching_tools.py

Coaching context aggregation tool for the career coach agent.

Assembles a minimal, token-efficient coaching payload from existing
Phase 8 analytics data. GPT-4o uses this payload to generate advice.
"""

from typing import Any

from app.services.analytics_service import (
    get_overview,
    get_category_performance,
    get_topic_performance,
    get_strengths,
    get_weaknesses,
    get_improvement,
)


def get_coaching_context_tool(user_id: str) -> dict[str, Any]:
    """
    Aggregate the minimum analytics data needed for career coaching.

    Deliberately limits data size to control token costs:
    - Overview: top-level counts and scores
    - Category performance: 4 scores
    - Top 8 topics (sorted by average score)
    - Top 5 strengths
    - Top 5 weaknesses
    - Improvement trend

    Args:
        user_id: Authenticated user (injected by backend).

    Returns:
        Coaching context payload (dict, JSON-serializable).
    """
    overview = get_overview(user_id_str=user_id)
    category_perf = get_category_performance(user_id_str=user_id)
    topic_perf = get_topic_performance(user_id_str=user_id, limit=8)
    strengths = get_strengths(user_id_str=user_id, top_n=5)
    weaknesses = get_weaknesses(user_id_str=user_id, top_n=5)
    improvement = get_improvement(user_id_str=user_id)

    return {
        "overview": {
            "total_interviews": overview.get("total_interviews", 0),
            "evaluated_interviews": overview.get("evaluated_interviews", 0),
            "average_score": overview.get("average_score"),
            "best_score": overview.get("best_score"),
            "lowest_score": overview.get("lowest_score"),
            "latest_score": overview.get("latest_score"),
        },
        "category_performance": category_perf,
        "top_topics": topic_perf,
        "top_strengths": [s["text"] for s in strengths],
        "top_weaknesses": [w["text"] for w in weaknesses],
        "improvement": improvement,
    }
