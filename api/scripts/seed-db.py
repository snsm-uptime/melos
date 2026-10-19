"""Database seeding script for testing"""
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

# Add api src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from api.src.adapters.persistence.database import engine, SessionLocal
from api.src.adapters.persistence.models import (
    Kitchen, Category, Ingredient, Recipe, RecipeIngredient,
    Member, Invite, Source
)


def seed_database():
    """Populate database with test data"""
    session: Session = SessionLocal()

    try:
        # Check if data already exists
        existing_kitchens = session.query(Kitchen).count()
        if existing_kitchens > 0:
            print("Database already seeded, skipping...")
            return

        # Create test kitchen
        kitchen_id = uuid4()
        owner_id = uuid4()
        test_kitchen = Kitchen(
            id=kitchen_id,
            name="Test Kitchen",
            owner_id=owner_id,
            content_language="en",
            timezone="UTC"
        )
        session.add(test_kitchen)
        session.flush()

        # Create categories
        categories = {}
        category_names = ["Produce", "Dairy", "Pantry", "Protein", "Spices"]
        for cat_name in category_names:
            cat = Category(
                id=uuid4(),
                kitchen_id=kitchen_id,
                name=cat_name
            )
            session.add(cat)
            session.flush()
            categories[cat_name] = cat.id

        # Create ingredients
        ingredients = {}
        ingredient_data = [
            ("Flour - All Purpose", "Pantry", "cup"),
            ("Sugar - Granulated", "Pantry", "cup"),
            ("Butter", "Dairy", "cup"),
            ("Eggs", "Dairy", "unit"),
            ("Milk", "Dairy", "cup"),
            ("Salt", "Spices", "tsp"),
            ("Vanilla Extract", "Pantry", "tsp"),
            ("Chocolate Chips", "Pantry", "cup"),
            ("Chicken Breast", "Protein", "lb"),
            ("Olive Oil", "Pantry", "tbsp"),
        ]

        for ing_name, category, default_unit in ingredient_data:
            ing = Ingredient(
                id=uuid4(),
                kitchen_id=kitchen_id,
                canonical_name=ing_name,
                category_id=categories[category],
                unit=default_unit,
                aliases=[]
            )
            session.add(ing)
            session.flush()
            ingredients[ing_name] = ing.id

        # Create a source
        source = Source(
            id=uuid4(),
            kitchen_id=kitchen_id,
            source_type="text",
            source_text="Test recipe from seed"
        )
        session.add(source)
        session.flush()

        # Create test recipe
        recipe = Recipe(
            id=uuid4(),
            kitchen_id=kitchen_id,
            title="Chocolate Chip Cookies",
            instructions="1. Mix dry ingredients\n2. Add wet ingredients\n3. Add chocolate chips\n4. Bake at 350F for 12 minutes",
            source_id=source.id,
            yield_servings=24,
            cook_time_minutes=12,
            prep_time_minutes=10,
            difficulty="easy",
            created_by_user_id=owner_id
        )
        session.add(recipe)
        session.flush()

        # Add recipe ingredients
        recipe_ingredients_data = [
            ("Flour - All Purpose", 2.25, "cup", True),
            ("Butter", 1.0, "cup", True),
            ("Sugar - Granulated", 0.75, "cup", True),
            ("Eggs", 2, "unit", True),
            ("Vanilla Extract", 1.0, "tsp", True),
            ("Chocolate Chips", 2.0, "cup", True),
            ("Salt", 1.0, "tsp", False),
        ]

        for ing_name, quantity, unit, is_linear in recipe_ingredients_data:
            ri = RecipeIngredient(
                id=uuid4(),
                recipe_id=recipe.id,
                ingredient_id=ingredients[ing_name],
                quantity=quantity,
                unit=unit,
                is_linear=is_linear
            )
            session.add(ri)

        # Create test member
        member = Member(
            id=uuid4(),
            kitchen_id=kitchen_id,
            user_id=owner_id,
            role="owner",
            is_active=True
        )
        session.add(member)

        # Create test invite (7 days from now)
        invite = Invite(
            id=uuid4(),
            kitchen_id=kitchen_id,
            email="test@example.com",
            token=str(uuid4()),
            role="member",
            expires_at=datetime.utcnow() + timedelta(days=7),
            accepted=False
        )
        session.add(invite)

        # Commit all changes
        session.commit()
        print(f"✓ Database seeded successfully")
        print(f"  Kitchen: Test Kitchen ({kitchen_id})")
        print(f"  Owner: {owner_id}")
        print(f"  Categories: {len(categories)}")
        print(f"  Ingredients: {len(ingredients)}")
        print(f"  Recipes: 1")
        print(f"  Members: 1")

    except Exception as e:
        session.rollback()
        print(f"✗ Error seeding database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
