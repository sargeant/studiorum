---
title: Simple Mermaid Test
description: Testing direct Mermaid HTML approach
---

# Simple Mermaid Test

This page tests Mermaid using direct HTML approach to bypass pymdownx.superfences issues.

## Test 1: Direct HTML Mermaid

<div class="mermaid">
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
</div>

## Test 2: Architecture Diagram

<div class="mermaid">
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
</div>

## Test 3: Sequence Diagram

<div class="mermaid">
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
</div>

<script>
// Debug info for this page
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        const diagrams = document.querySelectorAll('.mermaid');
        console.log('=== SIMPLE TEST PAGE DEBUG ===');
        console.log('Found', diagrams.length, 'mermaid diagrams');
        diagrams.forEach((el, i) => {
            console.log(`Diagram ${i} content (first 100 chars):`, el.textContent?.slice(0, 100));
            console.log(`Diagram ${i} has SVG:`, el.querySelector('svg') !== null);
        });
    }, 2000);
});
</script>
