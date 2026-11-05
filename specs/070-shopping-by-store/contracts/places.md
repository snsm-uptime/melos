# Contract: places (new, all scoped to the signed-in person)

Every route needs a session (401 otherwise). BFF routes mirror them under `ui/app/api/me/...`.

## GET /me/places
200 `{"defaults": ["supermarket","farmers_market","butcher","fish_market","bakery","pharmacy","other"], "custom": [{"id","name"}]}` (custom sorted by name).

## POST /me/places  `{"name": "Asian market"}`
201 `{"id","name"}`. 422 `place_name_invalid` (empty or over 40), 409 `place_name_taken` (same as a default or own place, case and accents ignored), 409 `place_limit` (30 already).

## PATCH /me/places/{id}  `{"name": "..."}`
200 `{"id","name"}`. Same errors; 404 when not the caller's.

## DELETE /me/places/{id}
204. Its ingredients fall back to Supermarket. 404 when not the caller's. (The ui asks for confirmation first.)

## GET /me/ingredient-places
200 `{"items": [{"name": "tomato", "place": PlaceRef}]}`: every name from research R7, alphabetical, with the caller's place (Supermarket when unset).

## PUT /me/ingredient-places  `{"name": "Tomatoes", "place": PlaceRef}`
200 `{"name": "tomato", "place": PlaceRef}` (name returned normalized). 422 `invalid_place`, 422 `ingredient_name_invalid` (empty after normalizing).

## GET /me/place-sources
200 `{"items": [{"user_id","alias"}]}`: people sharing a kitchen or personal notebook with the caller, caller excluded.

## POST /me/places/copy  `{"source_user_id": "uuid"}`
200 with the new `GET /me/places` body. Replaces all the caller's custom places and ingredient places with a copy (snapshot, no link). 404 when the source is not in `/me/place-sources`.
