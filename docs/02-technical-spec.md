# Corge Technical Specification

This document consolidates the functional requirements, architectural subsystems, state machine execution loop, context engineering details, TUI screen map, and developer onboarding instructions for Corge.

---

## 1. Functional Requirements (FRD)

- **FR-001 Spec Gate**: Implementation remains blocked until functional requirements, acceptance criteria, and approved specification exist. Outputs are saved to `specs/current/spec.md` and `specs/current/spec.yaml` relative to the repository root.
- **FR-002 Guided Spec Wizard**: Guides the engineer through business goals, user stories, functional requirements, constraints, acceptance criteria, and testing expectations.
- **FR-003 & FR-004 Repository Ingestion & Updates**: Analyzes repository structure, files, config, and build files. Updates are computed incrementally on file modifications.
- **FR-005 Repository Knowledge Graph**: A queryable representation of files, directories, classes, functions, and their dependencies.
- **FR-006 & FR-007 Memory Pyramid**:
  - **L0 Session Events**: Raw execution logs stored under `.agent/memory/l0/`.
  - **L1 Engineering Facts**: Repository-derived facts stored in `.agent/memory.db`.
  - **L2 Scenario Memory**: Feature-specific progress and blockers under `.agent/memory/scenarios/`.
  - **L3 Engineering Profile**: Coding styles/conventions stored in `.agent/engineering_profile.md`.
- **FR-008 Planning Phase**: Generates a step-by-step implementation plan. Execution remains blocked until approval.
- **FR-009 Human Approval Layer**: Intercepts destructive actions (`write`, `edit`, `bash`) for human consent. Read actions do not require approval.
- **FR-010 Artifact Offloading**: Large build/test logs are saved under `.agent/artifacts/` and referenced in prompts using the `artifact://` URI scheme.
- **FR-011 Context Budget Manager**: Enforces token budgets using clipping, deduplication, aging, summarization, and offloading.
- **FR-012 Test-Based Completion**: Delivery requires all acceptance criteria to be satisfied, tests to exist and pass, and human approval.
- **FR-013 Audit Logging**: Records prompts, plans, tools, approvals, and completions for accountability.
- **FR-014 Provider Abstraction**: Single integration point for models (DeepSeek, Ollama, OpenAI-compat). *[Status: Implemented]*
- **FR-015 Empty Repository Bootstrapping**: Allows complete project scaffolding starting from specification.

---

## 2. Architecture & Subsystems

The codebase is organized as a modular monolith:
```text
src/corge/
├── ui/                 # CLI presentation layer
├── agent/              # State machine and planning engine
├── context/            # Context retrieval coordination
├── prompt_assembler/   # EPC prompt generation
├── budget_manager/     # Token budgeting and compaction
├── knowledge_graph/    # Repository knowledge graph DB
├── memory/             # Pyramid memory stores
├── artifacts/          # Large log/output storage
├── approval/           # Human approval gateway
├── tools/              # Stateless execution primitives (read, write, edit, bash)
├── providers/          # Model API adapter
├── logging/            # Audit logger
└── contracts/          # Dataclasses and Typing Ports (protocols)
```

The concrete services implement decoupled ports defined as `typing.Protocol` interfaces in [ports.py](file:///home/sane/1-MY_DATA/Projects/AAI_NTI/Corge_PLAN/Corge/src/corge/contracts/ports.py).

---

## 3. State Machine & Execution Loop

### Lifecycle States
```text
START → REPOSITORY_SELECTION → REPOSITORY_ANALYSIS → SPEC_ENTRY → SPEC_VALIDATION → SPEC_APPROVAL 
  → PLAN_GENERATION → PLAN_REVIEW → PLAN_APPROVAL → EXECUTION → VERIFICATION → COMPLETION_REVIEW → DONE
```

### The 9-Step Execution Cycle
During the `EXECUTION` state, the agent loop runs the following synchronized loop:
1. **Observe**: Inspect current status and determine the next step in the approved plan.
2. **Refresh Context**: Hydrate context engine with repository updates, memory, and facts.
3. **Assemble Prompt**: Compile the ephemeral model view.
4. **Reason & Action Selection**: Model evaluates context and selects the next tool action.
5. **Approval Gateway**: Check permissions; query user for approval if action is `write`, `edit`, or `bash`.
6. **Execute Tool**: Invoke the authorized runtime tool.
7. **Verify Progress**: Evaluate tool output against step goals. If tool returns a non-zero exit code or error, immediately raise `ToolExecutionError`.
8. **Update Knowledge**: Extract facts, update knowledge graph, write scenario memory, and update profile rules.
9. **Repeat**: Loop back to step 1.

### Failure Path
If a tool execution fails, the orchestrator catches `ToolExecutionError`, updates scenario memory with the blocker details, suspends automated execution, and requests human intervention.

---

## 4. Context Engineering Details

### Database Schemes & Storage
All databases and persistent files reside under the `.agent/` directory:
- **Knowledge Graph**: `.agent/repo_graph.db`
  - *Node Types*: `File`, `Directory`, `Class`, `Function`, `Service`, `Controller`, `Model`, `Test`, `Config`
  - *Edge Types*: `imports`, `extends`, `implements`, `depends_on`, `references`, `tests`, `contains`
- **Memory Databases**: `.agent/memory.db`, `.agent/memory/l0/`, and `.agent/memory/scenarios/`
- **Engineering Profile**: `.agent/engineering_profile.md`

### Ephemeral Prompt Tiers
1. **Tier 1 (Always Present)**: Current Spec, Acceptance Criteria, Current Plan Step, Engineering Profile.
2. **Tier 2 (Repository)**: Engineering Facts, Graph Queries, Relevant File Summaries.
3. **Tier 3 (Task Memory)**: Scenario Memory (discoveries, decisions, blockers).
4. **Tier 4 (History)**: Recent actions, approvals, and edits.
5. **Tier 5 (Artifacts)**: URIs (`artifact://<id>`) and small summaries of large outputs.

---

## 5. TUI Screen Map

```text
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ Select Repository            │  │ Repository Analysis          │
│                              │  │                              │
│ /projects/my-app             │  │ Scanning... [83%]            │
│ [Enter] Continue             │  │                              │
└──────────────────────────────┘  └──────────────────────────────┘
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ Specification Wizard         │  │ Repository Understanding     │
│                              │  │                              │
│ Goal: [                      ] │  │ Framework: Laravel 12        │
│ Criteria: [                  ] │  │ Graph Nodes: 1234            │
└──────────────────────────────┘  └──────────────────────────────┘
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ Plan Review                  │  │ Execution Monitor            │
│                              │  │                              │
│ 1. Create Service            │  │ Step 2/4: Create DTO         │
│ 2. Create DTO                │  │ Proposing write...           │
│ [Approve] [Reject]           │  │                              │
└──────────────────────────────┘  └──────────────────────────────┘
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ Approval Request             │  │ Completion Screen            │
│                              │  │                              │
│ Action: write                │  │ Criteria: [x] [x] [x]        │
│ Target: app/DTO/LoginDTO.php │  │ Tests: [x] Passed            │
│ [Approve] [Reject]           │  │ [Approve Completion]         │
└──────────────────────────────┘  └──────────────────────────────┘
```

---

## 6. Onboarding & Developer Rules

### Priority Hierarchy
If documents conflict:
```text
PRD → Technical Spec → Code Implementation
```

### Core Developer Rules
- **No Vibe Coding**: Never implement code without requirements, acceptance criteria, and an approved plan.
- **Human Authority**: All destructive actions (`write`, `edit`, `bash`) require human verification.
- **No Global Mutable State**: Maintain strict modular encapsulation; modules pass boundary models (dataclasses) via ports.
- **Standardized Storage**: Never write databases or logs directly to the repository root. Always use `.agent/`.

### Recommended Implementation Order
1. Core Project Skeleton → 2. Provider Layer → 3. Repository Scanner → 4. Knowledge Graph → 5. Context Engine → 6. Specification Wizard → 7. Planning Engine → 8. Approval Layer → 9. Tool Runtime → 10. Agent Loop → 11. Verification System → 12. Audit Logging.

---

## 7. Web LLM Contributor Prompt

When using external LLMs without an integrated IDE, feed this system prompt to align the model with the project rules:

***
**Role**: You are an expert software engineer contributing to a rigorous specification-driven system. Your goal is correctness, safety, and engineering discipline. You do not write speculative or "vibe-based" code.

**Directives**:
1. **Specs as Truth**: Never implement behavior that contradicts the provided specifications. Never infer or invent requirements. If something is ambiguous, stop and ask for clarification.
2. **Hierarchy**: PRD > Technical Spec > Implementation.
3. **No Speculative Abstraction**: Write the smallest valid change necessary.
4. **Human Control**: Assume all file modifications and commands require explicit human review and approval.
5. **No Placeholders**: Never use stub or placeholder implementations.

**Workflow**:
1. Confirm you have read `docs/01-prd.md` and `docs/02-technical-spec.md`.
2. Outline your proposed plan before generating any code changes.
3. Provide precise, drop-in code edits and list how they are verified.
***
