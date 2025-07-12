Testing Guide
=============

Comprehensive testing strategy for 5e2pdf development.

Testing Philosophy
------------------

5e2pdf follows a multi-layered testing approach:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Ensure acceptable performance characteristics

Test Structure
--------------

.. code-block:: text

   tests/
   ├── unit/                    # Fast, isolated tests
   │   ├── test_models.py       # Pydantic model tests
   │   ├── test_omnidexer.py    # Content loading tests
   │   ├── test_cli.py          # CLI command tests
   │   ├── test_renderers.py    # Rendering tests
   │   └── test_tag_resolver.py # Tag resolution tests
   ├── integration/             # Component interaction tests
   │   ├── test_cli_integration.py
   │   └── test_rendering_pipeline.py
   ├── fixtures/                # Test data and utilities
   │   ├── sample_data/         # Sample JSON files
   │   ├── expected_output/     # Expected LaTeX output
   │   └── conftest.py          # Shared fixtures
   └── performance/             # Performance benchmarks
       └── test_benchmarks.py

Running Tests
-------------

Basic Test Execution
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run with verbose output
   pytest -v

   # Run specific test file
   pytest tests/unit/test_models.py

   # Run specific test
   pytest tests/unit/test_models.py::test_spell_validation

Test Categories
~~~~~~~~~~~~~~

.. code-block:: bash

   # Run only unit tests (fast)
   pytest tests/unit/

   # Run only integration tests
   pytest tests/integration/

   # Run tests with specific markers
   pytest -m "not slow"

   # Run tests matching pattern
   pytest -k "spell"

Coverage Reporting
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run with coverage
   pytest --cov=src

   # Generate HTML coverage report
   pytest --cov=src --cov-report=html

   # Coverage with missing lines
   pytest --cov=src --cov-report=term-missing

Unit Testing Guidelines
----------------------

Model Testing
~~~~~~~~~~~~~

Test Pydantic models thoroughly:

.. code-block:: python

   class TestSpellModel:
       """Tests for Spell data model."""

       def test_valid_spell_creation(self):
           """Test creating a valid spell from JSON data."""
           data = {
               "name": "Magic Missile",
               "level": 1,
               "school": "V",
               "time": [{"number": 1, "unit": "action"}],
               "range": {"type": "point", "distance": {"type": "feet", "amount": 120}},
               "components": {"v": True, "s": True},
               "duration": [{"type": "instant"}],
               "entries": ["Three darts of magical force..."],
               "source": {"abbreviation": "PHB", "name": "Player's Handbook"}
           }
           
           spell = Spell.model_validate(data)
           
           assert spell.name == "Magic Missile"
           assert spell.level == 1
           assert spell.school == "V"

       def test_spell_validation_errors(self):
           """Test that invalid data raises validation errors."""
           invalid_data = {"name": "Invalid Spell"}  # Missing required fields
           
           with pytest.raises(ValidationError) as exc_info:
               Spell.model_validate(invalid_data)
           
           errors = exc_info.value.errors()
           required_fields = [error["loc"][0] for error in errors if error["type"] == "missing"]
           assert "level" in required_fields
           assert "school" in required_fields

       def test_spell_computed_properties(self):
           """Test computed property methods."""
           spell_data = {
               # ... complete spell data
           }
           spell = Spell.model_validate(spell_data)
           
           assert spell.get_level_text() == "1st level"
           assert "120 feet" in spell.get_range_text()
           assert "V, S" in spell.get_components_text()

CLI Testing
~~~~~~~~~~~

Test CLI commands with Typer's testing utilities:

.. code-block:: python

   from typer.testing import CliRunner
   from src.cli.main import app

   class TestCLICommands:
       """Tests for CLI command functionality."""

       def setup_method(self):
           """Set up test fixtures."""
           self.runner = CliRunner()

       def test_version_command(self):
           """Test version command output."""
           result = self.runner.invoke(app, ["version"])
           
           assert result.exit_code == 0
           assert "5e2pdf" in result.stdout
           assert "v2.0.0" in result.stdout

       def test_help_command(self):
           """Test help command output."""
           result = self.runner.invoke(app, ["--help"])
           
           assert result.exit_code == 0
           assert "5e2pdf" in result.stdout
           assert "Convert D&D 5e JSON data" in result.stdout

       @patch('src.cli.main.get_omnidexer')
       def test_list_content_command(self, mock_omnidexer):
           """Test list content command with mocked dependencies."""
           # Setup mock
           mock_omni = Mock()
           mock_omni.get_all_by_type.return_value = [
               Mock(name="Fireball", source=Mock(abbreviation="PHB"))
           ]
           mock_omnidexer.return_value = mock_omni
           
           result = self.runner.invoke(app, ["list", "content", "--type", "spell"])
           
           assert result.exit_code == 0
           assert "Fireball" in result.stdout

Renderer Testing
~~~~~~~~~~~~~~~

Test rendering components with expected output:

.. code-block:: python

   class TestLaTeXRenderer:
       """Tests for LaTeX rendering functionality."""

       def test_spell_rendering(self, sample_spell):
           """Test that spell renders to expected LaTeX."""
           renderer = SpellRenderer()
           context = RenderContext(title="Test Document")
           
           latex_output = renderer.render(sample_spell, context)
           
           assert "\\spell{" in latex_output
           assert sample_spell.name in latex_output
           assert str(sample_spell.level) in latex_output

       def test_document_structure(self, sample_content_items):
           """Test complete document rendering structure."""
           renderer = LaTeXDocumentRenderer()
           context = RenderContext(title="Test Document")
           
           document = renderer.render_document(sample_content_items, context)
           
           assert document.startswith("\\documentclass")
           assert "\\begin{document}" in document
           assert "\\end{document}" in document
           assert "Test Document" in document

Mocking and Fixtures
-------------------

Common Fixtures
~~~~~~~~~~~~~~

Create reusable test fixtures:

.. code-block:: python

   # tests/conftest.py
   import pytest
   from unittest.mock import Mock

   @pytest.fixture
   def sample_spell_data():
       """Sample spell data for testing."""
       return {
           "name": "Test Spell",
           "level": 1,
           "school": "V",
           "time": [{"number": 1, "unit": "action"}],
           "range": {"type": "point", "distance": {"type": "feet", "amount": 30}},
           "components": {"v": True, "s": False, "m": False},
           "duration": [{"type": "instant"}],
           "entries": ["A test spell for unit testing."],
           "source": {"abbreviation": "TEST", "name": "Test Source"}
       }

   @pytest.fixture
   def sample_spell(sample_spell_data):
       """Sample Spell model instance."""
       from src.core.models.spells import Spell
       return Spell.model_validate(sample_spell_data)

   @pytest.fixture
   def mock_omnidexer():
       """Mock omnidexer for testing."""
       omnidexer = Mock()
       omnidexer.find.return_value = None
       omnidexer.get_all_by_type.return_value = []
       omnidexer.get_statistics.return_value = {"total": 0}
       return omnidexer

   @pytest.fixture
   def temp_json_file(tmp_path, sample_spell_data):
       """Temporary JSON file for testing."""
       import json
       file_path = tmp_path / "test_spell.json"
       file_path.write_text(json.dumps({"spell": [sample_spell_data]}))
       return file_path

Mocking External Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from unittest.mock import patch, Mock, mock_open

   class TestFileOperations:
       """Test file I/O operations."""

       @patch('builtins.open', new_callable=mock_open, read_data='{"spell": []}')
       def test_json_loading(self, mock_file):
           """Test JSON file loading with mocked file system."""
           from src.core.loaders.json_loader import JSONLoader
           
           loader = JSONLoader()
           data = loader.load_file("fake_file.json")
           
           mock_file.assert_called_once_with("fake_file.json", 'r', encoding='utf-8')
           assert data == {"spell": []}

       @patch('subprocess.run')
       def test_latex_compilation(self, mock_subprocess):
           """Test LaTeX compilation with mocked subprocess."""
           mock_subprocess.return_value.returncode = 0
           
           from src.renderers.latex.document import compile_pdf
           result = compile_pdf("test.tex")
           
           mock_subprocess.assert_called_once()
           assert result.success is True

Integration Testing
------------------

Testing Component Interactions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class TestRenderingPipeline:
       """Integration tests for the complete rendering pipeline."""

       @pytest.mark.integration
       def test_complete_spell_conversion(self, temp_json_file):
           """Test complete conversion from JSON to LaTeX."""
           from src.core.loaders.omnidexer import Omnidexer
           from src.renderers.latex.document import LaTeXDocumentRenderer
           from src.renderers.base.context import RenderContext
           
           # Load content
           omnidexer = Omnidexer()
           asyncio.run(omnidexer.load_file(temp_json_file))
           
           # Get loaded content
           spells = omnidexer.get_all_by_type(ContentType.SPELL)
           assert len(spells) == 1
           
           # Render to LaTeX
           context = RenderContext(title="Test Document")
           renderer = LaTeXDocumentRenderer()
           latex_output = renderer.render_document(spells, context)
           
           # Verify output
           assert "\\documentclass" in latex_output
           assert spells[0].name in latex_output

       @pytest.mark.integration  
       def test_cli_to_output_workflow(self, temp_json_file, tmp_path):
           """Test complete CLI workflow."""
           from typer.testing import CliRunner
           from src.cli.main import app
           
           runner = CliRunner()
           output_file = tmp_path / "output.tex"
           
           # Run CLI command
           result = runner.invoke(app, [
               "quick", 
               str(temp_json_file),
               "--output", str(output_file)
           ])
           
           # Verify success
           assert result.exit_code == 0
           assert output_file.exists()
           
           # Verify output content
           content = output_file.read_text()
           assert "\\documentclass" in content

Performance Testing
------------------

Benchmarking Critical Paths
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import time
   import pytest

   class TestPerformance:
       """Performance tests for critical operations."""

       @pytest.mark.slow
       def test_omnidexer_loading_performance(self, large_dataset):
           """Test omnidexer loading performance with large dataset."""
           from src.core.loaders.omnidexer import Omnidexer
           
           start_time = time.time()
           
           omnidexer = Omnidexer()
           asyncio.run(omnidexer.load_all_data())
           
           load_time = time.time() - start_time
           
           # Performance assertion (adjust based on requirements)
           assert load_time < 10.0, f"Loading took {load_time:.2f}s, expected < 10s"

       @pytest.mark.slow
       def test_rendering_performance(self, large_content_set):
           """Test rendering performance with large content set."""
           from src.renderers.latex.document import LaTeXDocumentRenderer
           
           start_time = time.time()
           
           renderer = LaTeXDocumentRenderer()
           context = RenderContext(title="Performance Test")
           output = renderer.render_document(large_content_set, context)
           
           render_time = time.time() - start_time
           
           assert render_time < 5.0, f"Rendering took {render_time:.2f}s, expected < 5s"
           assert len(output) > 1000  # Ensure actual content was generated

Memory Usage Testing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import psutil
   import os

   def test_memory_usage_during_loading():
       """Test memory usage stays within acceptable bounds."""
       process = psutil.Process(os.getpid())
       initial_memory = process.memory_info().rss
       
       # Perform memory-intensive operation
       omnidexer = Omnidexer()
       asyncio.run(omnidexer.load_all_data())
       
       peak_memory = process.memory_info().rss
       memory_increase = peak_memory - initial_memory
       
       # Assert memory increase is reasonable (adjust threshold as needed)
       max_increase_mb = 500 * 1024 * 1024  # 500 MB
       assert memory_increase < max_increase_mb

Test Data Management
-------------------

Sample Data Creation
~~~~~~~~~~~~~~~~~~~

Create realistic test data:

.. code-block:: python

   # tests/fixtures/data_generators.py
   def generate_spell_data(name="Test Spell", level=1, **overrides):
       """Generate valid spell data for testing."""
       base_data = {
           "name": name,
           "level": level,
           "school": "V",
           "time": [{"number": 1, "unit": "action"}],
           "range": {"type": "point", "distance": {"type": "feet", "amount": 30}},
           "components": {"v": True, "s": False, "m": False},
           "duration": [{"type": "instant"}],
           "entries": [f"A test spell named {name}."],
           "source": {"abbreviation": "TEST", "name": "Test Source"}
       }
       base_data.update(overrides)
       return base_data

   def generate_adventure_data(name="Test Adventure"):
       """Generate valid adventure data for testing."""
       return {
           "name": name,
           "id": name.lower().replace(" ", "-"),
           "source": {"abbreviation": "TEST", "name": "Test Source"},
           "level": {"min": 1, "max": 5},
           "contents": [
               {
                   "name": "Introduction",
                   "entries": ["This is a test adventure."]
               }
           ]
       }

Continuous Integration
---------------------

GitHub Actions Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # .github/workflows/test.yml
   name: Tests

   on: [push, pull_request]

   jobs:
     test:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           python-version: [3.11, 3.12]

       steps:
       - uses: actions/checkout@v3
       
       - name: Set up Python ${{ matrix.python-version }}
         uses: actions/setup-python@v4
         with:
           python-version: ${{ matrix.python-version }}
       
       - name: Install dependencies
         run: |
           pip install -e ".[dev,test]"
       
       - name: Run linting
         run: |
           black --check src/ tests/
           ruff check src/ tests/
           mypy src/
       
       - name: Run tests
         run: |
           pytest --cov=src --cov-report=xml
       
       - name: Upload coverage
         uses: codecov/codecov-action@v3

Test Maintenance
---------------

Keeping Tests Current
~~~~~~~~~~~~~~~~~~~~

- **Review test coverage** regularly
- **Update tests** when changing APIs
- **Remove obsolete tests** for removed features
- **Add regression tests** for fixed bugs

Test Performance
~~~~~~~~~~~~~~~

- **Keep unit tests fast** (< 1 second each)
- **Use integration test markers** for slower tests
- **Mock external dependencies** in unit tests
- **Profile slow tests** and optimize

Documentation
~~~~~~~~~~~~

- **Document complex test scenarios**
- **Explain mock usage** and test data
- **Keep test names descriptive**
- **Add docstrings** for test classes and complex tests