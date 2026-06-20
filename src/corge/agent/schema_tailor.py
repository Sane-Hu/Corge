"""Tech-stack schema tailor — satisfies ``contracts.SchemaTailorPort``.

Spec traceability:
    Argument of Specs RD § 2, Layer 1  — dynamic schema tailoring
    Resolved Design § 2               — KG detects framework, fallback to generic

Loads tech-stack-specific system prompts from ``src/corge/schemas/stack/``.
Falls back to ``generic.yaml`` when the framework is unrecognised.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Any

from corge.contracts import (
    GraphQuery,
    KnowledgeGraphPort,
)

# todo: uses stdlib yaml-like parsing via json fallback.
#       Upgrade path: add PyYAML when real YAML schemas are needed.

_SCHEMAS_PACKAGE = "corge.schemas.stack"


def _load_schema_file(name: str) -> dict[str, Any]:
    """Load a schema file from the schemas/stack package.

    Returns an empty dict on missing file (safe fallback).
    """
    try:
        ref = importlib.resources.files(_SCHEMAS_PACKAGE).joinpath(name)
        text = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError, ModuleNotFoundError):
        return {}

    # Simple key: value parser for our minimal YAML subset.
    # todo: naive line parser; upgrade to PyYAML for nested schemas.
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ": " in line:
            key, value = line.split(": ", 1)
            result[key.strip()] = value.strip()
    return result


class SchemaTailor:
    """Concrete schema tailor.  Satisfies ``contracts.SchemaTailorPort``."""

    def __init__(self, knowledge_graph: KnowledgeGraphPort) -> None:
        self._kg = knowledge_graph

    def detect_framework(self) -> str | None:
        """Query the Knowledge Graph for config nodes that reveal the framework.

        Checks for known config file patterns (e.g. ``manage.py`` → Django,
        ``package.json`` → Node/React).  Returns ``None`` if unrecognised.
        """
        result = self._kg.query_graph(GraphQuery(expression="files"))

        framework_markers: dict[str, str] = {
            "manage.py": "django",
            "settings.py": "django",
            "next.config.js": "nextjs",
            "next.config.ts": "nextjs",
            "angular.json": "angular",
            "Cargo.toml": "rust",
            "go.mod": "go",
            "build.gradle": "gradle",
            "pom.xml": "maven",
        }

        for node in result.nodes:
            basename = Path(node.node_id).name
            if basename in framework_markers:
                return framework_markers[basename]

        return None

    def fetch_schema(self, framework_id: str | None) -> dict[str, object]:
        """Load the schema for the given framework, or generic fallback."""
        if framework_id:
            schema = _load_schema_file(f"{framework_id}.yaml")
            if schema:
                return schema

        return _load_schema_file("generic.yaml")
