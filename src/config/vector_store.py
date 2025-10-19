from .llm import embeddings
import os
from langchain_pinecone import PineconeVectorStore
from pydantic import BaseModel
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

API_PINCONE_KEY = os.getenv("PINECONE_API_KEY")

test_rag_vector_store = PineconeVectorStore(
    index_name="rag-vector-store",
    embedding=embeddings,
    pinecone_api_key=API_PINCONE_KEY,
)


class PineconeVectorStoreCRUD(BaseModel):
    index_name: str
    embedding: GoogleGenerativeAIEmbeddings
    pinecone_api_key: str

    def __init__(
        self,
        index_name: str,
        embedding: GoogleGenerativeAIEmbeddings,
        pinecone_api_key: str,
        k: int = 5,
        score_threshold: float = 0.3,
    ) -> VectorStore:
        self.vector_store = PineconeVectorStore(
            index_name=index_name,
            embedding=embedding,
            pinecone_api_key=pinecone_api_key,
        )
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": k, "score_threshold": score_threshold},
        )

    async def search(self, query: str, filter: Optional[Dict[str, Any]] = None):
        return await self.retriever.ainvoke(query, filter=filter)

    async def add_documents(self, documents: List[Document], ids: List[str]):
        await self.vector_store.aadd_documents(documents, ids=ids)

    async def get_documents(self, filter: Optional[Dict[str, Any]] = None):
        return await self.vector_store.asimilarity_search("", filter=filter)

    async def delete_documents(self, ids: List[str]):
        await self.vector_store.adelete(ids=ids)

    async def update_documents(self, documents: List[Document], ids: List[str]):
        await self.vector_store.aadd_documents(documents, ids=ids)


test_rag_vector_store = PineconeVectorStore(
    index_name="rag-vector-store",
    embedding=embeddings,
    pinecone_api_key=API_PINCONE_KEY,
)
