# AsyncServiceBridge Design Document

## Overview

The AsyncServiceBridge is an improved async bridge architecture for MCP server integration that builds on the lessons learned from the previous async_bridge implementation while simplifying for the pure async MCP context.

## Key Improvements Over Previous Implementation

### Problems with Previous async_bridge

The previous async_bridge implementation was successful in many ways but had critical issues:

1. **Complex Event Loop Management**: Required complex sync/async bridging with ThreadPoolExecutor
2. **CLI Context Conflicts**: 66 test failures due to event loop management in sync CLI context
3. **Nested Event Loop Issues**: Problems when async code was called from sync contexts
4. **High Complexity**: Too much boilerplate code for simple MCP tool implementation

### Solutions in New Design

1. **Pure Async Context**: MCP server runs in async context, eliminating sync/async bridging complexity
2. **Simplified Service Access**: High-level helpers for common MCP operations
3. **Protocol-Based Architecture**: Maintains the successful service container integration patterns
4. **Request Isolation**: Full request-scoped containers for tool isolation

## Architecture Components

### 1. AsyncServiceBridge

**Purpose**: Main integration point between MCP tools and the service container system.

**Key Features**:
- Creates request-scoped service contexts for MCP tools
- Manages service container lifecycle for requests
- Provides protocol-based service access patterns
- Handles performance monitoring and error propagation
- Supports hot-reload configuration

**Usage Pattern**:
```python
bridge = AsyncServiceBridge(enable_performance_monitoring=True)

async with bridge.create_tool_context("search_spells") as ctx:
    spells = await ctx.search_spells("fireball")
```

### 2. MCPServiceContext

**Purpose**: Request-scoped service context with MCP-specific helpers.

**Key Features**:
- Simplified access to services through AsyncRequestContext facade
- High-level operation helpers (search, resolve, etc.)
- Performance tracking integration
- Error handling with MCP error types
- Resource lifecycle tied to request scope

**Benefits Over Direct AsyncRequestContext**:
- Reduces complexity for MCP tool implementers
- Provides domain-specific helpers
- Automatic error handling and conversion
- Built-in performance tracking

**Common Operations**:
```python
async with create_mcp_service_context("my_tool") as ctx:
    # High-level search operations
    spells = await ctx.search_spells("fireball")
    creatures = await ctx.search_creatures("dragon")

    # Content resolution
    adventure = await ctx.resolve_adventure("lost-mine-of-phandelver")
    book = await ctx.resolve_book("players-handbook")

    # Generic content search with filtering
    items = await ctx.search_content("magic", "item", sources=["phb"], limit=10)
```

### 3. MCPToolBase

**Purpose**: Base class for MCP tools with integrated service access.

**Key Features**:
- Automatic service bridge integration
- Standard error handling patterns
- Performance monitoring integration
- Configuration override support
- Eliminates boilerplate code

**Example Implementation**:
```python
class SearchSpellsTool(MCPToolBase):
    tool_name = "search_spells"
    tool_version = "1.0.0"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params.get("query", "")
        sources = params.get("sources")

        async with self.create_context(sources=sources) as ctx:
            spells = await ctx.search_spells(query)
            return {
                "spells": [spell.model_dump() for spell in spells],
                "total": len(spells),
                "query": query,
            }
```

### 4. Integration with ModernMCPRequestHandler

**Purpose**: Shows how the bridge integrates with existing MCP infrastructure.

**Key Features**:
- Bridge-based handler methods alongside existing handlers
- Performance metrics integration
- Consistent error handling patterns
- Gradual migration path

**Comparison**:

**Before (Complex pattern)**:
```python
async def _handle_search_spells_async(self, params, ctx: AsyncRequestContext):
    # Manual service access
    omnidexer = await ctx.get_service(OmnidexerProtocol)

    # Manual error handling
    try:
        results = omnidexer.search(query)
        # Complex result processing...
    except Exception as e:
        # Manual error conversion...
```

**After (Bridge pattern)**:
```python
async def _handle_search_spells_bridge(self, params, ctx: MCPServiceContext):
    # Simple high-level operation
    spells = await ctx.search_spells(query, sources=sources, limit=limit)

    # Automatic error handling and result formatting
    return {
        "spells": [spell.model_dump() for spell in spells],
        "total": len(spells),
        "query": query,
    }
```

## Service Container Integration

### Request-Scoped Containers

The bridge maintains the successful patterns from the previous implementation:

1. **Protocol-Based Service Registration**: All services implement protocols
2. **Dependency Injection**: Services are automatically injected based on dependencies
3. **Lifecycle Management**: Proper async resource cleanup
4. **Configuration Override**: Request-specific configuration support

### Service Access Patterns

**Direct Protocol Access**:
```python
async with create_mcp_service_context("tool") as ctx:
    omnidexer = await ctx.omnidexer()
    tag_resolver = await ctx.tag_resolver()
    content_factory = await ctx.content_factory()
    config = await ctx.config()
```

**High-Level Helpers** (Recommended):
```python
async with create_mcp_service_context("tool") as ctx:
    spells = await ctx.search_spells("fireball")
    adventure = await ctx.resolve_adventure("lost-mine")
```

## Performance Monitoring

### Integrated Metrics

The bridge includes comprehensive performance monitoring:

1. **Request Tracking**: Each context has a unique request ID
2. **Operation Metrics**: Cache hits/misses, operation counts
3. **Duration Tracking**: Request execution timing
4. **Resource Usage**: Service access patterns

### Metrics Access

```python
# From bridge
bridge = AsyncServiceBridge()
metrics = await bridge.get_context_metrics()

# From handler
handler = ModernMCPRequestHandler()
metrics = await handler.get_bridge_metrics()
```

## Error Handling

### Automatic Error Conversion

The bridge automatically converts exceptions to MCP-compatible errors:

1. **Structured Errors**: All errors follow MCPError format
2. **Error Categories**: Proper categorization (processing, validation, etc.)
3. **Error Propagation**: Errors are collected and returned in JSON-RPC format
4. **Logging Integration**: Structured logging with error context

### Error Handling Patterns

```python
async with create_mcp_service_context("tool") as ctx:
    try:
        result = await ctx.search_spells("invalid query")
    except MCPException as e:
        # Handle MCP-specific errors
        logger.error(f"MCP error: {e.mcp_error.message}")

    # Or check for errors in context
    if ctx.has_errors():
        errors = ctx.get_errors()
        # Handle errors...
```

## Configuration Override Support

### Request-Specific Configuration

The bridge supports configuration overrides at multiple levels:

**Tool Level**:
```python
config = ApplicationConfig(sources=["phb", "xge"])
async with create_mcp_service_context("tool", config_override=config) as ctx:
    # Tool uses overridden configuration
```

**Handler Level**:
```python
response = await handler.handle_request_with_bridge(
    method="search_spells",
    params={"query": "fireball"},
    config_overrides={"sources": ["phb"]}
)
```

### Hot-Reload Support

Configuration can be updated during request execution:

```python
async with create_mcp_service_context("tool") as ctx:
    # Change configuration mid-request
    new_config = ApplicationConfig(sources=["xge"])
    await ctx.request_context.reload_configuration(new_config)
```

## Migration Guide

### From Manual Service Access

**Before**:
```python
async with async_request_context() as ctx:
    omnidexer = await ctx.get_service(OmnidexerProtocol)
    results = omnidexer.search(query)
    # Manual error handling...
    # Manual result processing...
```

**After**:
```python
async with create_mcp_service_context("tool") as ctx:
    results = await ctx.search_spells(query)
    # Automatic error handling and result processing
```

### From Complex Error Handling

**Before**:
```python
try:
    # Service operations...
except Exception as e:
    error = MCPError(
        message=f"Operation failed: {e}",
        error_code=MCPErrorCode.INTERNAL_ERROR,
        category=ErrorCategory.PROCESSING,
    )
    await ctx.add_async_error(error)
    raise MCPException(error)
```

**After**:
```python
# Automatic error handling in bridge helpers
results = await ctx.search_spells(query)  # Errors handled automatically
```

## Factory Functions

### Convenience Functions

For simple use cases, factory functions eliminate the need to manage bridge instances:

```python
# Simple context creation
async with create_mcp_service_context("tool") as ctx:
    results = await ctx.search_spells("fireball")

# Direct container access (for advanced use cases)
container = await create_mcp_request_container()
async with container as ctx:
    # Full AsyncRequestContext API
```

## Testing Patterns

### Mock-Friendly Design

The bridge architecture is designed to be easily testable:

```python
# Test with real bridge
async def test_tool():
    bridge = AsyncServiceBridge(enable_performance_monitoring=False)
    async with bridge.create_tool_context("test_tool") as ctx:
        # Test tool operations
        pass

# Test with mock context
async def test_tool_with_mock():
    # Mock MCPServiceContext for unit tests
    pass
```

## Deployment Considerations

### Memory Usage

- Request-scoped containers prevent memory leaks
- Automatic cleanup on context exit
- WeakSet references for async resources

### Performance

- Service caching within request scope
- Lazy service initialization
- Efficient protocol-based service access

### Monitoring

- Structured logging integration
- Performance metrics collection
- Error tracking and reporting

## Future Enhancements

### Planned Improvements

1. **Service Discovery**: Automatic detection of available MCP tools
2. **Batch Operations**: Support for batched requests
3. **Caching Layer**: Request-level caching for improved performance
4. **Circuit Breaker**: Error handling patterns for service failures

### Extension Points

1. **Custom Contexts**: Specialized contexts for different tool types
2. **Middleware Support**: Request/response middleware for cross-cutting concerns
3. **Plugin Architecture**: Dynamic tool registration and discovery

## Conclusion

The AsyncServiceBridge successfully addresses the limitations of the previous async_bridge implementation while preserving its successful patterns. By eliminating complex sync/async bridging and providing high-level helpers, it significantly simplifies MCP tool development while maintaining the full power of the service container architecture.

The design enables:
- **Rapid Tool Development**: Simple patterns for common operations
- **Consistent Error Handling**: Automatic error conversion and propagation
- **Performance Monitoring**: Built-in metrics and tracking
- **Service Integration**: Full access to the modern service container system
- **Testing Support**: Mock-friendly architecture for unit testing

This architecture provides a solid foundation for all current and future MCP tool implementations while maintaining compatibility with the existing codebase.
