# 02-frd.md

# Functional Requirements Document (FRD)

## FR-001 Specification Gate

Implementation must be blocked until:

- Functional Requirements exist
- Acceptance Criteria exist
- Specification is approved

Outputs:

```text
/specs/current/spec.md
/specs/current/spec.yaml
```

---

## FR-002 Guided Specification Wizard

The wizard must actively guide engineers toward specifications favorable to reliable implementation.

The wizard elicits:

- Business Goal
- User Story
- Functional Requirements
- Constraints
- Acceptance Criteria
- Testing Expectations

Goal:

Reduce ambiguity before planning begins.

---

## FR-003 Repository Ingestion

System analyzes:

- Repository Tree
- Key Files
- Configuration Files
- Build Files

Outputs:

- Repository Snapshot
- File Summaries
- Initial Knowledge Graph
- Engineering Facts

---

## FR-004 Incremental Repository Updates

Repository understanding must be incrementally updated.

Triggers:

- Agent modifications
- Human modifications
- File creation
- File deletion

Full re-analysis should be avoided.

---

## FR-005 Repository Knowledge Graph

The system maintains a structured graph representing:

- Files
- Directories
- Classes
- Functions
- Dependencies
- Architectural Relationships

The graph must be queryable by the agent.

---

## FR-006 Engineering Profile

The system maintains:

```text
.agent/engineering_profile.md
```

Representing repository and team conventions.

Sources:

- Repository analysis
- AGENTS.md
- User modifications
- Historical implementation patterns

---

## FR-007 Memory Pyramid

The system maintains four memory layers.

### L0 Session Events

Raw activity storage.

### L1 Engineering Facts

Repository-derived facts.

### L2 Scenario Memory

Feature-specific memory.

### L3 Engineering Profile

Repository-specific coding conventions.

---

## FR-008 Planning Phase

Agent generates implementation plan.

Execution remains blocked until approval.

---

## FR-009 Human Approval Layer

Approval required for:

- write
- edit
- bash

Approval not required for:

- read

---

## FR-010 Artifact Offloading

Large outputs must be stored externally.

Examples:

- Test output
- Build logs
- Command logs

Prompt receives summaries and references instead of raw content.

---

## FR-011 Context Budget Management

System must manage token budgets using:

- Clipping
- Deduplication
- Aging
- Summarization
- Artifact Offloading

---

## FR-012 Test-Based Completion

Completion requires:

- Acceptance Criteria satisfied
- Tests exist
- Tests pass
- Human approval

---

## FR-013 Audit Logging

System records:

- Prompts
- Plans
- Tool Calls
- Approvals
- Results

---

## FR-014 Provider Abstraction

Provider interface supports:

- DeepSeek
- Ollama
- OpenAI-compatible APIs

POC optimized for DeepSeek Flash.

---

## FR-015 Empty Repository Bootstrapping

Agent can initialize a project from specification alone.

```text
Empty Directory
    ↓
Specification
    ↓
Plan Generation
    ↓
Application Skeleton
```
