"""
app/tools/resume_tools.py

Resume-related tools for the agentic AI layer.

Only retrieves resume data for the authenticated user.
GPT-4o cannot retrieve another user's resume.
"""

from typing import Any

from app.services.resume_service import get_resume


def get_resume_tool(user_id: str, resume_id: str) -> dict[str, Any]:
    """
    Retrieve resume text and metadata for the authenticated user.

    Ownership is enforced: the resume must belong to user_id.
    Extracted text is truncated to limit token usage.

    Args:
        user_id:   Authenticated user (injected by backend).
        resume_id: Target resume ID.

    Returns:
        Resume metadata and a safe excerpt of the extracted text.

    Raises:
        ValueError: Resume not found or access denied.
    """
    resume = get_resume(resume_id=resume_id, user_id=user_id)

    if resume is None:
        raise ValueError("Resume not found or access denied.")

    # Truncate extracted text to prevent excessive token usage
    extracted_text = resume.get("extracted_text", "") or ""
    truncated_text = extracted_text[:5000]

    return {
        "id": str(resume.get("_id", resume_id)),
        "filename": resume.get("filename", ""),
        "file_type": resume.get("file_type", ""),
        "file_size": resume.get("file_size"),
        "text_length": resume.get("text_length", 0),
        "extracted_text_excerpt": truncated_text,
        "text_truncated": len(extracted_text) > 5000,
        "created_at": str(resume.get("created_at", "")),
    }
