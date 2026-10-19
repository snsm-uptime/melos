#!/usr/bin/env python3
"""
Development user seeding script.

When SEED_DEV_USER=1, creates a test user, kitchen, recipes, and conversation history
to support immediate UI/chat testing without manual data entry.

Environment variables:
- SEED_DEV_USER: Set to "1" to enable seeding
- SEED_DEV_USER_EMAIL: Email of test user (default: dev@example.com)
- SEED_DEV_USER_PASSWORD: Password (default: dev-password)
- SEED_DEV_USER_ALIAS: Display alias (default: Dev User)
- SEED_DEV_USER_KITCHEN: Kitchen name (default: Dev Kitchen)

Expected seed data (per spec.md Development Seeding):
1. User: email, hashed password, alias
2. Kitchen: kitchen_name, owner=user
3. Membership: user membership in kitchen
4. 3–5 Recipes: with ingredients and steps
5. Cart: 2 recipes, 1 meal each, 2 people
6. Shopping List: archived, with items
7. Conversations: 4–6 messages with timestamps
"""

import os
import sys
from datetime import datetime, timedelta


def seed_dev_data():
    """Seed development database with test user, kitchen, recipes, and conversations."""
    if os.getenv('SEED_DEV_USER') != '1':
        return
    
    # Configuration from environment
    email = os.getenv('SEED_DEV_USER_EMAIL', 'dev@example.com')
    password = os.getenv('SEED_DEV_USER_PASSWORD', 'dev-password')
    alias = os.getenv('SEED_DEV_USER_ALIAS', 'Dev User')
    kitchen_name = os.getenv('SEED_DEV_USER_KITCHEN', 'Dev Kitchen')
    
    print(f"[SEED] Development data for {alias} ({email})...")
    
    # TODO: Implement after DB schema and models are finalized
    # Schema implementation in Phase 3 (Task T044)


if __name__ == '__main__':
    seed_dev_data()
