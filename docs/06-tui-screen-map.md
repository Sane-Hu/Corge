# 06-tui-screen-map.md

# TUI Screen Map

## Design Principles

The UI should make software delivery understandable.

The engineer should always know:

- Current objective
- Current plan step
- Current repository understanding
- Current approvals
- Current blockers

The UI should reinforce the Human-Agent Contract.

---

# Startup Screen

```text
┌──────────────────────────────┐
│ Select Repository            │
│                              │
│ /projects/my-app             │
│ /projects/new-project        │
│                              │
│ [Enter] Continue             │
└──────────────────────────────┘
```

---

# Repository Analysis Screen

```text
┌──────────────────────────────┐
│ Repository Analysis          │
│                              │
│ Scanning Tree                │
│ Summarizing Files            │
│ Building Graph               │
│ Extracting Facts             │
│ Building Profile             │
│                              │
│ Progress: 83%               │
└──────────────────────────────┘
```

---

# Specification Wizard

## Step 1

```text
Feature Goal
```

---

## Step 2

```text
User Story
```

---

## Step 3

```text
Functional Requirements
```

---

## Step 4

```text
Constraints
```

---

## Step 5

```text
Acceptance Criteria
```

---

## Step 6

```text
Testing Expectations
```

---

## Step 7

```text
Review Specification
```

---

# Repository Understanding Screen

```text
┌──────────────────────────────┐
│ Repository Understanding     │
│                              │
│ Framework: Laravel 12        │
│ Tests: Pest                  │
│ Architecture: Service Layer  │
│ DTO Usage: High              │
│                              │
│ Graph Nodes: 1234            │
│ Graph Edges: 5689            │
└──────────────────────────────┘
```

---

# Engineering Profile Screen

```text
┌──────────────────────────────┐
│ Engineering Profile          │
│                              │
│ ✓ Service Classes            │
│ ✓ DTOs                       │
│ ✓ Constructor Injection      │
│ ✓ Pest                       │
│ ✓ readonly Classes           │
│                              │
│ [Edit Profile]               │
└──────────────────────────────┘
```

---

# Plan Review Screen

```text
┌──────────────────────────────┐
│ Generated Plan               │
│                              │
│ 1. Create Service            │
│ 2. Create DTO                │
│ 3. Update Controller         │
│ 4. Add Tests                 │
│                              │
│ [Approve] [Reject]           │
└──────────────────────────────┘
```

---

# Execution Screen

```text
┌──────────────────────────────┐
│ Current Step                 │
│                              │
│ Step 2 / 4                   │
│ Create DTO                   │
│                              │
│ Current File                 │
│ app/DTO/LoginDTO.php         │
│                              │
│ Current Action               │
│ Proposing write              │
└──────────────────────────────┘
```

---

# Memory Screen

```text
┌──────────────────────────────┐
│ Scenario Memory              │
│                              │
│ Progress                     │
│ Decisions                    │
│ Discoveries                  │
│ Blockers                     │
│ Next Actions                 │
└──────────────────────────────┘
```

---

# Approval Modal

```text
┌──────────────────────────────┐
│ Approval Required            │
│                              │
│ Action: Write File           │
│                              │
│ Target: LoginDTO.php         │
│                              │
│ Reason: Step 2 of plan       │
│                              │
│ [Approve] [Reject]           │
└──────────────────────────────┘
```

---

# Completion Screen

```text
┌──────────────────────────────┐
│ Completion Review            │
│                              │
│ Acceptance Criteria          │
│ ✓                            │
│ ✓                            │
│ ✓                            │
│                              │
│ Tests                        │
│ ✓ Passed                     │
│                              │
│ [Approve Completion]         │
└──────────────────────────────┘
```