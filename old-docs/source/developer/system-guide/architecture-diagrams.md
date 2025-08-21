# Architecture Diagrams

Visual representations of the 5e2pdf system architecture and data flow.

## System Overview

```mermaid
graph TB
    subgraph "Data Sources"
        JSON[5etools JSON Files]
        META[Metadata Files]
        CONTENT[Content Files]
    end

    subgraph "Core System"
        OM[Omnidexer]
        CM[ContentMerger]
        SC[ServiceContainer]
        CFG[UnifiedConfig]
    end

    subgraph "Processing"
        TR[TagResolver]
        EP[EntryProcessor]
        CT[ContentTracker]
    end

    subgraph "Rendering"
        LR[LaTeX Renderer]
        TR2[Template Engine]
        PDF[PDF Compiler]
    end

    JSON --> OM
    META --> CM
    CONTENT --> CM
    CM --> OM
    OM --> SC
    CFG --> SC
    SC --> EP
    EP --> TR
    EP --> CT
    EP --> LR
    LR --> TR2
    TR2 --> PDF
    CT --> LR

    style JSON fill:#e1f5fe
    style META fill:#e1f5fe
    style CONTENT fill:#e1f5fe
    style PDF fill:#c8e6c9
```

## Data Flow Pipeline

```mermaid
flowchart LR
    subgraph Input
        J[JSON Files]
        C[Config]
    end

    subgraph Loading
        L1[Source Manager]
        L2[Content Loader]
        L3[Metadata Loader]
    end

    subgraph Merging
        M1[ContentMerger]
        M2[Cache Layer]
    end

    subgraph Models
        P1[Pydantic Models]
        P2[Validation]
    end

    subgraph Rendering
        R1[Template Selection]
        R2[Tag Processing]
        R3[LaTeX Generation]
    end

    subgraph Output
        O1[LaTeX File]
        O2[PDF File]
    end

    J --> L1
    C --> L1
    L1 --> L2
    L1 --> L3
    L2 --> M1
    L3 --> M1
    M1 --> M2
    M2 --> P1
    P1 --> P2
    P2 --> R1
    R1 --> R2
    R2 --> R3
    R3 --> O1
    O1 --> O2
```

## Service Container Architecture

```mermaid
classDiagram
    class ServiceContainer {
        <<interface>>
        +get_omnidexer()
        +get_config()
        +get_tag_resolver()
        +get_content_merger()
        +get_source_manager()
        +get_latex_compiler()
        +get_jinja_environment()
        +get_content_tracker()
    }

    class DefaultServiceContainer {
        -_omnidexer
        -_config
        -_tag_resolver
        -_content_merger
        -_source_manager
        -_latex_compiler
        -_jinja_environment
        -_content_tracker
        +register_service()
        +reset_all()
    }

    class Omnidexer {
        +load_all_data()
        +find()
        +find_one()
        +get_all_by_type()
    }

    class TagResolver {
        +resolve()
        +parse()
        +register_handler()
    }

    class ContentMerger {
        +merge()
        +cache_get()
        +cache_set()
    }

    ServiceContainer <|-- DefaultServiceContainer
    DefaultServiceContainer --> Omnidexer
    DefaultServiceContainer --> TagResolver
    DefaultServiceContainer --> ContentMerger
```

## Entry Processing System

```mermaid
flowchart TD
    E[Entry Data] --> T{Type?}

    T -->|String| S[Text with Tags]
    T -->|Dict| D[Structured Entry]
    T -->|List| L[Entry List]

    S --> TP[Tag Parser]
    TP --> AST[Parse to AST]
    AST --> TH[Tag Handlers]
    TH --> CT[Content Tracker]
    TH --> LO[LaTeX Output]

    D --> REP[RecursiveEntryProcessor]
    REP --> |entries| S
    REP --> |table| TAB[Table Renderer]
    REP --> |list| LST[List Renderer]
    REP --> |inset| INS[Inset Renderer]

    L --> ITER[Iterate Items]
    ITER --> REP

    CT --> APP[Appendix Generation]

    style E fill:#ffe0b2
    style LO fill:#c8e6c9
    style APP fill:#c8e6c9
```

## Tag Resolution Process

```mermaid
sequenceDiagram
    participant Entry
    participant Parser
    participant AST
    participant Handler
    participant Tracker
    participant Output

    Entry->>Parser: Text with {@tag}
    Parser->>AST: Parse to nodes

    loop For each tag node
        AST->>Handler: Resolve tag
        Handler->>Handler: Lookup content
        Handler->>Tracker: Track reference
        Handler->>Output: Generate LaTeX
    end

    AST->>Output: Combine results
    Tracker->>Output: Generate appendix
```

## Content Loading Hierarchy

```mermaid
graph TD
    subgraph Sources
        S1[PHB - Player's Handbook]
        S2[MM - Monster Manual]
        S3[DMG - Dungeon Master's Guide]
        S4[XGE - Xanathar's]
        S5[TCE - Tasha's]
        SN[... More Sources]
    end

    subgraph Content Types
        C1[Spells]
        C2[Creatures]
        C3[Items]
        C4[Classes]
        C5[Races]
        C6[Adventures]
        C7[Books]
    end

    subgraph Omnidexer
        I1[Index by Name]
        I2[Index by Source]
        I3[Index by Type]
        I4[Deep Index]
    end

    S1 --> C1
    S1 --> C3
    S1 --> C4
    S1 --> C5

    S2 --> C2

    S3 --> C3

    C1 --> I1
    C1 --> I2
    C1 --> I3

    C2 --> I1
    C2 --> I2
    C2 --> I3

    I1 --> I4
    I2 --> I4
    I3 --> I4
```

## LaTeX Rendering Pipeline

```mermaid
flowchart TB
    subgraph Input
        C[Content Object]
        CTX[RenderingContext]
    end

    subgraph Template Selection
        TM{Content Type?}
        T1[spell.tex.j2]
        T2[creature.tex.j2]
        T3[item.tex.j2]
        T4[adventure.tex.j2]
    end

    subgraph Processing
        J[Jinja2 Engine]
        F[Filters]
        M[Macros]
    end

    subgraph Compilation
        L[LaTeX Source]
        X[XeLaTeX/PDFLaTeX]
        P[PDF Output]
    end

    C --> TM
    CTX --> TM

    TM -->|spell| T1
    TM -->|creature| T2
    TM -->|item| T3
    TM -->|adventure| T4

    T1 --> J
    T2 --> J
    T3 --> J
    T4 --> J

    J --> F
    F --> M
    M --> L
    L --> X
    X --> P

    style C fill:#ffe0b2
    style P fill:#c8e6c9
```

## Configuration Hierarchy

```mermaid
graph TD
    subgraph Sources
        ENV[Environment Variables]
        CLI[CLI Arguments]
        FILE[Config File]
        DEF[Defaults]
    end

    subgraph UnifiedConfig
        UC[Config Resolution]
        PR[Profile Selection]
        VAL[Validation]
    end

    subgraph Categories
        R[Rendering Config]
        L[LaTeX Config]
        S[Source Config]
        O[Output Config]
    end

    ENV -->|Override| UC
    CLI -->|Override| UC
    FILE -->|Override| UC
    DEF -->|Base| UC

    UC --> PR
    PR --> VAL

    VAL --> R
    VAL --> L
    VAL --> S
    VAL --> O

    style ENV fill:#ffecb3
    style CLI fill:#ffecb3
    style FILE fill:#ffecb3
    style DEF fill:#e0e0e0
```

## Error Handling Flow

```mermaid
flowchart TD
    OP[Operation] --> R{Result?}

    R -->|Success| S[Success[T]]
    R -->|Failure| F[Failure]

    S --> V[Value]
    S --> M[Metadata]

    F --> E[Error]
    F --> C[Context]
    F --> ST[Stack Trace]

    F --> H{Handler?}
    H -->|Recovery| REC[Recovery Strategy]
    H -->|Fallback| FB[Fallback Value]
    H -->|Propagate| P[Bubble Up]

    REC --> OP
    FB --> V
    P --> LOG[Error Log]

    style S fill:#c8e6c9
    style F fill:#ffcdd2
    style V fill:#c8e6c9
```

## Testing Architecture

```mermaid
graph LR
    subgraph Test Categories
        U[Unit Tests]
        I[Integration Tests]
        L[LaTeX Tests]
        P[Performance Tests]
    end

    subgraph Test Utilities
        RT[reset_test_environment]
        F[Fixtures]
        M[Mocks]
        D[Test Data]
    end

    subgraph Parallel Execution
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
        WN[Worker N]
    end

    U --> F
    U --> M
    I --> RT
    I --> D
    L --> D

    RT --> W1
    RT --> W2
    RT --> W3
    RT --> WN

    W1 --> |Isolated| R1[Results]
    W2 --> |Isolated| R2[Results]
    W3 --> |Isolated| R3[Results]
    WN --> |Isolated| RN[Results]
```

## Deployment Architecture

```mermaid
graph TB
    subgraph Development
        DEV[Local Dev]
        TEST[Testing]
    end

    subgraph CI/CD
        GH[GitHub Actions]
        LINT[Linting]
        UNIT[Unit Tests]
        BUILD[Build]
    end

    subgraph Distribution
        PYPI[PyPI Package]
        GIT[GitHub Release]
        DOC[Documentation]
    end

    subgraph User Environment
        PIP[pip install]
        UV[uv install]
        TEX[LaTeX Installation]
    end

    DEV --> TEST
    TEST --> GH
    GH --> LINT
    GH --> UNIT
    GH --> BUILD

    BUILD --> PYPI
    BUILD --> GIT
    BUILD --> DOC

    PYPI --> PIP
    PYPI --> UV
    PIP --> TEX
    UV --> TEX

    style DEV fill:#e3f2fd
    style PYPI fill:#c8e6c9
    style GIT fill:#c8e6c9
    style DOC fill:#c8e6c9
```

## Memory and Performance

```mermaid
graph TD
    subgraph Caching Layers
        L1[LRU Cache - Hot Data]
        L2[TTL Cache - Merged Content]
        L3[Disk Cache - Compiled LaTeX]
    end

    subgraph Memory Management
        LL[Lazy Loading]
        GC[Garbage Collection]
        PS[Pool Size Limits]
    end

    subgraph Performance Optimizations
        PAR[Parallel Processing]
        BATCH[Batch Operations]
        INDEX[Pre-built Indexes]
    end

    L1 --> |Fast| LL
    L2 --> |Medium| LL
    L3 --> |Slow| LL

    LL --> GC
    GC --> PS

    PS --> PAR
    PAR --> BATCH
    BATCH --> INDEX

    style L1 fill:#ffecb3
    style L2 fill:#ffe0b2
    style L3 fill:#ffccbc
```

## See Also

- {doc}`architecture-overview` - Detailed text description
- {doc}`design-patterns` - Implementation patterns
- {doc}`/user-guide/quickstart-tutorial` - Getting started guide
