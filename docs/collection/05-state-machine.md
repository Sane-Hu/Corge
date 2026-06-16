# 05-state-machine.md

# State Machine

## Primary Lifecycle

```text
START
  ↓
REPOSITORY_SELECTION
  ↓
REPOSITORY_ANALYSIS
  ↓
SPEC_ENTRY
  ↓
SPEC_VALIDATION
  ↓
SPEC_APPROVAL
  ↓
PLAN_GENERATION
  ↓
PLAN_REVIEW
  ↓
PLAN_APPROVAL
  ↓
EXECUTION
  ↓
VERIFICATION
  ↓
COMPLETION_REVIEW
  ↓
DONE
```

---

## Execution Loop

```text
EXECUTION
    ↓
CONTEXT_REFRESH
    ↓
PROMPT_ASSEMBLY
    ↓
ACTION_SELECTION
    ↓
APPROVAL_REQUIRED?
    ↓
EXECUTE
    ↓
VERIFY_PROGRESS
    ↓
UPDATE_KNOWLEDGE
    ↓
NEXT_STEP
```

---

## Approval Path

```text
ACTION_PROPOSED
       ↓
APPROVAL_MODAL
       ↓
 ┌───────────────┐
 │               │
 ▼               ▼
APPROVED      REJECTED
 │               │
 ▼               ▼
EXECUTE      REPLAN
```

---

## Blocked Path

```text
EXECUTION
    ↓
BLOCKER_DETECTED
    ↓
DOCUMENT_BLOCKER
    ↓
USER_DECISION
    ↓
CONTINUE
```

---

## Repository Change Path

Triggered when:

- Agent edits files
- Human edits files
- New files appear
- Files are removed

```text
FILE_CHANGED
     ↓
GRAPH_UPDATE
     ↓
FACT_EXTRACTION
     ↓
PROFILE_UPDATE
     ↓
MEMORY_UPDATE
     ↓
CONTEXT_INVALIDATION
     ↓
CONTEXT_REFRESH
     ↓
CONTINUE
```

---

## Empty Repository Bootstrap Path

```text
EMPTY_REPOSITORY
        ↓
SPECIFICATION
        ↓
PLAN_GENERATION
        ↓
PROJECT_SCAFFOLDING
        ↓
GRAPH_CREATION
        ↓
NORMAL_EXECUTION
```

---

## Session Recovery Path

```text
SESSION_START
      ↓
LOAD_MEMORY
      ↓
LOAD_SCENARIOS
      ↓
LOAD_GRAPH
      ↓
LOAD_ARTIFACTS
      ↓
RESTORE_CONTEXT
      ↓
CONTINUE_WORK
```

---

## Completion Criteria

Transition to DONE requires:

```text
✓ Acceptance Criteria Satisfied

✓ Tests Exist

✓ Tests Pass

✓ No Active Blockers

✓ User Approval
```
