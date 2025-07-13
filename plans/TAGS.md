# Tag Resolution System Overhaul

> Current Issue: Regex-based parsing with 25+ tag types is becoming unmaintainable and error-prone.
>  Recommended Solution:
>  - Migrate to a formal parsing library like lark or pyparsing
>  - Define clear grammar for tag syntax
>  - Implement visitor pattern over Abstract Syntax Tree (AST)
>  - Benefits: Better error handling, easier extensibility, cleaner separation of parsing vs resolution

This might be important to know since I plan to add it later; I want to be able to print a full adventure, and anytime it uses a specific tag type (e.g., spell or item) I want to store that fact for later. In the appendix of the LaTeX document, I want to add descriptions of all the spells/items/creatures mentioned in the book. Don't try to implement that feature for now, I'm just raising it here in case it makes a different to the new tag system implementation. 


Use the TDD pattern to plan this. Discuss with Gemini at the plan stage to get a second 
opinion and revise your thinking if needed.

## Implementation

⏺ Deep Dive: New Tag Resolution System Architecture

  Let me walk you through the technical details of how this new system works, from parsing to rendering to content tracking.

  🏗️ System Architecture Overview

  The new tag system follows a pipeline architecture with clear separation of concerns:

  Raw Text → Parser → AST → Renderer → LaTeX Output
                       ↓
                  Content Tracker → Appendix Data

  Let me break down each component:

  📝 1. Grammar-Based Parsing (Lark)

  Grammar Definition

  The system starts with a formal grammar in tag_grammar.lark:

  document: (text | tag)*
  tag: "{@" tag_type tag_content "}"
  tag_type: WORD
  tag_content: (pipe_separated_content)*
  pipe_separated_content: "|" content_part
  content_part: (text_fragment | nested_tag | escaped_char)*

  This grammar handles:
  - Nested tags: {@creature Dragon|MM|{@bold great} wyrm}
  - Escaped characters: {@spell Name\\|with\\|pipes|PHB}
  - Multiple components: {@adventure Chapter 1|CoS|Into the Mists|21}

  Parser Implementation

  The TagParser class uses Lark with a regex fallback:

  def parse(self, text: str) -> DocumentNode:
      try:
          # Try formal parsing first
          return self._parse_with_lark(text)
      except LarkError:
          # Fall back to regex for complex cases
          return self._parse_with_regex_fallback(text)

  Why the fallback? Real-world 5e.tools data sometimes has malformed tags or edge cases that break formal parsing. The regex fallback ensures we never
  fail completely.

  🌳 2. Abstract Syntax Tree (AST)

  Node Hierarchy

  Every parsed element becomes a node in the AST:

  class ASTNode:
      def __init__(self, original_text_span=None):
          self.original_text_span = original_text_span  # For debugging
          self.children = []  # Child nodes

  class TextNode(ASTNode):
      def __init__(self, text: str):
          super().__init__()
          self.text = text

  class CreatureTagNode(TagNode):
      def __init__(self, name: str, source=None, display_text_nodes=None, page=None):
          super().__init__("creature")
          self.name = name              # "Ancient Red Dragon"
          self.source = source          # "MM"
          self.page = page             # "123"
          self.display_text_nodes = display_text_nodes or [TextNode(name)]
          self.children.extend(self.display_text_nodes)

  Example AST Structure

  For the text: "Cast {@spell Fireball|PHB} at the {@creature Ancient Red Dragon|MM}!"

  DocumentNode
  ├── TextNode("Cast ")
  ├── SpellTagNode(name="Fireball", source="PHB")
  │   └── TextNode("Fireball")  # display_text_nodes
  ├── TextNode(" at the ")
  ├── CreatureTagNode(name="Ancient Red Dragon", source="MM")
  │   └── TextNode("Ancient Red Dragon")  # display_text_nodes
  └── TextNode("!")

  Nested Tag Support

  For: {@creature Ancient Red Dragon|MM|{@bold great} wyrm}

  CreatureTagNode(name="Ancient Red Dragon", source="MM")
  ├── BoldTagNode
  │   └── TextNode("great")
  └── TextNode(" wyrm")

  🎭 3. Handler System (Strategy Pattern)

  Handler Interface

  Each tag type has a specialized handler:

  class TagHandler(ABC):
      @abstractmethod
      def handles(self, tag_type: str) -> bool:
          pass

      @abstractmethod
      def render(self, node: TagNode, context: RendererContext) -> str:
          pass

      @abstractmethod
      def track_content(self, node: TagNode, tracker: ContentTracker) -> None:
          pass

  Concrete Handler Example

  class CreatureTagHandler(TagHandler):
      def handles(self, tag_type: str) -> bool:
          return tag_type == "creature"

      def render(self, node: CreatureTagNode, context: RendererContext) -> str:
          # Render display text recursively (handles nested tags)
          display_text = "".join(
              context.render_node(child) for child in node.display_text_nodes
          )
          # Escape LaTeX and apply formatting
          escaped_text = self._escape_latex(display_text)
          return f"\\textbf{{{escaped_text}}}"

      def track_content(self, node: CreatureTagNode, tracker: ContentTracker) -> None:
          # Track for appendix generation
          tracker.add_content("creature", node.name, node.source, node.page)

  LaTeX Escaping

  Each handler includes comprehensive LaTeX character escaping:

  def _escape_latex(self, text: str) -> str:
      replacements = {
          '\\': '\\textbackslash{}',
          '{': '\\{', '}': '\\}',
          '$': '\\$', '&': '\\&', '%': '\\%',
          '#': '\\#', '^': '\\textasciicircum{}',
          '_': '\\_', '~': '\\textasciitilde{}',
      }
      for char, replacement in replacements.items():
          text = text.replace(char, replacement)
      return text

  🎨 4. Unified Renderer

  Rendering Pipeline

  The TagRenderer orchestrates the entire rendering process:

  def render_node(self, node: ASTNode, context: RendererContext) -> str:
      if isinstance(node, TextNode):
          return node.text

      elif isinstance(node, TagNode):
          # Find appropriate handler
          handler = self._handlers.get(node.tag_type)
          if handler:
              # Track content for appendix
              handler.track_content(node, self.content_tracker)
              # Render the tag
              return handler.render(node, context)
          else:
              # Fallback for unknown tags
              return self._fallback_render(node)

      elif isinstance(node, DocumentNode):
          # Render all children
          return "".join(self.render_node(child, context) for child in node.children)

  Recursive Rendering

  The system handles nested content through recursive calls:

  # In CreatureTagHandler.render()
  display_text = "".join(
      context.render_node(child) for child in node.display_text_nodes
  )

  This means {@creature Dragon|MM|{@bold great} wyrm} processes as:
  1. CreatureTagHandler gets called
  2. It recursively renders display_text_nodes
  3. BoldTagHandler processes {@bold great}
  4. Result: \textbf{\textbf{great} wyrm}

  📊 5. Content Tracking System

  TrackedContent Data Structure

  @dataclass
  class TrackedContent:
      content_type: str    # "creature", "spell", "item"
      name: str           # "Ancient Red Dragon"
      source: Optional[str] = None  # "MM"
      page: Optional[str] = None    # "123"

      def to_tuple(self) -> Tuple[str, str, Optional[str]]:
          return (self.content_type, self.name, self.source)

  ContentTracker Implementation

  class ContentTracker:
      def __init__(self):
          self._tracked_content: Set[TrackedContent] = set()
          self._content_counts: Dict[Tuple[str, str, Optional[str]], int] = {}

      def add_content(self, content_type: str, name: str, source=None, page=None):
          content = TrackedContent(content_type, name, source, page)

          # Set automatically handles deduplication
          self._tracked_content.add(content)

          # Track reference count
          key = content.to_tuple()
          self._content_counts[key] = self._content_counts.get(key, 0) + 1

  Appendix Export

  The tracker can export data for appendix generation:

  def export_for_appendix(self) -> Dict[str, List[Dict[str, str]]]:
      result = {}
      for content_type in self.get_content_types():
          type_content = self.get_tracked_content_by_type(content_type)
          result[content_type] = []

          for content in type_content:
              entry = {
                  "name": content.name,
                  "type": content.content_type,
                  "reference_count": self.get_content_count(
                      content.content_type, content.name, content.source
                  )
              }
              if content.source:
                  entry["source"] = content.source
              if content.page:
                  entry["page"] = content.page
              result[content_type].append(entry)

      return result

  Example output:
  {
      'creature': [
          {
              'name': 'Ancient Red Dragon',
              'type': 'creature',
              'source': 'MM',
              'reference_count': 3
          }
      ],
      'spell': [
          {
              'name': 'Fireball',
              'type': 'spell',
              'source': 'PHB',
              'reference_count': 1
          }
      ]
  }

  🔄 6. Backward Compatibility Facade

  API Preservation

  The NewTagResolverFacade maintains the existing interface:

  class NewTagResolverFacade:
      def __init__(self, omnidexer=None):
          self.parser = TagParser()
          self.renderer = TagRenderer(omnidexer)

      def process_text(self, text: str) -> str:
          """Maintains compatibility with old TagResolver.process_text()"""
          try:
              document = self.parser.parse(text)
              return self.renderer.render_document(document)
          except Exception:
              # Graceful fallback
              return text

      def register_tag_handler(self, tag_type: str, handler_func: Callable):
          """Legacy handler registration"""
          wrapper = LegacyHandlerWrapper(tag_type, handler_func)
          self.renderer.register_handler(wrapper)

  Legacy Handler Adaptation

  Old-style handler functions get wrapped:

  class LegacyHandlerWrapper(TagHandler):
      def __init__(self, tag_type: str, handler_func: Callable):
          self.tag_type = tag_type
          self.handler_func = handler_func

      def render(self, node, context) -> str:
          # Create legacy TagMatch-like object
          legacy_tag = LegacyTagMatch(node)
          return self.handler_func(legacy_tag)

  🚀 7. Processing Flow Example

  Let's trace through a complete example:

  Input: "Cast {@spell Fireball|PHB} at {@creature Ancient Red Dragon|MM|great wyrm}!"

  Step 1: Parsing

  parser = TagParser()
  document = parser.parse(text)
  # Creates AST with TextNode, SpellTagNode, TextNode, CreatureTagNode, TextNode

  Step 2: Rendering Setup

  renderer = TagRenderer()
  context = RendererContext(renderer)

  Step 3: Document Rendering

  result = renderer.render_document(document)

  This triggers:
  1. render_node(TextNode("Cast ")) → "Cast "
  2. render_node(SpellTagNode(...)) →
    - SpellTagHandler.track_content() tracks "Fireball"
    - SpellTagHandler.render() → "\\textit{Fireball}"
  3. render_node(TextNode(" at ")) → " at "
  4. render_node(CreatureTagNode(...)) →
    - CreatureTagHandler.track_content() tracks "Ancient Red Dragon"
    - CreatureTagHandler.render() processes display_text_nodes:
        - Renders TextNode("great wyrm") → "great wyrm"
    - Returns "\\textbf{great wyrm}"
  5. render_node(TextNode("!")) → "!"

  Step 4: Final Output

  "Cast \\textit{Fireball} at \\textbf{great wyrm}!"

  Step 5: Content Tracking

  tracked = renderer.get_tracked_content()
  # Returns:
  # [
  #   TrackedContent(content_type="creature", name="Ancient Red Dragon", source="MM"),
  #   TrackedContent(content_type="spell", name="Fireball", source="PHB")
  # ]

  ⚡ 8. Performance Characteristics

  Time Complexity

  - Parsing: O(n) where n is text length
  - Rendering: O(m) where m is number of AST nodes
  - Content Tracking: O(1) insertion, O(k log k) sorting where k is unique content count

  Memory Usage

  - AST Storage: Proportional to tag count and nesting depth
  - Content Tracking: One TrackedContent object per unique reference
  - Handler Registry: Fixed size (25+ handlers)

  Optimization Features

  - Lazy Evaluation: Only processes tags when rendering
  - Deduplication: Set-based content tracking
  - Fallback Strategy: Regex parsing for edge cases
  - Efficient String Operations: Minimal string copying during rendering

  🎯 9. Extensibility Points

  Adding New Tag Types

  class MyCustomTagHandler(TagHandler):
      def handles(self, tag_type: str) -> bool:
          return tag_type == "mycustom"

      def render(self, node, context) -> str:
          return f"\\custom{{{node.name}}}"

      def track_content(self, node, tracker) -> None:
          tracker.add_content("mycustom", node.name)

  # Register the handler
  renderer.register_handler(MyCustomTagHandler())

  Custom Output Formats

  The handler system makes it trivial to add HTML output:

  class HTMLCreatureTagHandler(TagHandler):
      def render(self, node, context) -> str:
          return f"<strong>{node.name}</strong>"

  Advanced Content Processing

  class DetailedContentTracker(ContentTracker):
      def add_content_with_context(self, content_type, name, context_info):
          # Enhanced tracking with additional metadata
          pass

  🔮 10. Future Appendix Generation

  The content tracking system is designed for the future appendix feature you mentioned. Here's how it would work:

  Appendix Generation Flow

  # 1. Process document and track content
  facade = NewTagResolverFacade()
  latex_output = facade.process_text(adventure_text)

  # 2. Get tracked content
  appendix_data = facade.get_tracked_content_detailed()

  # 3. Generate appendix sections
  for content_type, items in appendix_data.items():
      if content_type == "spell":
          for spell in items:
              # Look up full spell data from omnidexer
              spell_data = omnidexer.get_spell(spell["name"], spell["source"])
              # Generate full LaTeX spell block
              appendix_latex += render_spell_block(spell_data)

  Reference Statistics

  # Most referenced content
  popular_spells = sorted(
      appendix_data["spell"],
      key=lambda x: x["reference_count"],
      reverse=True
  )

  # Content by source book
  mm_creatures = [
      c for c in appendix_data["creature"]
      if c["source"] == "MM"
  ]

  This architecture provides a robust, extensible foundation that maintains backward compatibility while enabling powerful new features like automatic
  appendix generation. The formal parsing approach eliminates the maintenance burden of regex-based tag handling and provides a clean path for future
  enhancements.