"""Repository knowledge graph — satisfies ``contracts.KnowledgeGraphPort``."""

from corge.contracts import GraphQuery, GraphUpdate, RepositoryContext


class KnowledgeGraph:
    """Concrete knowledge graph stub.  Satisfies ``contracts.KnowledgeGraphPort``."""

    def build_graph(self, repository_context: RepositoryContext) -> None:
        raise NotImplementedError

    def update_graph(self, update: GraphUpdate) -> None:
        raise NotImplementedError

    def query_graph(self, query: GraphQuery) -> object:
        raise NotImplementedError
