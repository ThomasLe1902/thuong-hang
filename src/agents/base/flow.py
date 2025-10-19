from langgraph.graph import StateGraph, START, END
from src.config.llm import llm_2_0
from .func import State
from langgraph.graph.state import CompiledStateGraph


class PrimaryChatBot:
    def __init__(self):
        self.builder = StateGraph(State)

    @staticmethod
    def routing(state: State):
        pass

    def node(self):
        pass

    def edge(self):
        pass
    def __call__(self) -> CompiledStateGraph:
        self.node()
        self.edge()
        return self.builder.compile()
