# Data Modeling Patterns Catalog

**Version**: 1.1
**Date**: 2025-08-25
**Purpose**: Comprehensive catalog of established patterns from P1-P6 migration analysis

All Pydantic examples use the modern `model_config = ConfigDict()` syntax.

## Pattern Categories

### 1. Performance-Critical Infrastructure (Dataclass)

#### Core Statistics and Metrics

**Pattern**: High-frequency instantiation types with minimal validation

```python
@dataclass(frozen=True, slots=True)
class ProcessingStatistics:
    """Performance-critical statistics tracking."""
    total_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    duration_ms: float = 0.0
    memory_used_mb: float = 0.0

    def __post_init__(self) -> None:
        """Minimal validation - performance critical."""
        if self.total_processed < 0:
            raise ValueError("Total processed must be non-negative")

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_processed == 0:
            return 0.0
        return (self.success_count / self.total_processed) * 100

    def merge(self, other: 'ProcessingStatistics') -> 'ProcessingStatistics':
        """Merge two statistics objects."""
        return ProcessingStatistics(
            total_processed=self.total_processed + other.total_processed,
            success_count=self.success_count + other.success_count,
            error_count=self.error_count + other.error_count,
            duration_ms=self.duration_ms + other.duration_ms,
            memory_used_mb=max(self.memory_used_mb, other.memory_used_mb)
        )
```

**When to Use**:
- Hot path execution (>1000 instantiations/second)
- System metrics and performance tracking
- Cache statistics and monitoring
- Internal coordination objects

**Key Features**:
- `slots=True` for memory optimization
- `frozen=True` for immutability and hashability
- Minimal `__post_init__` validation
- Helper methods for common operations

#### Result and Error Types

**Pattern**: Core infrastructure for success/error handling

```python
@dataclass(frozen=True, slots=True)
class ErrorContext:
    """Error context information for debugging."""
    operation: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    stack_trace: str | None = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.operation.strip():
            raise ValueError("Operation name cannot be empty")

    def with_metadata(self, **kwargs: Any) -> 'ErrorContext':
        """Add metadata to error context."""
        new_metadata = {**self.metadata, **kwargs}
        return ErrorContext(
            operation=self.operation,
            timestamp=self.timestamp,
            metadata=new_metadata,
            stack_trace=self.stack_trace
        )

    def format_for_logging(self) -> str:
        """Format error context for logging."""
        return f"Operation: {self.operation} at {self.timestamp}"
```

#### Cache and Index Types

**Pattern**: High-performance lookup structures

```python
@dataclass(frozen=True, slots=True)
class IndexEntry:
    """Content index entry for fast lookups."""
    content_id: str
    content_type: str
    title: str
    source_page: int | None = None
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate index entry."""
        if not self.content_id or not self.content_type:
            raise ValueError("Content ID and type are required")

    def matches_query(self, query: str) -> bool:
        """Check if entry matches search query."""
        query_lower = query.lower()
        return (
            query_lower in self.title.lower() or
            query_lower in self.content_id.lower() or
            any(query_lower in tag.lower() for tag in self.tags)
        )

@dataclass(frozen=True, slots=True)
class CacheKey:
    """High-performance cache key."""
    namespace: str
    key: str
    version: str = "v1"

    def __str__(self) -> str:
        return f"{self.namespace}:{self.key}:{self.version}"

    def __hash__(self) -> int:
        return hash((self.namespace, self.key, self.version))
```

### 2. Business Logic with Validation (Pydantic)

#### MCP Tool Models

**Pattern**: External API integration with comprehensive validation

```python
class EncounterToolRequest(BaseModel):
    """MCP tool request for encounter management."""

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True
    )

    encounter_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the encounter"
    )
    party_level: int = Field(
        ...,
        ge=1,
        le=20,
        description="Average party level (1-20)"
    )
    party_size: int = Field(
        ...,
        ge=1,
        le=8,
        description="Number of players (1-8)"
    )
    difficulty: DifficultyLevel = Field(
        ...,
        description="Encounter difficulty level"
    )
    environment: EnvironmentType = Field(
        default=EnvironmentType.DUNGEON,
        description="Encounter environment"
    )
    special_requirements: list[str] = Field(
        default_factory=list,
        description="Special encounter requirements"
    )

    @field_validator('encounter_name')
    @classmethod
    def validate_encounter_name(cls, v: str) -> str:
        """Normalize and validate encounter name."""
        normalized = v.strip()
        if not normalized:
            raise ValueError("Encounter name cannot be empty")

        # Check for reserved names
        reserved = ['default', 'template', 'example']
        if normalized.lower() in reserved:
            raise ValueError(f"'{normalized}' is a reserved encounter name")

        return normalized

    @field_validator('special_requirements')
    @classmethod
    def validate_requirements(cls, v: list[str]) -> list[str]:
        """Validate and normalize special requirements."""
        return [req.strip() for req in v if req.strip()]

    @model_validator(mode='after')
    def validate_encounter_balance(self) -> Self:
        """Validate encounter balance rules."""
        # Legendary encounters require higher party levels
        if 'legendary' in self.special_requirements:
            if self.party_level < 5:
                raise ValueError("Legendary encounters require party level 5+")
            if self.difficulty == DifficultyLevel.EASY:
                raise ValueError("Legendary encounters cannot be Easy difficulty")

        # Large parties can handle higher difficulty
        if self.party_size >= 6 and self.difficulty == DifficultyLevel.DEADLY:
            # This is actually manageable for large parties
            pass
        elif self.party_size <= 2 and self.difficulty == DifficultyLevel.DEADLY:
            raise ValueError("Deadly encounters not recommended for small parties")

        return self
```

#### Configuration Classes

**Pattern**: System configuration with environment integration

```python
class LaTeXRenderingConfig(BaseModel):
    """LaTeX rendering service configuration."""

    model_config = ConfigDict(
        env_prefix='LATEX_',
        case_sensitive=False,
        validate_default=True,
        populate_by_name=True
    )

    compiler: Literal['pdflatex', 'xelatex', 'lualatex'] = Field(
        default='pdflatex',
        description="LaTeX compiler to use"
    )
    max_compile_time: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Maximum compilation time in seconds"
    )
    max_runs: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum compilation runs for cross-references"
    )
    output_directory: Path = Field(
        default=Path('./output'),
        description="Output directory for generated PDFs"
    )
    temp_directory: Path = Field(
        default=Path('./temp'),
        description="Temporary directory for compilation"
    )
    enable_shell_escape: bool = Field(
        default=False,
        description="Enable shell escape (security risk)"
    )
    font_directories: list[Path] = Field(
        default_factory=list,
        description="Additional font directories"
    )

    @field_validator('output_directory', 'temp_directory')
    @classmethod
    def ensure_directory_exists(cls, v: Path) -> Path:
        """Ensure directory exists and is writable."""
        v.mkdir(parents=True, exist_ok=True)

        # Test write permissions
        test_file = v / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
        except OSError as e:
            raise ValueError(f"Directory {v} is not writable: {e}")

        return v.resolve()

    @field_validator('font_directories')
    @classmethod
    def validate_font_directories(cls, v: list[Path]) -> list[Path]:
        """Validate font directories exist and are readable."""
        validated = []
        for path in v:
            if not path.exists():
                raise ValueError(f"Font directory does not exist: {path}")
            if not path.is_dir():
                raise ValueError(f"Font path is not a directory: {path}")
            validated.append(path.resolve())
        return validated

    @model_validator(mode='after')
    def validate_security_settings(self) -> Self:
        """Validate security-related configuration."""
        if self.enable_shell_escape:
            # Log security warning
            import logging
            logging.warning(
                "LaTeX shell escape enabled - this is a security risk in production"
            )

        return self

    def get_compiler_args(self) -> list[str]:
        """Get compiler-specific arguments."""
        base_args = ['-interaction=nonstopmode', '-halt-on-error']

        if self.compiler == 'pdflatex':
            base_args.extend(['-enc'])
        elif self.compiler == 'xelatex':
            base_args.extend(['-no-pdf'])

        if self.enable_shell_escape:
            base_args.append('-shell-escape')

        return base_args
```

#### API Request/Response Models

**Pattern**: External API boundaries with strict validation

```python
class ContentSearchRequest(BaseModel):
    """API request for content search operations."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string"
    )
    content_types: list[ContentType] = Field(
        default_factory=lambda: list(ContentType),
        description="Content types to include in search"
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of results to return"
    )
    include_metadata: bool = Field(
        default=False,
        description="Include additional metadata in results"
    )
    sort_by: SortOption = Field(
        default=SortOption.RELEVANCE,
        description="Sort order for results"
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional search filters"
    )

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and normalize search query."""
        # Remove potentially dangerous patterns
        dangerous_patterns = ['<script', 'javascript:', 'data:']
        query_lower = v.lower()

        for pattern in dangerous_patterns:
            if pattern in query_lower:
                raise ValueError(f"Query contains unsafe pattern: {pattern}")

        return v.strip()

    @field_validator('filters')
    @classmethod
    def validate_filters(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate search filters."""
        allowed_filters = {
            'min_level', 'max_level', 'source_book',
            'page_range', 'tags', 'difficulty'
        }

        invalid_filters = set(v.keys()) - allowed_filters
        if invalid_filters:
            raise ValueError(f"Invalid filters: {invalid_filters}")

        return v

class ContentSearchResponse(BaseModel):
    """API response for content search operations."""

    success: bool = Field(..., description="Whether the search succeeded")
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., ge=0, description="Total number of matches")
    results: list[ContentSearchResult] = Field(
        default_factory=list,
        description="Search results"
    )
    facets: dict[str, list[FacetValue]] = Field(
        default_factory=dict,
        description="Search facets for refinement"
    )
    search_time_ms: float = Field(..., ge=0, description="Search execution time")
    error_message: str | None = Field(None, description="Error message if failed")

    @model_validator(mode='after')
    def validate_response_consistency(self) -> Self:
        """Validate response data consistency."""
        if self.success:
            if self.error_message:
                raise ValueError("Success response cannot have error message")
            if self.total_results < len(self.results):
                raise ValueError("Total results cannot be less than returned results")
        else:
            if not self.error_message:
                raise ValueError("Failed response must have error message")
            if self.results:
                raise ValueError("Failed response cannot have results")

        return self
```

### 3. Internal Value Objects (Dataclass)

#### Coordinate and Geometric Types

**Pattern**: Mathematical value objects with computed properties

```python
@dataclass(frozen=True, slots=True)
class Point2D:
    """2D point for layout calculations."""
    x: float
    y: float

    def distance_to(self, other: 'Point2D') -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def midpoint(self, other: 'Point2D') -> 'Point2D':
        """Calculate midpoint between two points."""
        return Point2D(
            x=(self.x + other.x) / 2,
            y=(self.y + other.y) / 2
        )

    def translate(self, dx: float, dy: float) -> 'Point2D':
        """Translate point by given offsets."""
        return Point2D(self.x + dx, self.y + dy)

@dataclass(frozen=True, slots=True)
class Rectangle:
    """Rectangle for layout and collision detection."""
    top_left: Point2D
    width: float
    height: float

    def __post_init__(self) -> None:
        """Validate rectangle dimensions."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Rectangle dimensions must be positive")

    @property
    def bottom_right(self) -> Point2D:
        """Bottom-right corner of rectangle."""
        return Point2D(
            self.top_left.x + self.width,
            self.top_left.y + self.height
        )

    @property
    def center(self) -> Point2D:
        """Center point of rectangle."""
        return Point2D(
            self.top_left.x + self.width / 2,
            self.top_left.y + self.height / 2
        )

    @property
    def area(self) -> float:
        """Rectangle area."""
        return self.width * self.height

    def contains(self, point: Point2D) -> bool:
        """Check if point is inside rectangle."""
        return (
            self.top_left.x <= point.x <= self.top_left.x + self.width and
            self.top_left.y <= point.y <= self.top_left.y + self.height
        )

    def intersects(self, other: 'Rectangle') -> bool:
        """Check if this rectangle intersects with another."""
        return not (
            self.top_left.x + self.width < other.top_left.x or
            other.top_left.x + other.width < self.top_left.x or
            self.top_left.y + self.height < other.top_left.y or
            other.top_left.y + other.height < self.top_left.y
        )
```

#### Resource and Reference Types

**Pattern**: Resource identification and tracking

```python
@dataclass(frozen=True, slots=True)
class ContentReference:
    """Reference to content in the 5e system."""
    source_book: str
    content_type: str
    content_id: str
    page_number: int | None = None

    def __post_init__(self) -> None:
        """Validate content reference."""
        if not all([self.source_book, self.content_type, self.content_id]):
            raise ValueError("Source book, type, and ID are required")
        if self.page_number is not None and self.page_number < 1:
            raise ValueError("Page number must be positive")

    @property
    def full_reference(self) -> str:
        """Full reference string for citations."""
        base = f"{self.source_book}: {self.content_type}:{self.content_id}"
        if self.page_number:
            base += f" (p. {self.page_number})"
        return base

    def matches(self, source: str | None = None,
                content_type: str | None = None,
                content_id: str | None = None) -> bool:
        """Check if reference matches given criteria."""
        return (
            (source is None or self.source_book == source) and
            (content_type is None or self.content_type == content_type) and
            (content_id is None or self.content_id == content_id)
        )

@dataclass(frozen=True, slots=True)
class ResourceHandle:
    """Handle for managed resources with lifecycle tracking."""
    resource_id: str
    resource_type: str
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate resource handle."""
        if not self.resource_id or not self.resource_type:
            raise ValueError("Resource ID and type are required")

    @property
    def age_seconds(self) -> float:
        """Age of resource in seconds."""
        return time.time() - self.created_at

    def with_metadata(self, **kwargs: Any) -> 'ResourceHandle':
        """Create new handle with additional metadata."""
        new_metadata = {**self.metadata, **kwargs}
        return ResourceHandle(
            resource_id=self.resource_id,
            resource_type=self.resource_type,
            created_at=self.created_at,
            metadata=new_metadata
        )
```

### 4. Complex Business Rules (Pydantic)

#### State Management with Validation

**Pattern**: Complex state objects with business rule validation

```python
class CombatState(BaseModel):
    """Combat encounter state with comprehensive validation."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True
    )

    encounter_id: str = Field(..., min_length=1, description="Unique encounter ID")
    round_number: int = Field(default=1, ge=1, le=100, description="Current round")
    initiative_order: list[str] = Field(
        default_factory=list,
        description="Initiative order (participant IDs)"
    )
    current_participant: str | None = Field(
        None,
        description="Currently active participant ID"
    )
    participants: dict[str, ParticipantState] = Field(
        default_factory=dict,
        description="Participant states by ID"
    )
    effects: list[ActiveEffect] = Field(
        default_factory=list,
        description="Active effects in combat"
    )
    combat_log: list[CombatLogEntry] = Field(
        default_factory=list,
        description="Combat event log"
    )
    is_active: bool = Field(default=True, description="Whether combat is active")

    @field_validator('current_participant')
    @classmethod
    def validate_current_participant(cls, v: str | None,
                                   info: ValidationInfo) -> str | None:
        """Validate current participant exists in initiative order."""
        if v is None:
            return v

        # Access other fields through info.data
        initiative_order = info.data.get('initiative_order', [])
        if v not in initiative_order:
            raise ValueError(
                f"Current participant '{v}' not in initiative order"
            )
        return v

    @field_validator('participants')
    @classmethod
    def validate_participants_match_initiative(
        cls,
        v: dict[str, ParticipantState],
        info: ValidationInfo
    ) -> dict[str, ParticipantState]:
        """Validate participants match initiative order."""
        initiative_order = info.data.get('initiative_order', [])

        # All participants in initiative must have state
        missing_participants = set(initiative_order) - set(v.keys())
        if missing_participants:
            raise ValueError(
                f"Missing participant states: {missing_participants}"
            )

        return v

    @model_validator(mode='after')
    def validate_combat_state_consistency(self) -> Self:
        """Validate overall combat state consistency."""
        # Combat must have at least 2 participants to be active
        if self.is_active and len(self.participants) < 2:
            raise ValueError("Active combat requires at least 2 participants")

        # If combat is inactive, current participant should be None
        if not self.is_active and self.current_participant is not None:
            raise ValueError("Inactive combat cannot have current participant")

        # Validate effects are still valid
        valid_effects = []
        for effect in self.effects:
            if effect.remaining_rounds > 0:
                if effect.target_id not in self.participants:
                    raise ValueError(
                        f"Effect target '{effect.target_id}' not in participants"
                    )
                valid_effects.append(effect)

        # Update effects list (removing expired effects)
        object.__setattr__(self, 'effects', valid_effects)

        return self

    def advance_initiative(self) -> 'CombatState':
        """Advance to next participant in initiative order."""
        if not self.is_active or not self.initiative_order:
            return self

        if self.current_participant is None:
            next_participant = self.initiative_order[0]
        else:
            current_index = self.initiative_order.index(self.current_participant)
            next_index = (current_index + 1) % len(self.initiative_order)
            next_participant = self.initiative_order[next_index]

            # If we're back to the first participant, increment round
            if next_index == 0:
                return self.model_copy(
                    update={
                        'current_participant': next_participant,
                        'round_number': self.round_number + 1
                    }
                )

        return self.model_copy(update={'current_participant': next_participant})

    def add_participant(self, participant_id: str,
                       participant_state: ParticipantState,
                       initiative: int) -> 'CombatState':
        """Add new participant to combat."""
        if participant_id in self.participants:
            raise ValueError(f"Participant '{participant_id}' already in combat")

        # Insert in initiative order based on initiative value
        new_order = self.initiative_order.copy()
        inserted = False

        for i, existing_id in enumerate(self.initiative_order):
            existing_init = self.participants[existing_id].initiative
            if initiative > existing_init:
                new_order.insert(i, participant_id)
                inserted = True
                break

        if not inserted:
            new_order.append(participant_id)

        # Update participant state with initiative
        updated_state = participant_state.model_copy(
            update={'initiative': initiative}
        )

        new_participants = {**self.participants, participant_id: updated_state}

        return self.model_copy(update={
            'initiative_order': new_order,
            'participants': new_participants
        })
```

### 5. Mixed Patterns

#### Configuration with Performance Optimization

**Pattern**: Configuration classes that cache computed values

```python
class OptimizedRenderingConfig(BaseModel):
    """Rendering configuration with performance optimizations."""

    model_config = ConfigDict(
        extra="forbid",
        validate_default=True,
        frozen=True  # Enable caching since config is immutable
    )

    # Core configuration
    template_directory: Path = Field(..., description="Template directory")
    asset_directory: Path = Field(..., description="Asset directory")
    output_format: Literal['pdf', 'html', 'tex'] = Field(
        default='pdf',
        description="Output format"
    )

    # Performance settings
    enable_caching: bool = Field(default=True, description="Enable template caching")
    max_cache_size: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Maximum cache entries"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Cache TTL in seconds"
    )

    # Computed properties (cached)
    _computed_paths: dict[str, Path] = PrivateAttr(default_factory=dict)
    _template_cache: dict[str, Any] = PrivateAttr(default_factory=dict)

    @field_validator('template_directory', 'asset_directory')
    @classmethod
    def validate_directory_exists(cls, v: Path) -> Path:
        """Validate directory exists and is readable."""
        if not v.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return v.resolve()

    @property
    def template_search_paths(self) -> list[Path]:
        """Get template search paths with caching."""
        cache_key = 'template_search_paths'

        if cache_key not in self._computed_paths:
            paths = [
                self.template_directory,
                self.template_directory / 'common',
                self.template_directory / self.output_format
            ]
            # Filter to existing directories
            existing_paths = [p for p in paths if p.exists() and p.is_dir()]
            self._computed_paths[cache_key] = existing_paths

        return self._computed_paths[cache_key]

    @property
    def cache_config(self) -> dict[str, Any]:
        """Get cache configuration as dataclass for performance."""
        # Return high-performance dataclass for cache operations
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True)
        class CacheConfig:
            enabled: bool
            max_size: int
            ttl_seconds: int

        return CacheConfig(
            enabled=self.enable_caching,
            max_size=self.max_cache_size,
            ttl_seconds=self.cache_ttl_seconds
        )
```

## Anti-Patterns to Avoid

### 1. Dataclass Anti-Patterns

#### Over-Complex Validation
```python
# ❌ DON'T: Complex validation in dataclass
@dataclass
class BadExample:
    email: str
    age: int

    def __post_init__(self):
        # Too much validation logic - use Pydantic instead
        if "@" not in self.email or "." not in self.email.split("@")[1]:
            raise ValueError("Invalid email format")
        if not 13 <= self.age <= 120:
            raise ValueError("Age must be between 13 and 120")
        # ... 20 more lines of validation
```

#### Mutable Defaults
```python
# ❌ DON'T: Mutable default values
@dataclass
class BadExample:
    items: list = []  # Shared across all instances!
    metadata: dict = {}  # Shared across all instances!

# ✅ DO: Use field with default_factory
@dataclass
class GoodExample:
    items: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```

### 2. Pydantic Anti-Patterns

#### Missing Strict Validation
```python
# ❌ DON'T: Allow extra fields without intention
class BadExample(BaseModel):
    name: str
    # No ConfigDict - allows extra fields

# ✅ DO: Use strict validation
class GoodExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
```

#### Over-Permissive Types
```python
# ❌ DON'T: Use Any when specific types work
class BadExample(BaseModel):
    data: Any
    config: dict  # No type parameters

# ✅ DO: Use specific types
class GoodExample(BaseModel):
    data: dict[str, str] | list[int]
    config: dict[str, str | int | bool]
```

## Performance Benchmarks

### Instantiation Performance

```python
# Dataclass (with slots): ~0.5µs per instantiation
@dataclass(frozen=True, slots=True)
class FastStats:
    count: int
    value: float

# Pydantic BaseModel: ~5-10µs per instantiation
class ValidatedStats(BaseModel):
    count: int = Field(..., ge=0)
    value: float = Field(..., ge=0.0)
```

### Memory Usage

```python
# Dataclass with slots: ~56 bytes + field data
@dataclass(frozen=True, slots=True)
class Compact:
    x: float
    y: float

# Regular dataclass: ~304 bytes + field data
@dataclass
class Regular:
    x: float
    y: float

# Pydantic model: ~400-500 bytes + field data
class Validated(BaseModel):
    x: float
    y: float
```

### Serialization Performance

```python
# JSON serialization (Pydantic): ~20-50µs
# Manual dict conversion (dataclass): ~5-10µs
# But Pydantic includes validation and type coercion
```

## Migration Guidelines

### When to Migrate

**Dataclass → Pydantic**:
- Need JSON serialization for API boundaries
- Adding complex validation requirements
- Integration with external systems requiring strict validation
- Error messages need to be user-friendly

**Pydantic → Dataclass**:
- Performance becomes critical (>1000 instantiations/second)
- Validation overhead outweighs benefits
- Simple value objects with minimal validation needs
- Internal infrastructure components

### Migration Process

1. **Create new implementation** alongside existing
2. **Update all usage sites** with feature parity
3. **Run comprehensive tests** including performance benchmarks
4. **Remove old implementation** once all tests pass
5. **Update documentation** and type hints

---

**Usage**: Reference this catalog when implementing new data models or reviewing existing patterns. All patterns have been validated through the P1-P6 migration process and represent established architectural decisions.
