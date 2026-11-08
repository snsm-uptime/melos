"""CapturePictureRecipe against fake ports (spec 041 T026). No network, model or image library."""

from __future__ import annotations

import base64
import logging
from datetime import date
from uuid import uuid4

import pytest
from adapters.image.fake_pipeline import FakePicturePipeline
from adapters.llm.fake_extractor import FakeRecipeExtractor
from application import recipe_capture_picture
from application.ports import ProcessedPicture
from application.recipe_capture_picture import (
    CapturedPictureDraft,
    CapturePictureCommand,
    CapturePictureRecipe,
)
from application.recipe_extraction import (
    AIProviderError,
    DraftPart,
    InvalidOutput,
    LimitReached,
    NotARecipe,
    NotRecipeReason,
    RecipeExtraction,
    Unavailable,
)
from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.picture_tiers import CalibrationTable, Tier
from domain.recipe_draft import IngredientLine
from domain.recipe_picture import PictureRefused
from tests.picture_bytes import jpeg_bytes
from tests.test_recipe_capture_application import (
    FakeCatalog,
    FakeNotebooks,
    kitchen_facts,
    personal_facts,
)
from tests.unit_fakes import FakeUnits

TABLE = CalibrationTable(
    low=100.0,
    high=500.0,
    labelled_set="test",
    calibrated_on=date(2026, 11, 7),
    status="calibrated",
)
IMAGE = base64.b64encode(jpeg_bytes()).decode("ascii")


def _processed() -> ProcessedPicture:
    return ProcessedPicture(
        webp=b"RIFF\x00\x00\x00\x00WEBPVP8 ",
        tier=Tier.TIER_3,
        sharpness=None,
        original_dimensions=(64, 48),
        final_dimensions=(64, 48),
        size_kb=0.1,
        steps_taken=(),
    )


def _line(name: str = "onion") -> IngredientLine:
    return IngredientLine(name=name, vague=False, quantity=2.0, unit="Unit")


class _Harness:
    def __init__(self, script, *, pipeline_script=None) -> None:
        self.user_id = uuid4()
        self.notebooks = FakeNotebooks()
        self.catalog = FakeCatalog()
        self.extractor = FakeRecipeExtractor(script=script)
        self.pipeline = FakePicturePipeline(script=pipeline_script or _processed())
        self.capture = CapturePictureRecipe(
            self.notebooks,
            self.catalog,
            RecipeExtraction(self.extractor),
            self.pipeline,
            units=FakeUnits(),
            timeout_s=10.0,
            table=TABLE,
        )
        fact, self.notebook_id = personal_facts(self.user_id)
        self.notebooks.facts[self.notebook_id] = fact
        self.catalog.names[self.notebook_id] = ["onion", "salt"]

    def run(self, *, image: str = IMAGE, handwritten: bool | None = None, notebook_id=None):
        kwargs = {} if handwritten is None else {"handwritten": handwritten}
        return self.capture.execute(
            CapturePictureCommand(
                actor_user_id=self.user_id,
                notebook_id=notebook_id or self.notebook_id,
                image_base64=image,
                language="en",
                **kwargs,
            )
        )


def _complete(**overrides) -> DraftPart:
    fields = {
        "title": "Tomato soup",
        "base_servings": 6,
        "ingredient_lines": (_line(),),
        "steps": ("Blend.",),
    }
    fields.update(overrides)
    return DraftPart(**fields)


def test_a_complete_part_is_a_checked_draft_with_the_processed_picture() -> None:
    result = _Harness(_complete()).run()
    assert isinstance(result, CapturedPictureDraft)
    assert result.recipe.title == "Tomato soup"
    assert result.recipe.base_servings == 6
    assert result.recipe.servings_estimated is False
    assert result.recipe.steps == ("Blend.",)
    assert result.picture == _processed()
    assert result.language == "en"


def test_a_part_with_no_steps_still_opens_with_the_title_and_lines() -> None:
    result = _Harness(_complete(steps=())).run()
    assert isinstance(result, CapturedPictureDraft)
    assert result.recipe.title == "Tomato soup"
    assert result.recipe.steps == ()


def test_a_part_with_no_title_opens_with_a_blank_title() -> None:
    result = _Harness(_complete(title=None)).run()
    assert isinstance(result, CapturedPictureDraft)
    assert result.recipe.title == ""


def test_no_servings_gives_four_and_marks_them_estimated() -> None:
    result = _Harness(_complete(base_servings=None)).run()
    assert isinstance(result, CapturedPictureDraft)
    assert result.recipe.base_servings == 4
    assert result.recipe.servings_estimated is True


def test_the_catalog_names_reach_the_extractor() -> None:
    harness = _Harness(_complete())
    harness.run()
    assert harness.extractor.picture_calls[0].ingredient_names == ("onion", "salt")


def test_handwritten_reaches_the_pipeline_and_defaults_to_on() -> None:
    default = _Harness(_complete())
    default.run()
    assert default.pipeline.calls[0][1] is True
    printed = _Harness(_complete())
    printed.run(handwritten=False)
    assert printed.pipeline.calls[0][1] is False


def test_a_bad_picture_is_refused_before_any_read_or_call() -> None:
    harness = _Harness(_complete())
    with pytest.raises(PictureRefused):
        harness.run(image="")
    assert harness.pipeline.calls == []
    assert harness.extractor.picture_calls == []
    assert harness.notebooks.reads == []


def test_an_unknown_notebook_gets_no_pipeline_or_assistant_call() -> None:
    harness = _Harness(_complete())
    with pytest.raises(NotebookNotFoundError):
        harness.run(notebook_id=uuid4())
    assert harness.pipeline.calls == []
    assert harness.extractor.picture_calls == []


def test_an_archived_kitchen_gets_no_pipeline_or_assistant_call() -> None:
    harness = _Harness(_complete())
    fact, notebook_id = kitchen_facts(archived=True)
    harness.notebooks.facts[notebook_id] = fact
    with pytest.raises(KitchenArchivedError):
        harness.run(notebook_id=notebook_id)
    assert harness.pipeline.calls == []
    assert harness.extractor.picture_calls == []


def test_a_pipeline_refusal_passes_through_with_no_assistant_call() -> None:
    harness = _Harness(_complete(), pipeline_script=PictureRefused("too_large"))
    with pytest.raises(PictureRefused) as caught:
        harness.run()
    assert caught.value.kind == "too_large"
    assert harness.extractor.picture_calls == []


@pytest.mark.parametrize(
    "outcome",
    [
        NotARecipe(reason=NotRecipeReason.NOT_FOOD),
        InvalidOutput(),
        Unavailable(),
        LimitReached(30),
        AIProviderError(),
    ],
    ids=["not_a_recipe", "invalid", "unavailable", "limit", "provider"],
)
def test_assistant_outcomes_come_back_unchanged(outcome: object) -> None:
    assert _Harness(outcome).run() is outcome  # type: ignore[comparison-overlap]


def test_logs_hold_the_media_type_and_counts_and_never_the_picture_or_the_draft(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(recipe_capture_picture.logger, "disabled", False)
    caplog.set_level(logging.INFO)
    marker = "PICTURE-MARKER-TITLE"
    harness = _Harness(_complete(title=marker))
    harness.run()
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "picture capture outcome=CapturedPictureDraft" in text
    assert "bytes=" in text
    assert marker not in text
    assert IMAGE[:24] not in text
