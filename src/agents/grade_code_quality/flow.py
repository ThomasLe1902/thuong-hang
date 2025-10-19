from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from langchain_core.runnables import RunnableConfig
from .func import State, ParentGraphState
from .func import (
    check_relevant_criteria,
    analyze_code_file,
    grade_folder_structure,
)
import json
from src.utils.logger import logger
from src.config.llm import get_llm
from langchain_core.language_models.chat_models import BaseChatModel
from src.config.mongo import GradedAssignmentCRUD

flow = StateGraph(State)


class AgentCodeGrader:
    def __init__(self):
        self.flow = StateGraph(State)

    @staticmethod
    def routing_after_check_relevant_criteria(state: State):
        if not state["selected_files"]:
            return END
        else:
            return "analyze_code_file"

    def node(self):

        self.flow.add_node("check_relevant_criteria", check_relevant_criteria)
        self.flow.add_node("analyze_code_file", analyze_code_file)

    def edge(self):
        self.flow.add_edge(START, "check_relevant_criteria")
        self.flow.add_conditional_edges(
            "check_relevant_criteria",
            self.routing_after_check_relevant_criteria,
            {
                END: END,
                "analyze_code_file": "analyze_code_file",
            },
        )
        self.flow.add_edge("analyze_code_file", END)

    def __call__(self) -> CompiledStateGraph:
        self.node()
        self.edge()
        return self.flow.compile()


async def agent_processing(state: ParentGraphState):
    selected_files = state["selected_files"]
    criterias_list = state["criterias_list"]
    project_description = state["project_description"]
    agent_single_criteria = AgentCodeGrader()()

    # Process criteria sequentially instead of in batch
    output = []
    for index, criterias in enumerate(criterias_list, 1):
        logger.info(f"Processing criteria {index}/{len(criterias_list)}: {criterias}")

        single_result = await agent_single_criteria.ainvoke(
            {
                "selected_files": selected_files,
                "criterias": criterias,
                "project_description": project_description,
                "criteria_index": index,
                "llm": state["llm"],
            }
        )

        # Remove llm from result
        single_result.pop("llm", None)
        output.append(single_result)

    return {"output": output}


async def save_graded_assignment(state: ParentGraphState, config: RunnableConfig):
    """Save graded assignment to database after all processing is complete"""
    configuration = config.get("configurable", {})
    user_id = configuration.get("user_id")
    project_name = configuration.get("project_name", "")

    if user_id and state.get("output"):
        await GradedAssignmentCRUD.create(
            {
                "user_id": user_id,
                "project_name": project_name,
                "selected_files": state.get("selected_files", []),
                "folder_structure_criteria": state.get("folder_structure_criteria", ""),
                "criterias_list": state.get("criterias_list", []),
                "project_description": state.get("project_description", ""),
                "grade_result": state.get("output", []),
            }
        )
    return state


class AgentCodeGraderMultiCriterias:
    def __init__(self):
        self.flow = StateGraph(ParentGraphState)

    def node(self):
        self.flow.add_node("grade_folder_structure", grade_folder_structure)
        self.flow.add_node("agent_processing", agent_processing)
        self.flow.add_node("save_graded_assignment", save_graded_assignment)

    def edge(self):
        self.flow.add_edge(START, "grade_folder_structure")
        self.flow.add_edge(START, "agent_processing")
        self.flow.add_edge("grade_folder_structure", "save_graded_assignment")
        self.flow.add_edge("agent_processing", "save_graded_assignment")
        self.flow.add_edge("save_graded_assignment", END)

    def __call__(self) -> CompiledStateGraph:
        self.node()
        self.edge()
        return self.flow.compile()


agent_graph = AgentCodeGraderMultiCriterias()()


# async def grade_code(
#     selected_files: list[str],
#     criterias_list: list[str],
#     project_description: str = None,
# ):
#     """Process criteria evaluation using batch for multiple criteria or invoke for single criterion."""
#     agent = AgentCodeGrader()()
#     llm = get_llm("gemini-2.0-flash")
#     output = await agent.abatch(
#         [
#             {
#                 "selected_files": selected_files,
#                 "criterias": criterias,
#                 "project_description": project_description,
#                 "criteria_index": index,
#                 "llm": llm,
#             }
#             for index, criterias in enumerate(criterias_list, 1)
#         ]
#     )
#     return output


async def grade_streaming_fn(
    llm: BaseChatModel,
    file_paths: list[str],
    folder_structure_criteria: str,
    criterias_list: list[str],
    project_description: str = None,
    user_id: str = None,
    folder_file_paths: str = None,
):
    # Store folder structure result to include in final response
    folder_structure_result = ""

    # First, process folder structure
    if folder_structure_criteria:
        logger.info("Processing folder structure...")
        folder_structure_state = {
            "selected_files": file_paths,
            "folder_structure_criteria": folder_structure_criteria,
            "project_description": project_description,
            "llm": llm,
        }

        folder_result = await grade_folder_structure(folder_structure_state)
        folder_structure_result = folder_result.get("output_folder_structure", "")

        # Yield folder structure result
        try:
            project_structure_response = json.dumps(
                {
                    "type": "folder_structure",
                    "output": folder_structure_result,
                },
                ensure_ascii=False,
            )
            logger.info(f"Project structure response: {project_structure_response}")
            yield project_structure_response + "\n\n"
        except Exception as e:
            logger.error(f"Error serializing folder structure response: {e}")
            error_response = json.dumps(
                {
                    "type": "error",
                    "output": f"Error processing folder structure: {str(e)}",
                },
                ensure_ascii=False,
            )
            yield error_response + "\n\n"

    # Then, process each criteria sequentially
    agent_single_criteria = AgentCodeGrader()()
    all_results = []

    for index, criterias in enumerate(criterias_list, 1):
        logger.info(f"Processing criteria {index}/{len(criterias_list)}: {criterias}")

        single_result = await agent_single_criteria.ainvoke(
            {
                "selected_files": file_paths,
                "criterias": criterias,
                "project_description": project_description,
                "criteria_index": index,
                "llm": llm,
            }
        )

        # Remove llm from result
        single_result.pop("llm", None)
        all_results.append(single_result)

        # Yield intermediate result for this criteria
        try:
            criteria_response = json.dumps(
                {
                    "type": "criteria_result",
                    "criteria_index": index,
                    "total_criteria": len(criterias_list),
                    "result": single_result,
                    "partial_results": all_results.copy(),
                },
                ensure_ascii=False,
            )
            logger.info(f"Criteria {index} response: {criteria_response}")
            yield criteria_response + "\n\n"
        except Exception as e:
            logger.error(f"Error serializing criteria {index} response: {e}")
            error_response = json.dumps(
                {
                    "type": "error",
                    "output": f"Error processing criteria {index}: {str(e)}",
                },
                ensure_ascii=False,
            )
            yield error_response + "\n\n"

    # Finally, yield complete results
    try:
        final_response = json.dumps(
            {
                "type": "final",
                "output": all_results,
                "grade_folder_structure": folder_structure_result,
            },
            ensure_ascii=False,
        )
        yield final_response + "\n\n"
    except Exception as e:
        logger.error(f"Error serializing final response: {e}")
        error_response = json.dumps(
            {
                "type": "error",
                "output": f"Error processing final results: {str(e)}",
            },
            ensure_ascii=False,
        )
        yield error_response + "\n\n"

    # Save to database
    if user_id and all_results:
        await GradedAssignmentCRUD.create(
            {
                "user_id": user_id,
                "project_name": folder_file_paths or "",
                "selected_files": file_paths,
                "folder_structure_criteria": folder_structure_criteria,
                "criterias_list": criterias_list,
                "project_description": project_description or "",
                "grade_result": all_results,
            }
        )
