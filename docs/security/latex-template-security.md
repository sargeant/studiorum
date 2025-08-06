# LaTeX Template Security Guide

This document outlines the security measures implemented to prevent LaTeX injection attacks in the 5e2pdf project and provides guidelines for secure template development.

## Security Overview

The 5e2pdf project processes user-provided D&D content and generates LaTeX documents. This process inherently involves security risks, as malicious content could potentially:

- Execute arbitrary LaTeX commands
- Access the file system through `\input` or `\include` commands
- Execute shell commands via `\write18`
- Manipulate document structure
- Inject malicious formatting

## Critical Security Fixes Implemented

### 1. Template Escaping

**Issue**: Templates were not consistently using the `latex_escape` filter, allowing direct injection of LaTeX commands.

**Fix**: All templates now use proper escaping:

```jinja2
% INSECURE (old)
\subsection{<# creature.name #>}

% SECURE (new)
\subsection{<# creature.name | latex_escape #>}
```

**Files Fixed**:
- `spell_entry.tex.j2`
- `creature_entry.tex.j2`
- `item_entry.tex.j2`
- `feat_entry.tex.j2`
- `race_entry.tex.j2`
- `background_entry.tex.j2`
- `class_entry.tex.j2`
- `article.tex.j2`

### 2. Enhanced Security Functions

**New Functions Added** (`src/dnd5e/core/latex_utils.py`):

- `contains_dangerous_latex(text)`: Detects dangerous LaTeX patterns
- `validate_safe_latex(text)`: Validates content safety with detailed reporting
- `sanitize_latex_content(text)`: Conservative sanitization for untrusted content

**New Template Filter** (`template_engine.py`):

- `latex_safe_check`: Runtime security validation with logging

### 3. Comprehensive Security Testing

**Test Coverage** (`tests/security/test_latex_injection.py`):

- Basic LaTeX character escaping validation
- Unicode character handling
- Injection attempt detection
- Property-based security testing
- Performance validation
- Template vulnerability testing
- Secure pattern verification

## Security Patterns

### Template Development Guidelines

#### 1. User Input Escaping

**ALWAYS** escape user-provided content:

```jinja2
% Names, titles, descriptions from user data
\section{<# title | latex_escape #>}
\textit{<# user_description | latex_escape #>}
```

#### 2. Trusted Content Handling

For content that's already processed and trusted (like rendered entries), use `safe`:

```jinja2
% Content already processed by tag renderer
<# processed_description | safe #>
```

#### 3. Mixed Content

When mixing user input with trusted content:

```jinja2
% User name gets escaped, processed content is safe
\textbf{<# spell.name | latex_escape #>.} <# spell.description | safe #>
```

#### 4. Security Validation

For extra safety, you can add runtime checks:

```jinja2
% This will log warnings for dangerous content
<# user_content | latex_safe_check | safe #>
```

### Dangerous Patterns

The following LaTeX patterns are automatically detected as dangerous:

- **Command definitions**: `\newcommand`, `\def`, `\gdef`, `\edef`, `\xdef`
- **File operations**: `\input`, `\include`, `\InputIfFileExists`
- **Shell escapes**: `\write18`, `\immediate\write18`
- **Document structure**: `\documentclass`, `\usepackage`, `\begin{document}`
- **Category codes**: `\catcode`, `\lccode`, `\uccode`
- **Expansion control**: `\expandafter`, `\csname`, `\endcsname`

### Security Filters

#### `latex_escape`

Escapes all LaTeX special characters:

```python
{"%", "&", "$", "#", "^", "_", "~", "{", "}"}
```

Unicode characters are also converted to LaTeX equivalents:

```python
{"—": "---", "–": "--", "…": "\\ldots{}", "°": "\\textdegree{}"}
```

#### `safe`

Marks content as safe to include without escaping. **Only use for trusted content**.

#### `latex_safe_check`

Validates content for dangerous patterns and logs warnings. Can be chained with `safe`:

```jinja2
<# potentially_dangerous_content | latex_safe_check | safe #>
```

## Architecture Security

### Template Engine Configuration

- **Autoescape disabled**: HTML autoescape is inappropriate for LaTeX
- **Custom delimiters**: Uses `<#` `#>` instead of `{{` `}}` to avoid LaTeX conflicts
- **Manual escaping**: All escaping must be explicit via filters

### Content Processing Pipeline

1. **Data Loading**: Raw JSON data from 5etools
2. **Model Processing**: Pydantic models with validation
3. **Content Rendering**: Tag processing for rich content
4. **Template Rendering**: Jinja2 with security filters
5. **LaTeX Compilation**: Safe, escaped output

### Security Layers

1. **Input validation**: Pydantic models validate data structure
2. **Content processing**: Tag renderer processes 5etools markup safely
3. **Template security**: Explicit escaping of all user content
4. **Runtime validation**: Optional security checks with logging
5. **Output sanitization**: Final LaTeX is safe for compilation

## Testing and Validation

### Running Security Tests

```bash
# Run all security tests
uv run pytest tests/security/test_latex_injection.py -v

# Test specific security aspects
uv run pytest tests/security/test_latex_injection.py::TestLaTeXEscaping -v
```

### Test Coverage

The security test suite covers:

- **Basic escaping**: All LaTeX special characters
- **Unicode handling**: Proper conversion of Unicode to LaTeX
- **Injection attempts**: Common attack vectors
- **Property-based testing**: Randomized input validation
- **Performance**: Escaping performance with large content
- **Template security**: End-to-end template vulnerability testing

### Manual Security Validation

You can validate content manually:

```python
from dnd5e.core.latex_utils import validate_safe_latex, contains_dangerous_latex

# Check if content is safe
is_safe, issues = validate_safe_latex(user_content)
if not is_safe:
    print("Security issues found:", issues)

# Quick danger check
if contains_dangerous_latex(user_content):
    print("Dangerous LaTeX patterns detected!")
```

## Best Practices

### For Developers

1. **Always escape user input** in templates
2. **Review template changes** for security implications
3. **Run security tests** before committing template changes
4. **Use `safe` sparingly** and only for trusted content
5. **Validate assumptions** about content safety

### For Template Authors

1. **Understand the data flow** - know what's user input vs processed content
2. **Default to escaping** - use `latex_escape` unless certain content is safe
3. **Test with malicious input** - include dangerous patterns in test data
4. **Document security decisions** - explain why content is marked safe

### For Content Processors

1. **Validate input early** in the processing pipeline
2. **Sanitize at boundaries** between trusted and untrusted content
3. **Log security events** for monitoring and debugging
4. **Fail securely** - prefer escaped content over failing

## Security Monitoring

### Logging

The security system logs warnings when potentially dangerous content is detected:

```python
logger.warning(
    "Potentially dangerous LaTeX content detected: %s",
    content[:100] + "..." if len(content) > 100 else content
)
```

### Metrics

Monitor these security metrics:

- Number of security warnings logged
- Content flagged by `latex_safe_check`
- Template rendering failures due to security issues
- Performance impact of security validations

## Incident Response

### If You Suspect a Security Issue

1. **Do not ignore warnings** from security validation
2. **Investigate the source** of suspicious content
3. **Review recent template changes** that might have introduced vulnerabilities
4. **Check test coverage** for the affected templates
5. **Update security tests** to prevent regression

### If You Find a Vulnerability

1. **Document the vulnerability** with minimal examples
2. **Create tests** that demonstrate the issue
3. **Implement fixes** following the patterns in this guide
4. **Verify the fix** with comprehensive testing
5. **Update documentation** if new patterns are discovered

## Further Reading

- [LaTeX Security Considerations](https://en.wikibooks.org/wiki/LaTeX/Security)
- [Jinja2 Security Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/#security)
- [Template Injection Prevention](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/18-Testing_for_Server_Side_Template_Injection)

---

**Last Updated**: 2025-08-03
**Security Review Required**: When adding new templates or modifying existing ones
