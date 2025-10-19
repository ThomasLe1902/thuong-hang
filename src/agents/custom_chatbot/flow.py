from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from .func import collection_info_agent, create_prompt, save_prompt, State

checkpointer = InMemorySaver()


class CustomChatBot:
    def __init__(self):
        self.builder = StateGraph(State)

    @staticmethod
    def is_enough_information(state: State):
        messages = state["messages"]
        for message in messages:
            if isinstance(message, ToolMessage):
                return "create_prompt"
        return "END"

    def node(self):
        self.builder.add_node("collection_info_agent", collection_info_agent)
        self.builder.add_node("create_prompt", create_prompt)
        self.builder.add_node("save_prompt", save_prompt)

    def edge(self):
        self.builder.add_edge(START, "collection_info_agent")
        self.builder.add_conditional_edges(
            "collection_info_agent",
            self.is_enough_information,
            {"create_prompt": "create_prompt", "END": END},
        )
        self.builder.add_edge("create_prompt", "save_prompt")
        self.builder.add_edge("save_prompt", END)

    def __call__(self) -> CompiledStateGraph:
        self.node()
        self.edge()
        return self.builder.compile(checkpointer)


custom_chatbot = CustomChatBot()()
