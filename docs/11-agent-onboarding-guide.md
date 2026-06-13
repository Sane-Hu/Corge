# Agent Onboarding Guide

## Purpose

This document is intended for AI coding agents and human contributors.

Its purpose is to explain how to navigate and implement the system described by the project documents.

This document is authoritative for implementation workflow.

---

# Project Identity

This project is NOT:

- a chatbot
- a code generator
- a vibe-coding assistant

This project IS:

A specification-driven engineering system.

The system enforces a contract between a human engineer and an AI engineer.

Implementation must always follow:

Specification
    ↓
Planning
    ↓
Approval
    ↓
Execution
    ↓
Verification
    ↓
Completion

Any implementation that bypasses this workflow is considered incorrect.

---

# Authoritative Documents

The implementation is defined by the following documents.

Priority order matters.

---

## 1. PRD

File:

01-prd.md

Purpose:

Defines product vision.

When conflicts exist:

PRD wins over all lower documents.

---

## 2. FRD

File:

02-frd.md

Purpose:

Defines required behavior.

When conflicts exist:

FRD wins over architecture documents.

---

## 3. System Architecture

File:

03-system-architecture.md

Purpose:

Defines major subsystems.

---

## 4. Module Contracts

File:

04-module-contracts.md

Purpose:

Defines responsibilities.

Agents must not violate module boundaries.

---

## 5. State Machine

File:

05-state-machine.md

Purpose:

Defines allowed workflow states.

Agents must not introduce undocumented states.

---

## 6. TUI Screen Map

File:

06-tui-screen-map.md

Purpose:

Defines user interaction flow.

---

## 7. Agent Loop Specification

File:

07-agent-loop-specification.md

Purpose:

Defines runtime behavior.

---

## 8. Execution Roadmap

File:

08-execution-roadmap.md

Purpose:

Defines implementation order.

---

## 9. Context Engineering Specification

File:

09-context-engineering-spec.md

Purpose:

Defines memory architecture and prompt assembly.

This document is critical.

Most implementation quality depends on this subsystem.

---

## 10. Future Roadmap

File:

10-roadmap-future-versions.md

Purpose:

Defines intentionally deferred features.

Agents must not pull future features into v0.1 unless explicitly instructed.

---

# Mandatory Architectural Principles

The following principles are non-negotiable.

---

## Principle 1

No Vibe Coding

Never allow implementation without:

- Requirements
- Acceptance Criteria
- Approved Plan

---

## Principle 2

Specification First

Implementation is downstream of specifications.

Never reverse this relationship.

---

## Principle 3

Repository Awareness

Agent decisions must be repository-aware.

Never generate code in isolation.

---

## Principle 4

Incremental Understanding

Repository understanding must be updated incrementally.

Never rebuild repository context unnecessarily.

---

## Principle 5

Context Discipline

Prompt quality is a first-class concern.

Avoid:

- Context bloat
- Duplicate file reads
- Excessive logs
- Unbounded history

---

## Principle 6

Human Authority

Human engineers remain the final authority.

All destructive actions require approval.

---

## Principle 7

Verification Required

Completion requires:

- Passing Tests
- Acceptance Criteria Satisfaction
- Human Approval

---

# Recommended Implementation Order

Build systems in the following order.

1. Core Project Skeleton

2. Provider Layer

3. Repository Scanner

4. Knowledge Graph

5. Context Engine

6. Specification Wizard

7. Planning Engine

8. Approval Layer

9. Tool Runtime

10. Agent Loop

11. Verification System

12. Audit Logging

Following this order minimizes rework.

---

# Forbidden Architectural Changes

Do not introduce:

- Global mutable state
- Tight provider coupling
- Hidden approvals
- Direct tool execution from UI
- Direct tool execution from providers
- Context assembled inside tools
- Monolithic prompt builders
- Unbounded memory growth

These violate project architecture.

---

# Definition of Success

The project succeeds when:

A human engineer can provide a specification,

The agent can generate an approved plan,

Implement the plan,

Verify the implementation,

Pass tests,

And complete the task,

Without violating repository conventions or architectural constraints.

That outcome is the benchmark against which all implementation decisions should be evaluated.