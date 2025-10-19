from typing import TypedDict, Optional
from langchain_core.messages import AnyMessage, ToolMessage
from langgraph.graph.message import add_messages
from typing import Sequence, Annotated
from src.agents.custom_chatbot.prompt import get_custom_chatbot_chains
from src.config.mongo import bot_crud
from src.utils.helper import trim_messages_function
from langchain_core.runnables.config import RunnableConfig


class State(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    prompt: Optional[str]
    name: Optional[str]
    done: bool = False
    bot_id: str


def get_info_collection(messages):
    for idx, message in enumerate(messages):
        if isinstance(message, ToolMessage):
            break
    info = messages[idx - 1].tool_calls[0].get("args", {}).get("info", "")
    name = messages[idx - 1].tool_calls[0].get("args", {}).get("name", "")
    return name, info


async def collection_info_agent(state: State, config: RunnableConfig):
    configuration = config.get("configurable", {})
    model_name = configuration.get("model_name")
    api_key = configuration.get("api_key")
    _, collection_info_agent = get_custom_chatbot_chains(model_name, api_key)
    return await collection_info_agent.ainvoke(
        {"messages": trim_messages_function(state["messages"])}
    )


async def create_prompt(state: State, config: RunnableConfig):
    messages = state["messages"]
    name, info = get_info_collection(messages)
    configuration = config.get("configurable", {})
    model_name = configuration.get("model_name")
    api_key = configuration.get("api_key")
    create_system_chain, _ = get_custom_chatbot_chains(model_name, api_key)
    res = await create_system_chain.ainvoke({"new_prompt": info})
    return {"prompt": res.content, "name": name}


async def save_prompt(state: State, config: RunnableConfig):
    configuration = config.get("configurable", {})
    user_id = configuration.get("user_id")
    prompt = state["prompt"]
    name = state["name"]
    bot_id = await bot_crud.create(
        {"name": name, "prompt": prompt, "tools": [], "user_id": user_id}
    )
    return {"done": True, "bot_id": bot_id}
