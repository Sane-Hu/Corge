# Product Requirements Document (PRD)

## Product Vision

A repository-aware coding agent that enforces disciplined software engineering practices through specification-driven development. The system treats software delivery as a controlled engineering workflow governed by explicit requirements, acceptance criteria, planning, verification, and human approval.

---

## Core Philosophy: Made for Programmers, by Programmers

Corge does not permit implementation from vague prompts. Every implementation is grounded in:
1. **User Requirements** & **Acceptance Criteria**
2. **Approved Specification** & **Approved Execution Plan**
3. **Verifiable Tests**

### Human-Agent Contract Flow
```text
Freestyle Canvas → Structured Specification → Execution Plan → Coding → Verification → Approval
```
Each stage reduces ambiguity and increases machine executability. Neither the human nor the agent should need to infer missing requirements.

---

## Technical Context & Repository Awareness

### Context-Driven Engineering
The quality of implementation depends on the quality of context. The system must:
- be able to run on an existing repository or an empty directory.
- be able to load previous session context.
- be able to semantically transform the user freestyle canvas into a structured specification and an execution plan
- be able to execute the execution plan step-by-step with interactive approval for each step
- be able to ask for approval before executing any action that modify the codebase
- Minimize context bloat.
- Preserve architectural understanding.
- Learn repository conventions (e.g. Service layers, DTOs, test patterns).
- Maintain long-running coherence.
- be able to reason about the repository structure and architecture
- be able to learn from user feedback and correct its mistakes
- be able to refuse to follow instructions that violate the user's intent or the system's principles

### Repository Knowledge Graph & Memory
The agent maintains an evolving understanding of repository structure, architecture, and coding conventions (represented via a Knowledge Graph, Facts, Engineering Profile, and Scenario Memory).
The system supports both existing repositories and empty directories (for bootstrapping a project directly from specs). In the last case, the agent should be able to generate a repository structure and architecture based on the user's requirements and the system's principles

---

## Provider Abstraction

The POC is optimized for DeepSeek Flash, but the architecture must support:
- DeepSeek
- Ollama
- OpenAI-Compatible APIs
through a provider abstraction layer.

---

## POC Exit & Success Criteria

A user must be able to:
1. Load a repository or initialize from an empty directory.
2. Create a specification interactively using the Socratic Spec-Wizard with framework-aware schemas and interactive validation (Freestyle Canvas), where clarifying questions are opt-in and answers are dynamically integrated.
3. Generate an architectural and procedural implementation plan through iterative refinement loops.
4. Approve the generated plan.
5. Observe the agent's step-by-step implementation.
6. Approve individual tool actions (write, edit, bash) with the ability to preview live code diffs interactively and retry failed execution steps directly.
7. Run tests to verify the changes.
8. Validate and complete the delivery.
9. Save and resume/recover sessions later.
10. Ensure the agent preserves existing repository and engineering conventions (aided by the Bayesian heuristic updater).

---

## Non-Goals for POC (v0.1)

- IDE Integration
- GitHub Integration
- Decentralized Multi-Agent Swarms
- Vector Databases & Embedding Search
- Autonomous Background Tasks
- Cloud Collaboration
