from src.config.llm import get_llm_provider
from pydantic import BaseModel, Field
from typing import Literal
from fastapi import APIRouter, status, Depends, UploadFile, Form
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Any
import json
import datetime
from bson import ObjectId
import os

from src.config.monitoring import (
    increment_request_count,
    observe_request_duration,
    increment_database_queries,
    increment_agent_calls,
    observe_agent_duration,
)

from src.agents.prompt_optimization.prompt import (
    general_optimization_prompt,
    general_with_output_format_prompt,
    analytical_structured_optimization_prompt,
    professional_optimization_prompt,
    basic_optimization_prompt,
    step_by_step_planning_optimization_prompt,
)

router = APIRouter(prefix="/prompt-optimization", tags=["Prompt Optimization"])


class SystemPromptOptimizationRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="The user prompt that needs to be optimized and expanded.",
    )
    optimization_type: Literal[
        "general", "general_with_output_format", "analytical_structured"
    ] = Field(
        default="general",
        description="Type of optimization to apply. Default is 'general'.",
    )
    model_name: str = Field(
        default="gemini-2.5-flash",
        description="The name of the model to use for optimization. Default is 'gemini-2.5-flash'.",
    )
    api_endpoint: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai",
        description="The API endpoint for the LLM provider. Default is 'https://generativelanguage.googleapis.com/v1beta/openai'.",
    )
    api_key: str = Field(
        default=os.getenv("GOOGLE_API_KEY"),
        description="API key for authentication with the LLM provider. Optional.",
    )


class UserPromptOptimizationRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="The user prompt that needs to be optimized and expanded.",
    )
    optimization_type: Literal[
        "professional",
        "basic",
        "step_by_step_planning",
    ] = Field(
        default="general",
        description="Type of optimization to apply. Default is 'general'.",
    )
    model_name: str = Field(
        default="gemini-2.5-flash",
        description="The name of the model to use for optimization. Default is 'gemini-2.5-flash'.",
    )
    api_endpoint: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai",
        description="The API endpoint for the LLM provider. Default is 'https://generativelanguage.googleapis.com/v1beta/openai'.",
    )
    api_key: str = Field(
        default=os.getenv("GOOGLE_API_KEY"),
        description="API key for authentication with the LLM provider. Optional.",
    )


@router.post("/system-prompt", status_code=status.HTTP_200_OK)
async def create_system_prompt(
    request: SystemPromptOptimizationRequest,
):
    if request.optimization_type == "general":
        chain = general_optimization_prompt | get_llm_provider(
            request.model_name, request.api_endpoint, request.api_key
        )
    elif request.optimization_type == "general_with_output_format":
        chain = general_with_output_format_prompt | get_llm_provider(
            request.model_name, request.api_endpoint, request.api_key
        )
    elif request.optimization_type == "analytical_structured":
        chain = analytical_structured_optimization_prompt | get_llm_provider(
            request.model_name, request.api_endpoint, request.api_key
        )

    async def message_generator():
        async for message in chain.astream({"prompt": request.prompt}):
            yield json.dumps(
                {
                    "content": message.content,
                }
            ) + "\n\n"

    return StreamingResponse(
        message_generator(),
        media_type="text/event-stream",
    )


@router.post("/user-prompt", status_code=status.HTTP_200_OK)
async def create_user_prompt(
    request: UserPromptOptimizationRequest,
):
    if request.optimization_type == "professional":
        chain = professional_optimization_prompt | get_llm_provider(
            request.model_name, request.api_endpoint, request.api_key
        )
    elif request.optimization_type == "basic":
        chain = basic_optimization_prompt | get_llm_provider(
            request.model_name, request.api_endpoint, request.api_key
        )
    elif request.optimization_type == "step_by_step_planning":
        chain = step_by_step_planning_optimization_prompt | get_llm_provider(
            request.model_name, request.api_endpoint, request.api_key
        )

    async def message_generator():
        async for message in chain.astream({"prompt": request.prompt}):
            yield json.dumps(
                {
                    "content": message.content,
                }
            ) + "\n\n"

    return StreamingResponse(
        message_generator(),
        media_type="text/event-stream",
    )
