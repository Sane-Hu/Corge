# Corge

Corge is a specification-driven, repository-aware engineering system.

This project is not a chatbot, autocomplete tool, or vibe-coding assistant. It is
being built as a controlled engineering workflow that transforms approved
specifications into verified software changes.

The current codebase is a modular monolith skeleton. The packages under
`src/corge/` define module boundaries and typed contracts only. Most methods
intentionally raise `NotImplementedError` until their behavior is specified,
planned, implemented, and verified.

## Read This First

Before contributing, read the project documents in this order:

1. `AGENTS.md`
2. `docs/01-prd.md`
3. `docs/02-technical-spec.md`

If documents conflict, higher-priority documents win:

```text
PRD -> Technical Spec -> Implementation
```

Do not resolve unclear requirements by guessing. Open an issue or discussion and
name the conflicting or missing requirement.

## Architecture

The system is organized as a modular monolith:

```text
src/corge/
├── ui/
├── agent/
├── context/
├── prompt_assembler/
├── budget_manager/
├── knowledge_graph/
├── memory/
├── artifacts/
├── approval/
├── tools/
├── providers/
├── logging/
├── schemas/
└── contracts/
```

Each module owns the responsibilities documented in
`docs/02-technical-spec.md`. Keep behavior inside the module that owns it.
Do not bypass module boundaries for convenience.

Important boundaries:

- `ui` displays state and requests user input; it does not contain business logic.
- `agent` plans and coordinates execution; it does not directly execute tools.
- `tools` exposes stateless execution primitives.
- `approval` is the single approval authority.
- `providers` is the only external model integration point.
- `context`, `prompt_assembler`, and `budget_manager` keep context engineering
  separate from execution.
- `knowledge_graph`, `memory`, and `artifacts` preserve repository understanding,
  continuity, and large-output offloading.

## Development Setup

This project uses `uv`.

### Development Checks
```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

If your environment cannot write to the default `uv` cache, use a writable cache:

```bash
uv --cache-dir /tmp/corge-uv-cache run pytest
uv --cache-dir /tmp/corge-uv-cache run ruff check .
uv --cache-dir /tmp/corge-uv-cache run mypy src
```

### Running Corge

#### Option A: Run directly using `uv`
Run the terminal app directly from the project directory:
```bash
uv run corge [path/to/target/repo]
```

#### Option B: Clean CLI install (Recommended)
You can install Corge as a global/user tool using `uv tool`. By installing with `--editable`, any local code changes are immediately active:
```bash
uv tool install --editable /path/to/Corge
```
Once installed, simply run the **`corge`** command from any directory (including inside your operated-on repository):
```bash
corge [path/to/target/repo]
```
*(If no path argument is provided, Corge launches the interactive directory selector.)*

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to set up your development environment, run tests, and follow our contribution workflow.

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

This project is licensed under the terms of the MIT License. See [LICENSE](LICENSE) for details.

## Current Status

The repository contains the foundation skeleton, with the following implementation progress:

### Implemented Modules
- **Contracts & Port Definitions** ([contracts](src/corge/contracts))
- **Knowledge Graph** ([knowledge_graph](src/corge/knowledge_graph)): Includes Discovery Mode fuzzy search.
- **Context Engine** ([context](src/corge/context)): Integrates with `KnowledgeGraphPort` and `MemoryStorePort` to construct the layered `ContextBundle`. Enforces the strict 3-Layer isolation strategy (shielding the coding phase from argumentation context pollution) and implements the N-1 Markov state trajectory compression system.
- **Prompt Assembler** ([prompt_assembler](src/corge/prompt_assembler)): Renders the five-tier ephemeral prompt structure.
- **Artifact Store** ([artifacts](src/corge/artifacts)): Manages copying large files/logs to storage and referencing them via `artifact://` URIs.
- **Approval Gateway** ([approval](src/corge/approval)): Contains logic for UI delegation, audit logging delegation, and auto-approval for read actions.
- **UI & Presentation Layer** ([ui](src/corge/ui)): Uses an asynchronous `textual`-based Terminal UI (TUI). Integrates cleanly with `tmux` and manages synchronous Agent execution in background threads via `@work`. Supports Freestyle Canvas brainstorming with ghost text and active-validated sticky notes (`@node:<id>`) (validation is debounced to submit to prevent UI latency), side-by-side Interactive Diff editors with a dedicated "Reject" button, and fully functioning readouts for repository context, execution state, engineering profile, and memory logs.
- **Provider Adapter** ([providers](src/corge/providers)): Concrete OpenAI-compatible model integration adapter. Supports OpenAI (automatic prompt caching), DeepSeek (explicit prefix caching), and local Ollama (keep-alive management). Automatically handles reasoning models by stripping `<think>...</think>` tags and populating standard token usage details (`prompt_tokens`, `completion_tokens`, `cache_read_tokens`, `cache_write_tokens`).
- **Token Budget Manager** ([budget_manager](src/corge/budget_manager)): Enforces context token management to prevent bloat. Implements un-conditional transcript compaction, duplicate file/fact removal, and large-string clipping for cost-savings.
- **Tool Runtime** ([tools](src/corge/tools)): Stateless execution primitives. Primitives `read`, `write`, `edit` and `bash` are fully implemented with timeout handling, non-blocking threaded output streaming, and explicit occurrence-count checks to prevent ambiguous edits.
- **Logging** ([logging](src/corge/logging)): Includes Argumentation Logging for Socratic Q&A and canvas snapshots. Implements a dedicated `.agent/audit.jsonl` Audit Logger for serializing prompts, tools, approvals, and completion events with ISO-8601 timestamps.
- **Tech-Stack Schemas** ([schemas](src/corge/schemas)): Generic and framework-specific schemas (e.g., Laravel) for tailoring prompts.
- **Agent Subsystems** ([agent](src/corge/agent)): Fully implemented `SessionController` orchestration across specialized `SpecificationAgent` (with JSON gap parsing and Socratic loops), `PlanningAgent` (using sequential step identifiers), and `CodingAgent` (handling all 4 tool actions, completion evaluation, and interactive diff rejection pivots). Includes support for empty repository bootstrapping, session serialization/persistence, and standardizes learning updates via the `BayesianUpdater` implementation.
- **Memory Store** ([memory](src/corge/memory)): Fully implemented 4-tier memory pyramid with connection pooling and `journal_mode=WAL` for high-performance concurrent access. Includes L0 session events (append-only JSONL), L1 engineering facts (SQLite with deduplication), L2 scenario memory per feature (streamable JSONL), and L3 engineering profile (dynamically parsed, confidence-filtered markdown).
