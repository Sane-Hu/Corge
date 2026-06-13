"""Repository knowledge graph boundaries."""

from corge.contracts import GraphQuery, GraphUpdate, RepositoryContext


class KnowledgeGraph:
    """Knowledge graph responsibilities from docs/04-module-contracts.md."""

    def build_graph(self, repository_context: RepositoryContext) -> None:
        raise NotImplementedError

    def update_graph(self, update: GraphUpdate) -> None:
        raise NotImplementedError

    def query_graph(self, query: GraphQuery) -> object:
        raise NotImplementedError

