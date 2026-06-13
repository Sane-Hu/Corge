# 04-module-contracts.md

# Module Contracts

## ui

Responsibilities:

```python
show_spec_wizard()
show_plan()
show_execution()
show_logs()
request_approval()
show_repository_analysis()
show_repository_understanding()
show_engineering_profile()
show_memory()
show_completion_review()
```

No business logic.

---

## agent

Responsibilities:

```python
generate_plan()
execute_step()
evaluate_completion()
update_memory()
```

Cannot directly execute tools.

---

## context

Responsibilities:

```python
load_context()
refresh_context()
retrieve_relevant_context()
```

Coordinates context retrieval.

---

## prompt_assembler

Responsibilities:

```python
collect_context()
assemble_prompt()
```

Constructs execution prompts.

---

## budget_manager

Responsibilities:

```python
estimate_tokens()
rank_context()
clip()
deduplicate()
summarize()
compact()
```

Enforces context budgets.

---

## knowledge_graph

Responsibilities:

```python
build_graph()
update_graph()
query_graph()
```

Maintains repository understanding.

---

## memory

Responsibilities:

```python
store_event()
store_fact()
store_scenario()
update_profile()
```

Maintains Memory Pyramid.

---

## artifacts

Responsibilities:

```python
store_artifact()
retrieve_artifact()
summarize_artifact()
```

Handles context offloading.

---

## approval

Responsibilities:

```python
approve()
reject()
```

Single approval authority.

---

## tools

Responsibilities:

```python
read()
write()
edit()
bash()
```

Stateless execution primitives.

---

## providers

Responsibilities:

```python
chat()
```

Only external model integration point.

---

## logging

Responsibilities:

```python
record_prompt()
record_tool_call()
record_approval()
record_completion()
```

Provides auditability.

---

## Suggested Source Layout

```text
src/
├── ui/
├── agent/
├── context/
├── prompt_assembler/
├── budget_manager/
├── knowledge_graph/
├── memory/
├── artifacts/
├── approval/
├── tools/
├── providers/
└── logging/
```