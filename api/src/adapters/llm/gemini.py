"""Google Gemini adapter for recipe extraction, embeddings, and chat"""
from typing import List, Dict, Optional
from uuid import UUID
from api.src.application.ports import RecipeExtractor, Embedder, ChatModel
from api.src.domain.recipe import ParseResult, RecipeDraft
from api.src.settings import settings


class GeminiRecipeExtractor(RecipeExtractor):
    """Extract recipes using Gemini Vision and Language models"""

    async def extract_from_text(self, text: str) -> ParseResult:
        """Extract recipe from plain text via Gemini"""
        # TODO: Call Gemini API with text extraction prompt
        # Use TOON encoding for structured output
        return ParseResult(
            is_recipe=False,
            reason="Not implemented yet"
        )

    async def extract_from_url(self, url: str) -> ParseResult:
        """Extract recipe from URL via JSON-LD or text fallback"""
        # TODO: Fetch page, try JSON-LD first, fall back to text extraction
        return ParseResult(
            is_recipe=False,
            reason="Not implemented yet"
        )

    async def extract_from_image(self, image_data: bytes) -> ParseResult:
        """Extract recipe from image via Gemini Vision"""
        # TODO: Call Gemini Vision API with image, OCR -> text -> parse
        return ParseResult(
            is_recipe=False,
            reason="Not implemented yet"
        )


class GeminiEmbedder(Embedder):
    """Generate embeddings using Gemini Embeddings API"""

    async def embed_recipe(self, recipe_text: str) -> List[float]:
        """Generate embedding for recipe"""
        # TODO: Call Gemini Embeddings API
        return [0.0] * 768  # Placeholder

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for query"""
        # TODO: Call Gemini Embeddings API
        return [0.0] * 768  # Placeholder


class GeminiChatModel(ChatModel):
    """Chat model for kitchen assistant via Gemini"""

    async def answer(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]]
    ) -> tuple[str, List[UUID]]:
        """Answer question grounded in kitchen context"""
        # TODO: Build prompt with TOON context, call Gemini, parse response
        return "Not implemented yet", []
