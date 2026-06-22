"""Artifact offloading - satisfies ``contracts.ArtifactStorePort``.

Spec traceability:
    FRD FR-010  - large build/test logs are offloaded under
                  ``.agent/artifacts/`` and referenced with
                  ``artifact://`` URIs.
    09-context  - prompts receive artifact URIs and summaries, not raw
                  large content.

Storage layout:
    .agent/artifacts/index.json      metadata keyed by artifact id
    .agent/artifacts/objects/<id>.*  copied artifact payloads

The store is intentionally local and dependency-free. Future remote object
stores can replace this class without changing callers because the public
surface is the ``ArtifactStorePort`` protocol.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from corge.contracts import ArtifactReference

_URI_PREFIX = "artifact://"
_HASH_BYTES = 16


def _now() -> str:
    """Return current UTC time as ISO-8601 text."""
    return datetime.now(UTC).isoformat()


def _artifact_id(content: bytes) -> str:
    """Return a short, stable identifier for artifact content."""
    return hashlib.sha256(content).hexdigest()[: _HASH_BYTES * 2]


def _safe_suffix(path: Path) -> str:
    """Return a conservative suffix for the stored object filename."""
    suffix = path.suffix.lower()
    if suffix and suffix[1:].replace("-", "").replace("_", "").isalnum():
        return suffix
    return ".txt"


class ArtifactStore:
    """Concrete artifact store. Satisfies ``contracts.ArtifactStorePort``.

    ``root`` is the repository root. All persistent writes go under
    ``root/.agent/artifacts/``. If omitted, the current working directory is
    used so the class remains easy to instantiate in contract checks.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path(".")
        self._artifact_dir = self._root / ".agent" / "artifacts"
        self._objects_dir = self._artifact_dir / "objects"
        self._index_path = self._artifact_dir / "index.json"

    def store_artifact(self, path: Path, summary: str) -> ArtifactReference:
        """Copy ``path`` into artifact storage and return its prompt reference.

        The source path must point to an existing file. The returned
        ``ArtifactReference`` carries only the ``artifact://`` URI and caller
        supplied summary so prompt assembly can include compact Tier 5 context.
        """
        source = path.expanduser()
        if not source.is_file():
            raise FileNotFoundError(f"Artifact source does not exist: {path}")

        content = source.read_bytes()
        artifact_id = _artifact_id(content)
        stored_name = f"{artifact_id}{_safe_suffix(source)}"
        stored_path = self._objects_dir / stored_name

        self._objects_dir.mkdir(parents=True, exist_ok=True)
        if not stored_path.exists():
            shutil.copyfile(source, stored_path)

        index = self._load_index()
        index[artifact_id] = {
            "uri": f"{_URI_PREFIX}{artifact_id}",
            "summary": summary.strip(),
            "original_path": str(source),
            "stored_path": str(stored_path.relative_to(self._artifact_dir)),
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "created_at": index.get(artifact_id, {}).get("created_at", _now()),
        }
        self._write_index(index)

        return ArtifactReference(
            uri=f"{_URI_PREFIX}{artifact_id}",
            summary=summary.strip(),
        )

    def retrieve_artifact(self, reference: ArtifactReference) -> str:
        """Return the raw stored artifact content as text.

        Artifacts are decoded as UTF-8 with replacement so build logs with odd
        bytes remain retrievable instead of failing prompt/context workflows.
        """
        metadata = self._metadata_for(reference)
        stored_path = self._artifact_dir / str(metadata["stored_path"])
        if not stored_path.is_file():
            raise FileNotFoundError(f"Artifact payload is missing: {reference.uri}")
        return stored_path.read_text(encoding="utf-8", errors="replace")

    def summarize_artifact(self, reference: ArtifactReference) -> str:
        """Return the compact summary associated with an artifact reference."""
        try:
            metadata = self._metadata_for(reference)
        except KeyError:
            return reference.summary
        return str(metadata.get("summary") or reference.summary)

    def _metadata_for(self, reference: ArtifactReference) -> dict[str, Any]:
        artifact_id = self._id_from_uri(reference.uri)
        index = self._load_index()
        metadata = index.get(artifact_id)
        if not isinstance(metadata, dict):
            raise KeyError(f"Unknown artifact reference: {reference.uri}")
        return metadata

    def _id_from_uri(self, uri: str) -> str:
        if not uri.startswith(_URI_PREFIX):
            raise ValueError(f"Artifact URI must start with {_URI_PREFIX!r}: {uri}")
        artifact_id = uri[len(_URI_PREFIX):].strip()
        if not artifact_id or any(ch in artifact_id for ch in "/\\:"):
            raise ValueError(f"Invalid artifact id in URI: {uri}")
        return artifact_id

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if not self._index_path.exists():
            return {}
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            str(key): value
            for key, value in data.items()
            if isinstance(value, dict)
        }

    def _write_index(self, index: dict[str, dict[str, Any]]) -> None:
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        self._index_path.write_text(
            json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
