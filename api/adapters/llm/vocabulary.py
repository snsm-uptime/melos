"""Load the controlled recipe vocabulary from disk and hand it to the domain as parsed data.

The domain never reads files. This adapter reads categories.yaml and cuisine.yml
and passes their contents to `domain.recipe_draft.build_vocabulary`.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from domain.recipe_draft import Vocabulary, build_vocabulary

VOCABULARY_DIR = Path(__file__).resolve().parents[2] / "domain"


class _VocabularyLoader(yaml.SafeLoader):
    """YAML 1.2 booleans only: PyYAML would read the words y, n, on and off as booleans."""


_VocabularyLoader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_VocabularyLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def _read_yaml(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_VocabularyLoader)


def load_vocabulary(directory: Path = VOCABULARY_DIR) -> Vocabulary:
    """Read categories.yaml and cuisine.yml from `directory` and build the vocabulary."""
    categories = _read_yaml(directory / "categories.yaml")
    cuisine = _read_yaml(directory / "cuisine.yml")
    return build_vocabulary(categories, cuisine)


def load_vocabulary_documents(directory: Path = VOCABULARY_DIR) -> tuple[dict, dict]:
    """The parsed categories.yaml and cuisine.yml, for the vocabulary answer (FR-011)."""
    return (
        _read_yaml(directory / "categories.yaml"),
        _read_yaml(directory / "cuisine.yml"),
    )
