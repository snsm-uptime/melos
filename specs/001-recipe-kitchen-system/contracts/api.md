# API Contracts: Melos Recipe & Kitchen System

**Phase**: 1 (Design)  
**Date**: 2026-10-18  
**Status**: Draft

---

## Overview

This document specifies the REST API endpoints and request/response shapes for the Melos platform. All endpoints are prefixed with `/api/`. Authentication is session-based via httpOnly cookie (reused from finance-dashboard).

## General Rules

- All requests/responses use JSON
- All timestamps are ISO 8601 (UTC)
- All UUIDs are returned as strings
- Error responses use standard HTTP status codes
- Pagination uses `limit` (default 20, max 100) and `offset` query params
- Empty collections return `[]`

## Authentication Endpoints (Reused)

These endpoints are inherited from finance-dashboard; no Melos-specific changes.

- `POST /api/auth/register` — Create account
- `POST /api/auth/sign-in` — Sign in with email + password
- `POST /api/auth/sign-out` — Revoke session
- `GET /api/auth/session` — Get current user + session
- `GET /api/auth/me` — Get profile (alias, photo, theme)
- `PATCH /api/auth/me` — Update profile
- `POST /api/auth/password-reset/request` — Request password reset
- `POST /api/auth/password-reset/confirm` — Confirm with token
- `POST /api/auth/verify/request` — Request email verification (if enabled)
- `POST /api/auth/verify/confirm` — Confirm email

---

## Kitchen Endpoints

### GET /api/kitchens

List all kitchens the user is a member of.

**Query Params**:
```
limit: Integer (default 20)
offset: Integer (default 0)
```

**Response (200 OK)**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "My Kitchen",
      "owner_id": "uuid",
      "owner_name": "Alice",
      "created_at": "2026-10-18T12:00:00Z",
      "role": "owner",
      "member_count": 2,
      "recipe_count": 5
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

**Error (401)**: Not authenticated

---

### GET /api/kitchens/{id}

Get details of a specific kitchen.

**Response (200 OK)**:
```json
{
  "id": "uuid",
  "name": "My Kitchen",
  "owner_id": "uuid",
  "owner_name": "Alice",
  "created_at": "2026-10-18T12:00:00Z",
  "updated_at": "2026-10-18T12:00:00Z",
  "role": "owner",
  "timezone": "UTC",
  "content_language": "en",
  "members": [
    {
      "user_id": "uuid",
      "user_name": "Alice",
      "role": "owner",
      "joined_at": "2026-10-18T12:00:00Z"
    },
    {
      "user_id": "uuid",
      "user_name": "Bob",
      "role": "member",
      "joined_at": "2026-10-18T13:00:00Z"
    }
  ],
  "recipe_count": 5,
  "ingredient_count": 42
}
```

**Error (404)**: Kitchen not found (or user not a member)
**Error (401)**: Not authenticated

---

### POST /api/kitchens

Create a new kitchen (signed-up user automatically becomes owner).

**Request Body**:
```json
{
  "name": "Family Kitchen"
}
```

**Response (201 Created)**:
```json
{
  "id": "uuid",
  "name": "Family Kitchen",
  "owner_id": "uuid",
  "created_at": "2026-10-18T12:00:00Z",
  "role": "owner"
}
```

**Error (400)**: Validation error (name too long, empty, etc.)
**Error (401)**: Not authenticated

---

## Recipe Endpoints

### POST /api/kitchens/{id}/recipes/draft

Capture a recipe (text, URL, or photo) and return a draft without saving.

**Request Body** (multipart/form-data):
```json
{
  "source_type": "text" | "url" | "photo",
  "source": "recipe text content | https://example.com/recipe | [photo file]"
}
```

**Response (200 OK)**:
```json
{
  "is_recipe": true,
  "reason": null,
  "draft": {
    "title": "Chocolate Chip Cookies",
    "instructions": "1. Mix ingredients. 2. Bake...",
    "yield_servings": 24,
    "cook_time_minutes": 12,
    "prep_time_minutes": 15,
    "difficulty": "easy",
    "ingredients": [
      {
        "name": "Flour - All Purpose",
        "quantity": 2.25,
        "unit": "cup",
        "notes": null,
        "is_linear": true,
        "is_new": false,
        "ingredient_id": "uuid"
      },
      {
        "name": "Butter",
        "quantity": 1,
        "unit": "cup",
        "notes": "(softened)",
        "is_linear": true,
        "is_new": false,
        "ingredient_id": "uuid"
      }
    ],
    "source": {
      "type": "text",
      "url": null
    }
  }
}
```

**Response (200 OK - Extraction Failed)**:
```json
{
  "is_recipe": false,
  "reason": "Content does not appear to be a recipe. It looks like a shopping list.",
  "draft": null
}
```

**Error (400)**: Invalid source (empty, bad URL format, unsupported image format)
**Error (404)**: Kitchen not found
**Error (401)**: Not authenticated or user not a member

---

### POST /api/kitchens/{id}/recipes

Save a recipe (from draft or create new).

**Request Body**:
```json
{
  "title": "Chocolate Chip Cookies",
  "instructions": "1. Mix ingredients. 2. Bake...",
  "yield_servings": 24,
  "cook_time_minutes": 12,
  "prep_time_minutes": 15,
  "difficulty": "easy",
  "ingredients": [
    {
      "ingredient_id": "uuid (if existing) or null (if new)",
      "canonical_name": "Flour - All Purpose (only if new)",
      "quantity": 2.25,
      "unit": "cup",
      "notes": null,
      "is_linear": true,
      "category": "Pantry (only if ingredient is new)"
    }
  ],
  "source": {
    "type": "text" | "url" | "photo",
    "url": "optional if type=url"
  }
}
```

**Response (201 Created)**:
```json
{
  "id": "uuid",
  "kitchen_id": "uuid",
  "title": "Chocolate Chip Cookies",
  "instructions": "...",
  "yield_servings": 24,
  "cook_time_minutes": 12,
  "prep_time_minutes": 15,
  "difficulty": "easy",
  "created_by_user_id": "uuid",
  "created_at": "2026-10-18T12:00:00Z",
  "source_id": "uuid"
}
```

**Error (400)**: Validation error (missing title, invalid ingredients, etc.)
**Error (403)**: User not a member or insufficient role
**Error (404)**: Kitchen not found

---

### GET /api/kitchens/{id}/recipes

List recipes in a kitchen.

**Query Params**:
```
limit: Integer (default 20)
offset: Integer (default 0)
```

**Response (200 OK)**:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Chocolate Chip Cookies",
      "yield_servings": 24,
      "cook_time_minutes": 12,
      "created_by_user_name": "Alice",
      "created_at": "2026-10-18T12:00:00Z",
      "ingredient_count": 12
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

---

### GET /api/kitchens/{id}/recipes/{recipe_id}

Get full details of a recipe.

**Response (200 OK)**:
```json
{
  "id": "uuid",
  "kitchen_id": "uuid",
  "title": "Chocolate Chip Cookies",
  "instructions": "...",
  "yield_servings": 24,
  "cook_time_minutes": 12,
  "prep_time_minutes": 15,
  "difficulty": "easy",
  "created_by_user_id": "uuid",
  "created_at": "2026-10-18T12:00:00Z",
  "source": {
    "type": "text",
    "url": null
  },
  "ingredients": [
    {
      "ingredient_id": "uuid",
      "canonical_name": "Flour - All Purpose",
      "quantity": 2.25,
      "unit": "cup",
      "notes": null,
      "is_linear": true
    }
  ]
}
```

---

### PATCH /api/kitchens/{id}/recipes/{recipe_id}

Update a recipe.

**Request Body** (partial):
```json
{
  "title": "New Title",
  "yield_servings": 36
}
```

**Response (200 OK)**: Updated recipe (same shape as GET)

---

### DELETE /api/kitchens/{id}/recipes/{recipe_id}

Delete a recipe. Only members can delete; owners can delete any recipe.

**Response (204 No Content)**

**Error (403)**: User cannot delete this recipe

---

## Ingredient Endpoints

### GET /api/kitchens/{id}/ingredients

List ingredients in a kitchen's catalog.

**Query Params**:
```
limit: Integer (default 20)
offset: Integer (default 0)
category_id: UUID (optional filter)
```

**Response (200 OK)**:
```json
{
  "items": [
    {
      "id": "uuid",
      "canonical_name": "Flour - All Purpose",
      "category_name": "Pantry",
      "aliases": ["flour", "APF", "all-purpose"],
      "unit": "cup",
      "recipe_count": 5
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### POST /api/kitchens/{id}/ingredients/normalize

Normalize an ingredient name against the kitchen's catalog.

**Request Body**:
```json
{
  "name": "all-purpose flour"
}
```

**Response (200 OK)**:
```json
{
  "matched": true,
  "ingredient_id": "uuid",
  "canonical_name": "Flour - All Purpose",
  "confidence": 0.95,
  "suggestion": null
}
```

Or (if no match):
```json
{
  "matched": false,
  "ingredient_id": null,
  "canonical_name": null,
  "confidence": 0.0,
  "suggestion": "Create new ingredient 'Flour (alternative name)'"
}
```

---

## Shopping List Endpoints

### POST /api/kitchens/{id}/shopping-list

Generate a consolidated, scaled shopping list from selected recipes.

**Request Body**:
```json
{
  "recipe_ids": ["uuid", "uuid", "uuid"],
  "headcount": 6
}
```

**Response (200 OK)**:
```json
{
  "id": "uuid",
  "kitchen_id": "uuid",
  "recipe_ids": ["uuid", "uuid", "uuid"],
  "headcount": 6,
  "generated_at": "2026-10-18T12:00:00Z",
  "generated_by_user_id": "uuid",
  "items": [
    {
      "ingredient_id": "uuid",
      "canonical_name": "Flour - All Purpose",
      "category": "Pantry",
      "quantity": 5.25,
      "unit": "cup",
      "recipes_using": ["Chocolate Chip Cookies", "Bread"]
    },
    {
      "ingredient_id": "uuid",
      "canonical_name": "Salt",
      "category": "Pantry",
      "quantity": 0,
      "unit": "tsp",
      "notes": "to taste (review manually)",
      "recipes_using": ["Bread"]
    }
  ]
}
```

---

### GET /api/kitchens/{id}/shopping-list/{list_id}

Retrieve a saved shopping list.

**Response (200 OK)**: Same shape as POST response

---

### POST /api/kitchens/{id}/shopping-list/{list_id}/export

Export a shopping list as PDF.

**Query Params**:
```
format: "pdf" | "markdown" (default "pdf")
```

**Response (200 OK - PDF)**:
- Content-Type: application/pdf
- Body: PDF binary stream

**Response (200 OK - Markdown)**:
- Content-Type: text/markdown
- Body: Markdown text

---

## Conversation Endpoints

### GET /api/kitchens/{id}/conversations

List conversations in a kitchen.

**Response (200 OK)**:
```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "created_at": "2026-10-18T12:00:00Z",
      "message_count": 5,
      "last_message_at": "2026-10-18T12:15:00Z"
    }
  ]
}
```

---

### POST /api/kitchens/{id}/conversations

Create a new conversation.

**Request Body**:
```json
{
  "initial_message": "What recipes can we make with eggs and flour?"
}
```

**Response (201 Created)**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "created_at": "2026-10-18T12:00:00Z"
}
```

---

### GET /api/kitchens/{id}/conversations/{conversation_id}

Get a conversation with all messages.

**Query Params**:
```
limit: Integer (default 20, recent messages)
offset: Integer (default 0)
```

**Response (200 OK)**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "created_at": "2026-10-18T12:00:00Z",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "What recipes can we make with eggs and flour?",
      "created_at": "2026-10-18T12:00:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "You can make pancakes, waffles, or pasta...",
      "cited_recipe_ids": ["uuid", "uuid"],
      "created_at": "2026-10-18T12:01:00Z"
    }
  ]
}
```

---

### POST /api/kitchens/{id}/conversations/{conversation_id}/messages

Add a message to a conversation.

**Request Body**:
```json
{
  "content": "What about gluten-free options?",
  "mentioned_recipe_ids": ["uuid"] (optional)
}
```

**Response (201 Created)**:
```json
{
  "id": "uuid",
  "role": "user",
  "content": "What about gluten-free options?",
  "created_at": "2026-10-18T12:05:00Z"
}
```

The system will respond asynchronously with an assistant message in the conversation.

---

## Member & Invite Endpoints

### GET /api/kitchens/{id}/members

List members of a kitchen.

**Response (200 OK)**:
```json
{
  "items": [
    {
      "user_id": "uuid",
      "user_name": "Alice",
      "role": "owner",
      "joined_at": "2026-10-18T12:00:00Z"
    },
    {
      "user_id": "uuid",
      "user_name": "Bob",
      "role": "member",
      "joined_at": "2026-10-18T13:00:00Z"
    }
  ]
}
```

---

### POST /api/kitchens/{id}/invites

Send an invite to a new member.

**Request Body**:
```json
{
  "email": "bob@example.com",
  "role": "member"
}
```

**Response (201 Created)**:
```json
{
  "id": "uuid",
  "email": "bob@example.com",
  "role": "member",
  "invite_link": "https://melos.example.com/invites/accept?token=...",
  "expires_at": "2026-10-25T12:00:00Z"
}
```

---

### POST /api/invites/accept

Accept an invite (guest endpoint, no auth required initially).

**Request Body**:
```json
{
  "token": "..."
}
```

**Response (200 OK)**:
```json
{
  "kitchen_id": "uuid",
  "kitchen_name": "Family Kitchen",
  "role": "member",
  "action": "login_or_signup_then_join"
}
```

---

## Error Response Format

All errors follow this standard:

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "details": {}
}
```

Example:
```json
{
  "error": "validation_error",
  "message": "Recipe title is required",
  "details": {
    "field": "title"
  }
}
```

---

## Status Codes Summary

| Code | Use Case |
|------|----------|
| 200 | Success (GET, PATCH) |
| 201 | Resource created (POST) |
| 204 | No content (DELETE) |
| 400 | Validation error |
| 401 | Not authenticated |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 429 | Rate limited (auth endpoints) |
| 500 | Server error |
