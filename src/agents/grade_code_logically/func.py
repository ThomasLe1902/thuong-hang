from typing import TypedDict
from .prompt import TestCase, GenerateCode, grade_code_logically_chain, EvaluationOutput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_experimental.utilities import PythonREPL

from src.utils.logger import logger


class State(TypedDict):
    base_url: str
    api_endpoint: str
    method: str
    test_cases: list[TestCase]
    llm: BaseChatModel
    api_description: str
    field_description: str
    codes: list[str]
    code_response: list[str]
    final_result: dict[str, int]


async def code_generator(state: State):
    gen_code_chain = grade_code_logically_chain(state["llm"])["gen_code_chain"]
    preprocess_input = [
        {
            "base_url": state["base_url"],
            "api_endpoint": state["api_endpoint"],
            "method": state["method"],
            "test_case_description": test_case.test_case_description,
        }
        for test_case in state["test_cases"]
    ]
    response: list[GenerateCode] = await gen_code_chain.abatch(preprocess_input)
    return {
        "codes": [code.code for code in response],
    }


def code_excutor(state: State):
    logger.info("execute_python_code")
    codes = state["codes"]
    exe = PythonREPL()
    code_res_list = []
    for c in codes:
        api_response = exe.run(c)
        if not api_response:
            api_response = "Failed to execute code"

        code_res_list.append("Response when API is called: " + api_response)
    return {"code_response": code_res_list}


async def code_evaluator(state: State):
    logger.info("evaluate_python_code")
    code_response = state["code_response"]
    preprocess_input = [
        {
            "api_endpoint": state["api_endpoint"],
            "api_description": state["api_description"],
            "test_case_description": state["test_cases"][i].test_case_description,
            "field_description": state["field_description"],
            "expected_api_response": state["test_cases"][i].expected_output,
            "response_output": code_response[i],
        }
        for i, _ in enumerate(code_response)
    ]
    evaluation_chain = grade_code_logically_chain(state["llm"])["evaluation_chain"]
    evaluation_response: list[EvaluationOutput] = await evaluation_chain.abatch(
        preprocess_input
    )

    count = 0
    for i, eval_res in enumerate(evaluation_response):
        if str(eval_res.actual_api_response) == str(
            state["test_cases"][i].expected_output
        ):
            logger.info("Passed")
            count += 1
        else:
            logger.error("Failed")
            count += 1
    logger.info(f"Passed {count} / {len(evaluation_response)}")
    return {
        "final_result": {
            "passed": count,
            "total": len(evaluation_response),
            "evaluation_response": [
                {
                    "actual_api_response": str(eval_res.actual_api_response),
                    "reason": eval_res.reason,
                    "test_case_description": state["test_cases"][
                        i
                    ].test_case_description,
                }
                for eval_res in evaluation_response
            ],
        }
    }
