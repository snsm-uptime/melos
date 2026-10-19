"""JSON-LD extractor for schema.org/Recipe"""
import json
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup


class JSONLDExtractor:
    """Extract schema.org/Recipe from HTML via JSON-LD"""

    @staticmethod
    def extract(html: str) -> Optional[Dict[str, Any]]:
        """
        Extract first Recipe schema.org/Recipe from JSON-LD
        Returns dict with title, ingredients, instructions, yields, etc.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Find all script tags with type=application/ld+json
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)

                    # Handle both single object and array
                    items = data if isinstance(data, list) else [data]

                    for item in items:
                        if JSONLDExtractor._is_recipe(item):
                            return JSONLDExtractor._normalize(item)
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception:
            pass

        return None

    @staticmethod
    def _is_recipe(obj: Any) -> bool:
        """Check if object is a Recipe type"""
        if not isinstance(obj, dict):
            return False

        type_val = obj.get("@type", "")
        if isinstance(type_val, list):
            return "Recipe" in type_val
        return type_val == "Recipe"

    @staticmethod
    def _normalize(recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize recipe object to standard format"""
        return {
            "title": recipe.get("name", ""),
            "instructions": JSONLDExtractor._extract_instructions(recipe),
            "ingredients": JSONLDExtractor._extract_ingredients(recipe),
            "yield_servings": JSONLDExtractor._extract_yield(recipe),
            "cook_time_minutes": JSONLDExtractor._extract_cook_time(recipe),
            "prep_time_minutes": JSONLDExtractor._extract_prep_time(recipe),
        }

    @staticmethod
    def _extract_ingredients(recipe: Dict) -> str:
        """Extract ingredients as text"""
        ingredients = recipe.get("recipeIngredient", [])
        if isinstance(ingredients, list):
            return "\n".join(ingredients)
        return str(ingredients)

    @staticmethod
    def _extract_instructions(recipe: Dict) -> str:
        """Extract instructions as text"""
        instructions = recipe.get("recipeInstructions", [])

        if isinstance(instructions, list):
            # Handle array of instruction objects
            steps = []
            for item in instructions:
                if isinstance(item, str):
                    steps.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("description", "")
                    if text:
                        steps.append(text)
            return "\n".join(steps)
        else:
            return str(instructions)

    @staticmethod
    def _extract_yield(recipe: Dict) -> int:
        """Extract yield servings"""
        yield_val = recipe.get("recipeYield", 1)
        if isinstance(yield_val, list):
            yield_val = yield_val[0]

        if isinstance(yield_val, str):
            # Extract number from string like "4 servings"
            import re
            match = re.search(r"(\d+)", yield_val)
            return int(match.group(1)) if match else 1

        return int(yield_val) if yield_val else 1

    @staticmethod
    def _extract_cook_time(recipe: Dict) -> Optional[int]:
        """Extract cook time in minutes"""
        return JSONLDExtractor._parse_duration(recipe.get("cookTime"))

    @staticmethod
    def _extract_prep_time(recipe: Dict) -> Optional[int]:
        """Extract prep time in minutes"""
        return JSONLDExtractor._parse_duration(recipe.get("prepTime"))

    @staticmethod
    def _parse_duration(duration: Any) -> Optional[int]:
        """Parse ISO 8601 duration to minutes"""
        if not duration:
            return None

        try:
            import re
            # Parse PT2H30M format
            match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", str(duration))
            if match:
                hours, minutes, seconds = match.groups()
                total_minutes = (int(hours) * 60 if hours else 0) + (int(minutes) if minutes else 0)
                return total_minutes if total_minutes else None
        except:
            pass

        return None
