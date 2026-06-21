"""Tests for the schema tailor (Argument of Specs RD § 2, Layer 1)."""



from corge.agent.schema_tailor import SchemaTailor
from corge.contracts import (
    GraphNode,
    GraphQuery,
    GraphResult,
    GraphUpdate,
    RepositoryContext,
)


class _MockKnowledgeGraph:
    """Minimal KG stub for schema tailor tests."""

    def __init__(self, nodes: tuple[GraphNode, ...] = ()) -> None:
        self._nodes = nodes

    def build_graph(self, repository_context: RepositoryContext) -> None:
        pass

    def update_graph(self, update: GraphUpdate) -> None:
        pass

    def query_graph(self, query: GraphQuery) -> GraphResult:
        if query.expression == "files":
            return GraphResult(nodes=self._nodes)
        return GraphResult(nodes=())


def test_detect_django_framework() -> None:
    """Detects Django via manage.py in the graph."""
    nodes = (
        GraphNode(kind="file", node_id="src/main.py"),
        GraphNode(kind="file", node_id="manage.py"),
    )
    tailor = SchemaTailor(_MockKnowledgeGraph(nodes))
    assert tailor.detect_framework() == "django"


def test_detect_no_framework() -> None:
    """Returns None when no framework markers are found."""
    nodes = (GraphNode(kind="file", node_id="src/utils.py"),)
    tailor = SchemaTailor(_MockKnowledgeGraph(nodes))
    assert tailor.detect_framework() is None


def test_fetch_generic_fallback() -> None:
    """Loads generic.yaml when framework is None."""
    tailor = SchemaTailor(_MockKnowledgeGraph())
    schema = tailor.fetch_schema(None)
    assert schema.get("name") == "Generic"


def test_fetch_unknown_framework_falls_back() -> None:
    """Loads generic.yaml when framework has no matching schema file."""
    tailor = SchemaTailor(_MockKnowledgeGraph())
    schema = tailor.fetch_schema("UnknownFrameworkXYZ")
    assert schema.get("name") == "Generic"


def test_fetch_django_schema() -> None:
    """Loads django.yaml when framework is django."""
    tailor = SchemaTailor(_MockKnowledgeGraph())
    schema = tailor.fetch_schema("django")
    assert schema.get("name") == "Django"


def test_detect_laravel_framework() -> None:
    """Detects Laravel via artisan in the graph."""
    nodes = (
        GraphNode(kind="file", node_id="src/main.py"),
        GraphNode(kind="file", node_id="artisan"),
    )
    tailor = SchemaTailor(_MockKnowledgeGraph(nodes))
    assert tailor.detect_framework() == "laravel"


def test_fetch_laravel_schema() -> None:
    """Loads laravel.yaml when framework is laravel."""
    tailor = SchemaTailor(_MockKnowledgeGraph())
    schema = tailor.fetch_schema("laravel")
    assert schema.get("name") == "Laravel"

