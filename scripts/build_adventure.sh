#!/bin/bash

# Build script for D&D 5e adventures
# Usage: ./build_adventure.sh <json_file> [options]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"
OUTPUT_DIR="$PROJECT_DIR/output"
BUILD_DIR="$PROJECT_DIR/build"
ASSETS_DIR="$PROJECT_DIR/assets"

# Default options
NO_IMAGES="--no-images"
ADD_ITEMS="--add-items"
ADD_CREATURES="--add-creatures"
ADVENTURE_MODE="--adventure"

# Create build directory if it doesn't exist
mkdir -p "$BUILD_DIR"

# Function to show usage
usage() {
    echo "Usage: $0 <json_file> [options]"
    echo ""
    echo "Options:"
    echo "  --with-images     Include images in the output"
    echo "  --no-items        Don't add item lists"
    echo "  --no-creatures    Don't add creature lists"
    echo "  --book-mode       Use book mode instead of adventure mode"
    echo "  --article-mode    Use article mode instead of adventure mode"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 srd-data/adventures/cos.json"
    echo "  $0 srd-data/adventures/netherdeep.json --with-images"
    echo "  $0 srd-data/books/book-egw.json --book-mode"
}

# Parse arguments
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

JSON_FILE="$1"
shift

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-images)
            NO_IMAGES=""
            shift
            ;;
        --no-items)
            ADD_ITEMS=""
            shift
            ;;
        --no-creatures)
            ADD_CREATURES=""
            shift
            ;;
        --book-mode)
            ADVENTURE_MODE="--book"
            shift
            ;;
        --article-mode)
            ADVENTURE_MODE="--article"
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if JSON file exists
if [ ! -f "$PROJECT_DIR/$JSON_FILE" ]; then
    echo "Error: JSON file not found: $PROJECT_DIR/$JSON_FILE"
    exit 1
fi

# Extract base name for output file
BASENAME=$(basename "$JSON_FILE" .json)
OUTPUT_FILE="$BUILD_DIR/$BASENAME.tex"

echo "Building D&D 5e document..."
echo "Input: $JSON_FILE"
echo "Output: $OUTPUT_FILE"
echo "Options: $ADVENTURE_MODE $NO_IMAGES $ADD_ITEMS $ADD_CREATURES"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Run the conversion using modern CLI
uv run 5e2pdf convert "$JSON_FILE" --output "$OUTPUT_FILE" \
    $ADVENTURE_MODE \
    $NO_IMAGES \
    $ADD_ITEMS \
    $ADD_CREATURES

echo "LaTeX file generated: $OUTPUT_FILE"

# Optionally compile to PDF
read -p "Compile to PDF with xelatex? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Compiling to PDF..."
    cd "$BUILD_DIR"

    # Set font paths for LaTeX
    export OSFONTDIR="$ASSETS_DIR/fonts"

    # Run xelatex (may need multiple passes for TOC)
    echo "Running xelatex (pass 1)..."
    xelatex -interaction=nonstopmode "$BASENAME.tex"

    echo "Running xelatex (pass 2)..."
    xelatex -interaction=nonstopmode "$BASENAME.tex"

    if [ -f "$BASENAME.pdf" ]; then
        echo "PDF generated successfully: $BUILD_DIR/$BASENAME.pdf"
    else
        echo "PDF generation failed. Check the LaTeX log for errors."
        exit 1
    fi
fi

echo "Build complete!"
