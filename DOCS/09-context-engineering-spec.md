# 09-context-engineering-spec.md

# Context Engineering Specification

## Purpose

The Context Engineering System ensures the agent receives the smallest amount of information required to perform the next action while preserving architectural understanding, task continuity, and engineering conventions.

---

# Core Principle

The system separates:

```text
What the Agent Knows
```

from

```text
What the Model Sees
```

Knowledge is persistent.

Prompts are ephemeral.

---

# Knowledge System

Components:

```text
Repository Knowledge Graph

Memory Pyramid

Engineering Profile

Artifact Store
```

---

# Repository Knowledge Graph

## Purpose

Maintain repository understanding.

---

## Node Types

```text
File
Directory
Class
Function
Service
Controller
Model
Test
Config
```

---

## Edge Types

```text
imports
extends
implements
depends_on
references
tests
contains
```

---

## Storage

```text
repo_graph.db
```

---

## Incremental Updates

Triggered by:

- Human edits
- Agent edits
- File creation
- File deletion

Only affected portions are recomputed.

---

# Memory Pyramid

## L0 Session Events

Storage:

```text
.agent/memory/l0/
```

Contains:

- Tool Calls
- User Actions
- Approvals
- Test Runs

Never injected directly.

---

## L1 Engineering Facts

Storage:

```text
memory.db
```

Examples:

```text
Laravel 12

Uses Pest

Uses DTOs
```

---

## L2 Scenario Memory

Storage:

```text
.agent/memory/scenarios/
```

Tracks:

- Progress
- Decisions
- Discoveries
- Blockers
- Next Actions

---

## L3 Engineering Profile

Storage:

```text
.agent/engineering_profile.md
```

Examples:

```text
Use Service Layer

Use DTOs

Prefer Constructor Injection

Use readonly Classes
```

Always influences implementation.

---

# Engineering Profile Learning

Sources:

- Repository Analysis
- AGENTS.md
- User Edits
- Historical Implementations

---

## Confidence Scoring

Example:

```yaml
rules:
  - statement: Uses DTOs
    confidence: 0.93
```

Low-confidence rules are ignored.

---

# Artifact Store

Storage:

```text
.agent/artifacts/
```

Examples:

```text
test_run_001.log

build_004.log

migration_002.log
```

---

# Artifact References

Instead of injecting:

```text
5000 lines
```

Inject:

```text
artifact://test_run_001
```

plus summary.

---

# Prompt Assembly System

Responsible for selecting context.

---

# Priority Tiers

## Tier 1

Always Present

```text
Current Spec

Acceptance Criteria

Current Plan

Current Step

Engineering Profile
```

---

## Tier 2

Repository Understanding

```text
Engineering Facts

Graph Queries

Relevant File Summaries
```

---

## Tier 3

Task Memory

```text
Scenario Memory
```

---

## Tier 4

Recent Activity

```text
Recent Actions

Recent Approvals

Recent Edits
```

---

## Tier 5

Artifacts

Referenced only.

---

# Context Budget Manager

Responsibilities:

```text
Estimate Tokens

Rank Context

Compact Context

Enforce Limits
```

---

# Compaction Strategies

## Clipping

Shorten large outputs.

---

## Deduplication

Remove repeated file reads.

---

## Aging

Compress older information.

---

## Summarization

Compress long histories.

---

## Artifact Offloading

Replace verbose outputs with references.

---

# Retrieval Pipeline

```text
Determine Goal

Query Graph

Query Facts

Query Engineering Profile

Query Scenario Memory

Retrieve Relevant Files

Retrieve Recent Activity

Assemble Prompt

Compact

Execute
```

---

# Freshness Rules

When repository changes:

```text
Update Graph

Update Facts

Update Memory

Update Profile

Invalidate Stale Summaries
```

No full repository rebuild required.

---

# Success Metrics

The subsystem succeeds when:

- Repository understanding remains accurate
- Prompt size remains bounded
- Engineering conventions are preserved
- Sessions remain coherent
- Context quality improves over time
- Agent behavior becomes repository-specific