from dotenv import load_dotenv

load_dotenv(override=True)
from typing import List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.config.llm import get_llm
from src.agents.grade_code_logically.prompt import grade_code_logically_chain
from pydantic import BaseModel, Field
from src.apis.middlewares.auth_middleware import get_current_user
from src.apis.models.user_models import User
from typing import Annotated
from langchain_core.messages import AIMessage
from src.config.llm import llm_2_0
from src.agents.grade_code_logically.flow import api_testing_agent
from src.agents.grade_code_logically.prompt import OutputTestCases, TestCase
from src.config.monitoring import (
    increment_request_count,
    observe_request_duration,
    increment_database_queries,
    increment_agent_calls,
    observe_agent_duration,
)
import time


class GenerateTestCasesRequest(BaseModel):
    api_endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="API method")
    api_description: str = Field(..., description="API description")
    field_description: str = Field(..., description="Field description")


class TestAPIRequest(BaseModel):
    base_url: str = Field(..., description="Base URL")
    api_endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="API method")
    test_cases: list[TestCase] = Field(..., description="List of test cases")
    api_description: str = Field(..., description="API description")
    field_description: str = Field(..., description="Field description")


router = APIRouter(prefix="/api-testing", tags=["API Testing"])
user_dependency = Annotated[User, Depends(get_current_user)]


@router.post("/generate-test-cases", status_code=200)
async def generate_test_cases(body: GenerateTestCasesRequest):
    start_time = time.time()
    try:
        chain = grade_code_logically_chain(llm_2_0)
        result: OutputTestCases = await chain["gen_test_cases_chain"].ainvoke(body)
        return [
            {
                "test_case_description": tc.test_case_description,
                "expected_output": tc.expected_output,
            }
            for tc in result.test_cases
        ]
    except Exception as e:
        increment_agent_calls(
            "generate_test_cases",
            status="error",
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        end_time = time.time()
        duration = end_time - start_time

        observe_agent_duration(
            agent_type="generate_test_cases",
            duration=duration,
        )
        increment_agent_calls(
            "generate_test_cases",
            status="success",
        )


@router.post("/test-api", status_code=200)
async def test_api(body: TestAPIRequest):
    start_time = time.time()
    try:
        llm = get_llm(model_name="gemini-2.0-flash")
        result = await api_testing_agent.ainvoke(
            {
                "test_cases": body.test_cases,
                "llm": llm,
                "base_url": body.base_url,
                "api_endpoint": body.api_endpoint,
                "method": body.method,
                "api_description": body.api_description,
                "field_description": body.field_description,
            }
        )
        return result["final_result"]
    except Exception as e:
        increment_agent_calls(
            "test_api",
            status="error",
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        end_time = time.time()
        duration = end_time - start_time
        observe_agent_duration(
            agent_type="test_api",
            duration=duration,
        )
        increment_agent_calls(
            "test_api",
            status="success",
        )
