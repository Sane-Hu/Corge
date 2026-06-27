# Corge Technical Specification

This document consolidates the functional requirements, architectural subsystems, state machine execution loop, context engineering details, TUI screen map, and developer onboarding instructions for Corge.

---

## 1. Functional Requirements (FRD)

- **FR-001 Spec Gate**: Implementation remains blocked until functional requirements, acceptance criteria, and approved specification exist.
- **FR-002 Guided Spec Wizard**: Guides the engineer through business goals, user stories, functional requirements, constraints, acceptance criteria, and testing expectations.
- **FR-003 & FR-004 Repository Ingestion & Updates**: Analyzes repository structure, files, config, and build files. Updates are computed incrementally on file modifications.
- **FR-005 Repository Knowledge Graph**: A queryable representation of files, directories, classes, functions, and their dependencies.
- **FR-006 & FR-007 Memory Pyramid**:
  - **L0 Session Events**: Raw code/actions execution logs stored locally under `.agent/memory/l0/`.
  - **L1 Engineering Facts**: Repository-derived/user-derived facts stored locally in `.agent/memory.db`.
  - **L2 Scenario Memory**: Feature-specific progress and blockers locally under `.agent/memory/scenarios/` (streamable JSONL format).
  - **L3 Engineering Profile**: Coding styles/conventions derived from the repository, stored locally in `.agent/engineering_profile.md` and merged with a global profile at `~/.config/corge/global_profile.md`.
- **FR-008 Planning Phase**: Generates a step-by-step implementation plan. Execution remains blocked until approval.
- **FR-009 Human Approval Layer**: Intercepts destructive actions (`write`, `edit`, `bash`) for human consent. (`Read`) actions do not require approval.
- **FR-010 Artifact Offloading**: Large build/test logs are saved under `.agent/artifacts/` and referenced in prompts using the `artifact://` URI scheme.
- **FR-011 Context Budget Manager**: Minimizes context bloat and token cost by unconditionally clipping, deduplicating, and compacting the transcript in multi-turn sessions, using limits only as a hard fallback ceiling.
- **FR-012 Test-Based Completion**: Delivery requires all acceptance criteria to be satisfied, tests to exist and pass, and human approval.
- **FR-013 Audit Logging**: Records prompts, plans, tools, approvals, and completions for accountability. Detailed tool execution is stored locally in `.agent/audit.jsonl`, while high-level session events are tracked globally in `~/.config/corge/global_audit.jsonl`.
- **FR-014 Provider Abstraction**: Single integration point for models (DeepSeek, Ollama, OpenAI-compat) that automatically strips `<think>` tags and populates standardized usage fields.
- **FR-015 Empty Repository Bootstrapping**: Allows complete project scaffolding starting from specification.
- **FR-016 Argument of Specs (Wizard)**: Interactive Socratic specification wizard with schema tailoring based on framework. Clarifying questions are opt-in (capped at a configurable threshold to prevent cognitive overload, with support for iterative rounds) and answers are dynamically integrated via the LLM to refine the spec.
- **FR-017 Heuristic Learning**: Bayesian self-improvement via `~/.config/corge/spec_wizard_heuristics.json` to optimize spec generation across all projects based on user overrides and abandonment (using local `ArgumentationLog`).
- **FR-018 Freestyle Canvas**: Immutable snapshots, sticky notes with live graph validation, semantic gap blocking, and note types (active, later, todo).

---

## 2. Architecture & Subsystems

The codebase is organized as a modular monolith. To prevent tight coupling, modules are prohibited from importing concrete service classes from each other. Instead, cross-module communication is handled by passing frozen, slotted data models to interface ports defined as `typing.Protocol` classes in [ports.py](src/corge/contracts/ports.py).

The directory structure maps directly to the 8 logical modules defined in the system design:

*   **1. Shared Contracts Layer (`src/corge/contracts/`)**
    *   Defines the public interfaces ([ports.py](src/corge/contracts/ports.py)), dataclasses ([models.py](src/corge/contracts/models.py)), and enum states ([lifecycle.py](src/corge/contracts/lifecycle.py)).
*   **2. UI Module (`src/corge/ui/`)**
    *   A pure CLI presentation layer ([cli.py](src/corge/ui/cli.py)) with zero business logic. Contains the `DirectorySelectorApp` (using `CorgeDirectoryTree` with hidden files toggles, escape-based cancellation, and visual context preservation), and the Textual screens: `CanvasScreen`, `InteractiveDiffScreen`, `MessageScreen`, and `ConfirmScreen`.
*   **3. Agent Modules (`src/corge/agent/`)**
    *   Orchestration state machines (`SessionController`, `SpecificationAgent`, `PlanningAgent`, `CodingAgent`) and utility services (`SchemaTailor` for stack detection and YAML parser, `HeuristicUpdater` for spec optimization). The `SessionController` explicitly supports manual and backward lifecycle transitions (`transition_to()`) to gracefully handle rejections.
*   **4. Context Engineering Modules**
    *   `src/corge/context/`: Context retrieval coordination and N-1 context caching.
    *   `src/corge/prompt_assembler/`: Constructing prompts for model consumption.
    *   `src/corge/budget_manager/`: Unconditional transcript compaction, duplicate removal, and large-string clipping for multi-turn cost-savings.
    *   `src/corge/schemas/`: Tech-stack YAML definition templates.
*   **5. Knowledge & Persistence Modules**
    *   `src/corge/knowledge_graph/`: Repository structure parser and SQL database nodes/edges builder.
    *   `src/corge/memory/`: Pyramid L0 Session, L1 Facts, L2 Scenario, and L3 Profile database operations.
    *   `src/corge/artifacts/`: Heavy logging/execution output storage.
*   **6. Execution & Safety Modules**
    *   `src/corge/approval/`: Gateway logic to capture human consent decisions.
    *   `src/corge/tools/`: Stateless execution primitives (read, write, edit, bash), featuring explicit occurrence-count safety checks to prevent ambiguous file edits, and a shell command validation safety guard.
*   **7. Providers Module (`src/corge/providers/`)**
    *   Single model API adapter providing compatible interfaces for OpenAI, DeepSeek, and Ollama.
*   **8. Logging Module (`src/corge/logging/`)**
    *   Maintains audit trails and records interactive argumentation/Socratic wizard logs.

---

## 3. State Machine & Execution Loop

### Master Phases & Lifecycle States
The primary execution loop is managed by the `SessionController` across a 3-Layer Execution Flow (`MasterPhase`), orchestrating transitions between the `LifecycleState` states defined in [lifecycle.py](src/corge/contracts/lifecycle.py):

```text
  [ MasterPhase.SPECIFICATION ]
  START → REPOSITORY_SELECTION → REPOSITORY_ANALYSIS → SPEC_ENTRY → SPEC_VALIDATION → SPEC_APPROVAL 
                                                                                          │
  ┌───────────────────────────────────────────────────────────────────────────────────────┘
  │
  ▼
  [ MasterPhase.PLANNING ]
  PLAN_GENERATION → PLAN_REVIEW → PLAN_APPROVAL 
                                        │
  ┌─────────────────────────────────────┘
  │
  ▼
  [ MasterPhase.CODING ]
  EXECUTION → VERIFICATION → COMPLETION_REVIEW → DONE
```

### Nested State Machines
During the Spec and Plan master phases, nested loop state machines drive incremental refinement:

1.  **Specification Phase (`SpecState` execution)**
    *   `CANVAS_FREESTYLE`: User drafts freeform requirements and maps graph tags inside the TUI canvas.
    *   `CONCRETIZATION`: The `SpecificationAgent` compiles the canvas draft into structured fields (Acceptance Criteria, Constraints, Testing expectations).
    *   `ARGUMENTATION_DIFF`: Reconciles semantic gaps. The Socratic Wizard is optional and capped to a configurable threshold, supporting iterative rounds. Leftover gaps are formatted as inline templates inside a split-pane editor (`show_argumentation_diff`), which the user fills in manually.
    *   `SPEC_METASTABLE`: All gaps are successfully resolved or approved, and manual edits are merged. The manual editor screen is displayed unconditionally before advancing to Planning.
2.  **Planning Phase (`PlanState` execution)**
    *   `TECH_PLAN_REITERATION`: The `PlanningAgent` drafts and edits the architectural `TechnicalPlan` markdown.
    *   `STEPS_REITERATION`: Translates the architecture into granular, procedural steps (`ProceduralStep`), editing and finalizing them inside the interactive TUI split-editor.

### The 9-Step Execution Cycle
During the `EXECUTION` state, the agent loop runs the following synchronized loop:
1. **Observe**: Inspect current status and determine the next step in the approved plan.
2. **Refresh Context**: Hydrate context engine with repository updates, memory, and facts.
3. **Assemble Prompt**: Compile the ephemeral model view.
4. **Reason & Action Selection**: Model evaluates context and selects the next tool action.
5. **Approval Gateway**: Check permissions; query user for approval if action is `write`, `edit`, or `bash` (rendering live code diffs of the proposed edits via `Ctrl+D`).
6. **Execute Tool**: Invoke the authorized runtime tool.
7. **Verify Progress**: Evaluate tool output against step goals. If tool returns a non-zero exit code or error, immediately raise `ToolExecutionError`.
8. **Update Knowledge**: Extract facts, update knowledge graph, write scenario memory, and update profile rules.
9. **Repeat**: Loop back to step 1.

### Failure Path
If a tool execution fails, the orchestrator catches `ToolExecutionError`, updates scenario memory with the blocker details, suspends automated execution, and requests human intervention.

---

## 4. Context Engineering & Persistent Storage

### Database DDL & Storage Schema
Persistence is divided into repository-local state (`.agent/`) and global cross-project state (`~/.config/corge/`).

**Repository-Local Storage (`.agent/`)**

*   **Knowledge Graph Database (`.agent/repo_graph.db`)**
    Contains structural entities parsed from source code files (Python files parsed via stdlib `ast`). Uses `journal_mode=WAL` and persistent connection pooling for high-performance concurrent traversals.
    ```sql
    CREATE TABLE nodes (
        node_id TEXT PRIMARY KEY,   -- Stable identifier (e.g., "src/main.py::MyClass")
        kind    TEXT NOT NULL,      -- "file", "directory", "class", "function", "config", "test"
        path    TEXT NOT NULL,      -- Containing file path or directory path
        name    TEXT NOT NULL       -- Entity name (empty for files/directories)
    );
    CREATE TABLE edges (
        src TEXT NOT NULL,          -- Source node_id
        rel TEXT NOT NULL,          -- Relationship kind ("contains", "imports")
        dst TEXT NOT NULL,          -- Destination node_id or target module name
        PRIMARY KEY (src, rel, dst)
    );
    CREATE TABLE meta (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    ```

*   **L1 Engineering Facts Database (`.agent/memory.db`)**
    Contains facts derived dynamically during repository scan and execution loops. Uses `journal_mode=WAL` and connection pooling for concurrent writes.
    ```sql
    CREATE TABLE facts (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        fact      TEXT NOT NULL UNIQUE,
        source    TEXT NOT NULL DEFAULT '',
        timestamp TEXT NOT NULL DEFAULT ''
    );
    ```

*   **L0 Session Event Logs (`.agent/memory/l0/`)**
    Stored as append-only JSONL files named `<YmmddTHH>.jsonl` containing streams of L0 raw execution events:
    `{"kind": str, "timestamp": str, "payload": dict}`

*   **L2 Scenario Memory (`.agent/memory/scenarios/`)**
    Stored as streamable JSONL files per scenario named `<kind>.jsonl` to prevent data corruption during atomic concurrent writes, structured as streams of lines:
    `{"timestamp": str, "payload": dict}`

*   **L3 Engineering Profile (`.agent/engineering_profile.md`)**
    Markdown file containing repository-derived rules filtered by a confidence threshold ($\ge 0.5$). The Context Service dynamically parses the markdown and merges it with the global profile from `~/.config/corge/global_profile.md` to construct the execution prompt.

---

### Knowledge Graph Query Grammar
The query interface `query_graph()` processes string expressions matching the following grammar:
- `files`: Returns all nodes representing source files (`file`, `config`, `test`).
- `directories`: Returns all nodes representing folder directories (`directory`).
- `classes:<path>`: Returns all class nodes defined inside the specified file path.
- `functions:<path>`: Returns all top-level function nodes defined inside the specified file path.
- `imports:<path>`: Returns all import module targets declared within the specified file path.
- `imported_by:<path>`: Returns all file nodes that import the specified module path.
- `node:<node_id>`: Returns the exact node matching the unique identifier.
- `*` or `all`: Returns all nodes in the database.

---

### Framework-Aware Schema Tailoring
The `SchemaTailor` checks for signature configuration files to detect the tech stack. It first checks `~/.config/corge/schemas/` for custom user-defined global schemas. If none exist, it loads specialized system prompts from `src/corge/schemas/stack/`. If no signature is matched, it defaults to `generic.yaml`.

| Signature File | Detected Framework / Stack |
| :--- | :--- |
| `manage.py` / `settings.py` | `django` |
| `next.config.js` / `next.config.ts` | `nextjs` |
| `angular.json` | `angular` |
| `Cargo.toml` | `rust` |
| `go.mod` | `go` |
| `build.gradle` | `gradle` |
| `pom.xml` | `maven` |
| `artisan` | `laravel` |

---

### Bayesian Heuristic Learning
The `HeuristicUpdater` performs offline Bayesian self-improvement on spec-generation heuristics. It uses repo-local Socratic logs from the `ArgumentationLog` after spec completion or session abandonment to update the global priors stored in `~/.config/corge/spec_wizard_heuristics.json` based on global rules in `~/.config/corge/corge_heuristics.toml`. It computes an Exponentially Weighted Moving Average (EWMA) to smooth probability shifts and prevent overfitting or catastrophic forgetting:

$$P_{\text{new}} = (1 - \alpha) \cdot P_{\text{old}} + \alpha \cdot \text{Observation}$$

Where:
*   $\alpha = 1.0 - \text{decay\_rate}$ (decay rate is configured at `0.99` in `corge_heuristics.yaml`, yielding $\alpha = 0.01$).
*   $\text{Observation}$: Ratio of non-overridden interaction steps ($1.0 - \frac{\text{user overrides}}{\text{total interactions}}$).
*   **Delta Clipping safety constraint**: The change in probability is strictly capped to prevent extreme swings:
    $$\Delta P = P_{\text{new}} - P_{\text{old}}$$
    $$\text{If } |\Delta P| > \text{delta\_clip\_max} \ (0.05), \ \Delta P \leftarrow 0.05 \cdot \text{sign}(\Delta P)$$
*   **Abandonment Penalty**: If the session is abandoned prior to completion, the base engagement prior is penalized:
    $$P_{\text{engagement}} \leftarrow \max(0.0, P_{\text{engagement}} - \min(\text{delta\_clip\_max}, |\text{abandonment\_penalty}|))$$
    Where $\text{abandonment\_penalty} = -0.15$ and $\text{delta\_clip\_max} = 0.05$.

---

### Context Service & Isolation Policies
- **Markov Context Chaining**: Injects the active state from step N-1 into step N. It packages step context into the `MarkovStepContext` dataclass containing `agent_proposal`, `user_correction` for the preceding step, and a `compressed_trajectory` of previous steps (N-2 to N-Start) to allow learning from past trajectory iterations.
- **3-Layer Isolation**: Separates the specification, planning, and coding prompt contexts. To prevent overwhelming the model and instruction pollution, **Specification** phase prompts strictly omit file lists and repository facts. Detailed AST graphs, architectural files, and extensive codebases are injected only during the **Planning** and **Coding** phases. Argumentation logs and architectural plans are tailored explicitly to their active phase.

### Semantic Prompt Construction
Instead of numbered tiers, the prompt assembler constructs ephemeral prompts using phase-specific methods (`assemble_spec_prompt`, `assemble_plan_prompt`, `assemble_coding_prompt`). Context is structurally packaged into semantic XML-like tags to align with objective and constraint-based generation methodologies:
- `<objective>`: The immediate instruction or phase constraint.
- `<specification>`: Current Spec and Acceptance Criteria.
- `<engineering_profile>`: Engineering rules matching the threshold confidence.
- `<repository_facts>`: Engineering facts, Graph Queries.
- `<relevant_files>`: Relevant file paths or references.
- `<task_memory>`: Scenario Memory (discoveries, decisions, blockers).
- `<artifacts>`: URIs (`artifact://<id>`) and small summaries of large outputs.

---

## 5. TUI Screen Map

The presentation layer utilizes the `DirectorySelectorApp` and several fundamental UI screens within [cli.py](src/corge/ui/cli.py) to manage the interactive user loops. All screens are designed for keyboard-only efficiency by automatically focusing their primary interactive widgets on mount (e.g. text areas in `CanvasScreen`/`InteractiveDiffScreen`, model configuration inputs in `ProviderConfigScreen`, and the "No/Continue" buttons in `ConfirmScreen`/`MessageScreen`). All screens are overlaid with a global persistent `Header` that tracks the current agent phase and lifecycle state:

```text
                            ┌────────────────────────────────────────┐
                            │               Start /                  │
                            │         Repository Selection           │
                            └────────────────────────────────────────┘
                                                 │
                                                 ▼
                            ┌────────────────────────────────────────┐
                            │             CanvasScreen               │
                            │   - Raw freestyle brainstorming        │
                            │   - Anchored sticky notes & graph tags │
                            └────────────────────────────────────────┘
                                                 │
                                                 ▼
                            ┌────────────────────────────────────────┐
                            │         InteractiveDiffScreen          │
                            │   (Used for: Spec Gaps, Tech Plan,     │
                            │     Procedural Steps, & Approvals)     │
                            │                                        │
                            │   ┌────────────────┬────────────────┐  │
                            │   │ Left: Diff vs  │ Right: Draft   │  │
                            │   │ Prev (RichLog) │ (Editable)     │  │
                            │   └────────────────┴────────────────┘  │
                            │   │           [ Approve ]           │  │
                            │   └─────────────────────────────────┘  │
                            └────────────────────────────────────────┘
                                                 │
                                                 ▼
                            ┌────────────────────────────────────────┐
                            │             MessageScreen              │
                            │   (Used for: Execution Plans,          │
                            │     Errors, and Completion reviews)    │
                            │   ┌─────────────────────────────────┐  │
                            │   │ Title: ...                      │  │
                            │   │ Message: ...                    │  │
                            │   │          [ Continue ]           │  │
                            │   └─────────────────────────────────┘  │
                            └────────────────────────────────────────┘
```

### Screen Details and Transitions
0.  **`DirectorySelectorApp` (Repository Browser / Start Screen)**
    *   **Purpose**: Allows browsing and selecting the repository root directory before entering the agent orchestrator.
    *   **Key Widgets**: `CorgeDirectoryTree` (subclass of `DirectoryTree` filtering out hidden paths by default), `Input` for folder creation or manual path selection, and a "Select" button.
    *   **Interactive Features**:
        *   Pressing `h` toggles visibility of hidden files/folders (e.g. `.agent`, `.git`) in the directory tree.
        *   Pressing `Escape` while inputting folder paths/names safely cancels the input mode and refocuses the tree.
        *   Pressing `a` or clicking "Configure API (a)" displays `ProviderConfigScreen` to modify target or global API credentials directly on initial start.
        *   Fails gracefully if folder creation raises an OS permission/invalid character error, showing a description inline.
        *   Maintains the directory tree visible at all times during folder input.
        *   Automatically focuses the directory tree on app mount.
1.  **`CanvasScreen` (Freestyle Brainstorming / Spec Entry)**
    *   **Purpose**: Captured during the `CANVAS_FREESTYLE` sub-state. Allows free-form writing of feature goals, user stories, and technical requirements.
    *   **Key Widgets**: `TextArea` for raw text input, `Button` ("Submit to Concretization"), `Button` ("Back").
    *   **Transition**: On pressing Submit, dismisses canvas text to advance the agent to the `CONCRETIZATION` state. Pressing the "Back" button (or the `Escape` key) dismisses the screen and transitions the state machine back to the `REPOSITORY_ANALYSIS` phase. Automatically focuses the text area on mount.
2.  **`InteractiveDiffScreen` (Reused Split-Pane Editor)**
    *   **Purpose**: Side-by-side display of context references against editable drafts. This screen is highly parameterized and reused dynamically for:
        *   *Socratic Argumentation Diff*: Left pane displays raw Canvas text; right pane displays the Concretized Specification draft with unresolved semantic gaps formatted as inline templates (e.g. `[GAP: Topic]`). Prompt: "Resolve any gaps in the Specification."
        *   *Technical Plan Editor*: Left pane shows previous approved 'conceretized specification'; right pane displays the draft `TechnicalPlan` in custom `Corge`'s markdown format.
        *   *Procedural Steps Editor*: Left pane maps the `TechnicalPlan` draft; right pane renders editable `ProceduralStep` identifiers and lines. The editor parses bracketed step identifiers (e.g. `[step-auth] description`) using regex to preserve them rather than overwriting them with sequential IDs.
        *   *Human Approval Gateway*: Left pane defaults to the approval request context, toggling via `Ctrl+D` to a live diff of the proposed code change; right pane details the requested `ToolAction` parameter payload. The right pane details are set to read-only during tool approvals to prevent misleading edit text from being discarded.
    *   **Key Widgets**: Left pane defaults to a read-only `TextArea` showing reference material, but toggles via `Ctrl+D` to a hidden `RichLog` displaying a `difflib.unified_diff` of the current draft against the original draft (with syntax highlighting). Right pane is a `TextArea` for editable content, with "Approve" and "Back" / "Reject" buttons.
    *   **Transition**: On pressing Approve (or `Ctrl+A`), returning the modified content to the caller and proceeding to the next step. Pressing the customized "Back" / "Reject" button (or the `Escape` key) returns `None`, signaling the `SessionController` to execute a backward transition and request an updated plan/spec from the agent. The keybinding labels dynamically reflect the customized button text. Automatically focuses the interactive edit area on mount.
3.  **`MessageScreen` (Read-Only Dialogs / Alerts)**
    *   **Purpose**: Simulates modal notifications or summaries to the engineer.
    *   **Key Widgets**: Header `Static` title, Read-only `TextArea` showing messaging, `Button` ("Continue"), optionally `Button` ("Back") when back-navigation is supported, and optionally `Button` ("New Spec") when starting a fresh specification is supported.
    *   **Reused Cases**:
        *   *Execution Plan View*: Renders the plan steps layout while Corge's coding agent is executing the execution cycle.
        *   *Memory Events View*: Displays recent scenario memory events during the execution phase, offering buttons to continue, go back, or start a new fresh specification.
        *   *Completion Review*: Notifies that the implementation has successfully passed all acceptance and verification tests. (TODO: Add implementation status tracking and verification results in the message, per plan step)
        *   *Audit Logs view*: Parses JSONL records from `.agent/audit.jsonl` and formats them into a clean, human-readable bulleted list of proposed actions, approvals, and outcomes.
    *   **Transition**: Blocks execution until user input is provided. If the screen supports back-navigation (`show_back=True`), the user can click the "Back" button (or press `Escape`) to return to the previous screen or lifecycle state. If the screen supports starting a new spec (`show_new_spec=True`), the user can click "New Spec" (or press `n`) to reset the active spec/plan and transition back to `SPEC_ENTRY`. If there are pending approvals, it will display a message asking to approve or reject the pending approvals first with what the agent should realize first. If there are no pending approvals, it will proceed to the next step.
4.  **`ConfirmScreen` (Confirmation Dialog / Prompts)**
    *   **Purpose**: Dialog box asking for user confirmation before executing potentially destructive actions or opting into interactive workflows.
    *   **Key Widgets**: Title `Static` label, Message `TextArea`, and `Button` controls ("Yes", "No").
    *   **Reused Cases**:
        *   *Socratic Validation Opt-In*: Prompting the developer to run the clarifying questions loop when semantic gaps are detected.
        *   *Clear Backlog Notes*: Requiring verification before permanently erasing the persistent `.agent/sticky_notes.json` database.
        *   *Tool Execution Failures*: Prompting the developer to retry the active execution step after making code fixes inside their editor.
    *   **Transition**: Returns `True` (Yes) or `False` (No/Cancel/Escape) synchronously to the caller.

---

