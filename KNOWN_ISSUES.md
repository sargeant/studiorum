# Known Issues

## LaTeX Escaping of Unicode Quotes

**Issue**: Test `test_adventure_and_book_tags` fails due to LaTeX escaping converting Unicode single quotes to backticks.

**Status**: Known defect

**Details**: The `_escape_latex` method in `tag_resolver.py` converts Unicode left single quote (U+2018) to backtick, but the test expects regular apostrophes. This affects book reference rendering.

**Workaround**: None currently - test is expected to fail until resolved.

**Priority**: Low - does not affect core functionality
