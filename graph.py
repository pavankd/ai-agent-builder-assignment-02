from langgraph.graph import END, START, StateGraph

from nodes import critic, generator, prompt_writer, saver, should_continue, web_search
from state import ThumbnailState


def build_graph():
    g = StateGraph(ThumbnailState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    g.add_node("web_search", web_search)
    g.add_node("prompt_writer", prompt_writer)
    g.add_node("generator", generator)
    g.add_node("critic", critic)
    g.add_node("saver", saver)

    # ── Static edges ───────────────────────────────────────────────────────────
    g.add_edge(START, "web_search")
    g.add_edge("web_search", "prompt_writer")
    g.add_edge("prompt_writer", "generator")
    g.add_edge("generator", "critic")
    g.add_edge("saver", END)

    # ── Conditional edge (the Reflexion loop) ──────────────────────────────────
    g.add_conditional_edges(
        "critic",
        should_continue,
        {
            "prompt_writer": "prompt_writer",
            "saver": "saver",
        },
    )

    return g.compile()
