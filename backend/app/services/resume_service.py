"""
app/services/resume_service.py

Business logic for managing resumes in MongoDB.
"""

from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from app.models.resume import resumes_collection


def create_resume(
    user_id: str,
    filename: str,
    file_type: str,
    file_size: int,
    extracted_text: str
) -> dict:
    """
    Store resume metadata and extracted text in MongoDB.
    """
    now = datetime.now(timezone.utc)
    resume_doc = {
        "user_id": user_id,  # store as string since users.py auth might be using str, or ObjectId depending on setup. Let's assume auth passed it correctly.
        "filename": filename,
        "file_type": file_type,
        "file_size": file_size,
        "extracted_text": extracted_text,
        "text_length": len(extracted_text),
        "created_at": now,
        "updated_at": now
    }
    
    result = resumes_collection.insert_one(resume_doc)
    resume_doc["_id"] = str(result.inserted_id)
    return resume_doc


def get_user_resumes(user_id: str, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
    """
    Retrieve a paginated list of resumes for a specific user.
    """
    skip = (page - 1) * limit
    
    # Query for the user's resumes
    query = {"user_id": user_id}
    
    # Total count
    total = resumes_collection.count_documents(query)
    
    # Fetch paginated documents, newest first
    cursor = resumes_collection.find(query, {"extracted_text": 0}) \
        .sort("created_at", -1) \
        .skip(skip) \
        .limit(limit)
        
    resumes = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        resumes.append(doc)
        
    return resumes, total


def get_resume(resume_id: str, user_id: str) -> dict | None:
    """
    Retrieve a specific resume by ID, ensuring it belongs to the user.
    """
    try:
        obj_id = ObjectId(resume_id)
    except InvalidId:
        return None
        
    doc = resumes_collection.find_one({"_id": obj_id, "user_id": user_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


def delete_resume(resume_id: str, user_id: str) -> bool:
    """
    Delete a specific resume by ID, ensuring it belongs to the user.
    """
    try:
        obj_id = ObjectId(resume_id)
    except InvalidId:
        return False
        
    result = resumes_collection.delete_one({"_id": obj_id, "user_id": user_id})
    return result.deleted_count > 0
