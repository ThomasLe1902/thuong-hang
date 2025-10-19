"""
Enhanced custom chatbot functions with monitoring integration
This is an example of how to add monitoring to your AI agents
"""

import time
from typing import TypedDict, Optional
from langchain_core.messages import AnyMessage, ToolMessage
from langgraph.graph.message import add_messages
from typing import Sequence, Annotated
from langchain_core.runnables.config import RunnableConfig

from src.agents.custom_chatbot.prompt import get_custom_chatbot_chains
from src.config.mongo import bot_crud
from src.utils.helper import trim_messages_function

# Import monitoring utilities
from src.config.monitoring import (
    increment_agent_calls,
    observe_agent_duration,
    increment_database_queries,
    trace_operation,
)


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
    """Collection info agent with monitoring"""
    start_time = time.time()

    with trace_operation("collection_info_agent", agent_type="custom_chatbot"):
        try:
            configuration = config.get("configurable", {})
            model_name = configuration.get("model_name")
            api_key = configuration.get("api_key")

            # Get the agent chain
            _, collection_info_agent = get_custom_chatbot_chains(model_name, api_key)

            # Execute the agent
            result = await collection_info_agent.ainvoke(
                {"messages": trim_messages_function(state["messages"])}
            )

            # Record successful agent call
            increment_agent_calls("collection_info_agent", "success")

            return result

        except Exception as e:
            # Record failed agent call
            increment_agent_calls("collection_info_agent", "error")
            raise
        finally:
            # Record duration
            duration = time.time() - start_time
            observe_agent_duration("collection_info_agent", duration)


async def create_prompt(state: State, config: RunnableConfig):
    """Create prompt with monitoring"""
    start_time = time.time()

    with trace_operation("create_prompt", agent_type="custom_chatbot"):
        try:
            messages = state["messages"]
            name, info = get_info_collection(messages)

            configuration = config.get("configurable", {})
            model_name = configuration.get("model_name", "unknown")
            api_key = configuration.get("api_key")

            # Get the chain
            create_system_chain, _ = get_custom_chatbot_chains(model_name, api_key)

            # Execute the chain
            res = await create_system_chain.ainvoke({"new_prompt": info})

            # Record successful agent call
            increment_agent_calls("create_prompt", "success")

            return {"prompt": res.content, "name": name}

        except Exception as e:
            # Record failed agent call
            increment_agent_calls("create_prompt", "error")
            raise
        finally:
            # Record duration
            duration = time.time() - start_time
            observe_agent_duration("create_prompt", duration)


async def save_prompt(state: State, config: RunnableConfig):
    """Save prompt with monitoring"""
    start_time = time.time()

    with trace_operation("save_prompt", agent_type="custom_chatbot") as span:
        try:
            configuration = config.get("configurable", {})
            user_id = configuration.get("user_id")
            prompt = state["prompt"]
            name = state["name"]

            # Add attributes to the span
            span.set_attribute("user_id", str(user_id))
            span.set_attribute("bot_name", name)
            span.set_attribute("prompt_length", len(prompt))

            # Track database operation
            increment_database_queries("create", "bots")

            # Save to database
            bot_id = await bot_crud.create(
                {"name": name, "prompt": prompt, "tools": [], "user_id": user_id}
            )

            # Record successful operation
            increment_agent_calls("save_prompt", "success")

            return {"done": True, "bot_id": bot_id}

        except Exception as e:
            # Record failed operation
            increment_agent_calls("save_prompt", "error")
            raise
        finally:
            # Record duration
            duration = time.time() - start_time
            observe_agent_duration("save_prompt", duration)


# Example of custom business metric tracking
async def chatbot_conversation(state: State, config: RunnableConfig):
    """Example of a chatbot conversation with comprehensive monitoring"""
    start_time = time.time()

    with trace_operation(
        "chatbot_conversation",
        agent_type="custom_chatbot",
        user_id=config.get("configurable", {}).get("user_id"),
        bot_id=state.get("bot_id"),
    ) as span:
        try:
            # Your chatbot logic here
            messages = state["messages"]

            # Add custom attributes
            span.set_attribute("message_count", len(messages))
            span.set_attribute(
                "conversation_length",
                sum(len(msg.content) for msg in messages if hasattr(msg, "content")),
            )

            # Simulate processing
            result = {"messages": messages, "processed": True}

            # Record metrics
            increment_agent_calls("chatbot_conversation", "success")

            return result

        except Exception as e:
            increment_agent_calls("chatbot_conversation", "error")
            span.set_attribute("error_message", str(e))
            raise
        finally:
            duration = time.time() - start_time
            observe_agent_duration("chatbot_conversation", duration)
