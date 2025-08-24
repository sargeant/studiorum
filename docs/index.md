---
title: Studiorum Documentation
description: 5e content processing toolkit - LaTeX/PDF generation and MCP integration
---

<div class="hero-banner gradient-background">
  <h1 class="hero-title">Studiorum</h1>
  <p class="hero-subtitle">Content Toolkit for the 5th Edition of the World's Greatest Roleplaying Game</p>
</div>

## Getting Started

<div class="feature-cards">
  <div class="feature-card">
    <h3>User Guide</h3>
    <p>Create beautiful PDFs from 5e compatible spells, items, and creatures using professional typesetting.</p>
    <a href="user-guide/" class="btn-primary">Get Started</a>
  </div>

  <div class="feature-card">
    <h3>Developer Guide</h3>
    <p>Build applications with Studiorum's models and services for 5e content processing.</p>
    <a href="developer-guide/" class="btn-secondary">API Documentation</a>
  </div>

  <div class="feature-card">
    <h3>MCP Integration</h3>
    <p>Connect AI agents to 5e content through Model Context Protocol tools for intelligent content processing.</p>
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
