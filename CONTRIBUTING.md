# Contributing to Corge

Thank you for your interest in contributing to Corge! This project follows a structured, specification-driven, and repository-aware workflow to ensure correctness and architectural consistency.

Please read this document carefully before making or submitting changes.

---

## Code Quality & Tooling Setup

This project uses `uv` for Python dependency management and environment isolation.

### Setting Up Your Environment
Ensure you have `uv` installed, then set up the virtual environment:
```bash
git clone <repository-url>
cd Corge
uv venv
```

### Pre-Submission Development Checks
Before opening a pull request or requesting a review, you must run and pass the following checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

If your environment restricts writes to the default `uv` cache, configure a local or writable cache path:
```bash
uv --cache-dir /tmp/corge-uv-cache run pytest
uv --cache-dir /tmp/corge-uv-cache run ruff check .
uv --cache-dir /tmp/corge-uv-cache run mypy src
```

---

## Contribution Workflow

Keep changes small, specified, and module-owned.

1. **Start from a Spec/Requirement**: Always start from an approved specification or open an issue to define one first. Do not add code/behavior without a spec gate.
2. **Identify the Owning Module**: Refer to `docs/02-technical-spec.md` to identify which module is responsible for the behavior.
3. **Write/Update Tests**: Add or update unit tests under the `tests/` directory matching the module name.
4. **Preserve Boundaries**: Keep changes scoped to one subsystem. Do not violate port interfaces or collapse architectural layers.
5. **Run Checks**: Execute `pytest`, `ruff`, and `mypy` locally.
6. **Trace Changes**: In your commits and pull requests, explain how your change traces back to a documented requirement.

---

## Pull Request Checklist

Please ensure your pull request descriptions include this completed checklist:

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

---

## Contributing with Web-Based LLMs

If you are using a web-based AI assistant (like ChatGPT, Claude, or Gemini) without an integrated agentic IDE, you must align the AI with our strict, specification-driven rules.

Before asking your LLM to write code, provide it with the prompt template found in the **Web LLM Contributor Prompt** section of `docs/02-technical-spec.md` or `docs/donotread.md`.

This prompt ensures the AI respects architectural boundaries, avoids speculative abstraction, and adheres to the document hierarchy (`PRD` > `Technical Spec` > `Implementation`). Do not let an LLM invent requirements or bypass the module contracts.

---

## Avoiding Git Conflicts

This repository is designed modularly so contributors can work in parallel without constantly touching the same files. To prevent conflicts:

* Prefer one branch per issue or specification.
* Prefer one module per pull request.
* Avoid broad formatting-only commits across the repository.
* Avoid moving files between modules unless the architecture docs require it.
* Do not edit generated lock or config files unless dependency or tooling changes are part of the pull request.
* Do not combine documentation, architecture changes, tooling changes, and feature implementation in one pull request unless the specification requires it.
* Update shared contracts only when multiple modules genuinely need the new type.
* When changing `src/corge/contracts/`, mention every affected consumer module in the pull request description.
* Rebase or merge from the target branch before opening a pull request, then rerun the checks.

Files that are more conflict-prone require extra care:
* `pyproject.toml`
* `uv.lock`
* `src/corge/contracts/*`
* `docs/02-technical-spec.md`

Coordinate with other contributors before editing those files.

---

## Team Git Guide (For Beginners)

If you are new to the team or to Git workflows, follow this process:

### 1. Update Before You Start
Before starting new work, pull the latest changes from the main project:
```bash
git checkout main
git pull
```

### 2. Create Your Own Branch
Create a branch with a short name that describes the task:
```bash
git checkout -b your-branch-name
```
Good branch names:
* `context-refresh-contracts`
* `approval-gateway-tests`
* `docs-pr-checklist`

### 3. Make A Small Change & Check Status
Check what files you changed:
```bash
git status
```
See the exact edits:
```bash
git diff
```

### 4. Save Your Work With A Commit
Add only the files that belong to your task:
```bash
git add path/to/changed_file.py
git commit -m "Brief summary of what was changed"
```

### 5. Send Your Branch To GitHub
Push your branch:
```bash
git push -u origin your-branch-name
```

### 6. If Git Says There Is A Conflict
First, update your branch:
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
Edit the file so only the correct final content remains, then run the checks again.
