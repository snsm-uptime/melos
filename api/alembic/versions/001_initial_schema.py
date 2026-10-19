"""Initial schema with 21 entities.

Revision ID: 001
Create Date: 2026-10-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
    
    # Reused from finance-dashboard
    op.create_table(
        'user',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('alias', sa.String(255)),
        sa.Column('theme', sa.String(50), default='system'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    op.create_table(
        'session',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
    )
    
    op.create_table(
        'password_reset_token',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('used', sa.Boolean, default=False),
    )
    
    op.create_table(
        'email_verification',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('verified', sa.Boolean, default=False),
    )
    
    op.create_table(
        'preferences',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), unique=True, nullable=False),
        sa.Column('theme', sa.String(50), default='system'),
        sa.Column('locale', sa.String(10), default='en'),
    )
    
    # Melos-specific entities
    op.create_table(
        'kitchen',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    op.create_table(
        'membership',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False),
        sa.Column('kitchen_id', sa.Integer, sa.ForeignKey('kitchen.id'), nullable=False),
        sa.Column('role', sa.String(50), default='member'),
        sa.Column('joined_at', sa.DateTime, default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'kitchen_id', name='unique_user_kitchen'),
    )
    
    op.create_table(
        'invite',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('kitchen_id', sa.Integer, sa.ForeignKey('kitchen.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('accepted', sa.Boolean, default=False),
    )
    
    op.create_table(
        'category',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('kitchen_id', sa.Integer, sa.ForeignKey('kitchen.id'), nullable=False),
    )
    
    op.create_table(
        'ingredient',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category_id', sa.Integer, sa.ForeignKey('category.id')),
        sa.Column('kitchen_id', sa.Integer, sa.ForeignKey('kitchen.id'), nullable=False),
    )
    
    op.create_table(
        'recipe',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('kitchen_id', sa.Integer, sa.ForeignKey('kitchen.id'), nullable=False),
        sa.Column('servings', sa.Integer, default=1),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    op.create_table(
        'recipe_ingredient',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('recipe_id', sa.Integer, sa.ForeignKey('recipe.id'), nullable=False),
        sa.Column('ingredient_id', sa.Integer, sa.ForeignKey('ingredient.id'), nullable=False),
        sa.Column('quantity', sa.String(100)),
        sa.Column('unit', sa.String(50)),
    )
    
    op.create_table(
        'step',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('recipe_id', sa.Integer, sa.ForeignKey('recipe.id'), nullable=False),
        sa.Column('order', sa.Integer, nullable=False),
        sa.Column('description', sa.Text, nullable=False),
    )
    
    op.create_table(
        'cart',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('kitchen_id', sa.Integer, sa.ForeignKey('kitchen.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    op.create_table(
        'cart_item',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('cart_id', sa.Integer, sa.ForeignKey('cart.id'), nullable=False),
        sa.Column('recipe_id', sa.Integer, sa.ForeignKey('recipe.id')),
        sa.Column('meals', sa.Integer, default=1),
        sa.Column('people', sa.Integer, default=1),
    )
    
    op.create_table(
        'shopping_list',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('kitchen_id', sa.Integer, sa.ForeignKey('kitchen.id'), nullable=False),
        sa.Column('archived', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    op.create_table(
        'shopping_list_item',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('shopping_list_id', sa.Integer, sa.ForeignKey('shopping_list.id'), nullable=False),
        sa.Column('ingredient_id', sa.Integer, sa.ForeignKey('ingredient.id')),
        sa.Column('quantity', sa.String(100)),
        sa.Column('checked', sa.Boolean, default=False),
    )
    
    op.create_table(
        'conversation',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('kitchen_id', sa.Integer, sa.ForeignKey('kitchen.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    op.create_table(
        'message',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('conversation_id', sa.Integer, sa.ForeignKey('conversation.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id')),
        sa.Column('role', sa.String(50), nullable=False),  # 'user' or 'assistant'
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    op.create_table(
        'recipe_embedding',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('recipe_id', sa.Integer, sa.ForeignKey('recipe.id'), nullable=False),
        sa.Column('embedding', Vector(768)),  # pgvector
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    op.create_table(
        'source',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('recipe_id', sa.Integer, sa.ForeignKey('recipe.id')),
        sa.Column('url', sa.String(500)),
        sa.Column('title', sa.String(255)),
    )
    
    # Create indices
    op.create_index('idx_user_email', 'user', ['email'])
    op.create_index('idx_session_user_id', 'session', ['user_id'])
    op.create_index('idx_recipe_kitchen_id', 'recipe', ['kitchen_id'])
    op.create_index('idx_membership_user_kitchen', 'membership', ['user_id', 'kitchen_id'])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('source')
    op.drop_table('recipe_embedding')
    op.drop_table('message')
    op.drop_table('conversation')
    op.drop_table('shopping_list_item')
    op.drop_table('shopping_list')
    op.drop_table('cart_item')
    op.drop_table('cart')
    op.drop_table('step')
    op.drop_table('recipe_ingredient')
    op.drop_table('recipe')
    op.drop_table('ingredient')
    op.drop_table('category')
    op.drop_table('invite')
    op.drop_table('membership')
    op.drop_table('kitchen')
    op.drop_table('preferences')
    op.drop_table('email_verification')
    op.drop_table('password_reset_token')
    op.drop_table('session')
    op.drop_table('user')
    
    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS pgvector")

