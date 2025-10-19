from src.config.vector_store import test_rag_vector_store as vector_store
from typing import Optional, List
from fastapi import APIRouter, Query, Depends
from langchain_core.documents import Document
from src.apis.middlewares.auth_middleware import get_current_user
from src.apis.models.user_models import User
from typing import Annotated
from fastapi.responses import JSONResponse
from fastapi import status
from src.config.mongo import bot_crud
from bson import ObjectId
from pydantic import Field, BaseModel

router = APIRouter(prefix="/vector-store", tags=["Vector Store"])
user_dependency = Annotated[User, Depends(get_current_user)]


@router.get("/get-documents")
async def get_documents(user: user_dependency, bot_id: Optional[str] = None):
    chatbot = await bot_crud.read_one({"_id": ObjectId(bot_id), "user_id": user["id"]})
    if not chatbot:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Chatbot with id {bot_id} not found"},
        )

    documents = await vector_store.asimilarity_search(
        "", 10000, filter={"bot_id": bot_id}
    )
    return [doc.__dict__ for doc in documents]


class AddDocumentsRequest(BaseModel):
    ids: List[str] = Field(..., description="The IDs of the documents")
    documents: List[Document] = Field(..., description="The documents")
    bot_id: str = Field(..., description="The ID of the chatbot")


@router.post("/add-documents")
async def add_documents(
    user: user_dependency,
    body: AddDocumentsRequest,
):
    chatbot = await bot_crud.read_one(
        {"_id": ObjectId(body.bot_id), "user_id": user["id"]}
    )
    if not chatbot:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Chatbot with id {body.bot_id} not found"},
        )
    return await vector_store.aadd_documents(body.documents, ids=body.ids)


@router.delete("/delete-documents")
async def delete_documents(
    user: user_dependency, bot_id: Optional[str] = None, ids: List[str] = Query(None)
):
    chatbot = await bot_crud.read_one({"_id": ObjectId(bot_id), "user_id": user["id"]})
    if not chatbot:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Chatbot with id {bot_id} not found"},
        )
    document_data = await vector_store.asimilarity_search(
        "", 10000, filter={"bot_id": bot_id}
    )
    document_ids = [doc.id for doc in document_data]
    if not ids:
        ids = document_ids
    delete_ids = [id for id in ids if id in document_ids]
    return await vector_store.adelete(ids=delete_ids)
