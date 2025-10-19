from fastapi import APIRouter, status, Depends, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.runnables import RunnableConfig
import json
from langchain_core.messages.ai import AIMessageChunk
from src.utils.logger import logger
from src.agents.custom_chatbot.flow import custom_chatbot
from src.agents.update_custom_chatbot.flow import update_custom_chatbot
from src.apis.middlewares.auth_middleware import get_current_user
from src.apis.models.user_models import User
from typing import Annotated, List, Optional, Literal
from src.utils.helper import preprocess_messages
from src.config.mongo import bot_crud
from bson import ObjectId
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


async def message_generator(
    input_graph: dict, config: RunnableConfig, type: Literal["create", "update"]
):
    try:
        last_output_state = None

        try:
            async for event in (update_custom_chatbot).astream(
                input=input_graph, stream_mode=["messages", "values"], config=config
            ):
                try:
                    event_type, event_message = event
                    if event_type == "messages":
                        message, metadata = event_message

                        if (
                            isinstance(message, AIMessageChunk)
                            and metadata.get("langgraph_node") == "execute_tool"
                        ):
                            yield json.dumps(
                                {
                                    "type": "tools_message",
                                    "content": message.content,
                                    "metadata": {
                                        "node": metadata.get("langgraph_node"),
                                        "step": metadata.get("langgraph_step"),
                                        "checkpoint_ns": metadata.get(
                                            "checkpoint_ns", ""
                                        ),
                                    },
                                },
                                ensure_ascii=False,
                            ) + "\n\n"

                        elif isinstance(message, AIMessageChunk) and metadata[
                            "langgraph_node"
                        ] in ["generate_answer"]:
                            for char in message.content:
                                yield json.dumps(
                                    {
                                        "type": "message",
                                        "content": char,
                                    },
                                    ensure_ascii=False,
                                ) + "\n\n"
                                await asyncio.sleep(0.001)

                    if event_type == "values":
                        last_output_state = event_message
                except Exception as e:
                    logger.error(f"Error processing stream event: {str(e)}")
                    yield json.dumps(
                        {
                            "type": "error",
                            "content": "Error processing response " + str(e),
                        },
                        ensure_ascii=False,
                    ) + "\n\n"
                    return

            if last_output_state is None:
                raise ValueError("No output state received from workflow")

            try:
                final_response = json.dumps(
                    {
                        "type": "final",
                        "content": {
                            "final_response": last_output_state["messages"][-1].content,
                            "done": last_output_state.get("done", False),
                        },
                    },
                    ensure_ascii=False,
                )
                yield final_response + "\n\n"
            except Exception as e:
                logger.error(f"Error processing final response: {str(e)}")
                yield json.dumps(
                    {
                        "type": "error",
                        "content": "Error processing the final response" + str(e),
                    },
                    ensure_ascii=False,
                )
                return

        except Exception as e:
            logger.error(f"Error in workflow stream: {str(e)}")
            yield json.dumps(
                {"type": "error", "content": "Error processing stream" + str(e)},
                ensure_ascii=False,
            ) + "\n\n"
            return

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        yield json.dumps(
            {"type": "error", "content": "An unexpected error occurred" + str(e)},
            ensure_ascii=False,
        ) + "\n\n"
        return


@router.post("/custom_chatbot/update/stream")
async def update_chat_stream(
    query: str = Form(...),
    bot_id: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    attachs: List[UploadFile] = [],
    api_key: Optional[str] = Form(None),
    user: user_dependency = None,
):
    try:
        start_time = time.time()

        not_found = False
        messages = await preprocess_messages(query, attachs)
        bot = await bot_crud.read_one({"user_id": user["id"], "_id": ObjectId(bot_id)})
        if not bot:
            bot = {
                "prompt": "Chưa có prompt",
                "name": "Chưa có tên",
            }
            not_found = True

        return StreamingResponse(
            message_generator(
                input_graph={
                    "messages": messages,
                    "prompt": bot["prompt"],
                    "name": bot["name"],
                },
                config={
                    "configurable": {
                        "thread_id": bot_id,
                        "model_name": model_name,
                        "api_key": api_key,
                        "bot_id": bot_id,
                        "user_id": user["id"],
                        "bot_created": True if not not_found else False,
                    }
                },
                type="update",
            ),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Error in streaming endpoint: {str(e)}")
        increment_agent_calls(
            "custom_chatbot",
            status="error",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Streaming error: {str(e)}"},
        )
    finally:
        increment_agent_calls(
            "custom_chatbot",
            status="success",
        )
        end_time = time.time()
        duration = end_time - start_time
        observe_agent_duration(
            agent_type="custom_chatbot",
            duration=duration,
        )
