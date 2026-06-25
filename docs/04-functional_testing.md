# Corge Functional Testing Guide

This document defines how to functionally test Corge end-to-end, from a clean machine through a complete specification-driven delivery cycle. It is structured as an ordered sequence of test phases. Each phase must pass before the next begins.

---

## Prerequisites

| Requirement | Minimum Version | Verify |
| :--- | :--- | :--- |
| Python | 3.11 | `python3 --version` |
| `uv` (package manager) | latest | `uv --version` |
| Git | any | `git --version` |
| An LLM API key | — | DeepSeek, OpenAI, or a running Ollama instance |

---

## Phase 0 — Installation

### 0.1 Clone the repository

```bash
git clone <repository-url>
cd Corge
```

**Expected**: The working directory contains `pyproject.toml`, `README.md`, `config.toml.example`, `src/`, `tests/`, and `docs/`.

### 0.2 Create the virtual environment and install dependencies

```bash
uv sync
```

**Expected**: `uv` resolves the lock file (`uv.lock`) and installs all dependencies into `.venv/`. No errors or warnings about missing packages.

### 0.3 (Optional) Install `tiktoken` for precise token counting

```bash
uv sync --extra tiktoken
```

**Expected**: `tiktoken` is installed alongside the base dependencies.

### 0.4 Verify the unit test suite passes on the fresh install

```bash
uv run pytest
```

**Expected**: All tests in `tests/` pass. Zero failures. Zero errors.

### 0.5 Verify static analysis passes

```bash
uv run ruff check .
uv run mypy src
```

**Expected**: `ruff` reports no lint violations. `mypy` reports no type errors.

---

## Phase 1 — Configuration

### 1.1 Create `config.toml` from the example template

```bash
cp config.toml.example config.toml
```

Open `config.toml` and fill in:

| Field | Description |
| :--- | :--- |
| `model` | Model name, e.g. `"deepseek-chat"`, `"gpt-4o"`, or your Ollama model |
| `api_key` | Your provider API key (omit or leave blank for local Ollama) |
| `base_url` | API endpoint; defaults to `https://api.openai.com/v1` if blank |
| `max_tokens` | Max completion tokens per request; `0` uses the API default |

**Expected**: `config.toml` exists at the project root and is populated with valid credentials. Note that the application prioritizes reading/writing `~/.config/corge/CorgeAPIConfig.toml`, but checks `TARGET_REPO/CorgeAPIConfig.toml` as an override.

### 1.2 Verify the provider is reachable

Corge will fail fast at startup if the model endpoint cannot be reached. Before running the full session, confirm the API key and endpoint are valid by sending a minimal ping through the SDK (this can be a one-off script or a manual `curl`). A non-authentication error (e.g. a `401`) indicates a bad key. A non-connection error (e.g. a `5xx`) indicates a provider outage.

---

## Phase 2 — Choosing a Target Repository

Corge must be pointed at a target repository (the codebase it will engineer, not its own source). Two sub-cases exist:

### 2.1 Existing repository

Choose any small-to-medium Python (or other supported) repository that you own. The repository must be on your local filesystem.

**Functional criterion**: Corge correctly ingests the repository structure during `REPOSITORY_ANALYSIS`, populates the knowledge graph (`repo_graph.db`), and extracts engineering facts (`memory.db`) without crashing.

### 2.2 Empty directory (bootstrapping from scratch)

```bash
mkdir ~/my-new-project
```

Use this empty directory as the target. Corge must be able to scaffold the project structure from specification alone (FR-015).

**Functional criterion**: After spec and plan approval, Corge creates files in the empty directory as directed by the approved plan.

---

## Phase 3 — Session Startup & Repository Analysis

### 3.1 Launch Corge

There are two ways to target a repository:

**Option A: Launch with path argument**
Provide the path directly as a command-line argument:
```bash
uv run python -m corge /path/to/target/repository
```

**Option B: Launch interactively**
Run without arguments to launch the interactive directory explorer:
```bash
uv run python -m corge
```

> **Note**: Replace `python -m corge` with the actual entry-point command once the CLI entrypoint is finalized in `pyproject.toml`. The invocation may also be `uv run corge` if a `[project.scripts]` entry exists.

**Expected (Option B)**: A Textual `DirectorySelectorApp` is displayed in the terminal where you can:
- Use the arrow keys to navigate the file system tree (automatically focused on mount).
- Press `Enter` or `s` to select the currently highlighted directory.
- Press `h` to toggle the visibility of hidden files/folders.
- Press `c` to create a directory or `m` to manually enter a path. Hitting `Escape` while typing inside these inputs will safely cancel the input and refocus the tree, rather than quitting the entire application.
- Verify that directory creation errors (like writing to write-protected paths) show a clean inline error message instead of crashing the app.

### 3.2 Select the target repository

Complete the selection using Option A or Option B above.

**Expected**: The Textual TUI opens and the agent enters `REPOSITORY_ANALYSIS`. The TUI displays repository context (file count, detected tech stack, knowledge graph summary). The `.agent/` directory is created inside the target repository with:

```text
.agent/
├── repo_graph.db
├── memory.db
├── memory/
│   ├── l0/
│   └── scenarios/
├── engineering_profile.md
└── audit.jsonl
```

### 3.3 Framework detection & schema tailoring

If the target repository contains one of the signature files listed in the Technical Spec, verify the TUI reports the correct detected stack.

**Expected**: The `SchemaTailor` selects the matching schema from `src/corge/schemas/stack/`. If no signature is found, it falls back to `generic.yaml`.

Run through at least these three stack variants to exercise the schema files that currently exist:

| Target repository signature | Expected schema loaded |
| :--- | :--- |
| Contains `manage.py` or `settings.py` | `stack/django.yaml` |
| Contains `artisan` | `stack/laravel.yaml` |
| No recognised signature | `stack/generic.yaml` |

**How to verify without a real project**: Create a temp directory, add a file matching the signature (e.g. `touch manage.py`), and point Corge at it. The TUI context readout or the session log must name the detected stack.

---

## Phase 4 — Specification Phase

### 4.1 Freestyle Canvas (`CANVAS_FREESTYLE`)

The TUI opens the `CanvasScreen`. Write a short, realistic feature request in the free-form text area. For example:

```text
Add a REST endpoint /api/health that returns {"status": "ok", "version": "<semver>"}
with a 200 response. The version must be read from the package metadata.
Include one automated test.
```

Press **Submit to Concretization**.

**Expected**: The canvas text is captured. The agent transitions to `CONCRETIZATION`.

#### 4.1.a Sticky note validation (`context/sticky_validator.py`)

While still on the `CanvasScreen`, type a sticky note reference using the `@node:<id>` syntax, e.g.:

```text
@node:src/corge/tools/runtime.py
```

**Functional checks**:
- A valid node ID (one that exists in the knowledge graph) is accepted without an error indicator.
- An invalid or non-existent node ID (e.g. `@node:does_not_exist.py`) is rejected with a visible validation error in the TUI.
- Validation is debounced — the error does not fire on every keypress, only after the user stops typing briefly.

**Expected**: The `StickyValidator` in `context/sticky_validator.py` resolves each `@node:<id>` tag against the knowledge graph and surfaces errors inline. Submitting a canvas containing an unresolved sticky note must be blocked.

### 4.2 Concretization (`CONCRETIZATION`)

The `SpecificationAgent` compiles the freeform canvas into a structured specification. The schema used is framework-aware.

**Expected**: The agent produces a draft containing:
- Feature title
- Acceptance criteria (at minimum one verifiable criterion)
- Constraints
- Testing expectations

No manual input is required in this sub-state.

#### 4.2.a Socratic Spec Wizard Clarifying Questions (Opt-in)

If the concretization agent identifies semantic gaps in the specification draft, a `ConfirmScreen` dialog will ask: "Would you like to run the Socratic Spec Wizard to answer clarifying questions for the top N gaps?" (where N is capped by `max_socratic_questions` in `HeuristicConfig`, default 3, to prevent cognitive overload).

**Functional checks**:
- Selecting **No** (Opt-out) immediately bypasses Socratic questions and proceeds directly to the manual split-editor `InteractiveDiffScreen` (Phase 4.3).
- Selecting **Yes** (Opt-in) displays the Socratic questions screen. Provide answers and press **Submit Answers** (or select **Skip** / `Escape` to skip).
- If answers are submitted, the UI shows "Refining specification with answers..." and automatically generates a refined specification incorporating the user answers.
- If gaps still remain, a subsequent opt-in confirmation prompt is presented, allowing another round of Socratic Q&A (capped at the threshold).

**Expected**: The Socratic questions screen is displayed only on opt-in and is capped to the threshold limit. Iterative Q&A runs as long as gaps remain and the user opts in. Submitted answers are merged into the specification body by the LLM.

### 4.3 Argumentation Diff (`ARGUMENTATION_DIFF`)

The TUI opens the `InteractiveDiffScreen` split-editor unconditionally (even if 0 gaps remain, to allow user manual review). The left pane shows the original canvas text; the right pane is an editable text area containing the full concretized spec draft, with any unresolved semantic gaps formatted as inline templates (e.g. `[GAP: Topic]\nResolution: <Enter details here>`).

**Functional check — gap resolution**: If gaps exist, edit the right pane and replace the placeholder fields with your descriptions. Press **Approve**. The UI shows "Processing specification edits..." and uses the LLM to parse and merge the manual template responses back into structured specification fields.

**Functional check — review/edit**: If no gaps exist or for general edits, tweak the right pane text and press **Approve**.

**Functional check — rejection**: Press **Reject** (or `Escape`). Verify that the application navigates backward to the canvas screen (`SPEC_ENTRY`).

**Expected**: The spec manual refinement editor is shown unconditionally. Gaps are resolved using inline placeholder templates. The user's changes are merged into the final specification fields upon Approve. The spec transitions to `SPEC_METASTABLE` upon Approve. The `ArgumentationLog` writes the Socratic Q&A log to `.agent/` for future heuristic updates. If rejected, the controller transitions back to spec entry.

#### 4.3.a Argumentation log inspection (`logging/argumentation_log.py`)

After approving the spec, verify the log was written:

```bash
cat <target-repo>/.agent/argumentation_log.json | python3 -m json.tool
```

**Expected**: The file exists and contains a JSON array (or JSON Lines) of Socratic Q&A interaction records. Each record must include at minimum a `timestamp`, the canvas snapshot or wizard question, and the user response. An empty file or missing file is a failure.

### 4.4 Spec approval (`SPEC_METASTABLE`)

The `InteractiveDiffScreen` or a `MessageScreen` presents the final specification for human approval.

**Expected**: On approval, the agent advances to `MasterPhase.PLANNING`. The spec is immutably locked. The audit logger records the approval event locally to `.agent/audit.jsonl` and the completion/milestone globally to `~/.config/corge/global_audit.jsonl`.

---

## Phase 5 — Planning Phase

### 5.1 Technical Plan generation (`TECH_PLAN_REITERATION`)

The `PlanningAgent` drafts the architectural `TechnicalPlan` in markdown. The `InteractiveDiffScreen` opens showing a live highlighted unified diff on the left and the editable draft technical plan on the right.

**Functional checks**:
- The plan is readable and addresses the accepted spec requirements.
- The plan can be edited in the right pane before approval.
- Pressing **Approve** locks the technical plan.
- Pressing **Reject** (or `Escape`). Verify that the application navigates backward to the specification validation state (`SPEC_VALIDATION`).

### 5.2 Procedural Steps generation (`STEPS_REITERATION`)

The agent translates the technical plan into granular, sequenced `ProceduralStep` entries. The `InteractiveDiffScreen` re-opens showing a highlighted unified diff on the left and the editable procedural steps on the right.

**Functional checks**:
- Each step has a sequential identifier.
- Custom bracketed step identifiers (e.g. `[step-auth] authentication`) can be manually typed in the editor. Verify that they are parsed and preserved in the final plan rather than overwritten with sequential `step-N` IDs.
- Steps are granular enough to be individually executable.
- The right pane is editable; modifications are respected on approval.
- Pressing **Reject** (or `Escape`). Verify that the application navigates backward to the technical plan generation state (`PLAN_GENERATION`).

**Expected**: On approval, the agent advances to `MasterPhase.CODING`. The `Plan` (containing all `ProceduralStep` entries) is passed to the `CodingAgent`. If rejected, the controller transitions to the previous phase.

---

## Phase 6 — Coding Phase (Execution Loop)

The 9-Step execution cycle runs autonomously for each `ProceduralStep`. The test scenarios below cover the critical paths within this loop.

### 6.1 Context hydration

**Expected per step**: The `ContextService` queries the knowledge graph and memory pyramid and assembles a `ContextBundle`. The prompt assembler renders the semantically tagged ephemeral prompt. The budget manager clips and deduplicates content without destroying critical context.

#### 6.1.a Prompt Assembler semantic verification (`prompt_assembler/`)

After the first tool action executes, inspect the audit log or session L0 events to confirm the expected XML-like tags are present in the assembled prompt:

```bash
cat <target-repo>/.agent/memory/l0/<latest>.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    e = json.loads(line)
    if e.get('kind') == 'prompt_assembled':
        print(json.dumps(e['payload'], indent=2))
        break
"
```

**Expected**: The payload shows non-empty content for:
- `<objective>`: current execution constraints
- `<specification>`: current spec, acceptance criteria
- `<engineering_profile>`: active engineering rules
- `<repository_facts>`: engineering facts, graph query results
- `<task_memory>`: scenario memory
- `<recent_actions>`: recent action history
- `<artifacts>`: `artifact://` URIs (may be empty if no artifacts have been offloaded yet)

#### 6.1.b Budget Manager clipping verification (`budget_manager/`)

To trigger the budget manager's clipping logic, run a session against a large repository (many files, long history) or artificially lower `max_tokens` in `config.toml` to a small value (e.g. `512`).

**Expected**:
- The budget manager clips oversized strings rather than crashing or silently truncating the entire prompt.
- Duplicate file summaries and repeated facts are removed — the same file path must not appear twice in a single assembled prompt.
- The session continues without errors even when the raw context would exceed the configured token budget.
- The L0 log records a `budget_applied` (or equivalent) event when clipping fires.

#### 6.1.c Markov context chaining verification (`context/service.py`)

After at least two execution steps have completed, verify that the N-1 Markov state is injected into the current prompt.

**Expected**: The assembled prompt for step N must contain a `compressed_trajectory` field referencing the agent proposal and user correction from step N-1. Inspect the L0 JSONL log for consecutive `prompt_assembled` events and confirm the second entry's payload includes a non-empty `markov_state` or `compressed_trajectory` section referencing the prior step's outcome.

### 6.2 Tool action — `read`

The agent issues a `read` action against a file in the target repository.

**Expected**: The approval gateway auto-approves `read` without human input (FR-009). The `ToolRuntime` returns the file contents. The agent proceeds without interruption.

### 6.3 Tool action — `write` (human approval required)

The agent issues a `write` action to create or overwrite a file.

**Expected**:
1. The approval gateway intercepts the action and delegates to the UI.
2. The `InteractiveDiffScreen` opens with a highlighted unified diff of the changes on the left and the editable `ToolAction` payload on the right.
3. The engineer reviews and presses **Approve** (or **Reject**).
4. On approval, the `ToolRuntime` writes the file. The change is visible on disk.
5. The audit logger records the approval event.

### 6.4 Tool action — `edit` (human approval required)

The agent issues an `edit` action to modify a specific string in an existing file.

**Expected**:
- Same approval flow as `write`.
- The `ToolRuntime` applies the edit only if the target string occurrence count matches exactly (ambiguous edits are rejected with an error, not silently applied).
- The file on disk reflects the change after approval.

> [!TIP]
> Try performing an action with the coding agent that edits a file, and when prompted for approval, hit `Ctrl+D` to verify the code diff before hitting `Ctrl+A` to approve.

### 6.5 Tool action — `bash` (human approval required)

The agent issues a `bash` action (e.g. to run tests or install a dependency).

**Expected**:
- Same approval flow as `write`.
- The `ToolRuntime` streams output in real time.
- On a non-zero exit code or compilation error, a `ToolExecutionError` is raised and automated execution is suspended. A `ConfirmScreen` dialog is displayed: "Step <identifier> failed with error... Would you like to retry this step?". 
- You can fix the bug in another window, select **Yes** (to retry), and verify that the agent re-runs the failed step successfully. If you select **No**, automated execution suspends and the application exits.

### 6.6 Rejection flow

On the `InteractiveDiffScreen`, press **Reject** instead of **Approve** for any proposed action.

**Expected**: The gateway returns a rejection signal to the `CodingAgent`. The agent pivots (requests a new action from the model) rather than crashing. Execution resumes from the same plan step.

### 6.7 Knowledge update per step

After each tool execution, the agent updates persistence.

**Expected**:
- New facts are written to `.agent/memory.db`.
- The knowledge graph in `.agent/repo_graph.db` reflects any new or modified files.
- Scenario memory for the current feature is appended to `.agent/memory/scenarios/<kind>.jsonl`.
- The engineering profile (`.agent/engineering_profile.md`) is updated if new conventions are detected, and high confidence rules are also promoted to `~/.config/corge/global_profile.md`.

### 6.8 Artifact store offload (`artifacts/store.py`)

The artifact store activates when a tool output (e.g. a long `bash` log or a large file read) exceeds the inline storage threshold. To trigger it deliberately, run a `bash` command that produces many lines of output (e.g. `find . -type f` on a large repo, or a verbose test run).

**Expected**:
- The large output is written to `.agent/artifacts/` as a file (not inlined in the prompt).
- The prompt for the subsequent step references the offloaded content using an `artifact://` URI (`<artifacts>` block), not the raw text.
- The `.agent/artifacts/` directory is created automatically on first use.
- The `artifact://` reference is resolvable — the agent can retrieve the content when needed.

```bash
# Verify artifact files exist after a large bash output
ls -lh <target-repo>/.agent/artifacts/
```

**Failure indicator**: The large output is embedded verbatim in the prompt instead of being offloaded, causing prompt size to grow unboundedly.

---

## Phase 7 — Completion & Verification

### 7.1 Completion review

After all procedural steps execute successfully, the `CodingAgent` triggers a completion review.

**Expected**: The `MessageScreen` displays the delivery summary (plan steps, tool results). The engineer reviews and presses **Continue**.

### 7.2 Test verification (FR-012)

Run the tests in the target repository to validate the delivery:

```bash
# In the target repository directory
uv run pytest   # or the project's native test command
```

**Expected**: All tests pass. Acceptance criteria defined in the specification are satisfied.

### 7.3 Audit trail review

Inspect the audit log written during the session:

```bash
cat <target-repo>/.agent/audit.jsonl | python3 -m json.tool | head -100
```

**Expected**: The log contains entries for:
- Spec approval
- Plan approval
- Each tool invocation (action type, target, timestamp)
- Each human approval/rejection decision
- Completion event

### 7.4 Audit Logs TUI Viewer (UX-005)

When completing a session, or when invoking the log display command inside the TUI.

**Expected**:
- The log display screen (MessageScreen) shows the log history parsed into a clean, human-readable bulleted summary of event timestamps, action types (e.g. `PROPOSE_ACTION`), execution status, reasons, and decisions.
- Confirms that raw JSON/JSONL dumps are not displayed directly to the developer.

---

## Phase 8 — Session Persistence & Recovery

### 8.1 Mid-session interruption

During the coding phase, close the TUI (Ctrl+C or terminal close).

**Expected**: No data is lost. The `.agent/` directory retains all memory, the knowledge graph, and the audit log up to the last completed step.

### 8.2 Session resume

Restart Corge and point it at the same target repository.

**Expected**: Corge detects the existing `.agent/` directory, loads the previous session state (engineering profile, scenario memory, knowledge graph), and offers to resume from the last known state. The engineer does not need to re-enter the specification or re-approve the plan.

---

## Phase 9 — Bayesian Heuristic Learning (Post-Session)

### 9.1 Heuristic update after completion

After a completed session, the `HeuristicUpdater` runs an offline Bayesian update on `~/.config/corge/spec_wizard_heuristics.json`.

**Functional checks**:
- `~/.config/corge/spec_wizard_heuristics.json` exists (or is created) after the first completed session.
- The `engagement` prior is updated using the EWMA formula with `α = 0.01`.
- Delta clipping is enforced: no single update moves a probability by more than `0.05`.

### 9.2 Abandonment penalty

Start a session, advance through the spec wizard, and then quit before the plan is approved.

**Expected**: The `HeuristicUpdater` applies the abandonment penalty (`-0.05` after clipping) to the engagement prior in `~/.config/corge/spec_wizard_heuristics.json`.

---

## Phase 10 — Multi-Provider Smoke Test

Repeat Phase 3 → Phase 7 with each supported provider to verify the provider abstraction layer (FR-014).

| Provider | `model` value | `base_url` | `api_key` |
| :--- | :--- | :--- | :--- |
| DeepSeek | `deepseek-chat` | `https://api.deepseek.com/v1` | DeepSeek key |
| OpenAI | `gpt-4o` | *(blank)* | OpenAI key |
| Ollama | your local model | `http://localhost:11434/v1` | *(blank)* |

**Expected for all providers**:
- `<think>...</think>` tags from reasoning models are stripped from all content before it is rendered in the TUI or stored.
- `prompt_tokens`, `completion_tokens`, `cache_read_tokens`, `cache_write_tokens` are all populated in every response (zero-valued if not supported by the provider).

---

## Phase 11 — Automated Unit & Integration Tests

Run the full automated test suite after each change to the codebase:

```bash
uv run pytest -v
```

The test suite covers:

| Test File | Coverage Area |
| :--- | :--- |
| `tests/test_knowledge_graph.py` | Graph node/edge ingestion, query grammar |
| `tests/test_memory.py` | L0–L3 memory pyramid read/write correctness |
| `tests/test_prompt_assembler.py` | Semantic tagged prompt rendering |
| `tests/test_budget_manager.py` | Token clipping, deduplication, compaction |
| `tests/test_gateway.py` | Approval gateway routing and auto-approve for reads |
| `tests/test_agent.py` | Agent state machine transitions |
| `tests/test_public_contracts.py` | Interface ports and data model contracts |
| `tests/test_audit_logger.py` | Audit log entry serialization |
| `tests/test_tools.py` | Tool runtime primitives |
| `tests/test_imports.py` | Package import hygiene |

**Expected**: All tests pass. If any test fails, it must be fixed before the corresponding functional test phase above is considered passing.

---

## Acceptance Criteria Summary

| Phase | Gate |
| :--- | :--- |
| 0 — Installation | `uv run pytest` passes; `ruff` and `mypy` are clean |
| 1 — Configuration | `config.toml` is populated and the provider endpoint is reachable |
| 2 — Target Repo | A target repository or empty directory is selected |
| 3 — Startup | TUI opens; `.agent/` is created; tech stack detected for Django, Laravel, and generic fallback |
| 4 — Specification | Spec concretized, gaps resolved, approved; sticky validator rejects bad `@node:` tags; argumentation log written and non-empty |
| 5 — Planning | Technical plan and procedural steps are approved |
| 6 — Coding | All tool actions execute; approval gateway fires for write/edit/bash; rejection pivots correctly; budget manager clips large prompts; Markov chaining injects N-1 state; artifact store offloads large outputs |
| 7 — Completion | Delivery review shown; target repo tests pass; audit log is complete |
| 8 — Persistence | Session resumes correctly after mid-session interruption |
| 9 — Heuristics | Heuristic file updated after completion; abandonment penalty applied on early exit |
| 10 — Providers | All three providers complete a full session without errors |
| 11 — Unit Tests | Full `pytest` suite passes |

All phases must pass for a release to be considered functionally verified.

---

## Issue Log

Use this section to document issues discovered during manual testing. Add one entry per issue found. Do not edit or delete existing entries; mark them resolved instead.

### Issue Template

Copy the block below for each new issue:

```text
### ISSUE-<N> — <Short title>

- **Phase**: Phase <number> — <phase name>
- **Step**: <e.g. 6.3 — write approval>
- **Severity**: Critical | High | Medium | Low
- **Status**: Open | In Progress | Resolved
- **Reported by**: <name / handle>
- **Date**: YYYY-MM-DD

**Description**:
<What happened. Be specific: what you did, what you expected, what actually occurred.>

**Steps to reproduce**:
1. ...
2. ...
3. ...

**Observed output / error**:
<Paste the exact error message, stack trace, or TUI behaviour here.>

**Expected output**:
<What the correct outcome should have been per the spec or this document.>

**Environment**:
- OS: ...
- Python: ...
- Provider: ...
- Model: ...
- Corge commit: `git rev-parse --short HEAD`

**Resolution** *(fill in when fixed)*:
<Describe the fix, PR/commit reference, and who verified it.>
```

---

### Severity Guide

| Severity | Definition |
| :--- | :--- |
| **Critical** | Blocks a full phase; no workaround exists (e.g. TUI crash, data corruption, approval gateway bypassed) |
| **High** | Significant deviation from spec behaviour; workaround is painful or unreliable |
| **Medium** | Functional gap with an acceptable workaround |
| **Low** | Cosmetic, minor wording, or negligible edge case |

---

### Open Issues

*No issues recorded yet. Add entries here as they are found during testing.*

<!-- ISSUE ENTRIES START -->

<!-- ISSUE ENTRIES END -->

---

### Resolved Issues

*Move entries here from Open Issues once the fix is confirmed.*

<!-- RESOLVED ENTRIES START -->

<!-- RESOLVED ENTRIES END -->
