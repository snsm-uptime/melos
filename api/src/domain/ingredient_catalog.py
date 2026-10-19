"""Ingredient catalog and normalization"""
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID
import difflib


@dataclass
class Ingredient:
    """Standardized ingredient"""
    id: UUID
    kitchen_id: UUID
    canonical_name: str
    category_id: Optional[UUID] = None
    aliases: List[str] = None
    unit: str = "unit"

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class IngredientCatalog:
    """Manages ingredient name normalization"""

    SIMILARITY_THRESHOLD = 0.80

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize ingredient name for matching"""
        return name.lower().strip()

    @staticmethod
    def find_match(
        name: str,
        candidates: List[Ingredient],
        threshold: float = SIMILARITY_THRESHOLD
    ) -> Optional[Ingredient]:
        """Find best matching ingredient by name similarity"""
        if not candidates:
            return None

        normalized_name = IngredientCatalog.normalize_name(name)
        best_match = None
        best_ratio = 0

        for candidate in candidates:
            # Check exact match with aliases
            if normalized_name in [IngredientCatalog.normalize_name(alias)
                                   for alias in candidate.aliases]:
                return candidate

            # Check canonical name similarity
            ratio = difflib.SequenceMatcher(
                None,
                normalized_name,
                IngredientCatalog.normalize_name(candidate.canonical_name)
            ).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate

        return best_match if best_ratio >= threshold else None

    @staticmethod
    def suggest_merges(
        ingredients: List[Ingredient],
        threshold: float = 0.75
    ) -> List[tuple[Ingredient, Ingredient]]:
        """Suggest ingredients to merge based on similarity"""
        merges = []
        for i, ing1 in enumerate(ingredients):
            for ing2 in ingredients[i + 1:]:
                ratio = difflib.SequenceMatcher(
                    None,
                    IngredientCatalog.normalize_name(ing1.canonical_name),
                    IngredientCatalog.normalize_name(ing2.canonical_name)
                ).ratio()

                if ratio >= threshold:
                    merges.append((ing1, ing2))

        return merges
