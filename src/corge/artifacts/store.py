"""Artifact offloading boundaries."""

from pathlib import Path

from corge.contracts import ArtifactReference


class ArtifactStore:
    """Artifact responsibilities from docs/04-module-contracts.md."""

    def store_artifact(self, path: Path, summary: str) -> ArtifactReference:
        raise NotImplementedError

    def retrieve_artifact(self, reference: ArtifactReference) -> str:
        raise NotImplementedError

    def summarize_artifact(self, reference: ArtifactReference) -> str:
        raise NotImplementedError

