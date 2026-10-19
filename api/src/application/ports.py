"""Port interfaces for external services (dependency inversion)"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from src.domain.recipe import ParseResult, RecipeDraft


class RecipeExtractor(ABC):
    """Extract recipes from various sources"""

    @abstractmethod
    async def extract_from_text(self, text: str) -> ParseResult:
        """Extract recipe from plain text"""
        pass

    @abstractmethod
    async def extract_from_url(self, url: str) -> ParseResult:
        """Extract recipe from URL"""
        pass

    @abstractmethod
    async def extract_from_image(self, image_data: bytes) -> ParseResult:
        """Extract recipe from image via OCR"""
        pass


class Embedder(ABC):
    """Generate embeddings for semantic search"""

    @abstractmethod
    async def embed_recipe(self, recipe_text: str) -> List[float]:
        """Generate embedding for recipe"""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        pass


class ChatModel(ABC):
    """LLM chat interface for answering questions"""

    @abstractmethod
    async def answer(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]]
    ) -> tuple[str, List[UUID]]:
        """Answer question grounded in kitchen context, return (answer, cited_recipe_ids)"""
        pass


class PageFetcher(ABC):
    """Safely fetch and parse web pages"""

    @abstractmethod
    async def fetch_page(self, url: str) -> str:
        """Fetch page HTML with SSRF safety"""
        pass


class PdfRenderer(ABC):
    """Render shopping lists to PDF"""

    @abstractmethod
    async def render_shopping_list(
        self,
        kitchen_name: str,
        items: Dict[str, List[Dict[str, Any]]],
        headcount: int
    ) -> bytes:
        """Render shopping list template to PDF bytes"""
        pass


class RecipeRepository(ABC):
    """Recipe persistence interface"""

    @abstractmethod
    async def create(self, recipe: Any) -> UUID:
        pass

    @abstractmethod
    async def get(self, recipe_id: UUID, kitchen_id: UUID) -> Optional[Any]:
        pass

    @abstractmethod
    async def list_by_kitchen(self, kitchen_id: UUID) -> List[Any]:
        pass

    @abstractmethod
    async def delete(self, recipe_id: UUID, kitchen_id: UUID) -> bool:
        pass


class IngredientRepository(ABC):
    """Ingredient persistence interface"""

    @abstractmethod
    async def create(self, ingredient: Any) -> UUID:
        pass

    @abstractmethod
    async def get(self, ingredient_id: UUID, kitchen_id: UUID) -> Optional[Any]:
        pass

    @abstractmethod
    async def list_by_kitchen(self, kitchen_id: UUID) -> List[Any]:
        pass


class KitchenRepository(ABC):
    """Kitchen persistence interface"""

    @abstractmethod
    async def create(self, kitchen: Any) -> UUID:
        pass

    @abstractmethod
    async def get(self, kitchen_id: UUID) -> Optional[Any]:
        pass


class MemberRepository(ABC):
    """Member persistence interface"""

    @abstractmethod
    async def list_by_kitchen(self, kitchen_id: UUID) -> List[Any]:
        pass

    @abstractmethod
    async def get_member(self, kitchen_id: UUID, user_id: UUID) -> Optional[Any]:
        pass
