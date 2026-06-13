# AGENTS.md

# Mission

You are contributing to a specification-driven coding agent.

This repository does not build a chatbot, autocomplete tool, or vibe-coding assistant.

The product being built is a repository-aware engineering system that transforms approved specifications into verified software changes through a controlled workflow.

The primary goal is correctness, reliability, auditability, and engineering discipline.

The primary optimization target is not code generation speed.

The primary optimization target is specification-constrained software delivery.

---

# Read Before Making Changes

Before implementing architectural changes, read:

1. docs/01-prd.md
2. docs/02-frd.md
3. docs/03-system-architecture.md
4. docs/04-module-contracts.md
5. docs/07-agent-loop-specification.md
6. docs/09-context-engineering-spec.md

If there is a conflict:

PRD
→ FRD
→ Architecture
→ Module Contracts
→ Implementation

Higher-priority documents win.

---

# Core Principles

## Principle 1: No Vibe Coding

The system must never generate implementation directly from vague requests.

All implementation must originate from:

* Functional Requirements
* Acceptance Criteria
* Approved Plan

Any workflow that bypasses these artifacts is considered incorrect.

---

## Principle 2: Specification First

The workflow is:

Requirements
→ Acceptance Criteria
→ Specification
→ Plan
→ Approval
→ Execution
→ Verification
→ Completion

Do not reverse this order.

Do not collapse stages.

Do not skip stages.

---

## Principle 3: Human-Agent Contract

The human engineer and AI engineer operate through progressively refined artifacts.

Every stage must reduce ambiguity.

Every stage must increase executability.

The system exists to compress natural language requirements into verified software changes.

---

## Principle 4: Repository Awareness

The agent must never operate as if the repository were empty.

Before implementation:

* inspect repository structure
* inspect repository conventions
* inspect repository architecture

Repository context is mandatory.

---

## Principle 5: Incremental Understanding

Repository understanding must evolve incrementally.

Avoid rebuilding repository understanding from scratch whenever possible.

Prefer:

* graph updates
* targeted re-analysis
* incremental indexing

over full rescans.

---

## Principle 6: Context Discipline

Context quality is a first-class concern.

Avoid:

* repeated file reads
* duplicated content
* large unfiltered logs
* prompt bloat
* unnecessary transcript history

Assume context window space is scarce.

Treat tokens as a limited resource.

---

## Principle 7: Test-Based Completion

Tasks are not complete because the model says they are complete.

Tasks are complete when:

* Acceptance Criteria are satisfied
* Relevant tests exist
* Tests pass
* Human approval is granted

---

## Principle 8: Human Authority

The human engineer is always the final authority.

The system may recommend.

The system may automate.

The system may plan.

The system may implement.

The system may not override human approval.

---

# Architectural Rules

## UI Layer

Responsibilities:

* collect specifications
* display plans
* display execution
* request approvals

The UI must not contain business logic.

---

## Agent Layer

Responsibilities:

* planning
* reasoning
* execution decisions
* completion evaluation

The agent must not directly execute tools.

---

## Tool Layer

Responsibilities:

* read
* write
* edit
* bash

Tools must remain stateless.

Tools must not construct prompts.

Tools must not store memory.

---

## Context Layer

Responsibilities:

* repository analysis
* context retrieval
* memory retrieval
* prompt assembly support

The context layer must remain independent from providers.

---

## Provider Layer

Responsibilities:

* model communication

Providers must not:

* modify memory
* execute tools
* perform orchestration

Providers are adapters.

Nothing more.

---

# Memory Architecture

The project uses a memory pyramid.

## L0 — Session Events

Stores:

* tool calls
* approvals
* execution history

Raw event store.

Not directly loaded into prompts.

---

## L1 — Engineering Facts

Stores:

* repository facts
* framework facts
* discovered conventions

Examples:

* Uses Laravel
* Uses Pest
* Uses DTO Pattern

---

## L2 — Scenario Memory

Stores:

* feature-specific memory
* implementation progress
* blockers
* decisions

---

## L3 — Engineering Profile

Stores:

* team conventions
* architectural patterns
* coding preferences
* repository standards

This layer is extremely important.

The system should learn how the team builds software.

---

# Context Engineering Rules

Always prefer:

Current Spec
→ Current Acceptance Criteria
→ Current Plan
→ Engineering Profile
→ Relevant Repository Context

over:

Large transcripts
Large logs
Entire repositories

Prompts should contain only information necessary for the current task.

---

# Repository Knowledge Graph

Repository understanding is a first-class subsystem.

The graph should eventually represent:

* files
* modules
* imports
* dependencies
* architectural relationships

Do not treat repository analysis as a temporary preprocessing step.

Treat it as persistent knowledge.

---

# Approval Rules

Approval required:

* write
* edit
* delete
* bash

Approval not required:

* read
* inspect
* summarize
* search

Never bypass approval requirements.

---

# Logging Rules

All significant actions should be auditable.

Prefer structured logs.

Capture:

* plan generation
* approvals
* tool execution
* completion decisions

Logs should support future replay and debugging.

---

# Coding Standards

General standards:

* Python 3.12+
* Strict typing
* Small modules
* Dependency injection
* Explicit interfaces
* Clear ownership boundaries

Prefer:

* composition over inheritance
* immutable data structures where practical
* dataclasses for simple domain objects

Avoid:

* hidden side effects
* global mutable state
* tightly coupled modules

---

# POC Scope Protection

The following are intentionally out of scope for v0.1:

* Multi-agent systems
* Vector databases
* Embedding pipelines
* IDE integrations
* Git integrations
* Autonomous background execution
* Cloud collaboration

Do not introduce these unless explicitly requested.

---

# Definition of Success

A successful implementation enables the following workflow:

1. Analyze repository
2. Collect specification
3. Collect acceptance criteria
4. Generate plan
5. Obtain approval
6. Execute implementation
7. Run verification
8. Pass tests
9. Obtain completion approval

If a proposed change does not improve this workflow, reconsider whether it belongs in the project.
