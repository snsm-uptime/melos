"""Manual AI evaluation for picture capture (spec 041 SC-001, SC-006, SC-008). Needs GEMINI_API_KEY.

Reads every invented picture in tests/fixtures/ai_eval/pictures/, runs the real picture pipeline
and the real Gemini extractor (no database, no notebook), and prints each result for scoring
against CASES.md:

    docker compose exec api uv run python -m scripts.eval_picture_capture [--handwritten]
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from adapters.image.calibration import load_calibration_table
from adapters.image.pipeline import PillowPicturePipeline
from adapters.llm.gemini_extractor import GeminiRecipeExtractor
from api.settings import load_gemini_settings
from application.ports import Picture
from application.recipe_extraction import DraftPart, RecipeExtraction
from domain.recipe_picture import PictureRefused, check_picture

PICTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ai_eval" / "pictures"
SUFFIXES = {".png", ".jpg", ".jpeg", ".heic", ".heif"}


def main(argv: list[str]) -> int:
    handwritten = "--handwritten" in argv
    settings = load_gemini_settings()
    extraction = RecipeExtraction(
        GeminiRecipeExtractor(api_key=settings.api_key, model=settings.chat_model)
    )
    pipeline = PillowPicturePipeline()
    table = load_calibration_table()
    for path in sorted(p for p in PICTURES.iterdir() if p.suffix.lower() in SUFFIXES):
        print(f"== {path.name}")
        try:
            checked = check_picture(base64.b64encode(path.read_bytes()).decode("ascii"))
            processed = pipeline.process(checked, handwritten=handwritten, table=table)
        except PictureRefused as refused:
            print(f"   refused by the pipeline: {refused.kind}")
            continue
        print(
            f"   tier={processed.tier.value} sharpness={processed.sharpness} "
            f"final={processed.final_dimensions} size_kb={processed.size_kb}"
        )
        result = extraction.extract_picture(
            Picture(data=processed.webp, media_type="image/webp"),
            [],
            settings.image_timeout_s,
        )
        if isinstance(result, DraftPart):
            print(f"   outcome=recipe title={result.title!r} servings={result.base_servings}")
            for line in result.ingredient_lines:
                print(
                    f"     line: {line.name} qty={line.quantity} "
                    f"unit={line.unit} vague={line.vague}"
                )
            for step in result.steps:
                print(f"     step: {step}")
        else:
            print(f"   outcome={type(result).__name__} {getattr(result, 'reason', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
