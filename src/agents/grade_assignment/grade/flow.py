from langgraph.graph import StateGraph, START, END
from .func import State, grade_submit, run_code, merge_result
from langgraph.graph.state import CompiledStateGraph


class GradeFlow:
    def __init__(self):
        self.builder = StateGraph(State)

    @staticmethod
    def routing(state: State):
        pass

    def node(self):
        self.builder.add_node("grade", grade_submit)
        self.builder.add_node("run_code", run_code)
        self.builder.add_node("merge_result", merge_result)

    def edge(self):
        self.builder.add_edge(START, "grade")
        self.builder.add_edge(START, "run_code")
        self.builder.add_edge("grade", "merge_result")
        self.builder.add_edge("run_code", "merge_result")
        self.builder.add_edge("merge_result", END)

    def __call__(self) -> CompiledStateGraph:
        self.node()
        self.edge()
        return self.builder.compile()


grade_agent = GradeFlow()()
