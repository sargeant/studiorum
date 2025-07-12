Contributing to 5e2pdf
======================

We welcome contributions to 5e2pdf! This guide will help you get started.

Development Setup
----------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.11 or higher
- Git
- LaTeX distribution (for testing PDF generation)

Setting Up the Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/your-repo/5e2pdf.git
   cd 5e2pdf

   # Install in development mode with all dependencies
   pip install -e ".[dev,docs,test]"

   # Set up pre-commit hooks
   pre-commit install

   # Run tests to verify setup
   pytest

Project Structure
~~~~~~~~~~~~~~~~

.. code-block:: text

   5e2pdf/
   ├── src/
   │   ├── cli/                 # Command-line interface
   │   ├── core/                # Core functionality
   │   │   ├── models/          # Data models
   │   │   ├── loaders/         # Content loading
   │   │   └── indexer/         # Content indexing
   │   └── renderers/           # Output generation
   ├── tests/                   # Test suite
   ├── docs/                    # Documentation
   └── examples/                # Example content

Contributing Guidelines
----------------------

Code Style
~~~~~~~~~~

We use several tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Linting and import sorting  
- **mypy**: Type checking
- **pytest**: Testing

Run the full quality check:

.. code-block:: bash

   # Format code
   black src/ tests/

   # Lint and fix issues
   ruff check src/ tests/ --fix

   # Type checking
   mypy src/

   # Run tests
   pytest

Commit Messages
~~~~~~~~~~~~~~

Use conventional commit format:

.. code-block:: text

   type(scope): description

   [optional body]

   [optional footer]

Types:
- ``feat``: New feature
- ``fix``: Bug fix  
- ``docs``: Documentation changes
- ``style``: Code style changes
- ``refactor``: Code refactoring
- ``test``: Test changes
- ``chore``: Build/tooling changes

Examples:

.. code-block:: text

   feat(cli): add spell search command
   
   fix(renderer): handle missing spell components
   
   docs(api): update omnidexer documentation

Pull Request Process
~~~~~~~~~~~~~~~~~~~

1. **Fork the repository** and create a feature branch
2. **Make your changes** following the code style guidelines
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Submit a pull request** with a clear description

Pull request template:

.. code-block:: text

   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature  
   - [ ] Documentation update
   - [ ] Refactoring

   ## Testing
   - [ ] Tests pass locally
   - [ ] Added tests for new functionality
   - [ ] Manual testing completed

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated

Development Workflow
-------------------

Adding New Content Types
~~~~~~~~~~~~~~~~~~~~~~~

1. **Create the model** in ``src/core/models/``:

   .. code-block:: python

      # src/core/models/new_type.py
      from pydantic import BaseModel
      from .content import ContentItem

      class NewType(ContentItem):
          """Model for new content type."""
          special_field: str
          optional_field: Optional[int] = None

2. **Add to ContentType enum** in ``src/core/models/content.py``

3. **Implement rendering** in ``src/renderers/latex/content.py``

4. **Add CLI support** in appropriate command modules

5. **Write tests** in ``tests/unit/test_models.py``

Adding New CLI Commands
~~~~~~~~~~~~~~~~~~~~~~

1. **Create command module** in ``src/cli/commands/``:

   .. code-block:: python

      # src/cli/commands/new_command.py
      import typer
      
      app = typer.Typer(help="New command functionality")
      
      @app.command()
      def subcommand():
          """Subcommand description."""
          pass

2. **Register in main CLI** in ``src/cli/main.py``

3. **Add tests** in ``tests/unit/test_cli.py``

Adding New Output Formats
~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Create renderer** implementing ``BaseRenderer``

2. **Add format-specific templates**

3. **Update CLI** to support new format

4. **Add comprehensive tests**

Testing Guidelines
-----------------

Test Structure
~~~~~~~~~~~~~

.. code-block:: text

   tests/
   ├── unit/                   # Unit tests
   │   ├── test_models.py      # Model tests
   │   ├── test_cli.py         # CLI tests
   │   └── ...
   ├── integration/            # Integration tests
   ├── fixtures/               # Test data
   └── conftest.py            # Test configuration

Writing Tests
~~~~~~~~~~~~

Use descriptive test names and follow the AAA pattern:

.. code-block:: python

   def test_spell_model_validates_required_fields():
       """Test that Spell model validates required fields."""
       # Arrange
       invalid_data = {"name": "Test Spell"}  # Missing required fields
       
       # Act & Assert
       with pytest.raises(ValidationError):
           Spell.model_validate(invalid_data)

   def test_spell_model_creates_valid_instance():
       """Test that Spell model creates valid instance with complete data."""
       # Arrange
       valid_data = {
           "name": "Test Spell",
           "level": 1,
           "school": "V",
           # ... other required fields
       }
       
       # Act
       spell = Spell.model_validate(valid_data)
       
       # Assert
       assert spell.name == "Test Spell"
       assert spell.level == 1

Mock External Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~

Use pytest fixtures for consistent test data:

.. code-block:: python

   @pytest.fixture
   def mock_omnidexer():
       """Mock omnidexer for testing."""
       omnidexer = Mock()
       omnidexer.find.return_value = Mock()
       return omnidexer

   def test_cli_command_with_mock(mock_omnidexer):
       """Test CLI command with mocked dependencies."""
       with patch('src.cli.main.get_omnidexer', return_value=mock_omnidexer):
           # Test CLI functionality
           pass

Documentation Guidelines
-----------------------

Docstring Style
~~~~~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def complex_function(param1: str, param2: int = 0) -> Dict[str, Any]:
       """Brief description of the function.
       
       Longer description if needed, explaining the purpose,
       behavior, and any important details.
       
       Args:
           param1: Description of the first parameter.
           param2: Description of the second parameter with default.
           
       Returns:
           Dictionary containing the results with keys:
           - 'result': The main result
           - 'metadata': Additional information
           
       Raises:
           ValueError: If param1 is empty.
           TypeError: If param2 is not an integer.
           
       Example:
           >>> result = complex_function("test", 42)
           >>> print(result['result'])
           'processed test'
       """

API Documentation
~~~~~~~~~~~~~~~~

All public APIs should have comprehensive docstrings including:

- Purpose and behavior
- Parameter descriptions with types
- Return value descriptions
- Exception information
- Usage examples

Update the Sphinx documentation when adding new modules or changing APIs.

User Documentation
~~~~~~~~~~~~~~~~~

When adding new features:

1. **Update CLI reference** with new commands/options
2. **Add examples** showing practical usage
3. **Update quickstart guide** if it affects basic workflows
4. **Add troubleshooting info** for common issues

Issue Reporting
--------------

Bug Reports
~~~~~~~~~~

Use the bug report template:

.. code-block:: text

   **Describe the bug**
   Clear description of the problem

   **To Reproduce**
   Steps to reproduce:
   1. Run command '...'
   2. See error

   **Expected behavior**
   What you expected to happen

   **Environment:**
   - OS: [e.g. macOS 12.0]
   - Python version: [e.g. 3.11.0]
   - 5e2pdf version: [e.g. 2.0.0]

   **Additional context**
   - Log output
   - Sample files (if applicable)

Feature Requests
~~~~~~~~~~~~~~~

Use the feature request template:

.. code-block:: text

   **Is your feature request related to a problem?**
   Description of the problem

   **Describe the solution you'd like**
   Clear description of desired functionality

   **Describe alternatives you've considered**
   Other approaches you've thought about

   **Additional context**
   Examples, mockups, or related issues

Community Guidelines
-------------------

Code of Conduct
~~~~~~~~~~~~~~

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers get started
- Follow the project's technical standards

Communication
~~~~~~~~~~~~

- Use GitHub issues for bug reports and feature requests
- Use GitHub discussions for questions and general discussion
- Keep communication public when possible
- Be patient with response times

Recognition
~~~~~~~~~~

Contributors are recognized in:

- CONTRIBUTORS.md file
- Release notes for significant contributions
- Git commit history

Getting Help
-----------

If you need help contributing:

1. **Check the documentation** for existing answers
2. **Search GitHub issues** for similar problems
3. **Join GitHub discussions** for community help
4. **Open an issue** with the "question" label

Development Resources
--------------------

Useful Links
~~~~~~~~~~~

- `Python Type Hints Guide <https://docs.python.org/3/library/typing.html>`_
- `Pydantic Documentation <https://docs.pydantic.dev/>`_
- `Typer Documentation <https://typer.tiangolo.com/>`_
- `pytest Documentation <https://docs.pytest.org/>`_

Learning Resources
~~~~~~~~~~~~~~~~~

- LaTeX documentation for understanding output format
- 5etools data structure for understanding input format
- D&D 5th edition rules for content validation