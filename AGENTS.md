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
7. docs/11-agent-onboarding-guide

If there is a conflict:

PRD
→ FRD
→ Architecture
→ Module Contracts
→ Implementation

Higher-priority documents win.

---

# Core Principles

1. Specifications are the source of truth.
2. Never implement behavior that contradicts approved specifications.
3. Requirements are discovered from repository documents, not inferred from assumptions.
4. Prefer deterministic behavior over heuristic behavior.
5. Prefer explicit contracts over implicit coupling.
6. Prefer verification over confidence.
7. Every change must be traceable to a documented requirement.
8. Every modification must preserve repository consistency.
9. Architectural boundaries must be respected.
10. Temporary shortcuts become permanent defects; avoid them.
11. Minimize complexity whenever possible.
12. Avoid introducing hidden state.
13. Avoid introducing undocumented behavior.
14. Avoid introducing speculative abstractions.
15. Do not optimize for future requirements that do not exist.
16. Do not add features that are not requested by specifications.
17. Favor maintainability over cleverness.
18. Favor clarity over brevity.
19. Favor correctness over implementation speed.
20. Favor reproducibility over convenience.

---

# Required Operating Model

Before writing code:

1. Read all relevant specifications.
2. Identify affected modules.
3. Identify affected contracts.
4. Identify dependencies.
5. Create an implementation plan.
6. Validate the plan against repository architecture.

During implementation:

1. Make the smallest valid change.
2. Preserve existing interfaces unless specifications require changes.
3. Keep changes localized.
4. Maintain module responsibilities.
5. Avoid unrelated refactoring.
6. Avoid opportunistic feature additions.
7. Keep behavior aligned with specifications.

After implementation:

1. Verify requirements are satisfied.
2. Verify contracts remain valid.
3. Verify no architectural violations were introduced.
4. Verify no unrelated behavior changed.
5. Verify tests still pass.
6. Verify documentation remains accurate.

---

# Repository Awareness Requirements

You are not operating on isolated files.

You are operating on a connected system.

Before modifying code, identify:

- Which module owns the behavior.
- Which specifications define the behavior.
- Which interfaces expose the behavior.
- Which components consume the behavior.
- Which tests validate the behavior.

Do not make changes until system impact is understood.

---

# Specification Traceability

Every significant implementation decision should be traceable to:

- A PRD requirement.
- A FRD requirement.
- A module contract.
- An architecture constraint.
- An approved specification.

If traceability cannot be established:

Stop and request clarification.

Do not invent requirements.

---

# Architecture Preservation Rules

Do not:

- Collapse architectural layers.
- Bypass defined interfaces.
- Introduce hidden dependencies.
- Create circular dependencies.
- Mix infrastructure and business logic.
- Move logic across ownership boundaries without specification approval.
- Replace existing patterns without justification.
- Introduce framework-specific coupling into domain logic.

Maintain the architectural intent described in the repository documentation.

---

# Context Engineering Rules

Context is a managed resource.

When performing work:

1. Load only relevant context.
2. Prefer authoritative sources.
3. Resolve conflicts using repository precedence rules.
4. Avoid relying on stale assumptions.
5. Re-read specifications when uncertainty exists.
6. Validate implementation decisions against current repository state.

Do not treat previous assumptions as facts.

---

# Code Quality Expectations

Generated code must be:

- Correct.
- Readable.
- Testable.
- Deterministic.
- Maintainable.
- Consistent with repository conventions.

Avoid:

- Dead code.
- Placeholder implementations.
- Silent failures.
- Magic values.
- Unused abstractions.
- Unnecessary complexity.

---

# Testing Requirements

Changes are incomplete until verified.

When applicable:

1. Add tests for new behavior.
2. Update tests affected by requirement changes.
3. Preserve existing test coverage.
4. Verify regression risk.
5. Verify edge cases.
6. Verify failure paths.

Never claim code works without verification evidence.

---

# Documentation Requirements

Update documentation when:

- Behavior changes.
- Interfaces change.
- Contracts change.
- Architectural decisions change.
- Configuration changes.

Documentation must remain aligned with implementation.

---

# Prohibited Behaviors

Do not:

- Invent requirements.
- Invent APIs.
- Invent module responsibilities.
- Invent architecture.
- Invent specifications.
- Ignore repository documents.
- Ignore contract violations.
- Ignore failing tests.
- Hide uncertainty.
- Claim verification that was not performed.
- Modify unrelated systems.
- Introduce speculative functionality.
- Bypass established workflows.

---

# Decision-Making Under Uncertainty

If requirements are unclear:

1. Stop implementation.
2. Identify the ambiguity.
3. Identify affected specifications.
4. Explain available interpretations.
5. Request clarification.

Do not resolve ambiguous requirements independently.

---

# Definition of Done

Work is complete only when:

- Requirements are satisfied.
- Specifications remain consistent.
- Architecture remains valid.
- Contracts remain valid.
- Tests pass.
- Documentation is updated.
- No unintended changes were introduced.
- Traceability can be demonstrated.

Anything less is incomplete work.