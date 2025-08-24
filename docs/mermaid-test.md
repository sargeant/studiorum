---
title: Mermaid Diagram Tests
description: Testing various Mermaid syntax patterns for v11 compatibility
---

# Mermaid Diagram Tests

This page tests various Mermaid diagram types and syntax patterns to ensure v11 compatibility.

## Test 1: Simple Flowchart

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
```

## Test 2: Architecture Diagram (Original Problem)

```mermaid
graph TB
    subgraph DS ["Data Sources"]
        5E[5etools Data]
        LOCAL[Local Content]
        API[External APIs]
    end

    subgraph CP ["Core Processing"]
        MERGER[ContentMerger]
        OMNI[Omnidexer]
        RESOLVER[ContentResolver]
    end

    5E --> MERGER
    LOCAL --> MERGER
    API --> MERGER
    MERGER --> OMNI
    OMNI --> RESOLVER
```

## Test 3: Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant CLI
    participant ServiceContainer
    participant ContentResolver
    participant Omnidexer

    Client->>CLI: Request conversion
    CLI->>ServiceContainer: Get services
    ServiceContainer->>ContentResolver: Create resolver
    ContentResolver->>Omnidexer: Load content
    Omnidexer-->>ContentResolver: Content data
    ContentResolver-->>CLI: Processed content
    CLI-->>Client: Result
```

## Test 4: Class Diagram

```mermaid
classDiagram
    class ServiceContainer {
        +get_service(protocol) T
        +register_service(protocol, factory)
        -services: dict
        -descriptors: dict
    }

    class Omnidexer {
        +is_loaded() bool
        +get_content(id, type) T
        +search(query) SearchResult
        -content_cache: dict
    }

    ServiceContainer --> Omnidexer : creates
```

## Test 5: State Diagram

```mermaid
stateDiagram-v2
    [*] --> Unloaded
    Unloaded --> Loading : load_data()
    Loading --> Loaded : success
    Loading --> Error : failure
    Loaded --> Processing : process_content()
    Processing --> Complete : success
    Processing --> Error : failure
    Error --> Unloaded : reset()
    Complete --> [*]
```

## Test 6: Gantt Chart

```mermaid
gantt
    title Studiorum Development Timeline
    dateFormat  YYYY-MM-DD
    section Core System
    Service Container    :done, container, 2024-01-01, 2024-02-01
    Omnidexer           :done, omnidexer, 2024-02-01, 2024-03-01
    Content Resolution  :active, resolver, 2024-03-01, 2024-04-01
    section Rendering
    LaTeX Engine        :latex, after resolver, 30d
    MCP Integration     :mcp, after latex, 30d
```

## Test 7: Pie Chart

```mermaid
pie title Content Types Distribution
    "Adventures" : 35
    "Creatures" : 30
    "Spells" : 20
    "Items" : 15
```

## Test 8: User Journey

```mermaid
journey
    title User Content Conversion Journey
    section Setup
      Install studiorum: 5: User
      Configure sources: 4: User
    section Convert
      Select content: 5: User
      Run conversion: 3: User, CLI
      Review output: 4: User
    section Customize
      Adjust settings: 3: User
      Re-run conversion: 5: User, CLI
      Share result: 5: User
```

## Test 9: Git Graph

```mermaid
gitgraph
    commit id: "Initial"
    branch develop
    checkout develop
    commit id: "Service Container"
    commit id: "Omnidexer"
    branch feature/mcp
    checkout feature/mcp
    commit id: "MCP Server"
    commit id: "MCP Tools"
    checkout develop
    merge feature/mcp
    commit id: "Integration Tests"
    checkout main
    merge develop
    commit id: "Release v1.0"
```

## Test 10: Complex Flowchart with Styling

```mermaid
graph TB
    Start([Start Process]) --> Input{Input Valid?}
    Input -->|Yes| Process[Process Data]
    Input -->|No| Error[Show Error]
    Process --> Cache{Cache Hit?}
    Cache -->|Yes| FastPath[Use Cached Result]
    Cache -->|No| SlowPath[Compute Result]
    FastPath --> Output[Return Result]
    SlowPath --> Store[Store in Cache]
    Store --> Output
    Error --> End([End])
    Output --> End

    classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px

    class Start,End startEnd
    class Process,FastPath,SlowPath,Store,Output process
    class Input,Cache decision
    class Error error
```

## JavaScript Console Check

Open browser dev tools and check console for any Mermaid errors or warnings.

<script>
// Add debugging info
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        console.log('Mermaid version:', typeof mermaid !== 'undefined' ? mermaid.version || 'Version info not available' : 'Not loaded');
        console.log('Mermaid diagrams found:', document.querySelectorAll('.mermaid').length);
        console.log('Mermaid rendered diagrams:', document.querySelectorAll('.mermaid svg').length);
    }, 2000);
});
</script>
