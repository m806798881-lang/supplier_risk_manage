from graph.state import SupplyChainRiskState
from langgraph.graph import StateGraph, START, END
from graph.nodes import *


def route_by_risk(state: SupplyChainRiskState) -> str:
    """只返回节点名，不执行业务逻辑"""
    if state.get('error'):
        return 'error'
    if state.get('risk_level') == "high":
        return "high_risk"
    return "low_risk"


def route_after_fetch(state: SupplyChainRiskState) -> str:
    return "error" if state.get("error") else "ok"


def _build_graph(checkpointer):
    wf = StateGraph(SupplyChainRiskState)

    wf.add_node("fetch_supplier", fetch_supplier)
    wf.add_node("fetch_risk", fetch_risk)
    wf.add_node("deep_review", deep_review)
    wf.add_node("retrieve_policies", retrieve_policies)
    wf.add_node("human_approval", human_approval)
    wf.add_node("generate_report", generate_report)

    wf.add_edge(START, 'fetch_supplier')
    wf.add_conditional_edges('fetch_supplier', route_after_fetch, {
                             'error': END, 'ok': 'fetch_risk'})

    wf.add_conditional_edges(
        "fetch_risk",
        route_by_risk,
        {
            "high_risk": "deep_review",
            "low_risk": "retrieve_policies",
            "error": END,
        },
    )

    wf.add_edge("deep_review", "retrieve_policies")
    wf.add_edge("retrieve_policies", "human_approval")
    wf.add_edge("human_approval", "generate_report")
    wf.add_edge("generate_report", END)

    return wf.compile(checkpointer=checkpointer)
