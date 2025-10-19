from typing import TypedDict, Optional, List
from langchain_core.messages import AnyMessage, ToolMessage
from langgraph.graph.message import add_messages
from typing import Sequence, Annotated
from langchain_core.messages import RemoveMessage
from langchain_core.documents import Document
from .tools import retrieve_document, python_repl, duckduckgo_search
from src.config.llm import get_llm
from .prompt import template_prompt
from src.utils.helper import trim_messages_function
from langchain_core.runnables.config import RunnableConfig
from src.utils.logger import logger

tools = [retrieve_document, python_repl, duckduckgo_search]


class State(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    prompt: str
    tools: Optional[List[str]]
    selected_ids: Optional[List[str]]
    selected_documents: Optional[List[Document]]


def trim_history(state: State):
    history = state.get("messages", [])

    if len(history) > 20:
        num_to_remove = len(history) - 20
        remove_messages = [
            RemoveMessage(id=history[i].id) for i in range(num_to_remove)
        ]
        return {
            "messages": remove_messages,
            "selected_ids": [],
            "selected_documents": [],
        }

    return {}


def execute_tool(state: State):
    tool_calls = state["messages"][-1].tool_calls
    tool_name_to_func = {tool.name: tool for tool in tools}

    selected_ids = []
    selected_documents = []
    tool_messages = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        tool_func = tool_name_to_func.get(tool_name)
        if tool_func:
            if tool_name == "retrieve_document":
                documents = tool_func.invoke(tool_args.get("query"))
                documents = dict(documents)
                context_str = documents.get("context_str", "")
                selected_documents = documents.get("selected_documents", [])
                selected_ids = documents.get("selected_ids", [])
                if documents:
                    tool_messages.append(
                        ToolMessage(
                            tool_call_id=tool_id,
                            content=context_str,
                        )
                    )
                continue
            tool_response = tool_func.invoke(tool_args)
            tool_messages.append(
                ToolMessage(
                    tool_call_id=tool_id,
                    content=tool_response,
                )
            )

    return {
        "selected_ids": selected_ids,
        "selected_documents": selected_documents,
        "messages": tool_messages,
    }


async def generate_answer(state: State, config: RunnableConfig):
    configuration = config.get("configurable", {})
    messages = state["messages"]
    tool_names = state.get("tools", [])
    prompt = state["prompt"]
    model_name = configuration.get("model_name", "gemini-2.0-flash")
    reasoning = configuration.get("reasoning", False)
    logger.info(f"model_name: {model_name}")
    api_key = configuration.get("api_key", None)
    tool_name_to_func = {tool.name: tool for tool in tools}
    tool_functions = [
        tool_name_to_func[name] for name in tool_names if name in tool_name_to_func
    ]

    llm_call = template_prompt | get_llm(
        model_name, api_key, reasoning=reasoning
    ).bind_tools(tool_functions)

    if tool_functions:
        for tool in tool_functions:
            if tool.name == "retrieve_document":
                prompt += "Sử dụng tool `retrieve_document` để truy xuất tài liệu để bổ sung thông tin cho câu trả lời nếu câu hỏi liên quan đến domain knowledge của bạn"
            if tool.name == "python_repl":
                prompt += "Sử dụng tool `python_repl` để thực hiện các tác vụ liên quan đến tính toán phức tạp"
            if tool.name == "duckduckgo_search":
                prompt += "Sử dụng tool `duckduckgo_search` để tìm kiếm thông tin trên internet"
    prompt += "Note: Ngôn ngữ phản hồi/call tool dựa trên ngôn ngữ đầu vào của người dùng. Ví dụ: nếu người dùng nói tiếng Việt thì phản hồi/call tool cũng phải là tiếng Việt. Nếu người dùng nói tiếng Anh thì phản hồi/call tool cũng phải là tiếng Anh."

    response = await llm_call.ainvoke(
        {
            "messages": trim_messages_function(messages),
            "prompt": prompt,
        }
    )
    return {"messages": response}
