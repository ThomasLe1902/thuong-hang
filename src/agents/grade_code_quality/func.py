from .prompt import (
    CheckRelevantCriteriaOutput,
    AnaLyzeOutput,
    grade_code_quality_chain,
)
from src.utils.helper import (
    format_comment_across_file,
    build_tree,
    input_preparation,
)
from typing import TypedDict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from src.config.llm import get_llm
from langchain_core.messages import AIMessage
from src.utils.logger import logger


class ParentGraphState(TypedDict):
    folder_structure_criteria: Optional[str]
    project_description: Optional[str]
    selected_files: list[str]
    criterias_list: list[str]
    criteria_index: str
    output: Any
    output_folder_structure: str
    llm: BaseChatModel


class State(TypedDict):
    selected_files: list[str]
    criterias: str
    project_description: str
    analyze_code_result: list[any]
    grade_criteria: str
    criteria_index: int
    llm: BaseChatModel


async def project_description_generator(state: State):
    logger.info("Generating project description...")
    selected_files = state["selected_files"]
    file_tree = build_tree(selected_files)
    return {"project_description": file_tree}


async def check_relevant_criteria(state: State):
    logger.info("Checking relevant criteria...")
    criterias = state["criterias"]
    selected_files = state["selected_files"]
    criteria_index = state["criteria_index"]
    logger.info(f"Before check relevant criteria: {str(len(selected_files))}")
    project_description = state["project_description"]
    if project_description:
        project_description = "- Project description: " + project_description
    else:
        project_description = ""
    filter_datas, _ = input_preparation(
        selected_files, project_description, criterias, 5000
    )

    check_results: list[CheckRelevantCriteriaOutput] = await grade_code_quality_chain(
        state["llm"]
    )["check_relevant_criteria"].abatch(filter_datas)

    selected_files = [
        file_name
        for file_name, result in zip(selected_files, check_results)
        if result.relevant_criteria == True
    ]
    logger.info(f"After check relevant criteria: {str(len(selected_files))}")

    if not selected_files:
        return {"selected_files": selected_files}

    return {"selected_files": selected_files, "criteria_index": criteria_index}


async def analyze_code_file(state: State):
    logger.info("Analyzing code files...")
    criterias = state["criterias"]
    selected_files = state["selected_files"]
    criteria_index = state["criteria_index"]
    project_description = state["project_description"]
    filter_datas, _ = input_preparation(
        selected_files, project_description, criterias, 5000
    )
    analysis_results: list[AnaLyzeOutput] = await grade_code_quality_chain(
        state["llm"]
    )["analyze_code_file"].abatch(filter_datas)

    output = [
        {
            "file_name": data["file_name"],
            "comment": result.comment,
            "criteria_eval": result.criteria_eval,
            "rating": result.rating,
        }
        for data, result in zip(filter_datas, analysis_results)
    ]

    return {"analyze_code_result": output, "criteria_index": criteria_index}


async def summarize_code_review_controller(data, llm: BaseChatModel):

    files_name = [item["file_name"] for item in data["analyze_code_result"]]
    analyze_results = data["analyze_code_result"]
    criterias = data["criterias"]
    review_across_files = format_comment_across_file(
        files_name=files_name, analyze_results=analyze_results
    )
    review_response: AIMessage = await grade_code_quality_chain(llm)[
        "summarize_code_review"
    ].ainvoke({"criterias": criterias, "review_summary": review_across_files})
    return review_response.content


async def grade_folder_structure(state: ParentGraphState):
    logger.info("Organizing project structure...")
    selected_files = state["selected_files"]
    criteria = state["folder_structure_criteria"]
    if not criteria:
        return {}
    file_tree = build_tree(selected_files)

    response: AIMessage = await grade_code_quality_chain(state["llm"])[
        "organized_project_structure_grade"
    ].ainvoke(
        {
            "file_tree": file_tree,
            "criteria": criteria,
        }
    )
    return {
        "output_folder_structure": response.content,
    }
