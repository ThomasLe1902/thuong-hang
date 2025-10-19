from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from src.apis.middlewares.auth_middleware import get_current_user
from src.apis.models.user_models import User
from src.apis.models.grade_models import GradedAssignment
from src.config.mongo import GradedAssignmentCRUD
from typing import Annotated
from datetime import datetime
from bson import ObjectId
from fastapi.responses import JSONResponse
import os
from src.agents.grade_assignment.grade.flow import grade_agent
from src.agents.grade_assignment.gen_answer.prompt import chain_gen_answer

router = APIRouter(prefix="/graded-assignments", tags=["Graded Assignments"])
user_dependency = Annotated[User, Depends(get_current_user)]


class AnalyzeCodeResult(BaseModel):
    file_name: str
    comment: str
    criteria_eval: str
    rating: int


class GradeResultItem(BaseModel):
    selected_files: List[str]
    criterias: str
    project_description: str
    analyze_code_result: Optional[List[AnalyzeCodeResult]] = []
    criteria_index: int


class GradedAssignmentResponse(BaseModel):
    id: str
    user_id: str
    project_name: str
    selected_files: List[str]
    folder_structure_criteria: Optional[str]
    criterias_list: List[str]
    project_description: str
    grade_result: List[GradeResultItem]
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


@router.get("/", response_model=List[GradedAssignmentResponse])
async def get_user_assignments(user: user_dependency):
    """Get all graded assignments for the current user"""
    assignments = await GradedAssignmentCRUD.read({"user_id": user["id"]})
    for assignment in assignments:
        assignment["id"] = str(assignment["_id"])
        assignment["created_at"] = assignment["created_at"].isoformat()
        assignment["updated_at"] = assignment["updated_at"].isoformat()
    return assignments


@router.get("/{assignment_id}", response_model=GradedAssignmentResponse)
async def get_assignment(assignment_id: str, user: user_dependency):
    """Get a specific graded assignment by ID"""
    assignment = await GradedAssignmentCRUD.find_by_id(assignment_id)
    if not assignment or assignment["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment["id"] = str(assignment["_id"])
    assignment["created_at"] = assignment["created_at"].isoformat()
    assignment["updated_at"] = assignment["updated_at"].isoformat()
    return assignment


@router.delete("/{assignment_id}")
async def delete_assignment(assignment_id: str, user: user_dependency):
    """Delete a graded assignment"""
    assignment = await GradedAssignmentCRUD.find_by_id(assignment_id)
    if not assignment or assignment["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Assignment not found")

    deleted = await GradedAssignmentCRUD.delete_one({"_id": ObjectId(assignment_id)})
    if deleted:
        return {"message": "Assignment deleted successfully"}
    raise HTTPException(status_code=500, detail="Failed to delete assignment")


from src.agents.grade_assignment.assignment_extractor.func import (
    extract_text_from_images,
    split_question,
)


@router.post("/extract-text-from-images")
async def extract_text_endpoint(images: List[UploadFile] = File(...)):
    """
    API endpoint để trích xuất văn bản từ danh sách hình ảnh

    Args:
        images: Danh sách các file hình ảnh (jpg, png, etc.)

    Returns:
        JSON response chứa văn bản đã trích xuất
    """
    # Kiểm tra input
    if not images:
        raise HTTPException(
            status_code=400, detail="Vui lòng cung cấp ít nhất một hình ảnh"
        )

    # Kiểm tra định dạng file
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    for image in images:
        file_extension = os.path.splitext(image.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File {image.filename} không được hỗ trợ. Chỉ chấp nhận: {', '.join(allowed_extensions)}",
            )

    try:
        # Trích xuất văn bản
        extracted_text, split_questions, saved_image_path = (
            await extract_text_from_images(images)
        )

        return JSONResponse(
            content={
                "success": True,
                "message": "Trích xuất văn bản thành công",
                "data": {
                    "extracted_text": extracted_text,
                    "split_questions": split_questions,
                    "total_images": len(images),
                    "image_names": [img.filename for img in images],
                    "saved_combined_image": saved_image_path,
                },
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi không xác định: {str(e)}")


@router.post("/grade-assignment")
async def grade_assignment(
    assignment_questions: List[str], files: List[UploadFile] = File(...)
):
    """
    API endpoint để chấm điểm bài tập đã nộp

    Args:
        body: Chứa danh sách câu hỏi và nội dung code

    Returns:
        JSON response chứa kết quả chấm điểm
    """
    # Gọi flow chấm điểm
    result = await grade_agent.abatch(
        [
            {
                "code_content": await files[i].read(),
                "exercise_question": assignment_questions[i],
            }
            for i in range(len(files))
        ]
    )
    result = [res["final_result"] for res in result]

    return JSONResponse(content=result)


class GenerateAnswerRequest(BaseModel):
    exercise_questions: list[str] = Field(..., description="Danh sách câu hỏi bài tập")


@router.post("/generate-answer")
async def generate_answer(request: GenerateAnswerRequest):
    """
    API endpoint to generate an answer for a given exercise question

    Args:
        exercise_question: The question for which the answer is to be generated
        user_input: Additional user input that may influence the answer

    Returns:
        JSON response containing the generated answer and reasoning
    """
    # try:
    result = await chain_gen_answer.abatch(
        [{"exercise_question": question} for question in request.exercise_questions]
    )
    return JSONResponse(
        content=[
            {
                "answer": res.answer,
                "reasoning": res.reasoning,
                "exercise_question": request.exercise_questions[i],
            }
            for i, res in enumerate(result)
            if res is not None
        ]
    )
