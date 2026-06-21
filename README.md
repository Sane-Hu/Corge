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

## Team Development For Beginners

Git tracks changes to files. GitHub is the website where the team shares those
changes, reviews them, and decides what becomes part of the project.

The safest way to work is:

```text
main branch -> your branch -> pull request -> review -> merge
```

`main` is the shared project history. Do not work directly on `main`. Create your
own branch for each task so your work stays separate from everyone else's work.

### 1. Get The Project

Install Git, then copy the project to your machine:

```bash
git clone <repository-url>
cd Corge
```

Check which branch you are on:

```bash
git branch
```

If you see `main` with a star next to it, you are on the shared base branch.

### 2. Update Before You Start

Before starting new work, download the latest team changes:

```bash
git checkout main
git pull
```

This lowers the chance that you and someone else edit old versions of the same
files.

### 3. Create Your Own Branch

Create a branch with a short name that describes the task:

```bash
git checkout -b agent-plan-stubs
```

Good branch names:

- `context-refresh-contracts`
- `approval-gateway-tests`
- `docs-pr-checklist`

Avoid vague names like `changes`, `fix`, or `my-work`.

### 4. Make A Small Change

Work on one issue, one specification, or one module at a time. For this project,
that usually means editing one package under `src/corge/` plus its tests.

While working, check what files you changed:

```bash
git status
```

See the exact edits:

```bash
git diff
```

If you see unrelated files in the diff, stop and separate the work before
continuing.

### 5. Run Checks

Before sharing your work, run:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

If a check fails, fix it before opening a pull request. If you cannot fix it,
say clearly what failed and include the command output summary in the pull
request.

### 6. Save Your Work With A Commit

A commit is a named checkpoint. Add only the files that belong to your task:

```bash
git add README.md
git commit -m "Document team contribution workflow"
```

Use a commit message that says what changed. Keep commits focused. A reviewer
should be able to understand why the commit exists.

### 7. Send Your Branch To GitHub

Push your branch:

```bash
git push -u origin agent-plan-stubs
```

GitHub will show a button to open a pull request. A pull request is a request for
the team to review and merge your branch into `main`.

### 8. Open A Pull Request

In the pull request description, include:

- What requirement, issue, or spec this change implements.
- Which module owns the change.
- Which tests you ran.
- Any files that are likely to conflict with other work.
- Anything you are unsure about.

Ask for review before merging. Do not merge your own substantial change without
another person reviewing it.

### 9. If Git Says There Is A Conflict

A conflict means Git found two edits to the same part of a file and needs a
human to choose the correct result.

Do not panic and do not guess. First, update your branch:

```bash
git checkout main
git pull
git checkout your-branch-name
git merge main
```

If Git reports conflicts, open the listed files and look for markers like:

```text
<<<<<<< HEAD
your version
=======
other version
>>>>>>> main
```

Edit the file so only the correct final content remains, then run the checks
again. If the conflict is in `pyproject.toml`, `uv.lock`, `src/corge/contracts/`,
or an architecture document, ask the team before resolving it alone.

### 10. After Your Pull Request Is Merged

Return to `main` and update:

```bash
git checkout main
git pull
```

Then create a fresh branch for the next task. This keeps old work from leaking
into new work.

## Contribution Workflow

Keep changes small, specified, and module-owned.

1. Start from an approved requirement or open an issue to define one.
2. Identify the owning module in `docs/02-technical-spec.md`.
3. Update or add tests for the behavior before claiming completion.
4. Keep changes scoped to one subsystem whenever possible.
5. Run `pytest`, `ruff`, and `mypy` before opening a pull request.
6. Explain which requirement, contract, or architecture rule the change traces to.

Do not add feature behavior just because the skeleton makes it easy to do so.
Behavior belongs behind the specification gate.

## Contributing with Web-Based LLMs

If you are using a web-based AI assistant (like ChatGPT, Claude, or Gemini) without an integrated agentic IDE, you must align the AI with our strict, specification-driven rules.

Before asking your LLM to write code, provide it with the prompt template found in the Web LLM Contributor Prompt section of `docs/02-technical-spec.md`.

This prompt ensures the AI respects architectural boundaries, avoids speculative abstraction, and adheres to the document hierarchy (PRD > FRD > Architecture). Do not let an LLM invent requirements or bypass the module contracts.

## Avoiding Git Conflicts

This repository is intentionally modular so contributors can work in parallel
without constantly touching the same files.

Use these habits:

- Prefer one branch per issue or specification.
- Prefer one module per pull request.
- Avoid broad formatting-only commits across the repository.
- Avoid moving files between modules unless the architecture docs require it.
- Do not edit generated lock or config files unless dependency or tooling changes
  are part of the pull request.
- Do not combine documentation, architecture changes, tooling changes, and feature
  implementation in one pull request unless the specification requires it.
- Update shared contracts only when multiple modules genuinely need the new type.
- When changing `src/corge/contracts/`, mention every affected consumer module in
  the pull request description.
- Rebase or merge from the target branch before opening a pull request, then rerun
  the checks.

Files that are more conflict-prone require extra care:

- `pyproject.toml`
- `uv.lock`
- `src/corge/contracts/*`
- `docs/02-technical-spec.md`

Coordinate before editing those files.

## Pull Request Checklist

Use this checklist in every pull request:

```text
- [ ] I read the relevant specs and module contracts.
- [ ] The change is traceable to a documented requirement or approved issue.
- [ ] The owning module is identified.
- [ ] Module boundaries are preserved.
- [ ] No unrelated refactoring is included.
- [ ] Tests were added or updated where applicable.
- [ ] `uv run pytest` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run mypy src` passes.
- [ ] Documentation was updated if behavior, contracts, config, or architecture changed.
```

## Current Status

The repository contains the foundation skeleton, with the following implementation progress:

### Implemented Modules
- **Contracts & Port Definitions** ([contracts](src/corge/contracts))
- **Knowledge Graph** ([knowledge_graph](src/corge/knowledge_graph)): Includes Discovery Mode fuzzy search.
- **Context Engine** ([context](src/corge/context)): Implements Markov Context Chaining (N-1 injection) and layer isolation, ensuring Layer 1 Argumentation metadata does not leak into execution.
- **Approval Gateway** ([approval](src/corge/approval)): Contains logic for UI delegation, audit logging delegation, and auto-approval for read actions.
- **UI & Presentation Layer** ([ui](src/corge/ui)): Uses an asynchronous `textual`-based Terminal UI (TUI). Integrates cleanly with `tmux` and manages synchronous Agent execution in background threads via `@work`. Supports the Freestyle Canvas brainstorming and side-by-side Interactive Diff editors.
- **Provider Adapter** ([providers](src/corge/providers)): Concrete OpenAI-compatible model integration adapter. Supports OpenAI (automatic prompt caching), DeepSeek (explicit prefix caching), and local Ollama (keep-alive management). Automatically handles reasoning models by stripping `<think>...</think>` tags and populating standard token usage details (`prompt_tokens`, `completion_tokens`, `cache_read_tokens`, `cache_write_tokens`).
- **Logging** ([logging](src/corge/logging)): Includes Argumentation Logging for Socratic Q&A and canvas snapshots.
- **Tech-Stack Schemas** ([schemas](src/corge/schemas)): Generic and framework-specific schemas (e.g., Laravel) for tailoring prompts.
- **Agent Subsystems** ([agent](src/corge/agent)): Fully implemented `SessionController` orchestration across specialized `SpecificationAgent`, `PlanningAgent`, and `CodingAgent`. Includes LLM instruction logic for JSON gap parsing, procedural step chunking, and Markov chain execution. Also contains `HeuristicUpdater` (Bayesian spec-wizard learning) and `SchemaTailor` (framework-aware schema loading).

### Pending Implementation (Stub Modules)
- **Prompt Assembler** ([prompt_assembler](src/corge/prompt_assembler))
- **Token Budget Manager** ([budget_manager](src/corge/budget_manager))
- **Memory Store** ([memory](src/corge/memory))
- **Artifact Store** ([artifacts](src/corge/artifacts))
- **Tool Runtime** ([tools](src/corge/tools))
- **Audit Logging** ([logging](src/corge/logging)): Audit logger remains a stub.

