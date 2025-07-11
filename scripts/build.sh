#!/bin/bash

# Complete build script for D&D 5e PDF generation
# This script follows the workflow described in CLAUDE.md

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"
BUILD_DIR="$PROJECT_DIR/build"
ASSETS_DIR="$PROJECT_DIR/assets"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
usage() {
    echo "D&D 5e PDF Builder"
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  adventure <json_file>     Build an adventure PDF"
    echo "  book <json_file>          Build a book PDF"
    echo "  article <json_file>       Build an article PDF"
    echo "  list                      List available JSON files"
    echo "  clean                     Clean build artifacts"
    echo "  setup                     Setup dependencies"
    echo "  modern                    Use modern CLI (Phase 3 architecture)"
    echo ""
    echo "Options (for build commands):"
    echo "  --with-images             Include images in the output"
    echo "  --no-items                Don't add item lists"
    echo "  --no-creatures            Don't add creature lists"
    echo "  --no-spells               Don't add spell lists"
    echo "  --output <dir>            Specify output directory"
    echo "  --no-compile              Generate LaTeX only, don't compile PDF"
    echo "  --modern                  Use modern CLI (faster, more features)"
    echo "  --legacy                  Use legacy system (default for compatibility)"
    echo ""
    echo "Examples:"
    echo "  $0 adventure json_data/adventures/cos.json"
    echo "  $0 book json_data/books/book-egw.json --with-images"
    echo "  $0 article json_data/supplements/items.json --no-compile"
    echo "  $0 modern adventure json_data/adventures/cos.json --pdf"
    echo ""
    echo "Modern CLI:"
    echo "  ./bin/5e2pdf convert adventure <file> --pdf"
    echo "  ./bin/5e2pdf list files"
    echo "  ./bin/5e2pdf stats overview"
    echo ""
    echo "Workflow from CLAUDE.md:"
    echo "  git clone https://github.com/5etools-mirror-3/5etools-src"
    echo "  cd 5e2pdf"
    echo "  ./scripts/build.sh adventure .../5etools-src/data/adventure/adventure-cos.json"
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check uv
    if ! command -v uv &> /dev/null; then
        print_error "uv is required but not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    # Check if we can import required modules
    cd "$PROJECT_DIR"
    
    if ! uv run python -c "import dndtex" &> /dev/null; then
        print_error "dndtex module not found. Run './scripts/build.sh setup' to install dependencies."
        exit 1
    fi
    
    print_success "Python dependencies OK"
    
    # Check LaTeX (optional)
    if command -v xelatex &> /dev/null; then
        print_success "XeLaTeX found - PDF compilation available"
    else
        print_warning "XeLaTeX not found - LaTeX generation only"
    fi
}

# Function to setup project
setup_project() {
    print_status "Setting up project dependencies..."
    
    cd "$PROJECT_DIR"
    
    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        print_error "uv is required. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    # Install Python dependencies using uv
    print_status "Installing Python dependencies with uv..."
    uv sync
    
    # Create build directory
    mkdir -p "$BUILD_DIR"
    
    print_success "Setup complete"
}

# Function to clean build artifacts
clean_build() {
    print_status "Cleaning build artifacts..."
    
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"/*
        print_success "Build directory cleaned"
    fi
    
    # Clean any remaining artifacts in project root
    cd "$PROJECT_DIR"
    find . -name "*.aux" -o -name "*.fdb_latexmk" -o -name "*.mtc*" -o -name "*.maf" -o -name "*.log" -o -name "*.out" | xargs rm -f 2>/dev/null || true
    
    print_success "Cleanup complete"
}

# Function to list available JSON files
list_files() {
    print_status "Available JSON files:"
    echo ""
    
    if [ -d "$PROJECT_DIR/json_data" ]; then
        echo "📚 Books:"
        find "$PROJECT_DIR/json_data/books" -name "*.json" 2>/dev/null | sed 's|.*/||' | sort || echo "  (none found)"
        echo ""
        
        echo "🗡️  Adventures:"
        find "$PROJECT_DIR/json_data/adventures" -name "*.json" 2>/dev/null | sed 's|.*/||' | sort || echo "  (none found)"
        echo ""
        
        echo "📜 Supplements:"
        find "$PROJECT_DIR/json_data/supplements" -name "*.json" 2>/dev/null | sed 's|.*/||' | sort || echo "  (none found)"
    else
        echo "No json_data directory found. Make sure you've run the organization script."
    fi
}

# Function to build document
build_document() {
    local MODE="$1"
    local JSON_FILE="$2"
    shift 2
    
    # Parse additional options
    local OPTIONS=""
    local OUTPUT_OVERRIDE=""
    local COMPILE_PDF=true
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --with-images)
                # Remove --no-images if it's in default options
                ;;
            --no-items)
                OPTIONS="$OPTIONS"
                ;;
            --no-creatures)
                OPTIONS="$OPTIONS"
                ;;
            --no-spells)
                OPTIONS="$OPTIONS"
                ;;
            --output)
                OUTPUT_OVERRIDE="$2"
                shift 2
                ;;
            --no-compile)
                COMPILE_PDF=false
                shift
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Set default options based on mode
    case $MODE in
        adventure)
            OPTIONS="--adventure --no-images --add-items --add-creatures $OPTIONS"
            ;;
        book)
            OPTIONS="--book --no-images --add-items --add-creatures $OPTIONS"
            ;;
        article)
            OPTIONS="--article --no-images $OPTIONS"
            ;;
        *)
            print_error "Unknown mode: $MODE"
            exit 1
            ;;
    esac
    
    # Check if JSON file exists
    if [ ! -f "$PROJECT_DIR/$JSON_FILE" ]; then
        print_error "JSON file not found: $JSON_FILE"
        exit 1
    fi
    
    # Extract base name for output file
    BASENAME=$(basename "$JSON_FILE" .json)
    
    if [ -n "$OUTPUT_OVERRIDE" ]; then
        OUTPUT_FILE="$OUTPUT_OVERRIDE/$BASENAME.tex"
        mkdir -p "$OUTPUT_OVERRIDE"
    else
        OUTPUT_FILE="$BUILD_DIR/$BASENAME.tex"
        mkdir -p "$BUILD_DIR"
    fi
    
    print_status "Building $MODE: $JSON_FILE"
    print_status "Output: $OUTPUT_FILE"
    print_status "Options: $OPTIONS"
    
    # Change to project directory and set paths
    cd "$PROJECT_DIR"
    export OSFONTDIR="$ASSETS_DIR/fonts"
    
    # Run the conversion using uv
    uv run python "$SRC_DIR/json2tex.py" $OPTIONS --images "$ASSETS_DIR/images" "$JSON_FILE" > "$OUTPUT_FILE"
    
    print_success "LaTeX file generated: $OUTPUT_FILE"
    
    # Compile to PDF if requested and xelatex is available
    if [ "$COMPILE_PDF" = true ] && command -v xelatex &> /dev/null; then
        print_status "Compiling to PDF..."
        
        cd "$(dirname "$OUTPUT_FILE")"
        BASENAME_NO_EXT=$(basename "$OUTPUT_FILE" .tex)
        
        # Run xelatex multiple times for proper cross-references
        print_status "Running XeLaTeX (pass 1/2)..."
        xelatex -interaction=nonstopmode "$BASENAME_NO_EXT.tex" > /dev/null 2>&1 || {
            print_error "XeLaTeX compilation failed. Check the log file."
            exit 1
        }
        
        print_status "Running XeLaTeX (pass 2/2)..."
        xelatex -interaction=nonstopmode "$BASENAME_NO_EXT.tex" > /dev/null 2>&1 || {
            print_error "XeLaTeX compilation failed. Check the log file."
            exit 1
        }
        
        if [ -f "$BASENAME_NO_EXT.pdf" ]; then
            print_success "PDF generated: $(dirname "$OUTPUT_FILE")/$BASENAME_NO_EXT.pdf"
        else
            print_error "PDF generation failed"
            exit 1
        fi
    elif [ "$COMPILE_PDF" = true ]; then
        print_warning "XeLaTeX not found - skipping PDF compilation"
    fi
    
    print_success "Build complete!"
}

# Main script logic
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

COMMAND="$1"
shift

case $COMMAND in
    adventure|book|article)
        check_dependencies
        if [ $# -eq 0 ]; then
            print_error "JSON file required for $COMMAND command"
            usage
            exit 1
        fi
        build_document "$COMMAND" "$@"
        ;;
    modern)
        # Use modern CLI for all operations
        print_status "Using modern CLI (Phase 3 architecture)"
        cd "$PROJECT_DIR"
        if [ ! -x "bin/5e2pdf" ]; then
            print_error "Modern CLI not found. Run './scripts/build.sh setup' first."
            exit 1
        fi
        exec "./bin/5e2pdf" "$@"
        ;;
    list)
        list_files
        ;;
    clean)
        clean_build
        ;;
    setup)
        setup_project
        ;;
    --help|help)
        usage
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac