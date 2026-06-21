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

## 5. Decoupled Terminal Orchestration (Tmux Integration)

- **Proposal:** Implement an automated shell script to spin up a multi-pane tmux workspace. This decouples the core Textual TUI from the agent execution, test suite watchers, and database logs, running them as independent programs under a single tmux connection.
- **Current Implementation:** Corge's TUI runs as a single process in the foreground. There is no automated multi-pane environment orchestration.
- **Upgrade Path:** Integrate a startup wrapper script (e.g., `run_decoupled.sh`) that initializes a new tmux session and splits it into coordinated panes.
- **8 Core Benefits of Decoupling:**
  1. **Network Disconnection Resilience (Session Continuity):** Detaching from tmux or losing SSH connections does not interrupt the long-running coding agent or corrupt the TUI state.
  2. **Coordinated Multi-Client Monitoring:** Multiple developers can attach to the same tmux session simultaneously to monitor agent progress or perform collaborative reviews in real time.
  3. **Privilege Separation & Sandboxing:** The TUI can run on the host with user terminal privileges while the agent execution commands run inside a restricted container, bridging via tmux IPC.
  4. **Zero-Interference Terminal I/O:** Redirects raw command output (stdout/stderr) from tools and compilers to secondary panes, preventing corruption of the Textual TUI's alternate screen buffer.
  5. **Granular Process Signaling:** Stuck commands or infinite loops can be interrupted via `SIGINT` (Ctrl+C) inside the tool/container pane without killing or freezing the orchestrating Corge app.
  6. **Headless Execution with "Human-on-Demand" Hooking:** Runs the agent headlessly on cron or webhooks, only prompting the user when it hits a step that requires approval.
  7. **Programmatic Host-Side Terminal Control:** By mounting the host's tmux socket into the docker container, the agent can dynamically open new panes, flash terminal alerts, and adjust screen layout.
  8. **Resource Isolation & Profiling:** Allows launching parallel profiling tools, file system monitors, and SQL database shells side-by-side with the main agent without bloating the core process memory.
- **Reasoning for Deferral:** (MVP Scope) While a multi-pane tmux environment significantly enhances debugging and reliability, developers can currently run tmux manually and execute commands in multiple terminals. Automated scripting of the layout is a workflow convenience best deferred until multi-user and containerized staging deployment requirements are formalized.

## 6. Containerization & OS-Agnostic Execution (Docker Image)

- **Proposal:** Package Corge as a Docker image using standard multi-stage builds and `uv` to ensure consistent, OS-agnostic execution across different environments.
- **Current Implementation:** Corge runs locally using `uv run` on the host machine. There is no packaging or container setup in the codebase.
- **Upgrade Path:** Create a `Dockerfile` that sets up a secure, containerized environment with the required dependencies and configures it to run either natively or under a host-side tmux session.
- **Key Benefits of Containerization:**
  * **OS-Agnostic Consistency:** Guarantees that the Python environment, packages, and TUI dependencies render and behave identically on Linux, macOS, and Windows.
  * **Safe & Clean Sandboxing:** Isolates agent tool execution (e.g., executing arbitrary bash commands or file writes) from the host's files and processes.
  * **Zero-Setup Onboarding:** Eliminates the need for manual python/uv setups, path configurations, or SQLite library compatibility verification on a developer's local machine.
  * **Reproducible Test Environment:** Prevents "it works on my machine" issues for verification and test phases.
- **Reasoning for Deferral:** (MVP Scope) The current codebase is successfully run and validated in a virtual environment on the host via `uv`. Creating and managing a Docker release channel is not strictly required until the tool is packaged for general usage across external teams or remote CI/CD systems.
