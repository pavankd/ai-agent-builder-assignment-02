import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict


class ThumbnailState(TypedDict):
    topic: str
    search_summary: str
    dalle_prompt: str
    current_image_path: str
    iteration: int
    rating: int
    critique: str
    history: Annotated[list, operator.add]  # reducer: appends each critic entry
    output_dir: str
    target_rating: int
    max_iterations: int
    best_image_path: str
    best_rating: int
