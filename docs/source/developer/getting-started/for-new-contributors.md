# For New Contributors

Progressive onboarding from first contribution to independent development.

## Welcome to 5e2pdf!

This guide will help you make your first contribution and grow into an independent contributor to the 5e2pdf project.

## Your Learning Path

### Stage 1: Setup and Orientation (First Week)

#### Development Environment Setup
1. **Clone and Setup**
   ```bash
   git clone https://github.com/sargeant/5e2pdf.git
   cd 5e2pdf
   uv sync --extra dev
   ```

2. **Verify Installation**
   ```bash
   # Run tests to ensure everything works
   uv run pytest tests/unit/ -v

   # Check code quality tools
   uv run mypy src/
   uv run ruff check src/
   ```

3. **Install Pre-commit Hooks**
   ```bash
   uv run pre-commit install
   ```

#### Project Orientation
- Read {doc}`../system-guide/architecture-overview` to understand the big picture
- Browse {doc}`../api-reference/index` to see available components
- Review {doc}`../contributing/setup-guide` for detailed environment setup

#### First Success: Documentation Fix
**Goal**: Make a small documentation improvement to learn the workflow.

**Good First Issues**:
- Fix typos or grammar in documentation
- Add missing docstrings to public methods
- Improve code examples in docs
- Update outdated information

**Process**:
1. Create a branch: `git checkout -b fix/doc-improvement`
2. Make your changes
3. Test: `uv run pytest docs/` (if doc tests exist)
4. Commit: `git commit -m "docs: fix typo in API reference"`
5. Create PR with clear description

### Stage 2: Code Contribution (Weeks 2-4)

#### Understanding the Codebase
1. **Study Core Components**
   - Read {doc}`../system-guide/components` (Entry Processing section)
   - Examine how content models work in `src/dnd5e/core/models/`
   - Understand testing patterns in `tests/unit/models/`

2. **Follow the Data Flow**
   ```
   JSON Data → ContentParser → BaseContent → Omnidexer → LaTeX Renderer → PDF
   ```

3. **Understand Key Patterns**
   - Pydantic models for validation
   - Synchronous I/O operations
   - Protocol-based interfaces
   - Comprehensive error handling

#### Good Second Contributions
**Bug Fixes**: Small, well-defined problems
- Content parsing edge cases
- Validation improvements
- Error message clarity
- Test coverage gaps

**Feature Enhancements**: Extend existing functionality
- New validation rules for content models
- Additional LaTeX formatting options
- Improved error reporting
- Performance optimizations

**Process**:
1. **Find an Issue**: Look for `good-first-issue` or `help-wanted` labels
2. **Understand the Problem**: Read issue description and related code
3. **Plan Your Approach**: Write a comment describing your plan
4. **Follow TDD**: Write tests first, then implement
5. **Get Feedback**: Create draft PR early for feedback

### Stage 3: Component Ownership (Months 2-3)

#### Deeper System Understanding
1. **Master a Component**: Choose one area to specialize in
   - Content models and validation
   - LaTeX rendering system
   - Data loading and caching
   - Testing infrastructure

2. **Contribute Systematically**
   - Fix bugs in your chosen area
   - Add comprehensive tests
   - Improve documentation
   - Optimize performance

3. **Help Other Contributors**
   - Review pull requests in your area
   - Answer questions from new contributors
   - Identify good first issues for others

#### Advanced Contributions
**Architectural Improvements**: Enhance system design
- Refactor components for better separation of concerns
- Improve error handling patterns
- Add new extension points
- Optimize performance bottlenecks

**New Features**: Add significant functionality
- Support for new content types
- Additional output formats
- Advanced filtering and querying
- Integration with external tools

### Stage 4: Independent Development (Month 3+)

#### Project Leadership
1. **Technical Decision Making**
   - Participate in architectural discussions
   - Propose improvements and new features
   - Review complex pull requests
   - Mentor new contributors

2. **Project Maintenance**
   - Triage and prioritize issues
   - Maintain project documentation
   - Update dependencies and tooling
   - Ensure code quality standards

#### Advanced Skills Development
- **Performance Engineering**: Profile and optimize critical paths
- **API Design**: Create stable, extensible interfaces
- **Testing Strategy**: Design comprehensive test suites
- **Documentation**: Write clear implementation guides

## Contribution Types and Skills

### Documentation Contributions
**Skills Needed**: Writing, attention to detail
**Examples**:
- API documentation improvements
- Tutorial and guide creation
- Code example updates
- Error message clarification

**Growth Path**: Documentation → Code examples → API design

### Testing Contributions
**Skills Needed**: Understanding of edge cases, systematic thinking
**Examples**:
- Unit test additions
- Integration test scenarios
- Performance test development
- Test infrastructure improvements

**Growth Path**: Testing → Bug fixing → Feature development

### Bug Fix Contributions
**Skills Needed**: Debugging, systematic problem solving
**Examples**:
- Content parsing edge cases
- Error handling improvements
- Performance regression fixes
- Compatibility issue resolution

**Growth Path**: Bug fixes → Feature enhancements → Architecture improvements

### Feature Development
**Skills Needed**: Design thinking, implementation skills
**Examples**:
- New content type support
- Additional output options
- Enhanced filtering capabilities
- Integration features

**Growth Path**: Feature development → API design → System architecture

## Learning Resources

### Codebase Understanding
1. **Read Tests**: Tests are excellent documentation
   ```bash
   # Understand how components work by reading tests
   find tests/ -name "*.py" -exec grep -l "YourComponent" {} \;
   ```

2. **Use Debugging Tools**
   ```python
   # Add debugging to understand code flow
   import logging
   logging.basicConfig(level=logging.DEBUG)

   from dnd5e.core.logging import get_logger
   logger = get_logger(__name__)
   logger.debug("Understanding this code path")
   ```

3. **Experiment with Components**
   ```python
   # Create small scripts to understand how things work
   from dnd5e.core.models.content import Spell

   spell_data = {"name": "Test", "level": 1, "school": "Evocation"}
   spell = Spell.from_json(spell_data, "TEST")
   print(f"Created spell: {spell.name}")
   ```

### External Learning
1. **Python Skills**
   - Synchronous programming patterns
   - Type hints and mypy
   - Pydantic for data validation
   - pytest for testing

2. **Domain Knowledge**
   - D&D 5e content structure
   - LaTeX document generation
   - JSON data processing
   - Git workflow and collaboration

3. **Tools and Libraries**
   - UV for dependency management
   - Ruff for code quality
   - Sphinx for documentation
   - GitHub for collaboration

## Common Challenges and Solutions

### Challenge: Understanding Complex Code
**Solution**: Start with tests and work backwards
1. Find tests for the component you're studying
2. Run tests to see expected behavior
3. Add print statements to understand execution flow
4. Read supporting documentation

### Challenge: Setting Up Development Environment
**Solution**: Follow setup guide exactly, ask for help
1. Use the exact commands in {doc}`../contributing/setup-guide`
2. Check system requirements carefully
3. Ask for help in GitHub discussions if stuck
4. Document any additional steps needed for your environment

### Challenge: Choosing What to Work On
**Solution**: Start small and build up expertise
1. Look for `good-first-issue` labels
2. Ask maintainers for suggestions
3. Focus on one area initially
4. Gradually take on more complex tasks

### Challenge: Code Quality Requirements
**Solution**: Use tools and learn incrementally
1. Run `uv run ruff check src/` frequently
2. Use `uv run mypy src/` to catch type errors
3. Add comprehensive tests for your changes
4. Ask for code review feedback early and often

### Challenge: Understanding System Architecture
**Solution**: Focus on data flow and interfaces
1. Trace data from input to output
2. Understand key abstractions (BaseContent, ContentType, etc.)
3. Read interface definitions (Protocol classes)
4. Study component interaction patterns

## Getting Help and Support

### Where to Ask Questions
1. **GitHub Discussions**: General questions and design discussions
2. **Pull Request Reviews**: Specific code questions and feedback
3. **Issue Comments**: Questions about specific bugs or features
4. **Documentation**: Check existing docs first

### How to Ask Good Questions
1. **Be Specific**: Include exact error messages and steps to reproduce
2. **Show Your Work**: Explain what you've tried already
3. **Provide Context**: Include relevant code and configuration
4. **Be Patient**: Maintainers are volunteers with other commitments

### Contributing to Project Health
1. **Report Bugs Clearly**: Include reproduction steps and environment info
2. **Suggest Improvements**: Propose specific, actionable enhancements
3. **Help Other Contributors**: Answer questions when you can
4. **Maintain Quality**: Follow coding standards and test requirements

## Success Metrics

### Month 1 Goals
- [ ] Successfully set up development environment
- [ ] Made first documentation or small code contribution
- [ ] Understand basic project structure and workflow
- [ ] Can run tests and quality checks locally

### Month 2 Goals
- [ ] Made meaningful code contribution (bug fix or small feature)
- [ ] Understand one component deeply
- [ ] Can write tests for your changes
- [ ] Comfortable with pull request process

### Month 3 Goals
- [ ] Made complex contribution requiring design decisions
- [ ] Helped review other contributors' work
- [ ] Identified and proposed system improvements
- [ ] Comfortable with most areas of the codebase

### Ongoing Goals
- [ ] Regular contributor with component expertise
- [ ] Mentor new contributors
- [ ] Participate in architectural discussions
- [ ] Maintain high code quality standards

Welcome to the 5e2pdf community! We're excited to see your contributions and help you grow as a developer.
