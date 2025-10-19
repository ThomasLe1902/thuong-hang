from langgraph.graph import StateGraph, START, END
from src.config.llm import llm_2_0
from .func import State, code_evaluator, code_excutor, code_generator
from langgraph.graph.state import CompiledStateGraph


class APITestingAgent:
    def __init__(self):
        self.builder = StateGraph(State)

    @staticmethod
    def routing(state: State):
        pass

    def node(self):
        self.builder.add_node("gen_test_cases_chain", code_generator)
        self.builder.add_node("code_excutor", code_excutor)
        self.builder.add_node("code_evaluator", code_evaluator)

    def edge(self):
        self.builder.add_edge(START, "gen_test_cases_chain")
        self.builder.add_edge("gen_test_cases_chain", "code_excutor")
        self.builder.add_edge("code_excutor", "code_evaluator")
        self.builder.add_edge("code_evaluator", END)

    def __call__(self) -> CompiledStateGraph:
        self.node()
        self.edge()
        return self.builder.compile()


api_testing_agent = APITestingAgent()()
