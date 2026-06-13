# Corge

Corge is the working repository for a specification-driven coding agent.

This project is currently initialized as a team boilerplate only. It defines project structure, workflow artifacts, and development tooling, but it does not implement agent behavior, tool execution, provider calls, or a user interface.

## Setup

Install dependencies with `uv`:

```bash
uv sync
```

Run the placeholder test suite:

```bash
uv run pytest
```

Check that the package compiles:

```bash
python -m compileall src
```

## Starting Task Work

All implementation work must follow the repository workflow:

```text
Requirements
Acceptance Criteria
Specification
Plan
Approval
Execution
Verification
Completion
```

Use the templates in `specs/current/`, `acceptance/current/`, `plans/current/`, and `approvals/` to prepare task artifacts before implementation begins.

## Current Scope

The scaffold intentionally contains no runtime public APIs and no CLI. Module directories mirror the architecture documents so future work can implement the contracts without restructuring the repository.

