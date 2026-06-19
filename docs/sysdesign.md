# Corge Tactical System Design

This document provides a detailed, human-readable view of Corge's tactical system design. It highlights the strict modular separation, the internal components of each module, and the structured flow of execution.

## System Architecture & Module Execution

The diagram below separates the system into distinct color-coded modules. Rather than a complex web of unreadable dependencies, the arrows demonstrate a numbered, logical execution flow, illustrating how a specification is built, planned, hydrated with context, approved, and executed.

```mermaid
graph TD
    %% Styling Classes for distinct module coloring
    classDef uiStyle fill:#E1BEE7,stroke:#8E24AA,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef agentStyle fill:#FFF9C4,stroke:#FBC02D,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef contextStyle fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef knowledgeStyle fill:#BBDEFB,stroke:#1976D2,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef executionStyle fill:#FFCDD2,stroke:#D32F2F,stroke-width:2px,color:#000,rx:5,ry:5;
    classDef contractStyle fill:#ECEFF1,stroke:#607D8B,stroke-width:2px,stroke-dasharray: 5 5,color:#000,rx:10,ry:10;

    %% Modules separated by Subgraphs
    subgraph mod_contracts [Shared Contracts Layer]
        direction LR
        SharedModels((Data Models: Specification, Plan, ContextBundle))
    end

    subgraph mod_ui [UI Module]
        direction TB
        UI_TUI[Textual UI & Displays]
        UI_WIZ[Specification Wizard]
    end

    subgraph mod_agent [Agent Module]
        direction TB
        AG_CTRL[Session Controller]
        AG_PLAN[Planning Engine]
        AG_LOOP[Agent Loop]
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

    %% High-level Tactical Flow (numbered for readability)
    UI_WIZ -->|1. Generate Spec| AG_CTRL
    AG_CTRL -->|2. Pass to Plan Engine| AG_PLAN
    AG_PLAN -->|3. Provide Executable Plan| AG_LOOP

    AG_LOOP -->|4. Request Hydration| CTX_ENG
    CTX_ENG -->|5. Collect Parts| CTX_ASM
    CTX_ASM -->|6. Trim to Limits| CTX_BUD

    CTX_BUD -.->|Query Repo Structure| KN_GRAPH
    CTX_BUD -.->|Query Fact History| KN_MEM

    AG_LOOP -->|7. Propose Action| EX_APP
    EX_APP -->|8. Human Verification| UI_TUI
    EX_APP -->|9. Route to Tools| EX_TLS
    EX_TLS -->|10. Yield Result| AG_LOOP
    
    KN_MEM -->|Offload Cold Storage| KN_ART

    %% Centralized Dependency
    mod_ui -.->|Implements| mod_contracts
    mod_agent -.->|Consumes| mod_contracts
    mod_context -.->|Builds| mod_contracts
    mod_knowledge -.->|Informs| mod_contracts
    mod_execution -.->|Enforces| mod_contracts

    %% Apply Colors
    class UI_TUI,UI_WIZ uiStyle;
    class AG_CTRL,AG_PLAN,AG_LOOP agentStyle;
    class CTX_ENG,CTX_ASM,CTX_BUD contextStyle;
    class KN_GRAPH,KN_MEM,KN_ART knowledgeStyle;
    class EX_APP,EX_TLS executionStyle;
    class SharedModels contractStyle;
```

---

```mermaid
sequenceDiagram
    autonumber
    
    actor User
    participant UI as ui.UiPort
    participant PE as agent.PlanningEngine
    participant AL as agent.AgentLoop
    participant PA as prompt_assembler
    participant GW as approval.Gateway
    participant TR as tools.ToolRuntime

    %% Phase 1: Planning
    User->>UI: Interacts with Spec Wizard
    UI-->>PE: Yields `Specification` (title, body, criteria)
    
    PE->>PE: Analyzes requirements
    PE-->>AL: Yields `Plan` (tuple of `PlanStep`)
    
    %% Phase 2: Agent Loop (Execution)
    loop For each `PlanStep`
        AL->>PA: Requests context for current step
        PA-->>AL: Yields `ContextBundle` (Repo, Memory, Profile)
        
        AL->>AL: Evaluates `PlanStep` + `ContextBundle`
        
        %% Proposing Action
        AL->>GW: Submits `ApprovalRequest` (ToolAction, target)
        
        %% Human in the Loop
        GW->>UI: Delegates `request_approval`
        UI->>User: Displays requested action
        User-->>UI: Approves / Rejects
        UI-->>GW: Yields `ApprovalDecision`
        
        %% Resolution
        alt is APPROVED
            GW->>TR: Authorizes tool execution
            TR-->>AL: Yields `ToolResult`
        else is REJECTED
            GW-->>AL: Interrupts execution / requests pivot
        end
        
        AL->>AL: Evaluates `ToolResult` against `AcceptanceCriteria`
    end
    
    %% Phase 3: Completion
    AL->>UI: Triggers `show_completion_review(Plan)`
    UI->>User: Displays results
```
---

## Tactical Module Breakdown

To maintain the modular monolith, cross-communication is heavily restricted. Each module handles a precise slice of the architecture:

### 1. UI Module (Purple)
- **Role**: Pure presentation layer with zero business logic.
- **Components**: Handles the specification wizard, formatting repository analysis for the user, and throwing human-in-the-loop approval requests.

### 2. Agent Module (Yellow)
- **Role**: The core operational state machine.
- **Components**: The `Planning Engine` converts specs into strict plans. The `Agent Loop` consumes steps but relies completely on other modules to fetch context or execute tools. 

### 3. Context Engineering Modules (Green)
- **Role**: Gathering and optimizing data to ensure LLM interactions are precise and under token limits.
- **Components**: The `Prompt Assembler` gathers raw inputs. The `Budget Manager` aggressively clips, deduplicates, and condenses them to fit strict context windows.

### 4. Knowledge & Persistence Modules (Blue)
- **Role**: The source of long-term and short-term facts.
- **Components**: The `Knowledge Graph` maps the structural repository state. The `Memory Pyramid` retains past execution lessons (L0-L3), and the `Artifact Store` securely offloads bulk content.

### 5. Execution & Safety Modules (Red)
- **Role**: The only module that modifies the local environment.
- **Components**: The `Approval Gateway` intercepts tool requests and guarantees nothing runs without consent. The `Tool Runtime` blindly runs `read`, `write`, `edit`, and `bash` commands once authorized.

### 6. Shared Contracts Layer (Grey)
- **Role**: Defines the strict boundary objects and interfaces that traverse modules. 
- **Rule**: Modules communicate by passing models (e.g., `Specification`, `ApprovalRequest`) to interface ports (`typing.Protocol`), completely preventing hidden tight coupling.
