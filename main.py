import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from graph import build_graph

load_dotenv()


def _sanitize(topic: str) -> str:
    return "".join(c if c.isalnum() or c in "_ -" else "_" for c in topic)[:50].strip()


def main():
    topic = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else "Why Python is the best language for AI"
    target_rating = int(os.getenv("TARGET_RATING", "8"))
    max_iterations = int(os.getenv("MAX_ITERATIONS", "3"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("outputs", f"{timestamp}_{_sanitize(topic)}")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("  YouTube Thumbnail Designer  (Reflexion / LangGraph)")
    print("=" * 60)
    print(f"  Topic          : {topic}")
    print(f"  Target rating  : {target_rating}/10")
    print(f"  Max iterations : {max_iterations}")
    print(f"  Output dir     : {output_dir}")
    print("=" * 60 + "\n")

    graph = build_graph()

    initial_state = {
        "topic": topic,
        "search_summary": "",
        "dalle_prompt": "",
        "current_image_path": "",
        "iteration": 0,
        "rating": 0,
        "critique": "",
        "history": [],
        "output_dir": output_dir,
        "target_rating": target_rating,
        "max_iterations": max_iterations,
        "best_image_path": "",
        "best_rating": 0,
    }

    final_state = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    print(f"  Done. Best rating: {final_state.get('best_rating', final_state.get('rating', 0))}/10")
    print(f"  Output: {output_dir}/")
    print("=" * 60)

    return final_state


if __name__ == "__main__":
    main()
