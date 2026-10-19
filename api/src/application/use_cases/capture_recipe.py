"""Use case for capturing recipes from text, URL, or photo"""
from typing import Optional
from uuid import UUID
from src.domain.recipe import ParseResult, RecipeDraft
from src.application.ports import RecipeExtractor, PageFetcher


class CaptureRecipeUseCase:
    """Coordinate recipe extraction from various sources"""

    def __init__(
        self,
        extractor: RecipeExtractor,
        page_fetcher: PageFetcher
    ):
        self.extractor = extractor
        self.page_fetcher = page_fetcher

    async def capture_from_text(self, text: str) -> ParseResult:
        """Extract recipe from pasted text"""
        return await self.extractor.extract_from_text(text)

    async def capture_from_url(self, url: str) -> ParseResult:
        """Extract recipe from URL (fetch page then extract)"""
        return await self.extractor.extract_from_url(url)

    async def capture_from_photo(self, image_data: bytes) -> ParseResult:
        """Extract recipe from photo via OCR"""
        return await self.extractor.extract_from_image(image_data)
