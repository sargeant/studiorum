# Epic: LaTeX Rendering System

This epic implements a comprehensive LaTeX rendering system for 5e2pdf, building on the proven patterns from the original prototype while modernizing the architecture and enhancing functionality.

## Epic Overview

**Goal**: Transform 5e.tools JSON content into beautiful, professional-quality PDF documents that match D&D 5th edition styling using advanced LaTeX rendering.

**Foundation**: Extend the existing modern architecture (omnidexer, tag system, content models) with a robust LaTeX rendering pipeline that preserves the proven techniques from the original implementation.

## Requirements

### Input Sources

- 5e.tools content loaded via omnidexer
- Custom JSON files with 5e.tools format
- Homebrew content with validation
- Adventure modules and supplements

### Output

- Professional PDF documents with authentic D&D 5th edition styling
- Multi-column layouts with proper typography
- Complete stat blocks, spell descriptions, item tables
- Cross-references and appendices
- Image integration with automatic format conversion

### CLI Interface Design

```bash
# Content-specific rendering with filtering
5e2pdf spells --filter 'level <= 2 and source == "phb" and "Wizard" in classes' --output low-level-wizard-spells.pdf

5e2pdf creatures --filter 'cr <= 5 and type == "humanoid"' --output npcs.pdf --appendix spell,item

5e2pdf items --filter 'rarity in ["common", "uncommon"] and type == "weapon"' --output basic-weapons.pdf

5e2pdf class --filter 'class.name == "Wizard"' --output wizard-class.pdf --appendix spell

# Class rendering options (data structure dependent):
# Full class with all subclasses:
5e2pdf class --filter 'class.name == "Wizard"' --output complete-wizard.pdf
# Specific subclass only (if supported by data structure):
5e2pdf class --filter 'class.name == "Wizard" and subclass.name == "School of Evocation"' --output evocation-wizard.pdf

# Adventure and book rendering
5e2pdf adventure cos --output curse-of-strahd.pdf --appendix creature,spell,item

5e2pdf book phb --sections "classes,spells" --output player-reference.pdf

# Direct JSON file rendering
5e2pdf render homebrew-spells.json --output custom-spells.pdf --template supplement

# Quick conversion with auto-detection
5e2pdf quick monster-manual.json --output mm.pdf

# Batch processing
5e2pdf batch adventures/*.json --output-dir campaign-books/ --appendix all
```

### Advanced Features

- **Appendix Generation**: Automatic collection and rendering of referenced content
- **Template System**: Multiple document templates (book, supplement, adventure, reference)
- **Image Processing**: WebP to PNG conversion, token generation, image optimization
- **Font Integration**: Authentic D&D typography with fallback fonts
- **Cross-references**: Automatic page numbers and hyperlinks
- **Table of Contents**: Multi-level ToC with proper formatting

## Implementation Status

### Epic Issue Created

**Main Epic**: [Issue #21 - LaTeX Rendering System](https://github.com/sargeant/5e2pdf/issues/21)

### Phase 1: Core LaTeX Infrastructure ✅ **ISSUES CREATED**

#### Issue #22: LaTeX Template System Foundation

- **Status**: Created - Ready for implementation
- **URL**: <https://github.com/sargeant/5e2pdf/issues/22>
- **Dependencies**: None
- **Scope**: Jinja2-based template engine, DND class integration, template hierarchy

#### Issue #23: DND LaTeX Template Integration

- **Status**: Created - Ready for implementation
- **URL**: <https://github.com/sargeant/5e2pdf/issues/23>
- **Dependencies**: #22
- **Scope**: DND-5e-LaTeX-Template integration, font system, document classes

#### Issue #24: Document Structure Framework

- **Status**: Created - Ready for implementation
- **URL**: <https://github.com/sargeant/5e2pdf/issues/24>
- **Dependencies**: #22, #23
- **Scope**: Document assembly, LaTeX native ToC, built-in headers/footers

#### Issue #25: LaTeX Compilation Pipeline

- **Status**: Created - Ready for implementation
- **URL**: <https://github.com/sargeant/5e2pdf/issues/25>
- **Dependencies**: #22, #23, #24
- **Scope**: LuaLaTeX compilation, XeLaTeX fallback, multi-pass compilation

### Phase 2: Content Rendering System ✅ **ISSUES CREATED**

#### Issue #26: Enhanced Content Renderers

- **Status**: Created - Ready for implementation
- **URL**: <https://github.com/sargeant/5e2pdf/issues/26>
- **Dependencies**: #22, #23, #24, #25
- **Scope**: Creature stat blocks, spell rendering, item tables, content types

#### Issue #27: Advanced Layout Features

- **Status**: Created - Ready for implementation
- **URL**: <https://github.com/sargeant/5e2pdf/issues/27>
- **Dependencies**: #26
- **Scope**: Multi-column text, sidebars, table formatting, float positioning

#### Issue #28: Tag System Integration for LaTeX

- **Status**: Created - Ready for implementation
- **URL**: <https://github.com/sargeant/5e2pdf/issues/28>
- **Dependencies**: #26
- **Scope**: Cross-references, hyperlinks, content tracking, tag rendering

#### Issue #29: Image Processing Pipeline

- **Status**: Created - Ready for implementation
- **URL**: <https://github.com/sargeant/5e2pdf/issues/29>
- **Dependencies**: #27
- **Scope**: WebP conversion, image optimization, token generation, placement

---

## Remaining Roadmap (Future Issues)

The following phases remain to be converted into GitHub issues as the earlier phases progress:

### Summary of Remaining Work

- **Phase 3** (4 issues): Appendix generation, enhanced CLI, template customization, performance optimization
- **Phase 4** (3 issues): Testing/validation, documentation, integration/migration
- **Total remaining**: ~7 issues to be created later

### Phase 3: Advanced Features 📋 **ROADMAP**

**Epic Issue**: [Advanced LaTeX Features] - *To be created*

#### Issue 3.1: Appendix Generation System

- Implement automatic content collection via ContentTracker
- Add appendix template system
- Create content deduplication and sorting
- Add appendix table of contents

#### Issue 3.2: Enhanced CLI Interface

- Implement advanced filtering syntax
- Add batch processing capabilities
- Create output organization and naming
- Add progress reporting and verbose modes

#### Issue 3.3: Template Customization

- Add user-defined template support
- Implement template inheritance system
- Create template validation and testing
- Add configuration file support

#### Issue 3.4: Performance and Error Handling

- Implement concurrent rendering for large documents
- Add comprehensive error recovery
- Create memory management for large datasets
- Add rendering cache system

### Phase 4: Polish and Documentation 📋 **ROADMAP**

**Epic Issue**: [LaTeX System Polish] - *To be created*

#### Issue 4.1: Testing and Validation

- Add comprehensive LaTeX rendering tests
- Create visual regression testing
- Implement PDF output validation
- Add performance benchmarking

#### Issue 4.2: Documentation and Examples

- Create user guide with examples
- Add template development documentation
- Create troubleshooting guide
- Add sample outputs and galleries

#### Issue 4.3: Integration and Migration

- Create migration tools from original code
- Add compatibility testing with existing outputs
- Implement feature parity validation
- Add upgrade documentation

## Technical Architecture

### LaTeX Rendering Pipeline

```
JSON Data → Omnidexer → Content Models → Template Engine → LaTeX Source → LuaLaTeX → PDF
                ↓                           ↓
        Content Tracker ←→ Tag Resolver → Cross-references
```

### Template Hierarchy

```
base.tex.j2
├── book.tex.j2 (adventures, sourcebooks)
├── supplement.tex.j2 (spell lists, item collections)
├── reference.tex.j2 (quick references, tables)
└── article.tex.j2 (single-topic documents)
```

### Content Renderer Architecture

```python
class LaTeXContentRenderer:
    def render(self, content: BaseModel, context: RenderContext) -> str
    def get_template(self) -> str
    def prepare_context(self, content: BaseModel) -> Dict[str, Any]
```

### DND Template Integration

- DND-5e-LaTeX-Template installation and configuration
- `dndbook` and `dndarticle` class integration
- Template font system usage (almendra, coelacanth, crimson, etc.)
- Template environment and command utilization

## Success Criteria

### Functional Requirements

- [ ] Generate PDFs matching D&D 5e styling quality
- [ ] Support all major content types (creatures, spells, items, adventures)
- [ ] Implement advanced layouts (multi-column, stat blocks, tables)
- [ ] Provide comprehensive CLI with filtering and options
- [ ] Generate automatic appendices and cross-references

### Quality Requirements

- [ ] 95%+ visual fidelity to original D&D layouts
- [ ] < 30 second rendering for typical documents (50-100 pages)
- [ ] Robust error handling with graceful degradation
- [ ] Comprehensive test coverage (>90%)
- [ ] Cross-platform compatibility (Windows, macOS, Linux)

### User Experience Requirements

- [ ] Intuitive CLI with helpful error messages
- [ ] Rich progress reporting for long operations
- [ ] Template customization without coding
- [ ] Batch processing for multiple documents
- [ ] Integration with existing workflow tools

## Risk Mitigation

### Technical Risks

- **LaTeX Complexity**: Leverage proven patterns from original implementation
- **Template Dependencies**: Ensure DND-5e-LaTeX-Template availability and compatibility
- **Performance**: Use incremental rendering and caching strategies
- **Cross-platform**: Extensive testing on all target platforms

### Scope Risks

- **Feature Creep**: Strict adherence to MVP in each phase
- **Template Complexity**: Start with proven layouts, extend incrementally
- **Backward Compatibility**: Maintain compatibility with existing data formats

## Dependencies

### External Tools

- LuaLaTeX distribution (TeXLive, MiKTeX) with XeLaTeX fallback
- DND-5e-LaTeX-Template package
- Image conversion tools (dwebp)

### Python Packages

- Jinja2 (template engine)
- Pillow (image processing)
- Subprocess management (LaTeX compilation)
- Rich (progress reporting)

### Assets

- DND-5e-LaTeX-Template integration
- LaTeX package dependencies
- Template-compatible font packages
- Template base files

This epic builds on the solid foundation of the existing 5e2pdf architecture while incorporating the proven LaTeX techniques from the original implementation, ensuring both modern development practices and production-quality output.
