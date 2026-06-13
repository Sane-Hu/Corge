# 03-system-architecture.md

# System Architecture

```text
┌─────────────────────────────┐
│         Textual UI          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│     Session Controller      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        Agent Loop           │
└───────┬──────────┬──────────┘
        │          │
        ▼          ▼
 Context      Planner
 Engine

        │
        ▼

┌─────────────────────────────┐
│     Prompt Assembler        │
└──────────────┬──────────────┘
               │
               ▼

┌─────────────────────────────┐
│     Context Budgeter        │
└──────────────┬──────────────┘
               │
               ▼

┌─────────────────────────────┐
│      Repository Graph       │
└──────────────┬──────────────┘
               │
               ▼

┌─────────────────────────────┐
│       Memory Pyramid        │
└──────────────┬──────────────┘
               │
               ▼

┌─────────────────────────────┐
│       Artifact Store        │
└──────────────┬──────────────┘
               │
               ▼

┌─────────────────────────────┐
│      Approval Gateway       │
└──────────────┬──────────────┘
               ▼

┌─────────────────────────────┐
│       Tool Runtime          │
│ read write edit bash        │
└─────────────────────────────┘
```

---

## Architectural Principles

### Spec-Driven

All implementation originates from approved specifications.

### Context-Driven

Prompt quality is determined through context engineering.

### Repository-Aware

The system maintains a continuously evolving repository understanding.

### Human Controlled

Destructive actions require approval.

### Incremental

Repository understanding is updated incrementally rather than rebuilt.

---

## Major Subsystems

### UI Layer

Textual TUI.

### Agent Layer

Planning and execution.

### Context Layer

Prompt assembly and budgeting.

### Knowledge Layer

Graph and memory systems.

### Execution Layer

Tools and approvals.

### Persistence Layer

Logs, artifacts, memory.
