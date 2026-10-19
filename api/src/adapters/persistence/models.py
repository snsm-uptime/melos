"""SQLAlchemy models for all entities"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    UUID,
    Boolean,
    Enum,
    Float,
    ARRAY,
    Index,
)
from sqlalchemy.orm import relationship
from src.adapters.persistence.base import Base
import enum


class Kitchen(Base):
    __tablename__ = "kitchens"
    __table_args__ = (
        Index("ix_kitchens_owner_id", "owner_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    content_language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    recipes = relationship("Recipe", back_populates="kitchen")
    ingredients = relationship("Ingredient", back_populates="kitchen")
    categories = relationship("Category", back_populates="kitchen")
    shopping_lists = relationship("ShoppingList", back_populates="kitchen")
    conversations = relationship("Conversation", back_populates="kitchen")
    members = relationship("Member", back_populates="kitchen")
    invites = relationship("Invite", back_populates="kitchen")


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    kitchen = relationship("Kitchen", back_populates="categories")
    ingredients = relationship("Ingredient", back_populates="category")


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        Index("ix_ingredients_kitchen_id", "kitchen_id"),
        Index("ix_ingredients_canonical_name", "canonical_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    canonical_name = Column(String(100), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    aliases = Column(ARRAY(String), default=list)
    unit = Column(String(20), default="unit")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    kitchen = relationship("Kitchen", back_populates="ingredients")
    category = relationship("Category", back_populates="ingredients")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        Index("ix_recipes_kitchen_id", "kitchen_id"),
        Index("ix_recipes_created_by_user_id", "created_by_user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    title = Column(String(200), nullable=False)
    instructions = Column(Text, nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"))
    yield_servings = Column(Integer, default=1)
    cook_time_minutes = Column(Integer)
    prep_time_minutes = Column(Integer)
    difficulty = Column(String(20), default="medium")
    embedding = Column(ARRAY(Float), default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=False)
    is_deleted = Column(Boolean, default=False)

    kitchen = relationship("Kitchen", back_populates="recipes")
    source = relationship("Source", back_populates="recipes")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="recipe")
    shopping_list_recipes = relationship("ShoppingListRecipe", back_populates="recipe")
    message_recipes = relationship("MessageRecipe", back_populates="recipe")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    is_linear = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    source_type = Column(String(20), nullable=False)  # 'text', 'url', 'photo'
    source_url = Column(String(500))
    photo_filename = Column(String(255))
    source_text = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    recipes = relationship("Recipe", back_populates="source")


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    headcount = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=False)

    kitchen = relationship("Kitchen", back_populates="shopping_lists")
    recipes = relationship("ShoppingListRecipe", back_populates="shopping_list")


class ShoppingListRecipe(Base):
    __tablename__ = "shopping_list_recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    shopping_list_id = Column(UUID(as_uuid=True), ForeignKey("shopping_lists.id"), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)

    shopping_list = relationship("ShoppingList", back_populates="recipes")
    recipe = relationship("Recipe", back_populates="shopping_list_recipes")


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        Index("ix_members_kitchen_id", "kitchen_id"),
        Index("ix_members_user_id", "user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(String(20), nullable=False)  # 'visitor', 'member', 'owner'
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    kitchen = relationship("Kitchen", back_populates="members")


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (
        Index("ix_invites_token", "token"),
        Index("ix_invites_expires_at", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    email = Column(String(255), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    role = Column(String(20), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    accepted = Column(Boolean, default=False)

    kitchen = relationship("Kitchen", back_populates="invites")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_kitchen_id", "kitchen_id"),
        Index("ix_conversations_user_id", "user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id = Column(UUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    kitchen = relationship("Kitchen", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    author = Column(String(20), nullable=False)  # 'user', 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    recipe_citations = relationship("MessageRecipe", back_populates="message")


class MessageRecipe(Base):
    __tablename__ = "message_recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)

    message = relationship("Message", back_populates="recipe_citations")
    recipe = relationship("Recipe", back_populates="message_recipes")
