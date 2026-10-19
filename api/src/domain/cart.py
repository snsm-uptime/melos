"""Shopping list and cart logic"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from uuid import UUID


@dataclass
class CartItem:
    """Item in shopping cart"""
    ingredient_id: UUID
    ingredient_name: str
    category: str
    quantity: float
    unit: str
    is_linear: bool
    recipe_ids: List[UUID] = field(default_factory=list)


@dataclass
class ShoppingCart:
    """Shopping list with consolidation and scaling logic"""
    items: Dict[UUID, CartItem] = field(default_factory=dict)
    headcount: int = 1

    def add_recipe_items(
        self,
        recipe_ingredients: List[tuple[UUID, str, str, float, str, bool]],
        recipe_yield: int,
        recipe_id: UUID
    ):
        """Add recipe ingredients to cart with scaling"""
        scale_factor = self.headcount / max(recipe_yield, 1)

        for ing_id, ing_name, category, quantity, unit, is_linear in recipe_ingredients:
            scaled_qty = (quantity * scale_factor) if is_linear else quantity

            if ing_id in self.items:
                # Merge with existing item
                self.items[ing_id].quantity += scaled_qty
                if recipe_id not in self.items[ing_id].recipe_ids:
                    self.items[ing_id].recipe_ids.append(recipe_id)
            else:
                # Create new item
                self.items[ing_id] = CartItem(
                    ingredient_id=ing_id,
                    ingredient_name=ing_name,
                    category=category,
                    quantity=scaled_qty,
                    unit=unit,
                    is_linear=is_linear,
                    recipe_ids=[recipe_id]
                )

    def get_items_by_category(self) -> Dict[str, List[CartItem]]:
        """Group items by category for display"""
        grouped = {}
        for item in self.items.values():
            if item.category not in grouped:
                grouped[item.category] = []
            grouped[item.category].append(item)
        return grouped

    def get_non_linear_items(self) -> List[CartItem]:
        """Get items that need manual review"""
        return [item for item in self.items.values() if not item.is_linear]
