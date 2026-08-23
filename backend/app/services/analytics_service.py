"""
app/services/analytics_service.py

Phase 8 — Analytics & Performance Tracking service layer.

Architecture:
    MongoDB (interviews + feedback)
        ↓
    _get_enriched_feedback()  ← central join function
        ↓
    Individual analytics functions (pure computation)
        ↓
    Aggregated statistics
        ↓
    FastAPI Analytics APIs

Rules:
  - NO Gemini / LLM calls. All calculations are deterministic.
  - User isolation is enforced at the query level (user_id filter on every query).
  - Empty data returns valid zero/null structures, never errors.
  - Averages and percentages are rounded to 2 decimal places.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from app.models.interview import interviews_collection
from app.models.feedback import feedback_collection


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _round2(value: float) -> float:
    """Round to 2 decimal places."""
    return round(value, 2)


def _get_cutoff(days: int) -> datetime:
    """Return a UTC datetime `days` ago from now."""
    return datetime.now(timezone.utc) - timedelta(days=days)


def _get_enriched_feedback(
    user_id_str: str,
    days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Core data loader: returns all feedback docs for the user, joined with
    their corresponding interview documents via a MongoDB $lookup.

    - Optionally filtered: only feedback whose interview.completed_at falls
      within the last `days` days.
    - Always sorted: interview.completed_at ASC (oldest first).

    Each returned document has the full feedback fields PLUS an "interview"
    sub-document containing the interview metadata.
    """
    user_obj_id = ObjectId(user_id_str)

    pipeline: List[Dict] = [
        # 1. Filter feedback to this user only
        {"$match": {"user_id": user_obj_id}},
        # 2. Join with the interviews collection
        {
            "$lookup": {
                "from": "interviews",
                "localField": "interview_id",
                "foreignField": "_id",
                "as": "interview",
            }
        },
        # 3. Flatten the array (each feedback doc has exactly one matching interview)
        {"$unwind": "$interview"},
    ]

    # 4. Optional date filter on interview completion date
    if days is not None:
        cutoff = _get_cutoff(days)
        pipeline.append({"$match": {"interview.completed_at": {"$gte": cutoff}}})

    # 5. Sort chronologically
    pipeline.append({"$sort": {"interview.completed_at": ASCENDING}})

    return list(feedback_collection.aggregate(pipeline))


# ---------------------------------------------------------------------------
# 1. Overview
# ---------------------------------------------------------------------------

def get_overview(user_id_str: str, days: Optional[int] = None) -> Dict[str, Any]:
    """
    Returns aggregate counts and score summary for the authenticated user.

    - total_interviews / completed_interviews: filtered by created_at when days is set.
    - Score fields: derived from enriched feedback (filtered by completed_at).
    """
    user_obj_id = ObjectId(user_id_str)

    # Build the base date filter for interview counts
    interview_filter: Dict[str, Any] = {"user_id": user_obj_id}
    if days is not None:
        interview_filter["created_at"] = {"$gte": _get_cutoff(days)}

    total = interviews_collection.count_documents(interview_filter)
    completed = interviews_collection.count_documents({**interview_filter, "status": "completed"})

    # Get enriched feedback (applies days filter via completed_at)
    enriched = _get_enriched_feedback(user_id_str, days)
    evaluated = len(enriched)

    if not enriched:
        return {
            "total_interviews": total,
            "completed_interviews": completed,
            "evaluated_interviews": evaluated,
            "average_score": None,
            "best_score": None,
            "lowest_score": None,
            "latest_score": None,
        }

    scores = [doc["overall_score"] for doc in enriched]
    return {
        "total_interviews": total,
        "completed_interviews": completed,
        "evaluated_interviews": evaluated,
        "average_score": _round2(sum(scores) / len(scores)),
        "best_score": max(scores),
        "lowest_score": min(scores),
        "latest_score": enriched[-1]["overall_score"],  # sorted asc → last = most recent
    }


# ---------------------------------------------------------------------------
# 2. Score Trend
# ---------------------------------------------------------------------------

def get_score_trend(user_id_str: str, days: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Returns chronological (oldest→newest) score data for line-chart rendering.
    Each item represents one evaluated interview.
    """
    enriched = _get_enriched_feedback(user_id_str, days)

    result = []
    for doc in enriched:
        interview = doc.get("interview", {})
        date = (
            interview.get("completed_at")
            or doc.get("updated_at")
            or doc.get("created_at")
        )
        result.append({
            "interview_id": str(doc["interview_id"]),
            "title": interview.get("title", ""),
            "date": date,
            "score": doc["overall_score"],
        })

    return result


# ---------------------------------------------------------------------------
# 3. Category Performance
# ---------------------------------------------------------------------------

def get_category_performance(
    user_id_str: str, days: Optional[int] = None
) -> Dict[str, Optional[float]]:
    """
    Returns average scores for each Phase 7 evaluation category:
    technical, communication, problem_solving, relevance.
    """
    enriched = _get_enriched_feedback(user_id_str, days)

    if not enriched:
        return {
            "technical": None,
            "communication": None,
            "problem_solving": None,
            "relevance": None,
        }

    totals: Dict[str, float] = {
        "technical": 0.0,
        "communication": 0.0,
        "problem_solving": 0.0,
        "relevance": 0.0,
    }
    count = len(enriched)

    for doc in enriched:
        cat = doc.get("category_scores", {})
        for key in totals:
            totals[key] += cat.get(key, 0)

    return {key: _round2(totals[key] / count) for key in totals}


# ---------------------------------------------------------------------------
# 4. Topic Performance
# ---------------------------------------------------------------------------

def get_topic_performance(
    user_id_str: str,
    days: Optional[int] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Aggregates topic_analysis from Phase 7 feedback across all interviews.
    Returns topics sorted by average_score DESC.
    """
    enriched = _get_enriched_feedback(user_id_str, days)

    topic_scores: Dict[str, List[int]] = {}
    for doc in enriched:
        for topic_item in doc.get("topic_analysis", []):
            topic = (topic_item.get("topic") or "").strip()
            score = topic_item.get("score")
            if topic and score is not None:
                topic_scores.setdefault(topic, []).append(score)

    result = [
        {
            "topic": topic,
            "average_score": _round2(sum(scores) / len(scores)),
            "interviews_count": len(scores),
        }
        for topic, scores in topic_scores.items()
    ]

    result.sort(key=lambda x: x["average_score"], reverse=True)
    return result[:limit]


# ---------------------------------------------------------------------------
# 5. Strengths
# ---------------------------------------------------------------------------

def get_strengths(
    user_id_str: str,
    days: Optional[int] = None,
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """
    Aggregates strength strings from Phase 7 feedback.
    Normalizes to lowercase for counting, preserves original case for display.
    Returns sorted by count DESC.
    """
    enriched = _get_enriched_feedback(user_id_str, days)

    original_map: Dict[str, str] = {}
    counter: Counter = Counter()

    for doc in enriched:
        for s in doc.get("strengths", []):
            text = s.strip()
            if not text:
                continue
            norm = text.lower()
            if norm not in original_map:
                original_map[norm] = text  # first occurrence wins for display
            counter[norm] += 1

    return [
        {"text": original_map[norm], "count": count}
        for norm, count in counter.most_common(top_n)
    ]


# ---------------------------------------------------------------------------
# 6. Weaknesses
# ---------------------------------------------------------------------------

def get_weaknesses(
    user_id_str: str,
    days: Optional[int] = None,
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """
    Aggregates weakness strings from Phase 7 feedback.
    Normalizes to lowercase for counting, preserves original case for display.
    Returns sorted by count DESC.
    """
    enriched = _get_enriched_feedback(user_id_str, days)

    original_map: Dict[str, str] = {}
    counter: Counter = Counter()

    for doc in enriched:
        for w in doc.get("weaknesses", []):
            text = w.strip()
            if not text:
                continue
            norm = text.lower()
            if norm not in original_map:
                original_map[norm] = text
            counter[norm] += 1

    return [
        {"text": original_map[norm], "count": count}
        for norm, count in counter.most_common(top_n)
    ]


# ---------------------------------------------------------------------------
# 7. Interview History
# ---------------------------------------------------------------------------

def get_history(
    user_id_str: str,
    page: int = 1,
    limit: int = 10,
    days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Paginated list of all completed interviews, newest first.
    Includes score if the interview has been evaluated; None otherwise.
    """
    user_obj_id = ObjectId(user_id_str)

    match_filter: Dict[str, Any] = {"user_id": user_obj_id, "status": "completed"}
    if days is not None:
        match_filter["completed_at"] = {"$gte": _get_cutoff(days)}

    total = interviews_collection.count_documents(match_filter)
    skip = (page - 1) * limit

    interviews = list(
        interviews_collection.find(match_filter)
        .sort("completed_at", DESCENDING)
        .skip(skip)
        .limit(limit)
    )

    # Bulk-fetch feedback scores for these interviews
    interview_ids = [i["_id"] for i in interviews]
    feedback_by_interview = {
        doc["interview_id"]: doc["overall_score"]
        for doc in feedback_collection.find(
            {"interview_id": {"$in": interview_ids}},
            {"interview_id": 1, "overall_score": 1},
        )
    }

    items = []
    for interview in interviews:
        date = (
            interview.get("completed_at")
            or interview.get("updated_at")
            or interview.get("created_at")
        )
        items.append({
            "interview_id": str(interview["_id"]),
            "title": interview.get("title", ""),
            "role": interview.get("role", ""),
            "interview_type": interview.get("interview_type", ""),
            "difficulty": interview.get("difficulty", ""),
            "score": feedback_by_interview.get(interview["_id"]),
            "date": date,
        })

    return {"items": items, "page": page, "limit": limit, "total": total}


# ---------------------------------------------------------------------------
# 8. Interview Type Performance
# ---------------------------------------------------------------------------

def get_interview_type_performance(
    user_id_str: str, days: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Returns average overall_score grouped by interview_type (Technical, Behavioral, etc.).
    Sorted by average_score DESC.
    """
    enriched = _get_enriched_feedback(user_id_str, days)

    type_scores: Dict[str, List[int]] = {}
    for doc in enriched:
        itype = (doc.get("interview", {}).get("interview_type") or "").strip()
        if itype:
            type_scores.setdefault(itype, []).append(doc["overall_score"])

    result = [
        {
            "type": itype,
            "average_score": _round2(sum(scores) / len(scores)),
            "count": len(scores),
        }
        for itype, scores in type_scores.items()
    ]
    result.sort(key=lambda x: x["average_score"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# 9. Difficulty Performance
# ---------------------------------------------------------------------------

def get_difficulty_performance(
    user_id_str: str, days: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Returns average overall_score grouped by difficulty level.
    Only returns difficulty levels for which data exists.
    Sorted by average_score DESC.
    """
    enriched = _get_enriched_feedback(user_id_str, days)

    diff_scores: Dict[str, List[int]] = {}
    for doc in enriched:
        diff = (doc.get("interview", {}).get("difficulty") or "").strip()
        if diff:
            diff_scores.setdefault(diff, []).append(doc["overall_score"])

    result = [
        {
            "difficulty": diff,
            "average_score": _round2(sum(scores) / len(scores)),
            "count": len(scores),
        }
        for diff, scores in diff_scores.items()
    ]
    result.sort(key=lambda x: x["average_score"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# 10. Role Performance
# ---------------------------------------------------------------------------

def get_role_performance(
    user_id_str: str, days: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Returns average overall_score grouped by job role.
    Sorted by average_score DESC.
    """
    enriched = _get_enriched_feedback(user_id_str, days)

    role_scores: Dict[str, List[int]] = {}
    for doc in enriched:
        role = (doc.get("interview", {}).get("role") or "").strip()
        if role:
            role_scores.setdefault(role, []).append(doc["overall_score"])

    result = [
        {
            "role": role,
            "average_score": _round2(sum(scores) / len(scores)),
            "count": len(scores),
        }
        for role, scores in role_scores.items()
    ]
    result.sort(key=lambda x: x["average_score"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# 11. Improvement Analysis
# ---------------------------------------------------------------------------

_STABLE_THRESHOLD = 2.0  # Score difference < 2 points = "stable"


def get_improvement(user_id_str: str) -> Dict[str, Any]:
    """
    Compares earlier vs recent interview performance.

    Method:
      - Sort all evaluated interviews chronologically (oldest → newest).
      - Split into two halves: earlier[:mid] and recent[mid:].
      - Compare average scores.

    Requires ≥2 evaluated interviews; returns "insufficient_data" otherwise.

    trend values: "improving" | "declining" | "stable" | "insufficient_data"
    Note: Days filter is NOT applied — improvement is always computed from
    all available history to give a meaningful trend.
    """
    enriched = _get_enriched_feedback(user_id_str)  # no days filter

    if len(enriched) < 2:
        return {
            "previous_average": None,
            "recent_average": None,
            "score_difference": None,
            "improvement_percentage": None,
            "trend": "insufficient_data",
        }

    scores = [doc["overall_score"] for doc in enriched]  # already sorted asc
    mid = len(scores) // 2
    earlier_scores = scores[:mid]
    recent_scores = scores[mid:]

    prev_avg = _round2(sum(earlier_scores) / len(earlier_scores))
    recent_avg = _round2(sum(recent_scores) / len(recent_scores))
    diff = _round2(recent_avg - prev_avg)

    # Improvement percentage relative to the baseline (earlier average)
    if prev_avg > 0:
        pct = _round2((diff / prev_avg) * 100)
    else:
        pct = 0.0

    if abs(diff) < _STABLE_THRESHOLD:
        trend = "stable"
    elif diff > 0:
        trend = "improving"
    else:
        trend = "declining"

    return {
        "previous_average": prev_avg,
        "recent_average": recent_avg,
        "score_difference": diff,
        "improvement_percentage": pct,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# 12. Full Analytics (dashboard)
# ---------------------------------------------------------------------------

def get_full_analytics(
    user_id_str: str, days: Optional[int] = None
) -> Dict[str, Any]:
    """
    Consolidated analytics payload for the frontend dashboard.
    Returns a representative subset (top 5) for topics, strengths, weaknesses.
    Improvement is always from all history (no days filter).
    """
    return {
        "overview": get_overview(user_id_str, days),
        "score_trend": get_score_trend(user_id_str, days),
        "category_performance": get_category_performance(user_id_str, days),
        "top_topics": get_topic_performance(user_id_str, days, limit=5),
        "top_strengths": get_strengths(user_id_str, days, top_n=5),
        "top_weaknesses": get_weaknesses(user_id_str, days, top_n=5),
        "improvement": get_improvement(user_id_str),
    }
