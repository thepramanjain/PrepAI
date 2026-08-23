"""
app/routes/resume.py

API routes for managing resumes and extracting text.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from app.auth.dependencies import get_current_user
from app.schemas.resume import ResumeResponse, ResumeDetailResponse, ResumeListResponse
from app.services import resume_service
from app.utils.resume_parser import extract_text_from_pdf, extract_text_from_docx
import logging

router = APIRouter(
    prefix="/api/resumes",
    tags=["Resumes"],
    responses={401: {"description": "Unauthorized"}},
)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a resume (PDF or DOCX). Extracts text and stores metadata in MongoDB.
    Max file size is 5MB.
    """
    user_id = str(current_user["_id"])
    
    # 1. Validate file extension/type
    filename = file.filename or ""
    filename_lower = filename.lower()
    
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".docx")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only .pdf and .docx are allowed."
        )
        
    # 2. Read file and validate size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large. Maximum size is 5MB."
        )
        
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty."
        )

    # 3. Extract text based on file type
    try:
        if filename_lower.endswith(".pdf"):
            file_type = "pdf"
            extracted_text = extract_text_from_pdf(file_bytes)
        else:
            file_type = "docx"
            extracted_text = extract_text_from_docx(file_bytes)
    except Exception as e:
        logging.error(f"Error parsing resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the document. Ensure it is a valid PDF or DOCX file."
        )
        
    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract any text from the document."
        )

    # 4. Store in database
    resume_doc = resume_service.create_resume(
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        extracted_text=extracted_text
    )
    
    return resume_doc


@router.get("", response_model=ResumeListResponse)
def list_resumes(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    List all resumes for the authenticated user (paginated).
    """
    user_id = str(current_user["_id"])
    resumes, total = resume_service.get_user_resumes(user_id=user_id, page=page, limit=limit)
    
    return {
        "resumes": resumes,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific resume by ID, including its extracted text.
    """
    user_id = str(current_user["_id"])
    resume_doc = resume_service.get_resume(resume_id, user_id)
    
    if not resume_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found."
        )
        
    return resume_doc


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a specific resume by ID.
    """
    user_id = str(current_user["_id"])
    success = resume_service.delete_resume(resume_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found."
        )
