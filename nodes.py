import base64
import os
import shutil

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel, Field

from prompts import CRITIC_SYSTEM, PROMPT_WRITER_SYSTEM, PROMPT_WRITER_USER
from state import ThumbnailState
from tools import search_web


# ── Structured output schema for the critic ────────────────────────────────────

class CriticOutput(BaseModel):
    rating: int = Field(description="Overall thumbnail quality rating, integer from 1 to 10")
    critique: str = Field(description="Specific, actionable critique for the next iteration")


# ── Nodes ──────────────────────────────────────────────────────────────────────

def web_search(state: ThumbnailState) -> dict:
    topic = state["topic"]
    query = f"YouTube thumbnail design trends hooks {topic} high CTR visual style"
    summary = search_web(query)
    print(f"[web_search] retrieved {len(summary)} chars of research")
    return {"search_summary": summary}


def prompt_writer(state: ThumbnailState) -> dict:
    llm = ChatOpenAI(model="gpt-4o", temperature=0.9)

    critique_section = ""
    if state.get("critique") and state.get("iteration", 0) > 0:
        critique_section = (
            f"Previous iteration rating: {state['rating']}/10\n"
            f"Critique to address:\n{state['critique']}\n\n"
            "Incorporate this feedback and produce a significantly improved prompt.\n"
        )

    user_text = PROMPT_WRITER_USER.format(
        topic=state["topic"],
        search_summary=state["search_summary"],
        critique_section=critique_section,
    )

    messages = [
        SystemMessage(content=PROMPT_WRITER_SYSTEM),
        HumanMessage(content=user_text),
    ]
    response = llm.invoke(messages)
    print(f"[prompt_writer] prompt drafted ({len(response.content)} chars)")
    return {"dalle_prompt": response.content}


def generator(state: dict) -> dict:
    client = OpenAI()

    iteration = state.get("iteration", 0) + 1
    output_dir = state["output_dir"]

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"[generator] calling gpt-image-1 for iteration {iteration}...")

    response = client.images.generate(
        model="gpt-image-1",
        prompt=state["dalle_prompt"],
        size="1536x1024",   # closest 16:9 supported by gpt-image-1
        quality="medium",   # gpt-image-1 uses low/medium/high/auto
        n=1,
    )

    # gpt-image-1 returns base64 directly — no URL download needed
    img_bytes = base64.b64decode(response.data[0].b64_json)

    image_path = os.path.join(output_dir, f"iter_{iteration}.png")

    with open(image_path, "wb") as f:
        f.write(img_bytes)

    print(f"[generator] saved {image_path}")

    return {
        "current_image_path": image_path,
        "iteration": iteration,
    }


def critic(state: ThumbnailState) -> dict:
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(CriticOutput)

    image_path = state["current_image_path"]
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    messages = [
        SystemMessage(content=CRITIC_SYSTEM),
        HumanMessage(content=[
            {
                "type": "text",
                "text": f"Evaluate this YouTube thumbnail for the topic: \"{state['topic']}\"",
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}",
                    "detail": "high",
                },
            },
        ]),
    ]

    result: CriticOutput = structured_llm.invoke(messages)
    print(f"[critic] iteration {state['iteration']} rated {result.rating}/10")

    history_entry = {
        "iteration": state["iteration"],
        "dalle_prompt": state["dalle_prompt"],
        "image_path": state["current_image_path"],
        "rating": result.rating,
        "critique": result.critique,
    }

    updates: dict = {
        "rating": result.rating,
        "critique": result.critique,
        "history": [history_entry],  # reducer appends this to existing list
    }

    # Track the best image seen so far
    if result.rating > state.get("best_rating", 0):
        updates["best_image_path"] = state["current_image_path"]
        updates["best_rating"] = result.rating

    return updates


def saver(state: ThumbnailState) -> dict:
    output_dir = state["output_dir"]
    best_image = state.get("best_image_path") or state.get("current_image_path")

    final_path = os.path.join(output_dir, "final.png")
    shutil.copy2(best_image, final_path)

    report_lines = [
        "# YouTube Thumbnail Design Report",
        "",
        f"**Topic:** {state['topic']}",
        f"**Total Iterations:** {state.get('iteration', 0)}",
        f"**Best Rating:** {state.get('best_rating', state.get('rating', 0))}/10",
        f"**Final Image:** `final.png`",
        "",
        "## Web Research Summary",
        "",
        state.get("search_summary", ""),
        "",
        "## Iteration History",
        "",
    ]

    for entry in state.get("history", []):
        report_lines += [
            f"### Iteration {entry['iteration']}",
            "",
            "**DALL-E Prompt:**",
            "```",
            entry["dalle_prompt"],
            "```",
            "",
            f"**Rating:** {entry['rating']}/10",
            "",
            "**Critique:**",
            entry["critique"],
            "",
            f"**Image:** `{os.path.basename(entry['image_path'])}`",
            "",
        ]

    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))

    print(f"\n[saver] output dir : {output_dir}")
    print(f"[saver] best rating: {state.get('best_rating', state.get('rating', 0))}/10")
    print(f"[saver] files      : final.png, report.md + {state.get('iteration', 0)} iter_N.png")
    return {}


# ── Conditional edge ───────────────────────────────────────────────────────────

def should_continue(state: ThumbnailState) -> str:
    rating = state.get("rating", 0)
    iteration = state.get("iteration", 0)
    target_rating = state.get("target_rating", 8)
    max_iterations = state.get("max_iterations", 3)

    if rating >= target_rating or iteration >= max_iterations:
        print(f"[should_continue] stopping — rating={rating}, iter={iteration}")
        return "saver"

    print(f"[should_continue] looping — rating={rating} < {target_rating}, iter={iteration}/{max_iterations}")
    return "prompt_writer"
