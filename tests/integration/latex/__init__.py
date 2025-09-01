"""LaTeX integration tests.

These tests perform actual LaTeX compilation and require:
- LaTeX installation (texlive)
- DND-5e-LaTeX-Template
- Actual document compilation (slower than unit tests)

Unlike regular tests that mock LaTeX subprocess calls, these tests
execute real LaTeX compilation to validate end-to-end functionality.
"""
