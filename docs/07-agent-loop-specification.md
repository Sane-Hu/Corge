# 07-agent-loop-specification.md

# Agent Loop Specification

## Core Principle

The agent does not generate code directly from user requests.

The agent executes approved plans derived from approved specifications.

---

# Execution Cycle

```text
Observe
    ↓
Refresh Context
    ↓
Assemble Prompt
    ↓
Reason
    ↓
Select Action
    ↓
Request Approval
    ↓
Execute
    ↓
Verify
    ↓
Update Knowledge
    ↓
Repeat
```

---

# Context Sources

The agent may draw from:

```text
Current Specification

Acceptance Criteria

Current Plan

Repository Knowledge Graph

Engineering Facts

Engineering Profile

Scenario Memory

Relevant Files

Recent Actions

Artifact Summaries
```

---

# Prompt Assembly Rules

Always Include:

```text
Current Spec

Acceptance Criteria

Current Plan Step

Engineering Profile
```

---

Include If Relevant:

```text
Scenario Memory

Repository Facts

Related Files

Graph Queries
```

---

Never Include Automatically:

```text
Raw Logs

Large Test Output

Large Build Output

Old Session Events
```

These must be referenced through artifacts.

---

# Planning Phase

Input:

```text
Specification

Acceptance Criteria

Repository Understanding
```

Output:

```json
{
  "steps": []
}
```

Execution remains blocked.

---

# Knowledge Refresh Phase

After every successful action:

```text
Update Graph

Update Facts

Update Memory

Update Profile

Invalidate Stale Summaries
```

---

# Memory Pyramid Usage

## L0

Never injected directly.

Used for audits and reconstruction.

---

## L1

Queried for repository facts.

---

## L2

Primary task memory.

---

## L3

Always consulted during implementation.

---

# Artifact Usage

Large outputs become artifacts.

Example:

```text
artifact://test_run_001
```

Prompt receives:

```text
Summary
Reference
```

Not raw output.

---

# Completion Verification

The agent must verify:

```text
Acceptance Criteria

Tests

Repository Integrity

Plan Completion
```

before requesting final approval.

---

# Failure Handling

When blocked:

```text
Document Blocker

Update Scenario Memory

Request Human Guidance

Resume
```