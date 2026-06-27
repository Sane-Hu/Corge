# Corge Tactical System Design

This document provides a detailed, human-readable view of Corge's tactical system design. It highlights the strict modular separation, the internal components of each module, and the structured flow of execution.

## System Architecture & Module Execution

The diagram below separates the system into distinct color-coded modules. The arrows demonstrate a numbered, logical execution flow, illustrating how a specification is built, planned, hydrated with context, approved, and executed.

```mermaid
flowchart TD
    classDef uiStyle fill:#E1BEE7,stroke:#8E24AA,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef agentStyle fill:#FFF9C4,stroke:#FBC02D,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef contextStyle fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef knowledgeStyle fill:#BBDEFB,stroke:#1976D2,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef executionStyle fill:#FFCDD2,stroke:#D32F2F,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef loggingStyle fill:#FFE0B2,stroke:#F57C00,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef contractStyle fill:#ECEFF1,stroke:#607D8B,stroke-width:2px,stroke-dasharray: 5 5,color:#000,rx:10,ry:10;
    classDef providerStyle fill:#E0F7FA,stroke:#0097A7,stroke-width:2px,color:#000,rx:5,ry:5;

    subgraph mod_contracts [Shared Contracts Layer]
        direction LR
        SharedModels((Data Models: Specification, Plan, ContextBundle))
    end

    subgraph mod_ui [UI Module]
        direction TB
        UI_TUI[Textual UI & Displays]
        UI_WIZ[Spec Wizard & Canvas]
    end

    subgraph mod_agent [Agent Module]
        direction TB
        AG_CTRL[Session Controller]
        AG_SPEC[Specification Agent]
        AG_PLAN[Planning Agent]
        AG_CODE[Coding Agent]
        AG_LEARN[Schema Tailor & Heuristics]
    end

    subgraph mod_context [Context Engineering Modules]
        direction TB
        CTX_ENG[Context Service]
        CTX_ASM[Prompt Assembler]
        CTX_BUD[Budget Manager]
    end

    subgraph mod_knowledge [Knowledge & Persistence Modules]
        direction TB
        KN_GRAPH[Knowledge Graph]
        KN_MEM[Memory Pyramid]
        KN_ART[Artifacts Store]
    end

    subgraph mod_execution [Execution & Safety Modules]
        direction TB
        EX_APP[Approval Gateway]
        EX_TLS[Tool Runtime]
    end

    subgraph mod_logging [Logging Module]
        direction TB
        LOG_AUD[Audit Logger]
        LOG_ARG[Argumentation Log]
    end

    subgraph mod_providers [Providers Module]
        direction TB
        PRV_ADAPT[Model API Adapter]
    end

    UI_WIZ -->|1. Spec Interactions| AG_SPEC
    AG_SPEC -->|2. Generate Spec| AG_CTRL
    AG_CTRL -.->|Batch Update| AG_LEARN
    AG_CTRL -->|3. Pass to Planning| AG_PLAN
    AG_PLAN -->|4. Provide Executable Plan| AG_CODE

    AG_CODE -->|5. Request Hydration| CTX_ENG
    CTX_ENG -->|6. Collect Parts| CTX_ASM
    CTX_ASM -->|7. Trim to Limits| CTX_BUD

    CTX_BUD -.->|Query Repo Structure| KN_GRAPH
    CTX_BUD -.->|Query Fact History| KN_MEM
    
    CTX_BUD -->|8. Return Context| AG_CODE
    AG_CODE -->|9. Inference| PRV_ADAPT
    PRV_ADAPT -->|10. Action Decision| AG_CODE

    AG_CODE -->|11. Propose Action| EX_APP
    EX_APP -->|12. Human Verification| UI_TUI
    EX_APP -->|13. Route to Tools| EX_TLS
    EX_TLS -->|14. Yield Result| AG_CODE
    
    AG_CODE -->|15. Update Facts| KN_GRAPH
    AG_CODE -->|15. Update Facts| KN_MEM

    KN_MEM -->|Offload Cold Storage| KN_ART

    class UI_TUI,UI_WIZ uiStyle;
    class AG_CTRL,AG_SPEC,AG_PLAN,AG_CODE,AG_LEARN agentStyle;
    class CTX_ENG,CTX_ASM,CTX_BUD contextStyle;
    class KN_GRAPH,KN_MEM,KN_ART knowledgeStyle;
    class EX_APP,EX_TLS executionStyle;
    class LOG_AUD,LOG_ARG loggingStyle;
    class SharedModels contractStyle;
    class PRV_ADAPT providerStyle;
```

---

```mermaid
sequenceDiagram
    autonumber
    
    actor User
    participant UI as ui.UiPort
    participant SA as agent.SpecificationAgent
    participant PE as agent.PlanningAgent
    participant CA as agent.CodingAgent
    participant CTX as context.ContextService
    participant PRV as providers.Provider
    participant GW as approval.Gateway
    participant TR as tools.ToolRuntime
    participant KN as knowledge.Persistence
    participant LG as logging.ArgumentationLog

    User->>UI: Interacts with Spec Wizard & Canvas
    UI->>LG: Logs Socratic Q&A and Canvas Snapshots
    UI-->>SA: Submits interactive input
    SA->>PRV: Applies Schema Tailor & requests Spec
    PRV-->>SA: Yields drafted content
    SA->>SA: Applies Heuristics
    SA-->>PE: Yields `Specification` (title, body, criteria)
    
    PE->>PRV: Analyzes requirements for Technical Architecture
    PRV-->>PE: Yields Technical Plan
    PE->>PRV: Translates Architecture into Procedural Steps
    PRV-->>PE: Yields Procedural Steps
    PE-->>CA: Yields `Plan` (tuple of `PlanStep` / `ProceduralStep`)
    
    loop For each `PlanStep`
        CA->>CTX: Requests context for current step
        CTX->>KN: Queries structure and facts
        KN-->>CTX: Yields graph & memory data
        CTX->>CTX: Applies Markov Context Chaining (N-1 injection, layer isolation)
        CTX-->>CA: Yields `ContextBundle` (Repo, Memory, Profile, MarkovState)
        
        CA->>PRV: Evaluates `PlanStep` + `ContextBundle`
        PRV-->>CA: Yields Tool Action decision
        
        CA->>GW: Submits `ApprovalRequest` (ToolAction, target)
        
        GW->>UI: Delegates `request_approval`
        UI->>User: Displays requested action
        User-->>UI: Approves / Rejects
        UI-->>GW: Yields `ApprovalDecision`
        
        alt is APPROVED
            GW->>TR: Authorizes tool execution
            TR-->>CA: Yields `ToolResult`
        else is REJECTED
            GW-->>CA: Interrupts execution / requests pivot
        end
        
        CA->>CA: Evaluates `ToolResult` against `AcceptanceCriteria`
        CA->>KN: Extracts facts, updates graph & scenario memory
    end
    
    CA->>UI: Triggers `show_completion_review(Plan)`
    UI->>User: Displays results
```
---

## Tactical Module Breakdown

To maintain the modular monolith, cross-communication is heavily restricted. Each module handles a precise slice of the architecture.

### 1. UI Module (Purple)
- **Role**: Pure presentation layer with zero business logic.
- **Components**: Handles the directory selector (supporting visual context, safe folder creation, escape-based cancellation, hidden files toggles, and direct LLM API configuration via the ProviderConfigScreen), the specification wizard, the interactive Freestyle Canvas with sticky notes (supporting confirmation-protected clearing), formatting repository analysis for the user, the step by step plan outputs side by side with structured specs output, throwing human-in-the-loop approval requests (featuring live code diff toggles and read-only details to prevent misleading edits), custom confirmation screens (ConfirmScreen) for opt-ins and destructive prompts, ensuring default initial focus on screen mount for keyboard-only usability, structured audit log parsing and formatting, displaying completion review, and providing explicit "Back" buttons on screens to allow navigating back to the previous screen or lifecycle state (supporting backspace/escape keyboard bindings).

### 2. Agent Modules (Yellow)
- **Role**: The operational state machine and learning engine.
- **Components**: Divided into three master phase-specific agents: 
  - `Specification Agent`: handles SpecState reiterations, supporting opt-in Socratic spec questions (capped at a configurable threshold to prevent cognitive overload, with support for iterative rounds), dynamic LLM refinement of spec content based on user answers, formatting of remaining gaps into inline markdown templates, and merging user manual edits back into structured specification fields.
  - `Planning Agent`: handles PlanState reiterations (generating Technical Plans and Procedural Steps, parsing and preserving custom bracketed step identifiers in user-edited step descriptions).
  - `Coding Agent`: handles the tool execution loop. 
  - `Schema Tailor`: for framework-aware prompts 
  - `Heuristic Updater`: for Bayesian self-improvement of the spec wizard in a subsequent, post-execution phase. 
  - `Session Controller`: manages transitions between these three master phases, implementing robust backward navigation on cancel/rejection (including back-navigation buttons on all major screens), wrapping bootstrap connection errors with actionable advice, and step-retry loops on tool failures. 

### 3. Context Engineering Modules (Green)
- **Role**: Gathering and optimizing context data to ensure LLM interactions are precise and under token limits.
- **Components**: 
  - `Context Service`: retrieves relevant context for each agent when needed, from the: repo knowledge base, user profiles, user inputs and memory pyramid, enforcing context-layer isolation and applying context-chaining policies. 
  - `Prompt Assembler`: gathers context inputs for the current step, selects the appropriate `schema` for the current phase, and uses `schema tailoring` to generate framework-aware prompts. The assembler's templates are structured to place static components (schemas, specification, facts) at the beginning of the prompt to maximize LLM prompt/prefix caching.
  - `Budget Manager`: aggressively clips, deduplicates, and condenses context inputs to fit strict context windows when needed.

### 4. Knowledge & Persistence Modules (Blue)
- **Role**: The source of long-term and short-term facts of the codebase and project.
- **Components**: 
  - `Knowledge Graph`: maps the structural repository state.
  - `Memory Pyramid`: retains past execution lessons (L0-L3), and 
  - `Artifact Store`: securely offloads bulk content.

### 5. Execution & Safety Modules (Red)
- **Role**: The only module that modifies the local environment.
- **Components**: 
  - `Approval Gateway`: intercepts tool requests and guarantees nothing runs without consent, presenting live diffs of proposed code edits for verification prior to execution.
  - `Tool Runtime`: validates command execution safety (blocking privilege escalation and escaping deletions) and runs `read`, `write`, `edit`, and `bash` once authorized.

### 6. Shared Contracts Layer (Grey)
- **Role**: Defines the strict boundary objects and interfaces that traverse modules. 
- **Rule**: Modules communicate by passing models (e.g., `Specification`, `ApprovalRequest`) to interface ports (`typing.Protocol`), completely preventing hidden tight coupling and achieving high modularity and maintainability.

### 7. Providers Module
- **Role**: Model API adapter and integration point.
- **Components**: The `Provider` class implements an OpenAI-compatible adapter supporting OpenAI (with automatic prompt caching), DeepSeek (with prefix caching), and Ollama (with keep-alive support). It automatically handles reasoning/thinking models by stripping `<think>...</think>` tags from content and populating standardized usage fields.

### 8. Logging Module
- **Role**: Accountability, audit trailing, and historical learning data.
- **Components**: 
  - `AuditLogger` defines the interface for recording state transitions, tool invocations, and approvals. 
  - `ArgumentationLog` records Socratic Q&A and canvas snapshots to `argumentation_log.json`, to be consumed by the batch-phase heuristic updater.

