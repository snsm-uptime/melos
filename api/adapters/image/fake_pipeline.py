"""Stand-in PicturePipeline for tests: scripted results, no decoding (spec 041)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from application.ports import ProcessedPicture
from domain.picture_tiers import CalibrationTable
from domain.recipe_picture import CheckedPicture, PictureRefused


@dataclass(slots=True)
class FakePicturePipeline:
    """Returns the scripted results in order (the last one repeats). Records each call.

    A `PictureRefused` in the script is raised instead of returned.
    """

    script: ProcessedPicture | PictureRefused | list[ProcessedPicture | PictureRefused]
    calls: list[tuple[int, bool]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _index: int = 0

    def process(
        self,
        picture: CheckedPicture,
        *,
        handwritten: bool,
        table: CalibrationTable,
    ) -> ProcessedPicture:
        with self._lock:
            self.calls.append((len(picture.data), handwritten))
            if isinstance(self.script, list):
                result = self.script[min(self._index, len(self.script) - 1)]
                self._index += 1
            else:
                result = self.script
        if isinstance(result, PictureRefused):
            raise result
        return result
