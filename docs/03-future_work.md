# Future Work & Known Ceilings

This document tracks intentional simplifications across the codebase marked with `todo:` comments. In accordance with the project's lazy engineering principles (`AGENTS.md`), these items represent deferred implementations. They should only be addressed when their respective "ceilings" are hit or explicit requirements arise.

## 1. Multiple Think Blocks in Model Output

- **Location:** `src/corge/providers/provider.py`
- **Current Implementation:** A naive `find` and slice is used to strip out a single `<think>...</think>` block from model responses.
- **Upgrade Path:** Replace with a regex substitution (e.g., `re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)`).
- **Reasoning for Deferral:** (YAGNI) The parser currently strips single `<think>` blocks correctly. There is no evidence that our currently supported reasoning models emit multiple think blocks in a single response. Adding regular expressions increases complexity unnecessarily until this ceiling is actually encountered.

## 2. Advanced Knowledge Graph Searches

- **Location:** `src/corge/knowledge_graph/graph.py`
- **Current Implementation:** The `fuzzy_search` method uses a simple SQL `LIKE` scan across the SQLite nodes table.
- **Upgrade Path:** Embeddings or natural language-to-graph traversal when vector DB support is added.
- **Reasoning for Deferral:** (YAGNI) The application currently does not require or integrate a vector database. The simple `LIKE` scan sufficiently supports the current Discovery Mode fuzzy search use cases. A heavy architectural upgrade to vector embeddings should only be performed when explicitly required by a specification.

## 3. Nested YAML Schema Parsing

- **Location:** `src/corge/agent/schema_tailor.py`
- **Current Implementation:** A naive line parser splits flat `key: value` pairs manually without any third-party dependencies.
- **Upgrade Path:** Add `PyYAML` dependency to handle nested, true YAML schemas.
- **Reasoning for Deferral:** (Avoid Dependencies) All current framework schemas (e.g., `generic.yaml`, `django.yaml`, `laravel.yaml`) are entirely flat key-value pairs. Since there are no nested structures, the naive 10-line parser works flawlessly. Upgrading to `PyYAML` would introduce a third-party dependency, which violates our rule of avoiding new dependencies unless absolutely necessary.

## 4. Knowledge Graph Enhancements

The initial Knowledge Graph implementation (`src/corge/knowledge_graph/graph.py`) includes several `todo:` markers indicating Level B structural simplifications:

- **Cross-File Edges:** 
  - *Current:* Only simple `contains` and `imports` edges are supported.
  - *Upgrade Path:* Walk `ast.ClassDef.bases` across the node table to resolve names to file-qualified node IDs for `extends`, `implements`, and `tests` edges.
- **Nested Functions:**
  - *Current:* Only top-level functions are parsed to avoid noise.
  - *Upgrade Path:* Track parent scopes to support nested functions.
- **Database Initialization:**
  - *Current:* If the DB is empty (`update_graph` called before `build_graph`), it quietly no-ops.
  - *Upgrade Path:* Raise a descriptive error or accept the root path as a parameter.
- **Query Performance:**
  - *Current:* Linear table scans are used for text queries.
  - *Upgrade Path:* Add B-tree indexes on `(kind)`, `(path)`, and `(src, rel)` once query volume grows.

**Reasoning for Deferral:** (MVP Scope & YAGNI) The current parser meets the approved requirements for repository ingestion. Additional graph depth and index optimizations are not strictly required until the graph size scales significantly or downstream agents require deeper AST-level structural context.
