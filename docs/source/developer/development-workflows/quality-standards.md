# Quality Standards

Code quality requirements and validation processes for the 5e2pdf project.

## Code Quality Framework

### Type Safety Requirements

#### Full mypy Compliance
All code in `src/` and `tests/` must pass mypy type checking without errors:

```bash
# Must pass without errors
uv run mypy src/
uv run mypy tests/
```

#### Type Annotation Standards
```python
# Good: Complete type annotations
def process_content(
    content: BaseContent,
    config: Config
) -> ProcessingResult:
    """Process content with given configuration."""
    pass

# Avoid: Missing or partial annotations
def process_content(content, config):
    pass
```

#### Generic Type Usage
```python
from typing import TypeVar, Generic

T = TypeVar('T', bound=BaseContent)

class ContentProcessor(Generic[T]):
    def process(self, content: T) -> ProcessedContent[T]:
        return ProcessedContent(content)
```

### Code Style Standards

#### Ruff Configuration
The project uses ruff for linting and formatting with these key rules:

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
]
```

#### Formatting Requirements
```bash
# Auto-format code
uv run ruff format src/ tests/

# Check formatting
uv run ruff check src/ tests/
```

#### Import Organization
```python
# Standard library imports
import asyncio
from pathlib import Path
from typing import Any, Optional

# Third-party imports
import click
from pydantic import BaseModel, Field

# Local imports
from dnd5e.core.models import BaseContent
from dnd5e.core.config import Config
```

### Documentation Standards

#### Docstring Requirements
All public classes, methods, and functions must have docstrings:

```python
class ContentProcessor:
    """Process D&D content for rendering.

    This class handles the transformation of parsed content objects
    into render-ready formats with appropriate validation and
    error handling.

    Attributes:
        config: Processing configuration options
        cache: LRU cache for processed content
    """

    def __init__(self, config: Config) -> None:
        """Initialize processor with configuration.

        Args:
            config: Configuration object containing processing options

        Raises:
            ConfigError: If configuration is invalid
        """
        pass

    async def process(self, content: BaseContent) -> ProcessedContent:
        """Process content object for rendering.

        Args:
            content: Content object to process

        Returns:
            Processed content ready for rendering

        Raises:
            ProcessingError: If content cannot be processed
            ValidationError: If content fails validation
        """
        pass
```

#### Code Comments
Use comments sparingly for complex business logic:

```python
# Calculate spell save DC using standard D&D 5e formula
# DC = 8 + proficiency bonus + ability modifier
save_dc = 8 + proficiency_bonus + ability_modifier

# Use LRU cache to avoid reprocessing identical content
# TTL of 300 seconds balances memory usage with performance
@lru_cache(maxsize=128, ttl=300)
def process_spell_description(text: str) -> ProcessedText:
    pass
```

## Testing Standards

### Test Coverage Requirements

#### Minimum Coverage Thresholds
- **Overall**: 85% line coverage
- **Core Models**: 95% line coverage
- **API Interfaces**: 90% line coverage
- **Utilities**: 80% line coverage

#### Coverage Measurement
```bash
# Run tests with coverage
uv run pytest --cov=src/dnd5e --cov-report=html

# Check coverage thresholds
uv run pytest --cov=src/dnd5e --cov-fail-under=85
```

### Test Organization Standards

#### Test Structure
```
tests/
├── unit/                    # Fast, isolated unit tests
│   ├── models/             # Model validation and behavior
│   ├── parsers/            # Parser logic and edge cases
│   ├── utils/              # Utility function tests
│   └── conftest.py         # Shared fixtures
├── integration/            # Component interaction tests
│   ├── loading/            # End-to-end loading workflows
│   ├── rendering/          # Full rendering pipelines
│   └── conftest.py         # Integration fixtures
└── performance/            # Performance and regression tests
    ├── benchmarks/         # Performance benchmarks
    └── memory/             # Memory usage tests
```

#### Test Naming Conventions
```python
class TestSpellParser:
    """Test class names: Test + ClassUnderTest"""

    def test_parse_valid_spell_data_returns_spell_object(self):
        """Test methods: test_method_scenario_expected_result"""
        pass

    def test_parse_invalid_level_raises_validation_error(self):
        """Clear description of error conditions"""
        pass

    def test_parse_missing_required_field_raises_appropriate_error(self):
        """Specific error scenarios"""
        pass
```

#### Fixture Guidelines
```python
@pytest.fixture
def sample_spell_data() -> dict[str, Any]:
    """Provide realistic test data.

    Use production-like data structures to catch
    integration issues early.
    """
    return {
        "name": "Fireball",
        "level": 3,
        "school": "Evocation",
        "entries": [
            "A bright streak flashes from your pointing finger..."
        ]
    }

@pytest.fixture
def configured_parser(sample_config: Config) -> SpellParser:
    """Provide properly configured instances."""
    return SpellParser(config=sample_config)
```

### Test Quality Standards

#### Assertion Clarity
```python
# Good: Specific assertions with clear messages
def test_spell_level_validation():
    with pytest.raises(ValidationError) as exc_info:
        Spell.from_json({"name": "Test", "level": -1}, "TEST")

    assert "level must be between 0 and 9" in str(exc_info.value)
    assert exc_info.value.field_name == "level"

# Avoid: Vague assertions
def test_spell_validation():
    with pytest.raises(Exception):
        Spell.from_json(bad_data, "TEST")
```

#### Test Independence
```python
# Good: Each test is independent
class TestContentLoader:
    def test_load_spells_returns_spell_list(self, mock_data_source):
        loader = ContentLoader(mock_data_source)
        spells = loader.load_spells()
        assert len(spells) == 3

    def test_load_with_network_error_raises_loading_error(self, failing_data_source):
        loader = ContentLoader(failing_data_source)
        with pytest.raises(LoadingError):
            loader.load_spells()

# Avoid: Tests that depend on each other
class TestContentLoader:
    def test_load_spells(self):
        self.spells = loader.load_spells()  # State shared between tests
        assert len(self.spells) == 3

    def test_process_spells(self):
        processed = loader.process(self.spells)  # Depends on previous test
        assert processed
```

## Performance Standards

### Performance Requirements

#### Response Time Targets
- **Content Loading**: < 5 seconds for full dataset
- **Single Content Parsing**: < 100ms per item
- **PDF Generation**: < 30 seconds for typical book
- **Memory Usage**: < 500MB peak for full dataset

#### Performance Testing
```python
import time
import pytest

def test_spell_parsing_performance():
    """Ensure parsing performance doesn't regress."""
    large_spell_dataset = create_spell_dataset(1000)

    start_time = time.perf_counter()
    parsed_spells = parser.parse_spells(large_spell_dataset)
    duration = time.perf_counter() - start_time

    assert duration < 5.0  # 5 second threshold
    assert len(parsed_spells) == 1000

@pytest.mark.performance
def test_memory_usage_during_loading():
    """Monitor memory usage patterns."""
    import tracemalloc

    tracemalloc.start()

    omnidexer = Omnidexer()
    await omnidexer.load_all_data()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Convert to MB
    peak_mb = peak / 1024 / 1024

    assert peak_mb < 500  # 500MB threshold
```

### Code Efficiency Guidelines

#### Prefer Async for I/O Operations
```python
# Good: Async for I/O bound operations
async def load_content_files(file_paths: list[Path]) -> list[dict]:
    """Load multiple files concurrently."""
    async with aiofiles.open() as file:
        tasks = [load_single_file(path) for path in file_paths]
        return await asyncio.gather(*tasks)

# Avoid: Synchronous I/O in async context
async def load_content_files_slow(file_paths: list[Path]) -> list[dict]:
    results = []
    for path in file_paths:
        with open(path) as file:  # Blocking I/O
            results.append(json.load(file))
    return results
```

#### Use Appropriate Data Structures
```python
# Good: Use sets for membership testing
valid_schools = {"Abjuration", "Conjuration", "Divination", "Enchantment"}

def is_valid_school(school: str) -> bool:
    return school in valid_schools  # O(1) lookup

# Avoid: Lists for frequent lookups
valid_schools_list = ["Abjuration", "Conjuration", "Divination", "Enchantment"]

def is_valid_school_slow(school: str) -> bool:
    return school in valid_schools_list  # O(n) lookup
```

## Security Standards

### Input Validation
```python
from pydantic import BaseModel, Field, validator

class SpellInput(BaseModel):
    """Validate all external input."""
    name: str = Field(min_length=1, max_length=100)
    level: int = Field(ge=0, le=9)
    description: str = Field(max_length=10000)

    @validator('name')
    def validate_name(cls, v):
        # Prevent injection attacks
        if any(char in v for char in ['<', '>', '{', '}']):
            raise ValueError("Invalid characters in spell name")
        return v.strip()
```

### Dependency Security
```bash
# Regular security audits
uv run pip-audit

# Keep dependencies updated
uv sync --upgrade
```

### LaTeX Security
```python
def escape_latex_content(text: str) -> str:
    """Escape LaTeX special characters to prevent injection."""
    latex_special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '^': r'\textasciicircum{}',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '\\': r'\textbackslash{}'
    }

    for char, escape in latex_special_chars.items():
        text = text.replace(char, escape)

    return text
```

## Quality Enforcement

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: Ruff linting
        entry: uv run ruff check
        language: system
        files: ^(src|tests)/.*\.py$

      - id: ruff-format
        name: Ruff formatting
        entry: uv run ruff format
        language: system
        files: ^(src|tests)/.*\.py$

      - id: mypy
        name: Type checking
        entry: uv run mypy
        language: system
        files: ^src/.*\.py$

      - id: pytest-fast
        name: Fast tests
        entry: uv run pytest tests/unit/
        language: system
```

### CI/CD Quality Gates
```yaml
# GitHub Actions quality checks
name: Quality Checks
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Type checking
        run: uv run mypy src/

      - name: Linting
        run: uv run ruff check src/ tests/

      - name: Format checking
        run: uv run ruff format --check src/ tests/

      - name: Test suite
        run: uv run pytest --cov=src/dnd5e --cov-fail-under=85

      - name: Security audit
        run: uv run pip-audit
```

### Quality Metrics Dashboard
Track and monitor key quality indicators:

- **Code Coverage**: Minimum 85% maintained
- **Type Coverage**: 100% mypy compliance
- **Performance**: Benchmarks within thresholds
- **Security**: No known vulnerabilities
- **Documentation**: All public APIs documented

These quality standards ensure the 5e2pdf codebase remains maintainable, reliable, and secure as it grows and evolves.
