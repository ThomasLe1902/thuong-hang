from fastapi import APIRouter, status, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from src.utils.logger import logger
from src.apis.interfaces.file_processing_interface import (
    FileProcessingBody,
    FileIngressResponse,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import TextLoader
import os
import tempfile
import shutil
import fitz
from docx import Document as DocxDoc
from src.config.vector_store import test_rag_vector_store
from src.config.mongo import bot_crud
from bson import ObjectId
from src.apis.middlewares.auth_middleware import get_current_user
from src.apis.models.user_models import User
from typing import Annotated
from pydantic import BaseModel, Field
from src.config.monitoring import (
    increment_request_count,
    observe_request_duration,
    increment_database_queries,
    increment_agent_calls,
    observe_agent_duration,
)
import time

router = APIRouter(prefix="/file", tags=["File Processing"])
user_dependency = Annotated[User, Depends(get_current_user)]


class FileIngressResponse(BaseModel):
    bot_id: str = Field(..., title="Bot ID associated with the file")
    file_path: str = Field(..., title="Path to the processed file")
    chunks_count: int = Field(..., title="Number of chunks created")
    success: bool = Field(..., title="Whether the ingestion was successful")
    message: str = Field(
        "File processed and indexed successfully", title="Status message"
    )


async def get_file_processing_body(bot_id: str = Form(...)):
    return FileProcessingBody(bot_id=bot_id)


@router.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
):
    try:
        start_time = time.time()
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_extension = os.path.splitext(file.filename)[1].lower()
        file_type = file_extension.replace(".", "").upper()
        word_count = 0
        image_count = 0
        if file_extension == ".pdf":
            doc = fitz.open(temp_file_path)
            for page in doc:
                text = page.get_text("text")
                word_count += len(text.split())
                image_count += len(page.get_images(full=True))
        elif file_extension == ".docx":
            doc = DocxDoc(temp_file_path)
            for para in doc.paragraphs:
                word_count += len(para.text.split())
            image_count = 0
            for rel in doc.part._rels.values():
                if "image" in rel.target_ref:
                    image_count += 1
        else:
            shutil.rmtree(temp_dir)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": f"Unsupported file type: {file_extension}"},
            )

        shutil.rmtree(temp_dir)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "file_path": file.filename,
                "word_count": word_count,
                "image_count": image_count,
                "file_type": file_type,
            },
        )

    except Exception as e:
        logger.error(f"Error analyzing file: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error analyzing file: {str(e)}"},
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_request_duration(
            agent_type="analyze_file",
            duration=duration,
        )


@router.post("/ingress", response_model=FileIngressResponse)
async def ingress_file(
    user: user_dependency,
    file: UploadFile = File(...),
    bot_id: str = Form(...),
):
    start_time = time.time()
    chatbot = await bot_crud.find_by_id(bot_id)
    if not chatbot:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Chatbot with id {bot_id} not found"},
        )
    if chatbot["user_id"] != user["id"]:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": f"You are not authorized to access this chatbot"},
        )
    try:
        logger.info(f"Processing and indexing file: {file.filename} for bot: {bot_id}")

        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)

        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if file.filename.endswith(".pdf"):
            loader = PyMuPDFLoader(temp_file_path)
        elif file.filename.endswith(".docx"):
            loader = Docx2txtLoader(temp_file_path)
        elif file.filename.endswith(".txt"):
            loader = TextLoader(temp_file_path)
        else:
            raise ValueError(f"Unsupported file format: {file.filename}")

        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)

        for chunk in chunks:
            chunk.metadata = {"bot_id": bot_id}

        test_rag_vector_store.add_documents(chunks)

        try:
            chatbot = await bot_crud.find_by_id(bot_id)
            if chatbot:
                tools = chatbot.get("tools", [])
                retrieve_document_exists = False
                for tool in tools:
                    if (
                        isinstance(tool, dict)
                        and tool.get("name") == "retrieve_document"
                    ):
                        retrieve_document_exists = True
                        break
                if not retrieve_document_exists:
                    tools.append("retrieve_document")
                    await bot_crud.update({"_id": ObjectId(bot_id)}, {"tools": tools})
                    logger.info(f"Added retrieve_document tool to chatbot {bot_id}")
        except Exception as e:
            logger.error(f"Error updating chatbot tools: {str(e)}")

        shutil.rmtree(temp_dir)
        chunks_count = len(chunks)

        return FileIngressResponse(
            bot_id=bot_id,
            file_path=file.filename,
            chunks_count=chunks_count,
            success=True,
            message=f"File processed and indexed successfully. Created {chunks_count} chunks.",
        )

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        increment_request_count(
            method="POST",
            endpoint="/file/ingress",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "bot_id": bot_id,
                "file_path": file.filename if file else "unknown",
                "chunks_count": 0,
                "success": False,
                "message": f"Error processing file: {str(e)}",
            },
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_request_duration(
            method="POST",
            endpoint="/file/ingress",
            duration=duration,
        )
        increment_request_count(
            method="POST",
            endpoint="/file/ingress",
            status_code=status.HTTP_200_OK,
        )
