#!/bin/bash
# Build script for 5e2pdf documentation

set -e  # Exit on any error

echo "🏗️  Building 5e2pdf documentation..."

# Change to docs directory
cd "$(dirname "$0")/../docs"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf _build/*

# Build HTML documentation
echo "📖 Building HTML documentation..."
uv run sphinx-build -b html . _build/html

# Build PDF documentation (if LaTeX is available)
if command -v xelatex >/dev/null 2>&1; then
    echo "📄 Building PDF documentation..."
    uv run sphinx-build -b latex . _build/latex
    cd _build/latex
    xelatex 5e2pdf.tex
    xelatex 5e2pdf.tex  # Run twice for references
    cd ../..
    echo "📄 PDF documentation built: _build/latex/5e2pdf.pdf"
else
    echo "⚠️  XeLaTeX not found, skipping PDF generation"
fi

echo "✅ Documentation build complete!"
echo "📖 HTML documentation: docs/_build/html/index.html"

# Open documentation if on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🌐 Opening documentation in browser..."
    open _build/html/index.html
fi