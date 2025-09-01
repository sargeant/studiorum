---
title: Renderers API
description: Output rendering system for LaTeX, PDF, and custom formats
---

# Renderers API

Studiorum's rendering system provides flexible, extensible output generation from D&D content models to various formats including LaTeX, PDF, and custom formats.

## Core Rendering Architecture

### RenderingContext

The rendering context carries all necessary information for output generation:

```python
from studiorum.renderers.core.interfaces import RenderingContext
from typing import Any

@dataclass(frozen=True)
class RenderingContext:
    """Immutable rendering context for output generation."""

    output_format: str                          # "latex", "pdf", "markdown", etc.
    omnidexer: OmnidexerProtocol               # Content lookup service
    content_tracker: ContentTracker           # Cross-reference tracking
    metadata: dict[str, Any]                   # Additional rendering metadata

    def with_metadata(self, **kwargs: Any) -> RenderingContext:
        """Create new context with additional metadata."""
        new_metadata = {**self.metadata, **kwargs}
        return replace(self, metadata=new_metadata)

    def get_metadata[T](self, key: str, default: T = None) -> T:
        """Type-safe metadata access."""
        return self.metadata.get(key, default)
```

### DocumentRenderer Interface

Base interface for all document renderers:

```python
from abc import ABC, abstractmethod
from typing import Protocol

@runtime_checkable
class DocumentRenderer(Protocol):
    """Protocol for document rendering engines."""

    def get_supported_formats(self) -> list[str]:
        """Get list of supported output formats."""
        ...

    def render_document(
        self,
        content: list[Any],
        context: RenderingContext
    ) -> str:
        """Render complete document from content list."""
        ...

    def render_single_item(
        self,
        item: Any,
        context: RenderingContext
    ) -> str:
        """Render individual content item."""
        ...
```

## LaTeX Rendering System

### LaTeXDocumentRenderer

Primary renderer for LaTeX output:

```python
from studiorum.renderers.latex.document import LaTeXDocumentRenderer

class LaTeXDocumentRenderer:
    """Comprehensive LaTeX document renderer."""

    def __init__(self):
        self.entry_processor = RecursiveEntryProcessor()
        self.template_engine = TemplateEngine()

    def render_document(
        self,
        content: list[Any],
        context: RenderingContext
    ) -> str:
        """Render complete LaTeX document."""

        # Process all content entries
        processed_entries = []
        for item in content:
            rendered = self.entry_processor.process_entry(item, context)
            processed_entries.append(rendered)

        # Generate document structure
        document_parts = {
            "preamble": self._generate_preamble(context),
            "title_page": self._generate_title_page(context),
            "table_of_contents": self._generate_toc(context),
            "main_content": "\n\n".join(processed_entries),
            "appendices": self._generate_appendices(context),
            "index": self._generate_index(context)
        }

        # Render with template
        return self.template_engine.render_document(document_parts, context)

    def render_creature_stat_block(
        self,
        creature: Creature,
        context: RenderingContext
    ) -> str:
        """Render creature as LaTeX stat block."""

        template_data = {
            "name": creature.name,
            "size_type": f"{creature.size.value} {creature.creature_type.value}",
            "alignment": creature.alignment.value if creature.alignment else "unaligned",
            "armor_class": self._format_armor_class(creature.armor_class),
            "hit_points": self._format_hit_points(creature.hit_points),
            "speed": self._format_speeds(creature.speeds),
            "ability_scores": creature.ability_scores.dict(),
            "saving_throws": self._format_saving_throws(creature),
            "skills": self._format_skills(creature.skills),
            "senses": self._format_senses(creature.senses),
            "languages": self._format_languages(creature.languages),
            "challenge_rating": creature.challenge_rating.rating,
            "proficiency_bonus": creature.proficiency_bonus,
            "special_abilities": [
                self._format_special_ability(ability, context)
                for ability in creature.special_abilities
            ],
            "actions": [
                self._format_action(action, context)
                for action in creature.actions
            ],
            "legendary_actions": [
                self._format_legendary_action(action, context)
                for action in creature.legendary_actions
            ]
        }

        return self.template_engine.render_creature_stat_block(template_data, context)
```

### Entry Processing

The entry processor handles the recursive structure of D&D content:

```python
from studiorum.renderers.latex.entry_processor import RecursiveEntryProcessor

class RecursiveEntryProcessor:
    """Processes nested D&D content entries with tag resolution."""

    def __init__(self):
        self.tag_renderer = UnifiedTagRenderer()

    def process_entry(
        self,
        entry: Any,
        context: RenderingContext
    ) -> str:
        """Process any type of entry content."""

        if isinstance(entry, str):
            return self._process_text_with_tags(entry, context)

        elif isinstance(entry, dict):
            return self._process_structured_entry(entry, context)

        elif isinstance(entry, list):
            return self._process_list_entry(entry, context)

        else:
            # Handle Pydantic models
            return self._process_model_entry(entry, context)

    def _process_text_with_tags(
        self,
        text: str,
        context: RenderingContext
    ) -> str:
        """Process text content with embedded tags."""

        # Find all tags in the text
        tags = self._extract_tags(text)

        # Process each tag
        processed_text = text
        for tag in tags:
            rendered_tag = self.tag_renderer.render_tag(tag, context)
            processed_text = processed_text.replace(str(tag), rendered_tag)

        return processed_text

    def _process_structured_entry(
        self,
        entry: dict[str, Any],
        context: RenderingContext
    ) -> str:
        """Process structured entry (e.g., tables, lists)."""

        entry_type = entry.get("type", "text")

        if entry_type == "section":
            return self._render_section(entry, context)

        elif entry_type == "entries":
            return self._render_entries_block(entry, context)

        elif entry_type == "table":
            return self._render_table(entry, context)

        elif entry_type == "list":
            return self._render_list(entry, context)

        elif entry_type == "inset":
            return self._render_inset(entry, context)

        elif entry_type == "quote":
            return self._render_quote(entry, context)

        else:
            return self._render_generic_entry(entry, context)

    def _render_section(
        self,
        section: dict[str, Any],
        context: RenderingContext
    ) -> str:
        """Render section with title and content."""

        name = section.get("name", "")
        entries = section.get("entries", [])

        # Process section content
        content_parts = []
        for entry in entries:
            processed = self.process_entry(entry, context)
            content_parts.append(processed)

        # Format as LaTeX section
        section_content = "\n\n".join(content_parts)

        if name:
            return f"\\subsection{{{name}}}\n\n{section_content}"
        else:
            return section_content
```

### Tag Rendering System

The unified tag renderer handles all D&D content tags:

```python
from studiorum.renderers.latex.tag_renderer import UnifiedTagRenderer

class UnifiedTagRenderer:
    """Unified tag rendering system for all content types."""

    def __init__(self):
        self.handlers = self._register_handlers()

    def render_tag(
        self,
        tag: ParsedTag,
        context: RenderingContext
    ) -> str:
        """Render tag using appropriate handler."""

        handler = self.handlers.get(tag.tag_type)
        if handler:
            return handler.render(tag, context)
        else:
            # Fallback to generic rendering
            return self._render_generic_tag(tag, context)

    def _register_handlers(self) -> dict[str, TagHandler]:
        """Register all tag handlers."""
        return {
            "creature": CreatureTagHandler(),
            "spell": SpellTagHandler(),
            "item": ItemTagHandler(),
            "adventure": AdventureTagHandler(),
            "dice": DiceTagHandler(),
            "damage": DamageTagHandler(),
            "condition": ConditionTagHandler(),
            "sense": SenseTagHandler(),
            "skill": SkillTagHandler(),
            "action": ActionTagHandler(),
            "book": BookTagHandler(),
            "quickref": QuickrefTagHandler(),
            "note": NoteTagHandler(),
        }

# Example tag handler
class CreatureTagHandler:
    """Handler for {@creature} tags."""

    def render(
        self,
        tag: ParsedTag,
        context: RenderingContext
    ) -> str:
        """Render creature tag."""

        creature_name = tag.name
        source = tag.attributes.get("source")

        # Look up creature
        omnidexer = context.omnidexer
        creature = omnidexer.get_creature_by_name(creature_name)

        if not creature:
            return f"\\textbf{{{creature_name}}} (creature not found)"

        # Track for appendix
        context.content_tracker.track_creature(creature)

        # Format reference based on context
        display_name = tag.attributes.get("displayText", creature.name)

        if context.get_metadata("include_cr_in_references", False):
            return f"\\textbf{{{display_name}}} (CR {creature.challenge_rating.rating})"
        else:
            return f"\\textbf{{{display_name}}}"
```

## Template System

### Jinja2 Template Engine

Studiorum uses Jinja2 for flexible template rendering:

```python
from studiorum.renderers.core.template_engine import TemplateEngine

class TemplateEngine:
    """Jinja2-based template rendering engine."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir or self._get_default_template_dir()
        self.env = self._create_jinja_environment()

    def render_document(
        self,
        template_data: dict[str, Any],
        context: RenderingContext
    ) -> str:
        """Render complete document using template."""

        template_name = self._get_document_template(context.output_format)
        template = self.env.get_template(template_name)

        return template.render(
            **template_data,
            context=context,
            format=context.output_format
        )

    def render_creature_stat_block(
        self,
        creature_data: dict[str, Any],
        context: RenderingContext
    ) -> str:
        """Render creature stat block."""

        template = self.env.get_template("creature_stat_block.tex")
        return template.render(creature=creature_data, context=context)

    def render_spell_block(
        self,
        spell_data: dict[str, Any],
        context: RenderingContext
    ) -> str:
        """Render spell description block."""

        template = self.env.get_template("spell_block.tex")
        return template.render(spell=spell_data, context=context)

    def _create_jinja_environment(self) -> Environment:
        """Create configured Jinja2 environment."""

        loader = FileSystemLoader(self.template_dir)
        env = Environment(
            loader=loader,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )

        # Add custom filters
        env.filters.update({
            "latex_escape": self._latex_escape_filter,
            "format_modifier": self._format_modifier_filter,
            "format_dice": self._format_dice_filter,
            "pluralize": self._pluralize_filter,
            "title_case": str.title,
            "oxford_join": self._oxford_join_filter
        })

        # Add custom functions
        env.globals.update({
            "format_challenge_rating": self._format_challenge_rating,
            "format_speed_list": self._format_speed_list,
            "calculate_modifier": self._calculate_modifier
        })

        return env

    def _latex_escape_filter(self, text: str) -> str:
        """Escape LaTeX special characters."""
        escape_chars = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "^": r"\textasciicircum{}",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "\\": r"\textbackslash{}"
        }

        for char, replacement in escape_chars.items():
            text = text.replace(char, replacement)
        return text
```

### Template Structure

LaTeX templates follow a consistent structure:

```latex
{# creature_stat_block.tex #}
{% set cr_display = creature.challenge_rating %}
{% if creature.challenge_rating == "0" %}
    {% set cr_display = "0 (0 XP)" %}
{% endif %}

\begin{dndmonster}[float=!htb]{{{ creature.name|latex_escape }}}
    \begin{multicols}{2}
        \textit{{{ creature.size_type|latex_escape }}, {{ creature.alignment|latex_escape }}}

        \dndmonsterdescription{Armor Class}{{{ creature.armor_class }}}
        \dndmonsterdescription{Hit Points}{{{ creature.hit_points }}}
        \dndmonsterdescription{Speed}{{{ creature.speed|join(", ")|latex_escape }}}

        \begin{dndmonsterstats}
            {% for ability, score in creature.ability_scores.items() %}
                {{ score }} ({{ calculate_modifier(score)|format_modifier }})
                {% if not loop.last %} & {% endif %}
            {% endfor %}
        \end{dndmonsterstats}

        {% if creature.saving_throws %}
        \dndmonsterdescription{Saving Throws}{{{ creature.saving_throws|latex_escape }}}
        {% endif %}

        {% if creature.skills %}
        \dndmonsterdescription{Skills}{{{ creature.skills|join(", ")|latex_escape }}}
        {% endif %}

        \dndmonsterdescription{Challenge Rating}{{{ cr_display|latex_escape }}}

        {% for ability in creature.special_abilities %}
        \dndmonsteraction[{{ ability.name|latex_escape }}]{{{ ability.description|latex_escape }}}
        {% endfor %}

        \dndmonstermelee{Actions}
        {% for action in creature.actions %}
        \dndmonsteraction[{{ action.name|latex_escape }}]{{{ action.description|latex_escape }}}
        {% endfor %}

        {% if creature.legendary_actions %}
        \dndmonstermelee{Legendary Actions}
        {% for action in creature.legendary_actions %}
        \dndmonsteraction[{{ action.name|latex_escape }}]{{{ action.description|latex_escape }}}
        {% endfor %}
        {% endif %}
    \end{multicols}
\end{dndmonster}
```

## Content Tracking System

### ContentTracker

Tracks referenced content for appendices:

```python
from studiorum.core.references.content_tracker import ContentTracker

class ContentTracker:
    """Tracks referenced content for appendix generation."""

    def __init__(self):
        self._tracked_creatures: set[str] = set()
        self._tracked_spells: set[str] = set()
        self._tracked_items: set[str] = set()
        self._tracked_books: set[str] = set()

    def track_creature(self, creature: Creature) -> None:
        """Track a creature reference."""
        self._tracked_creatures.add(creature.name)

    def track_spell(self, spell: Spell) -> None:
        """Track a spell reference."""
        self._tracked_spells.add(spell.name)

    def track_item(self, item: Item) -> None:
        """Track an item reference."""
        self._tracked_items.add(item.name)

    def get_tracked_content(self) -> dict[str, set[str]]:
        """Get all tracked content."""
        return {
            "creatures": self._tracked_creatures.copy(),
            "spells": self._tracked_spells.copy(),
            "items": self._tracked_items.copy(),
            "books": self._tracked_books.copy()
        }

    def export_for_appendix(self) -> dict[str, list[dict[str, Any]]]:
        """Export tracked content for appendix generation."""

        # This would resolve names to full objects
        return {
            "creatures": self._resolve_creatures(),
            "spells": self._resolve_spells(),
            "items": self._resolve_items()
        }
```

## Custom Renderers

### Creating Custom Renderers

Implement the DocumentRenderer protocol:

```python
class MarkdownRenderer:
    """Custom Markdown renderer."""

    def get_supported_formats(self) -> list[str]:
        return ["markdown", "md"]

    def render_document(
        self,
        content: list[Any],
        context: RenderingContext
    ) -> str:
        """Render document as Markdown."""

        parts = []
        for item in content:
            rendered = self.render_single_item(item, context)
            parts.append(rendered)

        return "\n\n".join(parts)

    def render_single_item(
        self,
        item: Any,
        context: RenderingContext
    ) -> str:
        """Render individual item as Markdown."""

        if isinstance(item, Creature):
            return self._render_creature_markdown(item, context)
        elif isinstance(item, Spell):
            return self._render_spell_markdown(item, context)
        elif isinstance(item, dict):
            return self._render_dict_entry(item, context)
        else:
            return str(item)

    def _render_creature_markdown(
        self,
        creature: Creature,
        context: RenderingContext
    ) -> str:
        """Render creature as Markdown stat block."""

        lines = [
            f"# {creature.name}",
            f"*{creature.size.value} {creature.creature_type.value}*",
            "",
            f"**Armor Class** {creature.armor_class.display_value}",
            f"**Hit Points** {creature.hit_points.display_value}",
            f"**Speed** {', '.join(speed.display for speed in creature.speeds)}",
            "",
            "| STR | DEX | CON | INT | WIS | CHA |",
            "|-----|-----|-----|-----|-----|-----|",
            f"| {creature.ability_scores.strength} ({creature.get_modifier('strength'):+d}) | "
            f"{creature.ability_scores.dexterity} ({creature.get_modifier('dexterity'):+d}) | "
            f"{creature.ability_scores.constitution} ({creature.get_modifier('constitution'):+d}) | "
            f"{creature.ability_scores.intelligence} ({creature.get_modifier('intelligence'):+d}) | "
            f"{creature.ability_scores.wisdom} ({creature.get_modifier('wisdom'):+d}) | "
            f"{creature.ability_scores.charisma} ({creature.get_modifier('charisma'):+d}) |",
            "",
            f"**Challenge Rating** {creature.challenge_rating.rating}",
            ""
        ]

        # Add actions
        if creature.actions:
            lines.append("## Actions")
            lines.append("")
            for action in creature.actions:
                lines.append(f"**{action.name}.** {action.description}")
            lines.append("")

        return "\n".join(lines)

# Register custom renderer
from studiorum.renderers.registry import get_renderer_registry

registry = get_renderer_registry()
registry.register_renderer("markdown", MarkdownRenderer())
```

### Format-Specific Handlers

Create specialized handlers for different output formats:

```python
class HTMLRenderer:
    """HTML renderer for web output."""

    def get_supported_formats(self) -> list[str]:
        return ["html", "web"]

    def render_document(
        self,
        content: list[Any],
        context: RenderingContext
    ) -> str:
        """Render as HTML document."""

        # Use Jinja2 templates for HTML
        template_engine = TemplateEngine(template_dir="templates/html")

        document_data = {
            "title": context.get_metadata("title", "D&D Content"),
            "content_items": [
                self.render_single_item(item, context)
                for item in content
            ]
        }

        return template_engine.render_template("document.html", document_data)

    def render_single_item(
        self,
        item: Any,
        context: RenderingContext
    ) -> str:
        """Render individual item as HTML."""

        if isinstance(item, Creature):
            return self._render_creature_html(item, context)
        # ... other types

    def _render_creature_html(
        self,
        creature: Creature,
        context: RenderingContext
    ) -> str:
        """Render creature as HTML stat block."""

        return f"""
        <div class="creature-stat-block">
            <h2 class="creature-name">{creature.name}</h2>
            <p class="creature-type">
                <em>{creature.size.value} {creature.creature_type.value}</em>
            </p>

            <div class="creature-stats">
                <div class="stat-line">
                    <strong>Armor Class</strong> {creature.armor_class.display_value}
                </div>
                <div class="stat-line">
                    <strong>Hit Points</strong> {creature.hit_points.display_value}
                </div>
                <!-- ... more stats ... -->
            </div>

            <div class="creature-actions">
                <h3>Actions</h3>
                {self._render_actions_html(creature.actions)}
            </div>
        </div>
        """
```

## Renderer Configuration

### Renderer Settings

Configure renderer behavior through the context:

```python
# Create context with renderer-specific settings
context = RenderingContext(
    output_format="latex",
    omnidexer=omnidexer,
    content_tracker=content_tracker,
    metadata={
        # LaTeX-specific settings
        "latex_compiler": "xelatex",
        "include_toc": True,
        "include_index": False,
        "paper_size": "letter",
        "font_size": "10pt",

        # Rendering options
        "include_cr_in_references": True,
        "show_source_abbreviations": True,
        "group_similar_content": True,

        # Appendix settings
        "appendix_creatures": True,
        "appendix_spells": True,
        "appendix_items": True,
        "appendix_max_items": 50
    }
)

# Use configured context
renderer = LaTeXDocumentRenderer()
output = renderer.render_document(content, context)
```

### Template Customization

Customize templates for specific campaigns:

```python
# Campaign-specific template directory
campaign_templates = Path("campaigns/curse-of-strahd/templates")

# Create template engine with custom templates
template_engine = TemplateEngine(template_dir=campaign_templates)

# Override specific templates
context = context.with_metadata(
    template_overrides={
        "creature_stat_block.tex": "gothic_creature_block.tex",
        "spell_block.tex": "dark_magic_spell.tex"
    }
)
```

## Performance Optimization

### Caching

Implement caching for expensive rendering operations:

```python
from functools import lru_cache
from typing import Hashable

class CachingRenderer:
    """Renderer with built-in caching."""

    def __init__(self, base_renderer: DocumentRenderer):
        self.base_renderer = base_renderer

    @lru_cache(maxsize=1000)
    def _render_cached_item(
        self,
        item_hash: Hashable,
        item_data: str,
        format_type: str
    ) -> str:
        """Cache rendered items by hash."""
        # This would be called by render_single_item
        # with a hash of the item and format
        pass

    def render_single_item(
        self,
        item: Any,
        context: RenderingContext
    ) -> str:
        """Render with caching."""

        # Generate cache key
        item_hash = self._generate_item_hash(item, context.output_format)
        item_data = self._serialize_item(item)

        return self._render_cached_item(
            item_hash,
            item_data,
            context.output_format
        )
```

### Streaming Rendering

For large documents, use streaming:

```python
from typing import Generator

class StreamingRenderer:
    """Renderer that yields content in chunks."""

    def render_document_stream(
        self,
        content: list[Any],
        context: RenderingContext
    ) -> Generator[str, None, None]:
        """Yield document content in chunks."""

        # Yield document header
        yield self._render_document_header(context)

        # Yield each content item
        for item in content:
            rendered_item = self.render_single_item(item, context)
            yield rendered_item
            yield "\n\n"  # Item separator

        # Yield document footer
        yield self._render_document_footer(context)
```

## Testing Renderers

### Renderer Testing Patterns

```python
import pytest
from unittest.mock import Mock

class TestLaTeXRenderer:
    def setup_method(self):
        self.renderer = LaTeXDocumentRenderer()
        self.mock_omnidexer = Mock(spec=OmnidexerProtocol)
        self.content_tracker = ContentTracker()

        self.context = RenderingContext(
            output_format="latex",
            omnidexer=self.mock_omnidexer,
            content_tracker=self.content_tracker,
            metadata={}
        )

    def test_creature_stat_block_rendering(self):
        """Test creature stat block generation."""
        creature = self._create_test_creature()

        result = self.renderer.render_creature_stat_block(creature, self.context)

        # Verify LaTeX structure
        assert "\\begin{dndmonster}" in result
        assert "\\end{dndmonster}" in result
        assert creature.name in result
        assert str(creature.challenge_rating.rating) in result

    def test_content_tracking(self):
        """Test that content is properly tracked."""
        creature = self._create_test_creature()

        self.renderer.render_creature_stat_block(creature, self.context)

        # Verify creature was tracked
        tracked = self.content_tracker.get_tracked_content()
        assert creature.name in tracked["creatures"]

    def test_tag_processing_in_text(self):
        """Test tag processing in adventure text."""
        text_with_tags = "The {@creature Hobgoblin|SRD} attacks with a {@item scimitar|SRD}."

        # Mock omnidexer responses
        mock_hobgoblin = Mock()
        mock_hobgoblin.name = "hobgoblin"
        self.mock_omnidexer.get_creature_by_name.return_value = mock_hobgoblin

        mock_scimitar = Mock()
        mock_scimitar.name = "scimitar"
        self.mock_omnidexer.get_item_by_name.return_value = mock_scimitar

        result = self.renderer.entry_processor._process_text_with_tags(
            text_with_tags,
            self.context
        )

        # Verify tags were processed
        assert "hobgoblin" in result
        assert "scimitar" in result
        assert "{@creature" not in result  # Tags should be resolved
```

## Next Steps

- **[Services API](services.md)**: Service container and dependency injection
- **[Models API](models.md)**: Data models and validation
- **[Architecture Guide](../architecture.md)**: Overall system design
- **[AI Agents Guide](../ai-agents.md)**: MCP integration patterns
