# Corge Demo Script

> **Audience**: Stakeholders, Future Customers, Enthusiasts
> **Format**: Presentation with live TUI walkthrough
> **Duration**: ~30-40 minutes

---

## Part 1 — The Problem: Agentic Coding Has an Audience Problem

**Speaker**: "Let's start with an honest observation."

The agentic coding space is booming. Every week there's a new tool claiming to "build your app from a single prompt." But look at who these tools are built for:

- **General audiences**: Vibe-coding, prompt-and-pray, zero engineering discipline.
- **Black-box SDLC**: The agent does everything — requirements, design, implementation, testing — with the human reduced to a spectator.
- **Opinionated & opaque**: You cannot inspect the plan before execution. You cannot steer. You cannot say "no, not like that."

Now, who is actually *best* at coding? **LLMs.** They're great at generating syntactically correct code, reasoning about APIs, and pattern-matching across massive training data. But they're *terrible* at requirements engineering, architectural judgment, and knowing when to stop and ask.

**The insight**: The bottleneck is not code generation. It's **specification** and **verification**.

So we asked: *What if we stopped treating the LLM as an autonomous engineer and started treating it as a disciplined tool in a human-led engineering workflow?*

---

## Part 2 — The Answer: Corge

**Speaker**: "That question is why we built Corge."

**Corge** is a **specification-driven, software-engineer-first** agentic development system. It does not write code from vague prompts. It enforces a controlled engineering workflow:

```
Freestyle Canvas → Structured Specification → Execution Plan → Coding → Verification → Delivery
```

Each stage reduces ambiguity. Each stage increases machine executability. And the human is *always* in control.

### The Three Agents

Corge has three master-phase agents, each with a strict responsibility:

| Agent | Phase | Role |
|-------|-------|------|
| **Specification Agent** | SPECIFICATION | Elicits requirements, runs Socratic Q&A, produces a structured `Specification` with acceptance criteria |
| **Planning Agent** | PLANNING | Generates a `TechnicalPlan` (architecture) and `ProceduralStep`s (executable checklist) |
| **Coding Agent** | CODING | Executes the plan step-by-step — reads context, calls the LLM, requests human approval for every destructive action |

### The User Journey

1. **Launch & Repo Selection** — Point Corge at any repository (or empty directory via the keyboard-driven `DirectorySelectorApp`)
2. **Freestyle Canvas** — Write rough feature ideas on a canvas with `@node:` sticky notes that validate against the knowledge graph in real time
3. **Socratic Spec Wizard** — Opt-in clarifying questions (capped at 3 to prevent fatigue) that refine the spec iteratively
4. **Split-Pane Editor** — Manually edit any gap as inline `[GAP: Topic]` templates, then approve
5. **Technical Plan** — The planning agent produces architecture; you edit, approve, or reject (which navigates backwards)
6. **Procedural Steps** — Granular step-by-step checklist; bracketed IDs are preserved if you customize them
7. **Step-by-step Execution** — For each step, Corge hydrates context, calls the LLM, shows you exactly what it wants to do (with live `Ctrl+D` code diffs), and waits for your approval before writing/editing/running anything
8. **Verification & Completion** — All acceptance criteria checked, tests pass, audit log delivered

### Business Value

- **Traceability**: Every line of code is traceable to an approved spec and plan step
- **Safety**: No write/edit/bash executes without human consent
- **Quality**: Spec-driven development prevents scope creep and ambiguous requirements
- **Audit**: Full argumentation log (Socratic Q&A) + audit trail (every tool call, approval, and rejection)
- **Accountability**: The human is the engineer; the LLM is the tool

---

## Part 3 — Technical Architecture Overview

**Speaker**: "Now let's look under the hood."

### Stack for the POC

| Layer | Technology |
|-------|-----------|
| **Runtime** | Python 3.11+, `uv` package manager |
| **TUI Framework** | Textual (rich terminal UI) |
| **LLM Providers** | DeepSeek, OpenAI, Ollama (OpenAI-compatible adapter) |
| **Persistence** | SQLite (WAL mode, connection pooling) |
| **AST Parsing** | Python stdlib `ast` |
| **Static Analysis** | `ruff` for linting, `mypy` for type checking |
| **Testing** | `pytest` |

### The 5-Layer Architecture

We organized Corge as a **modular monolith** with 5 distinct layers communicating through `typing.Protocol` interfaces:

```
┌──────────────────────────────────────────────────────┐
│                 1. UI & UX Layer                      │
│          (Textual TUI — zero business logic)          │
├──────────────────────────────────────────────────────┤
│                 2. Middleware Layer                    │
│    (SessionController, ApprovalGateway, Logging)      │
├──────────────────────────────────────────────────────┤
│                 3. Logic Layer                         │
│   (SpecAgent, PlanAgent, CodingAgent, SchemaTailor)   │
├──────────────────────────────────────────────────────┤
│                 4. Data Layer                          │
│   (KnowledgeGraph, Memory Pyramid, Artifact Store)    │
├──────────────────────────────────────────────────────┤
│                 5. Infrastructure Layer                │
│   (Provider Adapter, ToolRuntime, Budget Manager)     │
└──────────────────────────────────────────────────────┘
```

### System Architecture — Module Map

The system is divided into **8 logical modules** plus a shared contracts layer:

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   UI (TUI)  │────▶│   Agent     │────▶│   Context        │
│  Purple     │     │  Yellow     │     │   Green          │
└─────────────┘     └─────────────┘     └──────────────────┘
                           │                     │
                           ▼                     ▼
                    ┌──────────────┐    ┌──────────────────┐
                    │  Execution   │    │  Knowledge &     │
                    │  & Safety    │    │  Persistence     │
                    │  Red         │    │  Blue            │
                    └──────────────┘    └──────────────────┘
                           │                     │
                           ▼                     ▼
                    ┌──────────────┐    ┌──────────────────┐
                    │  Providers   │    │  Logging         │
                    │  Cyan        │    │  Orange          │
                    └──────────────┘    └──────────────────┘
```

### How Modularity Serves the Business

Every module communicates through **protocol interfaces** in `contracts/ports.py` and passes only **frozen, slotted dataclasses** from `contracts/models.py`. This means:

- **Swappable UI**: Replace Textual with a web UI or IDE plugin — no business logic changes
- **Swappable providers**: Swap DeepSeek for Ollama with zero code changes
- **Testable in isolation**: Every module has a protocol; mock it, test it, verify it
- **No tight coupling**: The UI has no `import` from `agent`; the agent has no `import` from `tools`

---

## Part 4 — Layer & Module Deep Dive

### Layer 1: UI & UX (`ui/`)

**What**: A pure presentation layer built on Textual. Zero business logic.

**Key modules**:
- `cli.py` — `CorgeApp`, `DirectorySelectorApp`, `CanvasScreen`, `InteractiveDiffScreen`, `MessageScreen`, `ConfirmScreen`, `ProviderConfigScreen`
- `CorgeDirectoryTree` — Subclass of `DirectoryTree` with hidden file toggle (`h`), escape cancellation, safe folder creation

**Why**: Separating UI from logic means we can swap the terminal for VS Code or a web dashboard later. The UI is a view, not a controller.

**How it works**:

```python
# ui/cli.py — UiPort implementation
class CliUi:
    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Push an approval screen onto the Textual app and wait for the result."""
        response = self._app.push_screen_wait(
            InteractiveDiffScreen(
                title="Approval Required",
                left_content=request.reason,
                right_content=format_action(request),
                right_read_only=True,
                left_diff_content=self._compute_diff(request),
            )
        )
        return ApprovalDecision.APPROVED if response else ApprovalDecision.REJECTED
```

#### CanvasScreen — Sticky Note Validation

The `CanvasScreen` supports `@node:<id>` references (e.g., `@node:src/main.py::MyClass`) that validate against the knowledge graph *as you type* via the `StickyValidator` in `context/sticky_validator.py`:

```python
# context/sticky_validator.py
class StickyNoteValidator:
    def validate_node(self, node_id: str) -> StickyNoteStatus:
        result = self._graph.query_graph(GraphQuery(expression=f"node:{node_id}"))
        return StickyNoteStatus.ACTIVE if result.nodes else StickyNoteStatus.INVALID
```

**Key behavior**:
- Validation is **debounced** — fires only after the user stops typing briefly, not on every keystroke
- A valid `@node:` reference is accepted silently
- An invalid reference instantly shows a visible error indicator in the TUI
- Submitting the canvas with *any* unresolved sticky note is **blocked** — the spec phase cannot advance until all graph pointers are valid

This turns the canvas from a text dump into a **live knowledge graph–aware scratchpad**.

#### InteractiveDiffScreen — One Screen, Four Contexts

The `InteractiveDiffScreen` is a single parameterized component reused in 4 completely different workflows:

| Context | Left Pane | Right Pane | Right Read-Only? | Ctrl+D Toggle |
|---------|-----------|------------|------------------|---------------|
| Argumentation Diff | Raw canvas text | Concretized spec with `[GAP:]` templates | No (editable) | Shows unified diff vs canvas |
| Technical Plan Editor | Previous approved spec | Draft architecture plan | No (editable) | Shows unified diff vs previous |
| Procedural Steps Editor | Technical plan draft | Ordered step checklist | No (editable) | Shows unified diff vs original steps |
| Approval Gateway | Reason context (default) / code diff (Ctrl+D) | Tool action payload | **Yes** (read-only: prevents misleading edits) | Toggles between reason and `difflib.unified_diff` |

This is a textbook lazy-senior-dev pattern: one screen, four flags (`right_read_only`, `left_diff_content`, `left_pane_label`), infinite reuse.

#### ConfirmScreen — Three High-Leverage Uses

A 15-line confirmation dialog, reused in three places:

1. **Socratic Validation Opt-In**: "Semantic gaps detected. Run clarifying questions?" — Yes runs the wizard; No skips to the manual diff editor
2. **Clear Backlog Notes**: "Permanently erase `.agent/sticky_notes.json`?" — Only Yes proceeds with deletion
3. **Tool Execution Retry**: "Step failed. Retry after manual fixes?" — Yes re-runs the step; No suspends and exits

All three return a simple `bool`. No branching logic in the screen, no duplication in the callers.

#### TUI Responsiveness: The @work Pattern

The main session loop runs inside a Textual `@work(thread=True)` decorated method. This means the TUI stays responsive during long LLM calls — the user sees streaming tokens, loading indicators, and can cancel at any time:

```python
# __main__.py
class RealCorgeApp(CorgeApp):
    @work(thread=True)
    def run_session(self) -> None:
        while controller.state != LifecycleState.DONE:
            # ... long-running LLM calls, blocking IO ...
            # UI stays alive because Textual runs the event loop on the main thread
```

Without `@work`, every LLM `chat()` call would freeze the terminal for 10-60 seconds — a non-starter for interactive use.

**Key UX design decisions**:
- Every screen auto-focuses its primary widget on mount (keyboard-first)
- `Ctrl+D` toggles a live `difflib.unified_diff` during approvals so you see exactly what changes before authorizing
- `Ctrl+A` approves, `Escape` rejects — consistent across all screens
- The `CorgeDirectoryTree` keeps the tree visible during path input, and `Escape` safely cancels input instead of quitting

---

### Layer 2: Middleware (`agent/`, `approval/`, `logging/`)

**What**: Orchestration, safety gates, and accountability recording.

#### SessionController (`agent/session_controller.py`)

**What**: The master state machine that drives all 3 phases across 12 lifecycle states.

**Why**: By centralizing transitions in one place, we guarantee that rejections always navigate backward correctly, failures are caught, and the user is never in an undefined state.

**How**:

```python
# agent/session_controller.py — State transition table
_TRANSITIONS: dict[LifecycleState, LifecycleState] = {
    LifecycleState.START: LifecycleState.REPOSITORY_SELECTION,
    LifecycleState.REPOSITORY_SELECTION: LifecycleState.REPOSITORY_ANALYSIS,
    LifecycleState.SPEC_ENTRY: LifecycleState.SPEC_VALIDATION,
    LifecycleState.SPEC_VALIDATION: LifecycleState.SPEC_APPROVAL,
    LifecycleState.PLAN_GENERATION: LifecycleState.PLAN_REVIEW,
    LifecycleState.PLAN_REVIEW: LifecycleState.PLAN_APPROVAL,
    LifecycleState.EXECUTION: LifecycleState.VERIFICATION,
    LifecycleState.VERIFICATION: LifecycleState.COMPLETION_REVIEW,
    LifecycleState.COMPLETION_REVIEW: LifecycleState.DONE,
}

class SessionController:
    def transition_to(self, target: LifecycleState) -> None:
        """Navigate backward on reject/cancel."""
        if target not in _BACKWARD_TRANSITIONS.get(self.state, set()):
            raise InvalidTransitionError(...)
        self.state = target
```

The `__main__.py` loop consumes these states in a simple `while` loop — no hidden complexity:

```python
# __main__.py — The main orchestrator loop (simplified)
while controller.state != LifecycleState.DONE:
    if controller.state == LifecycleState.REPOSITORY_ANALYSIS:
        bundle = context_service.load_context(RepositoryContext(root=target_repo))
        knowledge_graph.build_graph(bundle.repository_context)
        ui.show_repository_analysis(bundle.repository_context)
        controller.advance()

    elif controller.state == LifecycleState.SPEC_ENTRY:
        spec = ui.show_spec_wizard()
        controller.advance()

    elif controller.state == LifecycleState.EXECUTION:
        for step in plan.steps:
            bundle = controller.collect_context(step, spec)
            controller.execute_step(step, bundle, on_token=ui.stream_token)
```

#### Session Persistence — Save & Resume

Before every state transition, the loop serializes the full `SessionState` to `.agent/`:

```python
# __main__.py (inside the while loop)
current_session_state = SessionState(
    lifecycle_state=controller.state,
    master_phase=controller.phase,
    spec_state=controller.spec_state,
    plan_state=controller.plan_state,
    specification=spec,
    plan=plan,
    technical_plan=tech_plan,
    procedural_steps=proc_steps,
    repo_root=self.target_repo,
)
save_session(agent_dir, current_session_state)
```

On relaunch, the controller calls `load_session(agent_dir)` and restores everything — lifecycle state, spec, plan, procedural steps. The engineer never re-enters specs or re-approves plans. Even mid-session crashes (Ctrl+C, terminal close) preserve `.agent/` state fully; the `.agent/memory.db`, `.agent/repo_graph.db`, and `.agent/audit.jsonl` all use SQLite WAL mode for crash-safe writes.

#### ApprovalGateway (`approval/gateway.py`)

**What**: The single chokepoint for all code-modifying operations.

**Why**: FR-009 mandates that no write/edit/bash executes without human consent. Reads auto-approve. Centralizing this in one 35-line class means we can audit every decision and guarantee safety.

**How**:

```python
# approval/gateway.py
class ApprovalGateway:
    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        if request.action == ToolAction.READ:
            decision = ApprovalDecision.APPROVED  # auto-approve reads
        else:
            decision = self._ui.request_approval(request)
        self._audit_logger.record_approval(request, decision)
        return decision
```

#### Audit Logger (`logging/`)

**What**: Dual-stream logging: local `.agent/audit.jsonl` for tool-level detail, global `~/.config/corge/global_audit.jsonl` for cross-project milestones.

**Why**: Accountability. Every prompt, plan, tool call, and approval is recorded. The argumentation log captures Socratic Q&A for the Bayesian heuristic updater.

#### Bayesian Heuristic Updater (`agent/bayesian_updater.py`)

**What**: An offline batch learner that improves the spec wizard across projects using Bayesian inference.

**Why**: The spec wizard asks better questions over time. Every session generates an `argumentation_log.json` — the heuristic updater consumes it post-session and adjusts global priors stored in `~/.config/corge/spec_wizard_heuristics.json`.

**The EWMA formula**:

$$
P_{\text{new}} = (1 - \alpha) \cdot P_{\text{old}} + \alpha \cdot \text{Observation}
$$

Where:
- $\alpha = 1.0 - \text{decay\_rate}$ — the configured `decay_rate` is `0.99`, yielding $\alpha = 0.01$
- $\text{Observation} = 1.0 - \frac{\text{user overrides}}{\text{total interactions}}$ — the ratio of non-overridden Socratic steps

**Delta clipping** prevents extreme swings in any single update:

$$\Delta P = P_{\text{new}} - P_{\text{old}}$$
$$\text{If } |\Delta P| > \text{delta\_clip\_max}\ (0.05),\ \Delta P \leftarrow 0.05 \cdot \text{sign}(\Delta P)$$

**Abandonment penalty**: If the user quits before completing the spec, the engagement prior is penalized by `-0.15` (clipped to `-0.05` max decrease per session):

$$P_{\text{engagement}} \leftarrow \max(0.0,\ P_{\text{engagement}} - \min(\text{delta\_clip\_max},\ |\text{abandonment\_penalty}|))$$

This means: after 20 successful sessions with zero overrides, the engagement prior approaches ~0.18. A single bad session can only drop it by 0.05. Lazy, conservative learning — exactly what you want from a drift-resistant system.

---

### Layer 3: Logic (`agent/specification_agent.py`, `agent/planning_agent.py`, `agent/coding_agent.py`)

**What**: The three specialist agents that interact with the LLM.

#### Specification Agent

**What**: Takes freestyle canvas text → structured `Specification` with title, body, acceptance criteria, constraints, testing expectations.

**How**: Uses the `SchemaTailor` to detect the framework (Django, Laravel, Next.js, Rust, etc.) and load matching schema templates. Runs the Socratic Q&A loop (configurable cap, opt-in rounds). Formats gaps as inline `[GAP: Topic]` placeholders.

```python
# agent/specification_agent.py
class SpecificationAgent:
    def concretize(self, canvas_text: str) -> Specification:
        prompt = self.prompt_assembler.assemble_spec_prompt(
            context=context,
            instruction=f"Concretize this canvas into a structured spec:\n{canvas_text}"
        )
        response = self.provider.chat(prompt)
        return self._parse_specification(response.content)

    def ask_socratic_question(self, gap: SemanticGap) -> tuple[str, str]:
        """Generate a clarifying question and return the user's answer."""
        question = self._generate_question(gap)
        answer = self._ui.show_question(question, context=gap.topic)
        return question, answer
```

#### Planning Agent

**What**: Specification → `TechnicalPlan` (markdown architecture) → `ProceduralStep`s (ordered checklist with bracketed IDs).

**Why**: Separating architecture from execution steps means the human can approve the high-level design before diving into implementation details.

#### Coding Agent

**What**: The 9-step execution loop for each plan step: Observe → Refresh Context → Assemble Prompt → Reason & Select Action → Approval Gateway → Execute Tool → Verify Progress → Update Knowledge → Repeat.

**Key design**: If a tool fails, `ToolExecutionError` is raised, execution suspends, the user gets a "Retry?" dialog, and scenario memory records the blocker.

#### Markov Context Chaining (N-1 Injection)

The coding agent doesn't operate in a vacuum. After each step, the system captures the `agent_proposal` and `user_correction` (if any) and injects them into the *next* step's prompt:

```python
@dataclass(frozen=True, slots=True)
class MarkovStepContext:
    agent_proposal: str           # What the LLM proposed for step N-1
    user_correction: str          # What the human changed (or "" if approved as-is)
    compressed_trajectory: str    # Summarized history of steps N-2 to N-Start
```

The `ContextService` packages this into `ContextBundle.markov_context` before every prompt assembly. This means the LLM can *learn from its mistakes mid-session* — if the human corrected a file path in step 3, the model won't repeat that error in step 4.

#### 3-Layer Context Isolation Policy

Not all phases need the same context. We enforce strict isolation to prevent instruction pollution:

| Phase | Context Injected | Context Strictly Omitted |
|-------|-----------------|--------------------------|
| **Specification** | Canvas text, framework schema, Socratic Q&A | File lists, AST graphs, repository facts, code contents |
| **Planning** | Approved spec, repo tree, AST nodes, config files | Execution logs, raw tool outputs |
| **Coding** | Spec, plan, knowledge graph, memory pyramid, markov state, artifacts | Canvas drafts, Socratic Q&A details |

Why? If the spec agent sees 10,000 files, it starts hallucinating architectural details instead of focusing on requirements. If the coding agent sees the raw canvas with resolved gaps, it gets distracted by discarded alternatives. Each phase gets only what it needs.

---

### Layer 4: Data (`knowledge_graph/`, `memory/`, `artifacts/`)

**What**: All persistence — structural, factual, and bulk.

#### Knowledge Graph (`knowledge_graph/graph.py`)

**What**: SQLite-backed AST parser that builds a `nodes` + `edges` graph of the repository. Supports a query grammar: `files`, `classes:<path>`, `imports:<path>`, `imported_by:<path>`, `node:<node_id>`.

**Why**: The LLM cannot navigate a filesystem. The knowledge graph gives it a queryable representation of the codebase structure — classes, functions, imports, dependencies — without dumping raw file trees into the prompt.

```python
# DDL used by the knowledge graph
CREATE TABLE nodes (
    node_id TEXT PRIMARY KEY,  -- "src/main.py::MyClass"
    kind    TEXT NOT NULL,     -- "file", "class", "function", ...
    path    TEXT NOT NULL,
    name    TEXT NOT NULL
);
CREATE TABLE edges (
    src TEXT NOT NULL,
    rel TEXT NOT NULL,         -- "contains", "imports"
    dst TEXT NOT NULL,
    PRIMARY KEY (src, rel, dst)
);
```

#### Memory Pyramid (`memory/`)

**4-tier pyramid matching FR-007**:

| Tier | Name | Storage | Purpose |
|------|------|---------|---------|
| L0 | Session Events | `.agent/memory/l0/<timestamp>.jsonl` | Raw execution logs |
| L1 | Engineering Facts | `.agent/memory.db` (SQLite) | Repository-derived truths |
| L2 | Scenario Memory | `.agent/memory/scenarios/<kind>.jsonl` | Feature-specific blockers & progress |
| L3 | Engineering Profile | `.agent/engineering_profile.md` | Coding conventions (confidence-filtered) |

**Why**: Not all facts are equally valuable. The pyramid lets us surface high-confidence conventions (L3) while still retaining raw logs (L0) for debugging and for the Bayesian heuristic updater.

#### Artifact Store (`artifacts/`)

**What**: Offloads large outputs (> threshold) to `.agent/artifacts/` and inserts `artifact://` URIs into prompts instead of inline content.

**Why**: Prevents context bloat. The budget manager has a hard ceiling; the artifact store ensures large build logs and test outputs don't consume it.

---

### Layer 5: Infrastructure (`providers/`, `tools/`, `budget_manager/`)

#### Provider Adapter (`providers/provider.py`)

**What**: An OpenAI-compatible adapter supporting 3 provider families in a single class with automatic provider detection.

**Why**: FR-014 mandates provider abstraction. The architecture must work with DeepSeek (POC-optimized), OpenAI, and Ollama. One adapter, no branching in business logic.

**Provider auto-detection**: The user enters just an API key and model name — the adapter guesses the endpoint:

```python
class Provider:
    def __init__(self, config: ProviderConfig):
        base_url = config.base_url
        if not base_url:
            if config.api_key.startswith("sk-or-"):
                base_url = "https://openrouter.ai/api/v1"  # OpenRouter
            elif config.model.startswith("deepseek-"):
                base_url = "https://api.deepseek.com/v1"    # DeepSeek

        self._client = openai.OpenAI(
            api_key=config.api_key or "not-needed",
            base_url=base_url,
            timeout=config.timeout,
        )

    def chat(self, messages, on_token=None):
        response = self._client.chat.completions.create(...)
        # Strip <think>...</think> blocks for reasoning models
        content = re.sub(r'<think>.*?</think>', '', response.choices[0].message.content, flags=re.DOTALL)
        return ChatResponse(content=content, usage=usage)
```

**Automatic handling per provider**:

| Provider | Detection | Caching | Special Handling |
|----------|-----------|---------|-----------------|
| DeepSeek | Model starts with `deepseek-` | `extra_body: {"prefix_caching": True}` | Standard |
| OpenAI | No special prefix | Automatic server-side (>1024 tokens) | Standard |
| Ollama | Local base URL (e.g. `localhost:11434`) | `extra_body: {"keep_alive": "-1"}` | Model stays loaded in RAM |
| OpenRouter | API key starts with `sk-or-` | Provider-dependent | Route to best available model |

No endpoint hunting, no configuration guessing. Just a key and a model name.

#### Tool Runtime (`tools/runtime.py`)

**What**: Four stateless primitives — `read`, `write`, `edit`, `bash` — with safety validation.

**Why**: The execution & safety module (red in the architecture) is the *only* module that modifies the local environment. All command execution is gated through `ToolRuntime` which enforces:
- No privilege escalation (`sudo`, `su`, `chmod +s`)
- No path traversal deletions (`rm -rf ../`, `rm -rf /`)
- No redirects to system paths (`> /etc/passwd`)
- Exact occurrence-count matching for `edit` to prevent ambiguous replacements

```python
class ToolRuntime:
    def bash(self, command: str, cwd: Path) -> ToolResult:
        validation = self._validate_bash(command, cwd)
        if not validation.valid:
            return ToolResult(action=ToolAction.BASH, output="", success=False, stderr=validation.error)
        result = subprocess.run(command, ...)
        return ToolResult(action=ToolAction.BASH, output=result.stdout, success=result.rc == 0)
```

#### Budget Manager (`budget_manager/`)

**What**: Unconditional transcript compaction, duplicate removal, and large-string clipping.

**Why**: Context windows are finite. The budget manager aggressively deduplicates and compacts before the hard ceiling is hit, so the LLM always sees the most relevant context.

---

## Part 5 — Summary: What We've Built

**Speaker**: "So where are we today?"

### Achievements

1. **Complete specification-driven workflow**: Freestyle → Spec → Plan → Code → Verify, with full backward navigation on rejection
2. **Interactive TUI with keyboard-first design**: `DirectorySelectorApp` (hidden files, escape cancellation), `CanvasScreen` (live sticky note validation), `InteractiveDiffScreen` (reusable split-pane with `Ctrl+D` diffs), `MessageScreen`, `ConfirmScreen`
3. **Three-phase agent system**: Specification Agent (Socratic Q&A, opt-in capped rounds, inline gap templates), Planning Agent (tech plan + procedural steps with bracketed IDs), Coding Agent (9-step execution loop with retry)
4. **Approval Gateway**: Read auto-approves; write/edit/bash blocks for human consent with live code diffs
5. **Knowledge Graph**: SQLite-backed AST parser with query grammar (`files`, `classes:<path>`, `imports:<path>`)
6. **Memory Pyramid**: L0-L3 with confidence-filtered engineering profiles, scenario memory, and fact storage
7. **Provider Abstraction**: Single adapter for DeepSeek, OpenAI, Ollama with automatic caching and thinking tag stripping
8. **Safety Validation**: Bash commands validated against privilege escalation, path traversal, and system file redirects
9. **Audit System**: Dual-stream logging (local `.agent/audit.jsonl` + global `~/.config/corge/global_audit.jsonl`) + argumentation log for heuristic learning
10. **Bayesian Heuristic Updater**: EWMA-based self-improvement of spec wizard engagement with delta clipping and abandonment penalties
11. **Artifact Offloading**: Large outputs spill to `.agent/artifacts/` with `artifact://` URIs
12. **Session Persistence**: Full state save/resume across restarts
13. **Modular Monolith**: 8 modules + shared contracts layer, communicating through `typing.Protocol` interfaces and frozen dataclasses

---

## Part 6 — Future Work & Roadmap

**Speaker**: "This is a POC. Here's what we're deferring until real usage demands it."

| Area | Current | Planned |
|------|---------|---------|
| **Git Integration** | No git awareness | Transactional rollbacks, incremental graph updates, automated commits, branch isolation |
| **IDE Plugins** | Standalone TUI only | VS Code / JetBrains extensions via JSON-RPC |
| **GitHub Integration** | Local TUI approvals | PR automation, spec-gap comments, remote approvals |
| **Containerization** | `uv run` on host | Docker multi-stage build with sandboxed execution |
| **Vector Search** | SQLite `LIKE` scans | Semantic search via Qdrant/Chroma |
| **Multi-Agent Swarms** | Linear `SessionController` | Event-driven decentralized agents |
| **Cloud Persistence** | Local `.agent/` + `~/.config/corge/` | PostgreSQL + S3 for team workspaces |
| **Background Tasks** | Synchronous TUI thread | Cron-scheduled reindexing, GC, heuristic learning |
| **Planning Agent Skills** | Hardcoded prompt templates | Externalized `skills/planning.yaml` with automated validation gates |
| **Tmux Decoupling** | Single foreground process | Multi-pane tmux workspace for headless execution |

Each deferral is intentional — they follow the **lazy senior dev philosophy** encoded in `AGENTS.md`:

> *"Lazy means efficient, not careless. The best code is the code never written, and the most wasted code is code that satisfies a checklist but is unusable by a human developer."*

Every deferred item in `docs/03-future_work.md` names its **ceiling** (the condition under which it becomes necessary) and its **upgrade path** (exactly what to build when that ceiling is hit). For example:
- The naive `<think>` tag parser stays until a model emits multiple think blocks
- SQL `LIKE` search stays until the codebase is large enough to need embeddings
- The flat YAML parser stays until a schema uses nested structures

We did not build for hypothetical scale. We built for the POC exit criteria in the PRD. Nothing more.

---

## Part 7 — What We Learned

**Speaker**: "Finally, here's what this project taught us as a team."

### From Ideation to Architecture

1. **Specs-first sounds slow; it's actually faster.** The time spent writing a structured spec and plan is paid back tenfold in reduced rework. The Socratic wizard catches ambiguities before a single line of code is written.

2. **Protocol-driven modularity works.** Using `typing.Protocol` for every module boundary meant we could develop and test modules in parallel. The UI team never waited on the agent team. The agent team never waited on the data layer.

3. **The hardest part is not code generation — it's context engineering.** Getting the right information into the prompt, in the right order, within token limits, without overwhelming the model — that's where the real engineering effort went.

4. **Human-in-the-loop is not a safety feature, it's a quality feature.** The approval gateway is not just about preventing damage. Every time a human reviews a diff and says "no, I want it done differently", the system learns. The Bayesian updater captures this signal.

5. **Keyboard-first TUI is harder than web UI, but worth it.** Software engineers live in the terminal. Making every screen focusable on mount, supporting `Ctrl+D` for diffs, `Ctrl+A` for approve, `Escape` for reject — this makes Corge feel like a native part of the developer toolkit, not a separate application.

6. **YAGNI is not laziness; it's discipline.** Every deferred feature in `docs/03-future_work.md` has a named ceiling and a clear upgrade path. We did not build for hypothetical scale. We built for the POC exit criteria in the PRD. Nothing more.

7. **The modular monolith was the right call.** A microservices architecture would have added coordination overhead, eventual consistency problems, and debugging complexity that would have killed the POC. SQLite with WAL mode and connection pooling handled everything we needed.

### What's Next for Us

- Collect real usage feedback from engineers using the POC
- Prioritize the deferred features that actual users request most
- Ship the Git integration (it's the #1 requested safety net)
- Prepare the Docker image for zero-setup onboarding

---

## Appendix: Live Demo Walkthrough

### What we'll show on screen

1. **`uv run python -m corge ./demo-project`** — Launch with a target repository
2. **Repository Analysis** — Auto-detects the tech stack (e.g., "Detected framework: generic"), shows file count, knowledge graph bootstrapping
3. **CanvasScreen** — Type a feature request: *"Add a health check endpoint"*
4. **Socratic Spec Wizard** — Opt-in when gaps are detected; answer 2-3 clarifying questions
5. **Argumentation Diff** — Review the spec, fill in `[GAP: Testing Strategy]`, approve
6. **Technical Plan** — Review the generated architecture, edit if needed, approve
7. **Procedural Steps** — Review the task list with bracketed IDs, approve
8. **Execution Loop** — Watch the coding agent work step-by-step:
   - See context hydration (knowledge graph queries appear in the log)
   - Approve a file `write` with `Ctrl+D` to preview the diff
   - Approve an `edit` with occurrence-count verification
   - Approve a `bash` command to run tests
   - **Reject** one action to demonstrate backward navigation
9. **Verification** — All steps complete, tests pass, delivery summary shown
10. **Audit Log** — View the formatted `audit.jsonl` inside the TUI

### Troubleshooting the Live Demo

| Symptom | Fix |
|---------|-----|
| Provider connection fails | Check `CorgeAPIConfig.toml` has the correct `api_key` and `base_url` |
| Textual screen glitches | Ensure terminal is 80x24 minimum; use a modern terminal emulator (Kitty, Ghostty, Alacritty) |
| Knowledge graph empty | Run against a directory with at least one `.py` file |
| Slow LLM response | Check rate limits; consider switching to Ollama with a local model for demo speed |
