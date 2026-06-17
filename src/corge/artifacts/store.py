"""Artifact offloading — satisfies ``contracts.ArtifactStorePort``."""

from pathlib import Path

from corge.contracts import ArtifactReference


class ArtifactStore:
    """Concrete artifact store stub.  Satisfies ``contracts.ArtifactStorePort``."""

    def store_artifact(self, path: Path, summary: str) -> ArtifactReference:
        raise NotImplementedError

    def retrieve_artifact(self, reference: ArtifactReference) -> str:
        raise NotImplementedError

    def summarize_artifact(self, reference: ArtifactReference) -> str:
        raise NotImplementedError
