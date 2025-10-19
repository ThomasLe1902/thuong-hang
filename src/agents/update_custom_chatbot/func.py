from typing import TypedDict, Optional
from langchain_core.messages import AnyMessage, ToolMessage
from langgraph.graph.message import add_messages
from typing import Sequence, Annotated
from src.config.llm import get_llm
from langchain_core.runnables.config import RunnableConfig
from src.utils.logger import logger

from .chains import update_prompt, collection_info_agent_prompt


class State(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    prompt: Optional[str]
    name: Optional[str]
    done: bool = False


async def execute_tool(state: State):
    tool_calls = state["messages"][-1].tool_calls

    tool_messages = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        # Xử lý các args name, prompt nếu không có thì set là empty string
        tool_args["name"] = tool_args.get("name", "")
        tool_args["prompt"] = tool_args.get("prompt", "")
        if tool_name == "update_prompt":
            tool_response = await update_prompt.ainvoke(tool_args)
        else:
            tool_response = "Tool không hợp lệ"
        tool_messages.append(
            ToolMessage(
                tool_call_id=tool_id,
                content=tool_response,
            )
        )

    return {
        "messages": tool_messages,
        "done": True,
    }


async def generate_answer(state: State, config: RunnableConfig):
    configuration = config.get("configurable", {})
    model_name = configuration.get("model_name")
    api_key = configuration.get("api_key")
    prompt = state["prompt"]
    name = state["name"]

    llm_call = collection_info_agent_prompt | get_llm(model_name, api_key).bind_tools(
        [update_prompt]
    )

    response = await llm_call.ainvoke(
        {
            "messages": state["messages"],
            "prompt": prompt,
            "name": name,
        }
    )
    logger.info(f"response: {response}")
    return {"messages": response}
