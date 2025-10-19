from dotenv import load_dotenv

load_dotenv(override=True)
from typing import List, Any, Optional
import os
import tempfile
import shutil
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.responses import JSONResponse, StreamingResponse
from src.utils.helper import (
    list_code_files_in_repository,
    create_file_tree,
    filter_file_paths,
    build_tree,
    read_file,
)
from src.agents.grade_code_quality.func import (
    project_description_generator,
    summarize_code_review_controller,
)
from src.config.llm import get_llm
from src.agents.grade_code_quality.prompt import grade_code_quality_chain
from pydantic import BaseModel, Field
from src.agents.grade_code_quality.flow import grade_streaming_fn
from src.config.constants import SUPPORTED_EXTENSIONS
from src.apis.middlewares.auth_middleware import get_current_user
from src.apis.models.user_models import User
from typing import Annotated
from langchain_core.messages import AIMessage

# Configuration
MAX_TOTAL_SIZE = 2 * 1024 * 1024  # 2MB total size limit for uploads
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per individual file


def get_directory_size(directory_path: str) -> int:
    """Calculate total size of directory in bytes"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
    except Exception as e:
        print(f"Error calculating directory size: {e}")
        return float("inf")  # Return large value to trigger size limit
    return total_size


def validate_upload_size(files: List[UploadFile]) -> tuple[bool, int]:
    """Validate total size of uploaded files"""
    total_size = 0
    for file in files:
        if hasattr(file, "size") and file.size:
            total_size += file.size
        else:
            # If size is not available, we'll check during read
            return True, 0  # Let it proceed, check during processing
    return total_size <= MAX_TOTAL_SIZE, total_size


def process_uploaded_files(files: List[UploadFile], extensions: List[str]) -> List[str]:
    """
    Process uploaded files and save them to the repo directory for grading

    Args:
        files: List of uploaded files
        extensions: List of allowed file extensions

    Returns:
        List of file paths relative to repo directory
    """
    from src.utils.helper import REPO_FOLDER

    # Create upload subdirectory similar to cloned repos
    upload_folder = os.path.join(REPO_FOLDER, "uploaded_project")

    # Clean and recreate upload directory
    if os.path.exists(upload_folder):
        shutil.rmtree(upload_folder)
    os.makedirs(upload_folder, exist_ok=True)

    try:
        total_size = 0
        file_paths = []

        for file in files:
            # Read file content
            content = file.file.read()
            file.file.seek(0)  # Reset file pointer

            # Check individual file size
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} exceeds individual size limit ({MAX_FILE_SIZE / 1024 / 1024:.2f}MB)",
                )

            total_size += len(content)

            # Check if file extension is allowed
            if extensions:
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in extensions:
                    continue

            # Create file path in upload directory maintaining directory structure
            file_path = os.path.join(upload_folder, file.filename)

            # Create directories if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write file
            with open(file_path, "wb") as f:
                f.write(content)

            # Store path relative to upload folder for consistency with cloned repos
            file_paths.append(os.path.join("uploaded_project", file.filename))

        # Check total size limit
        if total_size > MAX_TOTAL_SIZE:
            # Clean up on size limit exceeded
            try:
                if os.path.exists(upload_folder):
                    shutil.rmtree(upload_folder)
            except:
                pass  # Ignore cleanup errors
            raise HTTPException(
                status_code=400,
                detail=f"Total upload size ({total_size / 1024 / 1024:.2f}MB) exceeds limit ({MAX_TOTAL_SIZE / 1024 / 1024:.2f}MB)",
            )

        return file_paths

    except Exception as e:
        # Clean up on any error
        try:
            if os.path.exists(upload_folder):
                shutil.rmtree(upload_folder)
        except:
            pass  # Ignore cleanup errors
        raise e


class ProjectDescription(BaseModel):
    selected_files: List[str] = Field("None")
    api_key: Optional[str] = Field(None, description="API key")


router = APIRouter(prefix="/grade-code", tags=["Grade Code"])
user_dependency = Annotated[User, Depends(get_current_user)]


@router.post("/project-description-generation", status_code=200)
async def project_description_generation(body: ProjectDescription):
    try:
        file_paths = filter_file_paths(body.selected_files)
        file_tree = build_tree(file_paths)
        response: AIMessage = await grade_code_quality_chain(
            get_llm(api_key=body.api_key)
        )["project_description_generator"].ainvoke({"file_tree": file_tree})
        return JSONResponse(content=response.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read-code-content", status_code=200)
def read_code_content_route(file_path: str):
    content = read_file(file_path)
    return JSONResponse(content=content)


class RepoURL(BaseModel):
    url: str
    extensions: List[str] = SUPPORTED_EXTENSIONS


@router.post("/get-file-tree", status_code=200)
async def get_file_tree(repo: RepoURL):
    try:
        code_files = list_code_files_in_repository(
            repo.url, repo.extensions, 2
        )  # Changed to 2MB limit
        file_tree = create_file_tree(code_files)
        return {"file_tree": file_tree}
    except ValueError as e:
        # Handle repository size limit exceeded
        raise HTTPException(status_code=413, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-file-tree-upload", status_code=200)
async def get_file_tree_upload(
    files: List[UploadFile] = File(...),
    extensions: List[str] = Form(default=SUPPORTED_EXTENSIONS),
):
    """
    Get file tree from uploaded files

    - files: Multiple files maintaining folder structure
    - extensions: List of allowed file extensions
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    try:
        # Process uploaded files
        file_paths = process_uploaded_files(files, extensions)

        if not file_paths:
            raise HTTPException(
                status_code=400,
                detail="No valid files found with the specified extensions",
            )

        # Create file tree from uploaded files
        file_tree = create_file_tree(file_paths)

        return {"file_tree": file_tree, "file_count": len(file_paths)}

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-file-tree-unified", status_code=200)
async def get_file_tree_unified(
    repo_url: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    extensions: List[str] = Form(default=SUPPORTED_EXTENSIONS),
):
    """
    Unified endpoint to get file tree from either repository URL or uploaded files

    - repo_url: GitHub repository URL (optional)
    - files: Multiple uploaded files (optional)
    - extensions: List of allowed file extensions

    Note: Provide either repo_url OR files, not both
    """
    # Validate input: either repo_url or files must be provided, but not both
    if not repo_url and not files:
        raise HTTPException(
            status_code=400, detail="Either repo_url or files must be provided"
        )
    if repo_url and files:
        raise HTTPException(
            status_code=400, detail="Provide either repo_url or files, not both"
        )

    try:
        if repo_url:
            # Handle repository URL
            code_files = list_code_files_in_repository(
                repo_url, extensions, 2
            )  # 2MB limit
            file_tree = create_file_tree(code_files)
            return {"file_tree": file_tree, "source": "repository", "url": repo_url}
        else:
            # Handle file uploads
            file_paths = process_uploaded_files(files, extensions)

            if not file_paths:
                raise HTTPException(
                    status_code=400,
                    detail="No valid files found with the specified extensions",
                )

            file_tree = create_file_tree(file_paths)

            return {
                "file_tree": file_tree,
                "source": "upload",
                "file_count": len(file_paths),
            }

    except ValueError as e:
        # Handle repository size limit exceeded
        raise HTTPException(status_code=413, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup-upload", status_code=200)
async def cleanup_upload():
    """
    Clean up uploaded files from the repo directory
    """
    try:
        from src.utils.helper import REPO_FOLDER

        upload_folder = os.path.join(REPO_FOLDER, "uploaded_project")
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)
        return {"message": "Upload files cleaned up successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up: {str(e)}")


class GradeCodeRequest(BaseModel):
    selected_files: List[str]
    folder_structure_criteria: str = Field(
        None, description="Folder structure criteria"
    )
    criterias_list: List[str]
    project_description: str = Field(None, description="Project description")
    api_key: Optional[str] = Field(None, description="API key")


# @router.post("/grade", status_code=200)
# async def grade(body: GradeCodeRequest):
#     file_paths = filter_file_paths(body.selected_files)

#     if not file_paths:
#         raise HTTPException(
#             status_code=400,
#             detail="No valid files selected. Please select at least one file to grade.",
#         )
#     output = await grade_code(
#         file_paths,
#         body.criterias_list,
#         body.project_description,
#     )
#     return JSONResponse(content=output)


@router.post("/grade-stream", status_code=200)
async def grade_code_stream(body: GradeCodeRequest, user: user_dependency):
    folder_file_paths = body.selected_files[0].split("/")[0]
    file_paths = filter_file_paths(body.selected_files)
    if not file_paths:
        return JSONResponse(content="Not have any files path", status_code=404)
    llm = get_llm("gemini-2.0-flash-lite", api_key=body.api_key)

    return StreamingResponse(
        grade_streaming_fn(
            llm,
            file_paths,
            body.folder_structure_criteria,
            body.criterias_list,
            body.project_description,
            user["id"],
            folder_file_paths,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class GradeOverallInterface(BaseModel):
    data: Any


@router.post("/grade-overall", status_code=200)
async def grade_overall(body: GradeOverallInterface):
    llm = get_llm("gemini-2.0-flash")
    response = await summarize_code_review_controller(body.data, llm)
    return JSONResponse(content=response)
