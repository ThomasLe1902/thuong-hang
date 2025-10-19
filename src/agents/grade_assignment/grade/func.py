from typing import TypedDict
from .prompt import (
    chain_grade_assignment,
    GradingResult,
)
from loguru import logger


class State(TypedDict):
    code_content: str
    exercise_question: str
    grade_result: str
    code_evaluation: str
    final_result: str


def create_grading_table(grading_result: GradingResult):
    table = "| **Criteria** | **Score** | **Comment** |\n"
    table += "|--------------|-----------|-------------|\n"

    for criteria in grading_result.criteria_scores:
        table += f"| **{criteria.criteria_name}** | {criteria.score} | {criteria.comment} |\n"

    table += f"| **Total Score** | {grading_result.total_score} | {grading_result.total_comment} |\n"

    return table


async def grade_submit(state: State):

    response = await chain_grade_assignment.ainvoke(
        {
            "user_input": state["code_content"],
            "exercise_question": state["exercise_question"],
        }
    )

    grading_table = create_grading_table(response)

    return {"grade_result": grading_table}


async def run_code(state: State):
    logger.info("Running code file in user folder")
    return {}


#     assignment = assignment_dict[state["assignment_id"]]
#     code_content, output = run_code_file_in_folder(state["user_folder_path"])
#     code_evaluation_chain = create_code_evaluation_chain(state["llm"])

#     code_evaluation: CodeEvaluation = await code_evaluation_chain.ainvoke(
#         {
#             "code_content": code_content,
#             "code_output": output,
#             "problem_statement": assignment["problem_statement"],
#             "exercise_name": assignment["exercise_name"],
#         }
#     )

#     code_table = f"""
# | **Code Evaluation** | **Status** |
# |-------------------|------------|
# | {code_evaluation.comment} | {code_evaluation.status} |
# """

# return {"code_evaluation": code_table}


def merge_result(state: State):
    final_result = f"""
# Grading Results

## Assignment Grading
{state["grade_result"]}
"""
    return {"final_result": final_result}
