"""Initial schema creation

Revision ID: 001
Revises:
Create Date: 2026-10-18 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create kitchens table
    op.create_table(
        'kitchens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kitchens_owner_id', 'kitchens', ['owner_id'], unique=False)

    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kitchen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['kitchen_id'], ['kitchens.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create sources table
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kitchen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('source_url', sa.String(500)),
        sa.Column('photo_filename', sa.String(255)),
        sa.Column('source_text', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['kitchen_id'], ['kitchens.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ingredients table
    op.create_table(
        'ingredients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kitchen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('canonical_name', sa.String(100), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True)),
        sa.Column('aliases', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('unit', sa.String(20), nullable=False, server_default='unit'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['kitchen_id'], ['kitchens.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ingredients_kitchen_id', 'ingredients', ['kitchen_id'], unique=False)
    op.create_index('ix_ingredients_canonical_name', 'ingredients', ['canonical_name'], unique=False)

    # Create recipes table
    op.create_table(
        'recipes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kitchen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True)),
        sa.Column('yield_servings', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('cook_time_minutes', sa.Integer()),
        sa.Column('prep_time_minutes', sa.Integer()),
        sa.Column('difficulty', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['kitchen_id'], ['kitchens.id'], ),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recipes_kitchen_id', 'recipes', ['kitchen_id'], unique=False)
    op.create_index('ix_recipes_created_by_user_id', 'recipes', ['created_by_user_id'], unique=False)

    # Create recipe_ingredients table
    op.create_table(
        'recipe_ingredients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ingredient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('is_linear', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create shopping_lists table
    op.create_table(
        'shopping_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kitchen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('headcount', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['kitchen_id'], ['kitchens.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create shopping_list_recipes table
    op.create_table(
        'shopping_list_recipes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shopping_list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ),
        sa.ForeignKeyConstraint(['shopping_list_id'], ['shopping_lists.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create members table
    op.create_table(
        'members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kitchen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['kitchen_id'], ['kitchens.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_members_kitchen_id', 'members', ['kitchen_id'], unique=False)
    op.create_index('ix_members_user_id', 'members', ['user_id'], unique=False)

    # Create invites table
    op.create_table(
        'invites',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kitchen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('accepted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['kitchen_id'], ['kitchens.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='uq_invites_token')
    )
    op.create_index('ix_invites_token', 'invites', ['token'], unique=False)
    op.create_index('ix_invites_expires_at', 'invites', ['expires_at'], unique=False)

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kitchen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['kitchen_id'], ['kitchens.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversations_kitchen_id', 'conversations', ['kitchen_id'], unique=False)
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'], unique=False)

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'], unique=False)

    # Create message_recipes table
    op.create_table(
        'message_recipes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop all tables in reverse order of creation
    op.drop_table('message_recipes')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('invites')
    op.drop_table('members')
    op.drop_table('shopping_list_recipes')
    op.drop_table('shopping_lists')
    op.drop_table('recipe_ingredients')
    op.drop_table('recipes')
    op.drop_table('ingredients')
    op.drop_table('sources')
    op.drop_table('categories')
    op.drop_table('kitchens')
