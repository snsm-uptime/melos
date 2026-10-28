# Contract: Recipe list routes

Both routes need a signed-in session with an alias (same as the notebook read routes). They are reads; they write nothing.

## `GET /notebooks/{notebook_id}/recipes`

Query: `page` (integer, default 1, at least 1), `q` (text, default empty, at most 100 characters).

**200**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Lentil soup",
      "author_alias": "ana",
      "ingredient_count": 7,
      "notebook_id": "uuid",
      "notebook_name": "ana's Notebook",
      "created_at": "2026-10-27T12:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 12,
  "total": 1,
  "total_pages": 1
}
```
- `author_alias` is `null` when the author's account is gone.
- No matches or no recipes: `items` is `[]`, `total` 0, `page` 1, `total_pages` 1. The ui tells "empty notebook" from "no match" by whether `q` was sent.
- `page` past the last page returns the last page; the body's `page` is the one returned.

**404** `{"detail": "...", "code": "notebook_not_found"}` for a missing notebook and for one the caller may not read (identical body).

**422** `{"code": "invalid_page"}` when `page` is below 1 or not a number; `{"code": "invalid_query"}` when `q` is over 100 characters.

## `GET /notebooks/kitchens/{kitchen_id}/recipes`

Same query and body. Items come from every notebook of the kitchen, never from a personal notebook. A kitchen with no notebook returns the empty page and creates nothing.

**404** `{"detail": "...", "code": "kitchen_not_found"}` for a missing kitchen and for a non-member (identical body).

An archived kitchen the caller belongs to answers 200.

## Behaviour

- Order: `created_at` descending, then `id` descending.
- Filter: see [data-model.md](../data-model.md) "Filter rules".
- Surrounding spaces in `q` are ignored; a `q` of spaces only behaves as empty.
