"""
app/services/ai_question_service.py

Business logic for AI Question Generation.
"""

from fastapi import HTTPException, status
from bson import ObjectId
from google.genai import types
import json

from app.ai.gemini_client import gemini_wrapper
from app.ai.prompts import INTERVIEW_QUESTION_SYSTEM_PROMPT
from app.schemas.ai_question import GeneratedQuestionList
from app.models.interview import interviews_collection
from app.models.resume import resumes_collection  # Assuming resume.py exposes this
from app.models.question import questions_collection
from app.utils.helpers import utc_now


def _verify_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid ID format"
        )


def _get_interview_and_verify_ownership(interview_id_str: str, user_id_str: str):
    obj_id = _verify_object_id(interview_id_str)
    interview = interviews_collection.find_one({"_id": obj_id})
    
    if not interview or str(interview.get("user_id")) != user_id_str:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
        
    return interview


def generate_questions(interview_id: str, user_id: str, question_count: int = 10) -> dict:
    """
    Generate questions using Gemini based on interview details and resume (if available).
    """
    if question_count < 1 or question_count > 20:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="question_count must be between 1 and 20")

    # 1. Fetch Interview Context
    interview = _get_interview_and_verify_ownership(interview_id, user_id)
    
    # 2. Fetch Resume Context (if linked)
    resume_text = ""
    resume_id = interview.get("resume_id")
    if resume_id:
        resume = resumes_collection.find_one({"_id": resume_id})
        if resume and str(resume.get("user_id")) == user_id:
            # Safely truncate resume text to prevent massive token usage
            extracted_text = resume.get("extracted_text", "")
            resume_text = extracted_text[:15000] # Safe upper limit for context
            
    # 3. Build Prompt
    system_prompt = INTERVIEW_QUESTION_SYSTEM_PROMPT.format(question_count=question_count)
    
    job_description = interview.get("job_description", "")
    if job_description:
        job_description = job_description[:5000] # Safe limit
        
    user_prompt = f"""
Please generate {question_count} interview questions.

--- CANDIDATE & INTERVIEW DETAILS ---
Role: {interview.get('role')}
Experience Level: {interview.get('experience_level')}
Skills: {', '.join(interview.get('skills', []))}
Interview Type: {interview.get('interview_type')}
Difficulty: {interview.get('difficulty')}
"""

    if job_description:
        user_prompt += f"\n--- JOB DESCRIPTION ---\n{job_description}\n"
        
    if resume_text:
        user_prompt += f"\n--- CANDIDATE RESUME TEXT ---\n{resume_text}\n"
        
    # 4. Call Gemini
    try:
        client = gemini_wrapper.get_client()
        model_name = gemini_wrapper.model_name
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI Service is currently unconfigured or unavailable")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=GeneratedQuestionList,
                temperature=0.7,
            ),
        )
    except Exception as e:
        # e.g., Rate limits (429) or backend errors
        error_msg = str(e)
        if "429" in error_msg:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="AI Service rate limit exceeded. Please try again later.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to communicate with AI Service.")

    # 5. Parse and Validate Response
    if not response.text:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Received empty response from AI Service.")
        
    try:
        parsed_data = json.loads(response.text)
        validated_data = GeneratedQuestionList(**parsed_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to validate structured AI response.")
        
    generated_questions = validated_data.questions

    # 6. Store in Database (Clean Regeneration Strategy)
    # Delete existing 'gemini' source questions to prevent arbitrary bloating
    questions_collection.delete_many({
        "interview_id": interview["_id"],
        "source": "gemini"
    })
    
    # We must properly sequence the new questions, accounting for any 'manual' questions that exist
    current_count = questions_collection.count_documents({"interview_id": interview["_id"]})
    
    db_questions = []
    now = utc_now()
    
    start_number = current_count + 1
    for idx, q in enumerate(generated_questions):
        doc = {
            "interview_id": interview["_id"],
            "question_number": start_number + idx,
            "question": q.question,
            "category": q.category,
            "difficulty": q.difficulty.value, # Extract enum string
            "source": "gemini",
            "created_at": now
        }
        db_questions.append(doc)
        
    if db_questions:
        result = questions_collection.insert_many(db_questions)
        # Prepare response
        for i, doc in enumerate(db_questions):
            doc["_id"] = result.inserted_ids[i]
            
    # Update interview's question count
    new_total = questions_collection.count_documents({"interview_id": interview["_id"]})
    interviews_collection.update_one(
        {"_id": interview["_id"]},
        {"$set": {"question_count": new_total, "updated_at": now}}
    )

    # Convert ObjectIds to strings for API response
    response_items = []
    for doc in db_questions:
        doc["id"] = str(doc.pop("_id"))
        doc["interview_id"] = str(doc.pop("interview_id"))
        response_items.append(doc)

    return {
        "interview_id": str(interview["_id"]),
        "count": len(response_items),
        "questions": response_items
    }
