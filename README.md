# YouTube Thumbnail Designer — LangGraph Reflexion Agent

Generates, critiques, and iteratively improves YouTube thumbnails using the Reflexion pattern inside a compiled LangGraph state machine.

## Architecture

```
START → web_search → prompt_writer → generator → critic
                          ↑                          │
                          └──── rating < 8 & iter < 3 ┤
                                                      │
                         saver ←── rating ≥ 8 OR iter ≥ max
                           ↓
                          END
```

| Node | Role |
|---|---|
| `web_search` | One-time Tavily pull; stores `search_summary` |
| `prompt_writer` | Writes DALL-E 3 prompt; incorporates critic feedback on loops |
| `generator` | Calls DALL-E 3, saves `iter_N.png`, increments iteration |
| `critic` | GPT-4o vision → `CriticOutput(rating: int, critique: str)` via `with_structured_output` |
| `saver` | Copies best image to `final.png`, writes `report.md` |

The `should_continue` conditional edge routes `critic → prompt_writer` (loop) or `critic → saver` (done).

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo>
cd assigment-02
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install .
```

### 3. Set API keys

```bash
cp .env.example .env
# edit .env and fill in your keys
```

Required keys:
- `OPENAI_API_KEY` — needs DALL-E 3 and GPT-4o access
- `TAVILY_API_KEY` — free tier at [tavily.com](https://tavily.com)

## Usage

```bash
# Default topic
python main.py

# Custom topic
python main.py "10 Python tricks every developer should know"

# Tune thresholds via env vars
TARGET_RATING=7 MAX_ITERATIONS=2 python main.py "Machine learning for beginners"
```

Output lands in `outputs/<timestamp>_<topic>/`:
- `iter_1.png`, `iter_2.png`, … — each generated thumbnail
- `final.png` — highest-rated image
- `report.md` — full iteration history with prompts, ratings, and critiques

## Generate graph diagram

```bash
python make_diagram.py   # writes graph.png
```

## Key design decisions

- **State schema**: `ThumbnailState` (TypedDict) with `history: Annotated[list, operator.add]` — the append reducer accumulates every iteration's entry without overwriting.
- **Structured critic output**: `CriticOutput(rating: int, critique: str)` enforced via Pydantic + `with_structured_output()` — `rating` is always a real `int`.
- **Strict critic calibration**: Scores 5-7 on typical AI output; 8+ reserved for publish-ready work. This guarantees the loop fires on the first iteration in normal use.
- **No checkpointer**: `graph.compile()` is plain, as required.
