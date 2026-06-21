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

## 7. Deep Git Integration & Transactional Workspaces

- **Proposal:** Integrate Git source control commands directly into the tool runtime, context service, and agent execution loop to enable safe rollbacks, branch-isolated execution, and incremental graph updates.
- **Current Implementation:** Corge executes file edits directly on the local workspace without git awareness.
- **Upgrade Path:** Implement a Git client adapter inside the `tools` module and hook it into `SessionController` transitions (e.g., staging files, committing on step success, and reverting on verification failure).
- **8 Core Benefits of Git Integration:**
  1. **Transactional Rollbacks (Safety Gateways):** Before the coding agent starts a plan step, it can create a temporary git checkpoint. If a verification test fails or the developer rejects a diff, the agent can programmatically execute `git reset --hard` to instantly restore the workspace.
  2. **Incremental Knowledge Graph Updates (Performance):** The system can run `git diff --name-only` to identify exactly which files are modified and incrementally update only those nodes in the database.
  3. **Branch-Isolated Feature Pipelines (Parallelism):** Automatically branches off `main` (e.g., `git checkout -b corge/feature-name`) to run agent pipelines in isolation.
  4. **Author/History Ingestion (Context Mining):** Parses `git log` and `git blame` to feed historical context, author ownership, and editing frequency into the Knowledge Graph and L1 Facts.
  5. **Conflict Resolution & Automated Rebasing:** Pulls latest changes and performs automated rebasing to ensure changes are compatible with the latest main branch HEAD.
  6. **Automated, Traceable Commit Generation:** Writes clean, standardized commit messages and PR bodies describing modified files and tracing them back to approved specifications.
  7. **Diff-Based Context Pruning:** Utilizes `git diff` outputs to feed minimal changes into the prompt, preventing token bloat.
  8. **Sensitive File Guarding:** Checks `git check-ignore` to automatically block the agent from editing or committing sensitive configuration files (like `.env` or secret keys).
- **Reasoning for Deferral:** (MVP Scope) While Git integration provides robust safety nets, developers can currently manage commits and branching manually. Automated git operations are deferred until the agent runs autonomously in cloud environments where automatic rollback is critical.

## 8. IDE Integration (VS Code / JetBrains Extensions)

- **Proposal:** Build native IDE plugins for editors like VS Code and Cursor to embed Corge's spec-wizard, freestyle canvas, and interactive split diffs inline within the editor's workspace tabs.
- **Current Implementation:** Corge operates strictly as a standalone terminal process using Textual.
- **Upgrade Path:** Develop VS Code extension files calling a background JSON-RPC interface to render canvases and split editors directly inside the IDE.
- **Reasoning for Deferral:** (MVP Scope) Terminal UI (TUI) is fully functional and terminal-agnostic, meeting POC validation needs. IDE-specific custom views require maintaining separate client extension codebases.

## 9. GitHub Integration & Pull Request Automation

- **Proposal:** Integrate GitHub API support to allow Corge to autonomously open Pull Requests, post spec-gaps as PR comments, and receive user approvals or request edits directly from the GitHub interface.
- **Current Implementation:** All approvals and actions are verified locally via local standard input/Textual screens.
- **Upgrade Path:** Incorporate a GitHub API client using `PyGithub` or direct REST API requests under the `approval` and `logging` modules.
- **Reasoning for Deferral:** (MVP Scope) Local command-line execution and verification are sufficient for verifying the core flow of the modular monolith.

## 10. Decentralized Multi-Agent Swarms

- **Proposal:** Transition from a rigid, single-orchestrated `SessionController` model to a decentralized swarm of independent, specialist agents communicating asynchronously over message queues.
- **Current Implementation:** Sub-agents (`SpecificationAgent`, `PlanningAgent`, `CodingAgent`) are driven sequentially by the central `SessionController`.
- **Upgrade Path:** Implement an event-driven framework where specialist agents publish/subscribe to workspace events.
- **Reasoning for Deferral:** (Avoid Complexity) A linear execution flow is predictable, deterministic, and much easier to debug. A decentralized swarm adds coordination overhead and non-determinism, which should be avoided in the POC.

## 11. Vector Databases & Hybrid Semantic Search

- **Proposal:** Integrate a vector database (e.g., Qdrant, Chroma) to enable semantic vector retrieval and hybrid keyword-semantic queries over the repository, L0 execution logs, and L1 facts.
- **Current Implementation:** Fuzzy searching is handled using simple SQLite `LIKE` queries, and file structures are queried using AST nodes.
- **Upgrade Path:** Add a vector DB client wrapper inside the `knowledge_graph` module and introduce an embedding provider service.
- **Reasoning for Deferral:** (Avoid Dependencies) Standard SQL search and local AST relationships meet the requirements for small-to-medium codebases. Vector databases introduce heavy external container dependencies and token costs for embedding generation.

## 12. Autonomous Background Execution & Task Queues

- **Proposal:** Run agent execution plans as long-lived background workers with non-blocking queues, supporting async status polling and push notifications.
- **Current Implementation:** Agent code execution runs synchronously in a background thread of the active TUI.
- **Upgrade Path:** Integrate a background queue system (e.g., Celery, Redis, or simple async worker loops) to execute plans headlessly.
- **Reasoning for Deferral:** (YAGNI) The Textual worker thread model (`@work`) sufficiently isolates the UI from execution blocks without requiring extra infrastructure.

## 13. Cloud Collaboration & Remote Storage

- **Proposal:** Migrate local databases (`.agent/`) and artifact directories to remote, centralized databases (PostgreSQL) and cloud object stores (AWS S3) to support multi-user team workspaces.
- **Current Implementation:** All state databases, graphs, scenarios, logs, and artifacts are stored locally in the `.agent/` folder.
- **Upgrade Path:** Reimplement the repository knowledge graph, memory store, and artifact storage ports to target remote cloud connections.
- **Reasoning for Deferral:** (MVP Scope) Local disk persistence is robust and enables offline execution. Cloud infrastructure is a multi-tenant product requirement that is not needed for individual developer tool evaluation.
