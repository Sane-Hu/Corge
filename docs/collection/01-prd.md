# 01-prd.md

# Product Requirements Document (PRD)

## Product Name

Spec-First Coding Agent (Working Name)

---

## Product Vision

A repository-aware autonomous coding agent that enforces disciplined software engineering practices through specification-driven development.

Unlike vibe-coding tools, the system treats software delivery as an engineering process governed by explicit requirements, acceptance criteria, planning, verification, repository understanding, and human approval.

The agent acts as an AI software engineer operating under a mutual contract with the human engineer.

---

## Core Philosophy

### No Vibe Coding

The system does not permit implementation from vague prompts.

Every implementation must be grounded in:

- Functional Requirements
- Acceptance Criteria
- Approved Specification
- Approved Execution Plan
- Verifiable Tests

---

## Human-Agent Contract

Development progresses through progressively executable artifacts.

```text
Requirements
    ↓
Acceptance Criteria
    ↓
Specification
    ↓
Plan
    ↓
Implementation
    ↓
Verification
    ↓
Approval
```

Each stage reduces ambiguity and increases machine executability.

Neither the human nor the agent should need to infer missing requirements.

---

## Context-Driven Engineering

The quality of implementation depends on the quality of context.

The system must:

- Minimize context bloat
- Preserve architectural understanding
- Learn repository conventions
- Maintain long-running coherence
- Incrementally update repository understanding

Context Engineering is considered a first-class subsystem.

---

## Repository-Aware Engineering

The agent maintains an evolving understanding of:

- Repository Structure
- Architectural Patterns
- Framework Conventions
- Team Conventions
- File Relationships

Repository understanding is represented through:

```text
Repository Knowledge Graph
Engineering Facts
Engineering Profile
Scenario Memory
```

---

## Empty Repository Support

The system must support:

```text
Existing Repository
```

and

```text
Empty Directory
```

allowing complete project bootstrapping directly from specifications.

---

## Engineering Profile

The system learns how the engineering team writes software.

Examples:

- Service Layer usage
- DTO usage
- Repository Pattern usage
- Testing conventions
- Dependency Injection preferences

The profile influences all future implementations.

---

## DeepSeek First

The POC is optimized for DeepSeek Flash.

However the architecture must support:

- DeepSeek
- Ollama
- OpenAI-Compatible APIs

through a provider abstraction layer.

---

## Target Users

Primary:

- Senior Software Engineers
- Staff Engineers
- Technical Leads
- Solutions Architects

Secondary:

- Engineering Teams
- Mid-Level Developers

---

## Success Criteria

User can:

1. Load repository
2. Create specification
3. Define acceptance criteria
4. Approve generated plan
5. Observe execution
6. Approve changes
7. Run tests
8. Validate completion
9. Resume sessions later
10. Preserve repository conventions

---

## Non-Goals (POC)

- IDE Integration
- GitHub Integration
- Multi-Agent Systems
- Vector Databases
- Embedding Search
- Autonomous Background Tasks
- Cloud Collaboration
