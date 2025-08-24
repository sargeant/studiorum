---
title: Studiorum Documentation
description: 5e content processing toolkit - LaTeX/PDF generation and MCP integration
---

<div class="hero-banner gradient-background">
  <h1 class="hero-title">Studiorum</h1>
  <p class="hero-subtitle">Content Processing Toolkit for D&D 5e</p>
  <p class="hero-description">Transform 5etools JSON into professional PDFs and integrate with AI tools through MCP</p>
</div>

## Getting Started

<div class="feature-cards">
  <div class="feature-card">
    <h3>User Guide</h3>
    <p>Create beautiful PDFs from D&D adventures, spells, and creatures using professional LaTeX typesetting.</p>
    <a href="user-guide/" class="btn-primary">Get Started</a>
  </div>

  <div class="feature-card">
    <h3>Developer Guide</h3>
    <p>Build applications with studiorum's models and services for comprehensive D&D content processing.</p>
    <a href="developer-guide/" class="btn-secondary">API Documentation</a>
  </div>

  <div class="feature-card">
    <h3>MCP Integration</h3>
    <p>Connect AI agents to D&D content through Model Context Protocol tools for intelligent content processing.</p>
    <a href="user-guide/mcp-setup/" class="btn-accent">Setup MCP</a>
  </div>

  <div class="feature-card">
    <h3>Open Source</h3>
    <p>MIT licensed with modern Python architecture. Contributions welcome.</p>
    <a href="developer-guide/contributing/" class="btn-outline">Contributing</a>
  </div>
</div>

## Examples

<div class="examples-showcase">
  <div class="example-card">
    <h4>📚 Create Adventure PDF</h4>
    <div class="example-code">
      <pre><code>studiorum convert adventure MGA --output my-great-adventure.pdf</code></pre>
    </div>
  </div>

  <div class="example-card">
    <h4>🐍 Use Python Models</h4>
    <div class="example-code">
      <pre><code class="language-python">from studiorum.models import Spell

fireball = Spell.from_5etools("fireball")
print(f"Damage: {fireball.damage}")</code></pre>
    </div>
  </div>

  <div class="example-card">
    <h4>🔗 MCP Integration</h4>
    <div class="example-code">
      <pre><code class="language-json">{
  "name": "lookup_spell",
  "arguments": {"name": "fireball"}
}</code></pre>
    </div>
  </div>
</div>

## Architecture Overview

Studiorum provides a modern Python toolkit for processing 5e content from 5etools JSON format into professional LaTeX/PDF documents, with full MCP integration for AI applications.

<div class="mermaid">
graph TB
    A[5etools JSON] --> B[ContentMerger]
    B --> C[Omnidexer]
    C --> D[Pydantic Models]
    D --> E[ModernContextualAPI]
    E --> F{Output}
    F --> G[MCP Tools]
    F --> H[CLI Commands]
</div>

### Key Features

- **Professional PDF Generation**: LaTeX-based typesetting for beautiful documents
- **Modern Python Architecture**: Type-safe models with Pydantic validation
- **AI Integration Ready**: MCP server for Claude Code, ChatGPT, and other AI tools
- **Flexible Content Processing**: Support for adventures, spells, creatures, and more
- **High Performance**: Async architecture with intelligent caching

<div class="getting-started-cta">
  Choose your path above to get started with studiorum.
</div>
