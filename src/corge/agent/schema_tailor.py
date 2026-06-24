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


def _parse_schema_text(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ": " in line:
            key, value = line.split(": ", 1)
            result[key.strip()] = value.strip()
    return result

def _load_schema_file(name: str, global_dir: Path | None = None) -> dict[str, Any]:
    """Load a schema file from global config or the schemas/stack package.

    Returns an empty dict on missing file (safe fallback).
    """
    if global_dir:
        global_path = global_dir / "schemas" / name
        if global_path.exists():
            try:
                return _parse_schema_text(global_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    try:
        ref = importlib.resources.files(_SCHEMAS_PACKAGE).joinpath(name)
        text = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError, ModuleNotFoundError):
        return {}

    return _parse_schema_text(text)


class SchemaTailor:
    """Concrete schema tailor.  Satisfies ``contracts.SchemaTailorPort``."""

    def __init__(self, knowledge_graph: KnowledgeGraphPort, global_dir: Path | None = None) -> None:
        self._kg = knowledge_graph
        self._global_dir = global_dir

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
            "artisan": "laravel",
        }

        for node in result.nodes:
            basename = Path(node.node_id).name
            if basename in framework_markers:
                return framework_markers[basename]

        return None

    def fetch_schema(self, framework_id: str | None) -> dict[str, object]:
        """Load the schema for the given framework, or generic fallback."""
        if framework_id:
            schema = _load_schema_file(f"{framework_id}.yaml", self._global_dir)
            if schema:
                return schema

        return _load_schema_file("generic.yaml", self._global_dir)
