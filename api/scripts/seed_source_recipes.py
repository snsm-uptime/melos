"""Real recipes for the dev seed, read from a running Melos app (production) over its API.

Signs in as SEED_RECIPES_SOURCE_EMAIL at SEED_RECIPES_SOURCE_URL, lists the account's
notebooks, keeps those named in SEED_RECIPES_SOURCE_NOTEBOOKS (all when unset), and reads
each recipe's title, servings, ingredient lines and steps. One copy per title. No author,
alias, notebook or id is kept, and nothing is written to disk. Any failure returns [].
"""

from __future__ import annotations

import logging
import os
import unicodedata

import httpx
from domain.recipe_draft import IngredientLine

logger = logging.getLogger(__name__)

SeedRecipe = tuple[tuple, tuple[str, ...]]


def title_key(text: str) -> str:
    """Case- and accent-insensitive key, so "Galletas Clásicas" matches "galletas clasicas"."""
    decomposed = unicodedata.normalize("NFD", text.strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def _recipe(detail: dict) -> SeedRecipe:
    lines = tuple(
        IngredientLine(
            name=line["name"],
            vague=bool(line["vague"]),
            quantity=line.get("quantity"),
            unit=line.get("unit"),
            size=line.get("size"),
            note=line.get("note"),
            preparation=line.get("preparation"),
        )
        for line in detail["ingredient_lines"]
    )
    units = tuple(sorted({line.unit for line in lines if line.unit}))
    recipe = (detail["title"].strip(), int(detail["base_servings"]), lines, tuple(detail["steps"]))
    return recipe, units


def _fetch(client: httpx.Client, notebook_names: set[str]) -> list[SeedRecipe]:
    notebooks = client.get("/api/notebooks").raise_for_status().json()["notebooks"]
    chosen = [n for n in notebooks if not notebook_names or title_key(n["name"]) in notebook_names]
    if notebook_names:
        missing = notebook_names - {title_key(n["name"]) for n in chosen}
        if missing:
            logger.warning("Seed recipes: notebooks not found for the source account: %s", missing)

    recipes: list[SeedRecipe] = []
    seen: set[str] = set()
    for notebook in chosen:
        page, total_pages = 1, 1
        while page <= total_pages:
            listing = (
                client.get(f"/api/notebooks/{notebook['id']}/recipes", params={"page": page})
                .raise_for_status()
                .json()
            )
            total_pages = listing["total_pages"]
            for card in listing["items"]:
                key = title_key(card["title"])
                if key in seen:
                    continue
                seen.add(key)
                detail = client.get(f"/api/recipes/{card['id']}").raise_for_status().json()
                recipes.append(_recipe(detail))
            page += 1
    return recipes


def fetch_source_recipes() -> list[SeedRecipe]:
    """Recipes from the source app, each with the units it needs kept; [] when unset or failing."""
    base_url = (os.environ.get("SEED_RECIPES_SOURCE_URL") or "").strip().rstrip("/")
    email = (os.environ.get("SEED_RECIPES_SOURCE_EMAIL") or "").strip()
    password = os.environ.get("SEED_RECIPES_SOURCE_PASSWORD") or ""
    if not base_url:
        return []
    if not email or not password:
        logger.warning("Seed recipes: SEED_RECIPES_SOURCE_EMAIL/PASSWORD missing — skipping")
        return []
    names = {
        title_key(name)
        for name in (os.environ.get("SEED_RECIPES_SOURCE_NOTEBOOKS") or "").split(",")
        if name.strip()
    }
    try:
        with httpx.Client(base_url=base_url, timeout=20.0, follow_redirects=True) as client:
            client.post(
                "/api/auth/sign-in", json={"email": email, "password": password}
            ).raise_for_status()
            try:
                recipes = _fetch(client, names)
            finally:
                client.post("/api/auth/sign-out")
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        # Never log the response body or credentials; the class and status are enough.
        logger.warning("Seed recipes: fetch from %s failed (%s)", base_url, type(error).__name__)
        return []
    logger.info("Seed recipes: fetched %d recipe(s) from %s", len(recipes), base_url)
    return recipes
