from fastapi import APIRouter, status, Depends, UploadFile, Form
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Any
import json
import datetime
from bson import ObjectId
from langchain_core.messages.ai import AIMessageChunk
from src.apis.interfaces.chat_interface import RagAgentBody
from src.agents.rag_agent_template.flow import rag_agent_template_agent
from src.config.mongo import bot_crud
from src.utils.logger import logger
from src.apis.middlewares.auth_middleware import get_current_user
from src.apis.models.user_models import User
from typing import Annotated
from src.utils.helper import preprocess_messages
from src.config.llm import get_llm
import asyncio
from src.config.monitoring import (
    increment_request_count,
    observe_request_duration,
    increment_database_queries,
    increment_agent_calls,
    observe_agent_duration,
)
import time

router = APIRouter(prefix="/ai", tags=["AI"])
user_dependency = Annotated[User, Depends(get_current_user)]


async def message_generator(input_graph: dict, config: dict):
    last_output_state = None
    async for event in rag_agent_template_agent.astream(
        input=input_graph,
        stream_mode=["messages", "values"],
        config=config,
    ):
        event_type, event_message = event
        if event_type == "messages":
            message, metadata = event_message
            if isinstance(message, AIMessageChunk) and metadata["langgraph_node"] in [
                "generate_answer"
            ]:
                for char in message.content:
                    yield json.dumps(
                        {
                            "type": "message",
                            "content": char,
                        },
                        ensure_ascii=False,
                    ) + "\n\n"
                    await asyncio.sleep(0.001)  # Small delay for smooth streaming
        if event_type == "values":
            last_output_state = event_message

    if last_output_state is None:
        raise ValueError("No output state received from workflow")

    if "messages" not in last_output_state:
        raise ValueError("No LLM response in output")

    final_response = json.dumps(
        {
            "type": "final",
            "content": {
                "final_response": last_output_state["messages"][-1].content,
                "selected_ids": last_output_state.get("selected_ids", []),
                "selected_documents": last_output_state.get("selected_documents", []),
            },
        },
        ensure_ascii=False,
    )
    yield final_response + "\n\n"


class RagAgentBody(BaseModel):
    query: dict = Field(..., title="User's query message in role-based format")
    bot_id: Optional[str] = Field(None, title="Bot ID")
    conversation_id: Optional[str] = Field(None, title="Conversation ID")
    model_name: Optional[str] = Field(None, title="Model name to use")
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hình này là ở đâu vậy?"},
                    ],
                },
                "bot_id": "68357639f549b5ec217097c6",
                "conversation_id": "1",
                "model_name": "gemini-2.0-flash",
            }
        }
    }


@router.post("/rag_agent_template/stream")
async def rag_agent_template_stream(
    query: str = Form(...),
    bot_id: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    attachs: List[UploadFile] = [],
    api_key: Optional[str] = Form(None),
    reasoning: Optional[bool] = Form(False),
    user: user_dependency = None,
):
    try:
        logger.info(f"user mail: {user['email']}")

        start_time = time.time()
        tools = []
        if not bot_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Bot ID is required"},
            )
        data = await bot_crud.read_one({"_id": ObjectId(bot_id)})
        if not data or not data["prompt"]:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Bot not found"},
            )
        if data["public"] == False:
            if data["user_id"] != user["id"]:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "You are not authorized to access this chatbot"},
                )

        prompt = data["prompt"]
        tools = data["tools"]

        messages = await preprocess_messages(query, attachs)

        config = {
            "configurable": {
                "thread_id": conversation_id if conversation_id else "1",
                "bot_id": bot_id,
                "model_name": model_name,
                "api_key": api_key,
                "reasoning": reasoning,
            }
        }
        input_graph = {
            "messages": messages,
            "prompt": prompt,
            "tools": tools,
        }

        return StreamingResponse(
            message_generator(
                input_graph=input_graph,
                config=config,
            ),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"Error in streaming endpoint: {str(e)}")
        increment_agent_calls("rag_agent_template", status="error")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Streaming error: {str(e)}"},
        )
    finally:
        increment_agent_calls("rag_agent_template", status="success")
        end_time = time.time()
        duration = end_time - start_time
        observe_agent_duration(
            agent_type="rag_agent_template",
            duration=duration,
        )


class ChatbotDetailResponse(BaseModel):
    id: str
    name: str
    prompt: str
    tools: List[Any] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatbotUpdateRequest(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    tools: Optional[List[Any]] = None
    public: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Updated Chatbot Name",
                "prompt": "You are a helpful assistant specialized in travel advice.",
                "tools": [],
                "public": False,
            }
        }
    }


@router.get("/chatbots")
async def list_chatbots(user: user_dependency):
    start_time = time.time()
    increment_database_queries(
        operation="read",
        collection="chatbots",
    )
    # logger.info(f"User: {user}")
    try:
        chatbots = await bot_crud.read(
            {"user_id": user["id"]},
            sort=[("created_at", -1)],  # Sort by created_at in descending order
        )
        for bot in chatbots:
            if "_id" in bot:
                bot["id"] = str(bot.pop("_id"))

            if "created_at" in bot and isinstance(bot["created_at"], datetime.datetime):
                bot["created_at"] = bot["created_at"].isoformat()

            if "updated_at" in bot and isinstance(bot["updated_at"], datetime.datetime):
                bot["updated_at"] = bot["updated_at"].isoformat()

            if "expire_at" in bot and isinstance(bot["expire_at"], datetime.datetime):
                bot["expire_at"] = bot["expire_at"].isoformat()

        logger.info(f"Retrieved {len(chatbots)} chatbots")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"chatbots": chatbots},
        )

    except Exception as e:
        logger.error(f"Error retrieving chatbots: {str(e)}")
        increment_request_count(
            method="GET",
            endpoint="/chatbots",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to retrieve chatbots: {str(e)}"},
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_request_duration(
            method="GET",
            endpoint="/chatbots",
            duration=duration,
        )
        increment_request_count(
            method="GET",
            endpoint="/chatbots",
            status_code=status.HTTP_200_OK,
        )


@router.get("/chatbots/public")
async def list_chatbots_public():

    try:
        start_time = time.time()
        increment_database_queries(
            operation="read",
            collection="chatbots",
        )
        chatbots = await bot_crud.read(
            {"public": True},
            sort=[("created_at", -1)],  # Sort by created_at in descending order
        )
        for bot in chatbots:
            if "_id" in bot:
                bot["id"] = str(bot.pop("_id"))

            if "created_at" in bot and isinstance(bot["created_at"], datetime.datetime):
                bot["created_at"] = bot["created_at"].isoformat()

            if "updated_at" in bot and isinstance(bot["updated_at"], datetime.datetime):
                bot["updated_at"] = bot["updated_at"].isoformat()

            if "expire_at" in bot and isinstance(bot["expire_at"], datetime.datetime):
                bot["expire_at"] = bot["expire_at"].isoformat()

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"chatbots": chatbots}
        )
    except Exception as e:
        logger.error(f"Error retrieving public chatbots: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to retrieve public chatbots: {str(e)}"},
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_request_duration(
            method="GET",
            endpoint="/chatbots/public",
            duration=duration,
        )


@router.get("/chatbots/{chatbot_id}", response_model=ChatbotDetailResponse)
async def get_chatbot_detail(chatbot_id: str):
    start_time = time.time()
    increment_database_queries(
        operation="read",
        collection="chatbots",
    )
    try:
        chatbot = await bot_crud.find_by_id(chatbot_id)
        if not chatbot:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": f"Chatbot with ID {chatbot_id} not found"},
            )

        if "_id" in chatbot:
            chatbot["id"] = str(chatbot.pop("_id"))

        if "created_at" in chatbot and isinstance(
            chatbot["created_at"], datetime.datetime
        ):
            chatbot["created_at"] = chatbot["created_at"].isoformat()

        if "updated_at" in chatbot and isinstance(
            chatbot["updated_at"], datetime.datetime
        ):
            chatbot["updated_at"] = chatbot["updated_at"].isoformat()

        if "expire_at" in chatbot and isinstance(
            chatbot["expire_at"], datetime.datetime
        ):
            chatbot["expire_at"] = chatbot["expire_at"].isoformat()

        logger.info(f"Retrieved chatbot details for ID: {chatbot_id}")
        return chatbot

    except Exception as e:
        logger.error(f"Error retrieving chatbot details: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to retrieve chatbots: {str(e)}"},
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_request_duration(
            method="GET",
            endpoint=f"/chatbots/{chatbot_id}",
            duration=duration,
        )


class ChatbotCreateRequest(BaseModel):
    name: str
    prompt: str
    tools: List[Any] = []
    public: bool = False


@router.post("/chatbots/create")
async def create_chatbot(body: ChatbotCreateRequest, user: user_dependency):
    start_time = time.time()
    increment_database_queries(
        operation="create",
        collection="chatbots",
    )
    try:
        bot_id = await bot_crud.create(
            {
                "name": body.name,
                "prompt": body.prompt,
                "tools": body.tools,
                "public": body.public,
                "user_id": user["id"],
            }
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"bot_id": bot_id},
        )
    except Exception as e:
        logger.error(f"Error creating chatbot: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to create chatbot: {str(e)}"},
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_request_duration(
            method="POST",
            endpoint="/chatbots/create",
            duration=duration,
        )


@router.put("/chatbots/{chatbot_id}", response_model=ChatbotDetailResponse)
async def update_chatbot(
    chatbot_id: str, update_data: ChatbotUpdateRequest, user: user_dependency
):
    start_time = time.time()
    increment_database_queries(
        operation="update",
        collection="chatbots",
    )
    try:
        existing_chatbot = await bot_crud.read_one(
            {"_id": ObjectId(chatbot_id), "user_id": user["id"]}
        )

        if not existing_chatbot:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": f"Chatbot with ID {chatbot_id} not found"},
            )

        update_fields = {}
        if update_data.name is not None:
            update_fields["name"] = update_data.name
        if update_data.prompt is not None:
            update_fields["prompt"] = update_data.prompt
        if update_data.tools is not None:
            update_fields["tools"] = update_data.tools
        if update_data.public is not None:
            update_fields["public"] = update_data.public

        update_fields["updated_at"] = datetime.datetime.now()

        updated = await bot_crud.update({"_id": ObjectId(chatbot_id)}, update_fields)

        if not updated:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Failed to update chatbot"},
            )

        updated_chatbot = await bot_crud.find_by_id(chatbot_id)
        if "_id" in updated_chatbot:
            updated_chatbot["id"] = str(updated_chatbot.pop("_id"))
        if "created_at" in updated_chatbot and isinstance(
            updated_chatbot["created_at"], datetime.datetime
        ):
            updated_chatbot["created_at"] = updated_chatbot["created_at"].isoformat()
        if "updated_at" in updated_chatbot and isinstance(
            updated_chatbot["updated_at"], datetime.datetime
        ):
            updated_chatbot["updated_at"] = updated_chatbot["updated_at"].isoformat()
        if "expire_at" in updated_chatbot and isinstance(
            updated_chatbot["expire_at"], datetime.datetime
        ):
            updated_chatbot["expire_at"] = updated_chatbot["expire_at"].isoformat()
        logger.info(f"Updated chatbot with ID: {chatbot_id}")
        return updated_chatbot

    except Exception as e:
        logger.error(f"Error updating chatbot: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to update chatbot: {str(e)}"},
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_request_duration(
            method="PUT",
            endpoint=f"/chatbots/{chatbot_id}",
            duration=duration,
        )


@router.delete("/chatbots/{chatbot_id}")
async def delete_chatbot(chatbot_id: str, user: user_dependency):
    start_time = time.time()
    increment_database_queries(
        operation="delete",
        collection="chatbots",
    )
    try:
        existing_chatbot = await bot_crud.read_one(
            {"_id": ObjectId(chatbot_id), "user_id": user["id"]}
        )

        if not existing_chatbot:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": f"Chatbot with ID {chatbot_id} not found"},
            )

        deleted = await bot_crud.delete_one({"_id": ObjectId(chatbot_id)})

        if not deleted:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Failed to delete chatbot"},
            )

        logger.info(f"Deleted chatbot with ID: {chatbot_id}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Chatbot deleted successfully"},
        )

    except Exception as e:
        logger.error(f"Error deleting chatbot: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to delete chatbot: {str(e)}"},
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_request_duration(
            method="DELETE",
            endpoint=f"/chatbots/{chatbot_id}",
            duration=duration,
        )


@router.post("/test_gemini_api_key")
async def test_gemini_api_key(api_key: str = Form(...), model_name: str = Form(...)):
    try:
        llm = get_llm(model_name, api_key, include_thoughts=False)
        llm_response = await llm.ainvoke(
            "1 + 1 = ?. Chỉ trả lời đáp án, không có gì khác"
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": llm_response.content},
        )
    except Exception as e:
        logger.error(f"Error testing Gemini API key: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to test Gemini API key: {str(e)}"},
        )
