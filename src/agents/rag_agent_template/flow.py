from langgraph.graph import StateGraph, START, END
from .func import (
    State,
    trim_history,
    execute_tool,
    generate_answer,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import InMemorySaver


class RAGAgentTemplate:
    def __init__(self):
        self.builder = StateGraph(State)

    @staticmethod
    def should_continue(state: State):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "execute_tool"
        return END

    def node(self):
        self.builder.add_node("trim_history", trim_history)
        self.builder.add_node("generate_answer", generate_answer)
        self.builder.add_node("execute_tool", execute_tool)

    def edge(self):
        self.builder.add_edge(START, "trim_history")
        self.builder.add_edge("trim_history", "generate_answer")
        self.builder.add_conditional_edges(
            "generate_answer",
            self.should_continue,
            {
                END: END,
                "execute_tool": "execute_tool",
            },
        )
        self.builder.add_edge("execute_tool", "generate_answer")
        self.builder.add_edge("generate_answer", END)

    def __call__(self) -> CompiledStateGraph:
        self.node()
        self.edge()

        return self.builder.compile(checkpointer=InMemorySaver())


rag_agent_template_agent = RAGAgentTemplate()()
