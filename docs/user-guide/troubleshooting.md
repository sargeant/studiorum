---
title: Troubleshooting
description: Common issues and solutions when using studiorum
---

# Troubleshooting

Common issues you might encounter when using studiorum and how to resolve them. Check the list of [known issues](known-issues.md) first.

## Quick Diagnosis

Before diving into specific issues, try these quick diagnostic steps:

```bash
# Check system status
studiorum health check

# Verify installation
studiorum --version

# Test basic functionality
studiorum list creatures --limit 1
```

If these basic commands fail, start with [Installation Issues](#installation-issues).

## Common Errors

### "Content not found" Errors

**Error**: `Content not found: Ancient Red Dragon`

**Quick Fix**:
```bash
# Check exact name
studiorum list creatures | grep -i "red dragon"

# Use exact match
studiorum convert creatures "Ancient Red Dragon"
```

**See**: [Missing Source Data](#missing-source-data) for detailed solutions.

### LaTeX Compilation Errors

**Error**: `! LaTeX Error: File not found` or `pdflatex: command not found`

**Quick Fix**:
```bash
# Test LaTeX installation
pdflatex --version

# Install LaTeX (macOS)
brew install --cask mactex
```

**See**: [LaTeX Installation](#latex-installation) and [LaTeX Compilation Failures](#latex-compilation-failures).

### Image Processing Failures

**Error**: Images missing from output or `Image processing failed`

**Quick Fix**:
```bash
# Check image directory
echo $STUDIORUM_IMAGE__IMAGE_DIRECTORY

# Test with simple command
studiorum convert items "Bag of Holding" --images
```

**See**: [Image Issues](#image-issues) for comprehensive solutions.

### MCP Connection Problems

**Error**: `MCP server connection failed` in Claude Desktop

**Quick Fix**:
```bash
# Test MCP server manually
uv run studiorum mcp run --debug
```

**See**: [MCP Server Issues](#mcp-server-issues) for detailed troubleshooting.

---

## Installation Issues

### Python Version Compatibility

**Problem**: `studiorum requires Python 3.12+` error

**Solution**: Install Python 3.12 or later:

=== "uv"

    ```bash
    # Install Python 3.12 via uv
    uv python install 3.12
    uv python pin 3.12
    ```

=== "pyenv"

    ```bash
    # Install via pyenv
    pyenv install 3.12.0
    pyenv global 3.12.0
    ```

### Missing Dependencies

**Problem**: `ModuleNotFoundError` for required packages

**Solution**: Reinstall with all dependencies:

```bash
# Clean installation
pip uninstall studiorum
pip install studiorum[all]

# Or with uv
uv add studiorum --extra all
```

### LaTeX Installation

**Problem**: `pdflatex not found` error

**Solution**: Install a LaTeX distribution:

=== "macOS"

    ```bash
    # Install MacTeX (full distribution)
    brew install --cask mactex

    # Or BasicTeX (minimal)
    brew install --cask basictex
    ```

=== "Ubuntu/Debian"

    ```bash
    # Full installation
    sudo apt-get install texlive-full

    # Minimal installation
    sudo apt-get install texlive-latex-base texlive-latex-extra
    ```

=== "Windows"

    Download and install [MiKTeX](https://miktex.org/download) or [TeX Live](https://www.tug.org/texlive/).

## Content Issues

### Missing Source Data

**Problem**: `Content not found: Ancient Red Dragon`

**Solution**:

1. Check available repositories:

   ```bash
   studiorum data list
   ```

2. Update content index:

   ```bash
   studiorum index refresh
   ```

3. Verify exact naming:

   ```bash
   studiorum list content --type creature | grep -i dragon
   ```

### Outdated Content

**Problem**: Missing newly released content

**Solution**: Update to the latest content:

```bash
# Check data repositories status
studiorum data status

# Rebuild index
studiorum index rebuild

# Verify new content
studiorum list adventures --recent
```

### Permission Errors

**Problem**: `Permission denied` when accessing content files

**Solution**: Fix file permissions:

```bash
# Make content directory readable
chmod -R 755 ~/.studiorum/content/

# Reset ownership
sudo chown -R $USER ~/.studiorum/
```

## Conversion Errors

### LaTeX Compilation Failures

**Problem**: LaTeX compilation errors during PDF generation

**Solution**:

1. **Generate LaTeX only** to debug:

   ```bash
   studiorum convert creature "Beholder" --format latex --debug
   ```

2. **Check LaTeX log** for specific errors:

   ```bash
   # Look for specific error patterns
   grep -i "error\|warning" creature_beholder.log
   ```

3. **Try different compiler**:

   ```bash
   studiorum convert creature "Beholder" --compiler xelatex
   ```

4. **Common LaTeX fixes**:

   - **Missing packages**: Install required LaTeX packages

     ```bash
     # Ubuntu/Debian
     sudo apt-get install texlive-fonts-extra texlive-latex-extra
     ```

   - **Unicode issues**: Use XeLaTeX or LuaLaTeX for Unicode content

     ```bash
     studiorum convert --compiler xelatex creature "Beholder"
     ```

   - **Memory issues**: Increase LaTeX memory limits

     ```bash
     export max_print_line=1000
     export error_line=254
     ```

### Memory Issues

**Problem**: `MemoryError` during large conversions

**Solution**:

1. **Increase system limits**:

   ```bash
   # Set memory limit (4GB example)
   export STUDIORUM_MAX_MEMORY=4G
   ```

2. **Process in chunks**:

   ```bash
   # Convert creatures by CR range
   for cr in {1..5} {6..10} {11..15} {16..20}; do
       studiorum convert creatures --cr $cr --output "cr_$cr.tex"
   done
   ```

3. **Use streaming mode**:

   ```bash
   studiorum convert adventure "Large Campaign" --stream --output campaign.tex
   ```

### Encoding Issues

**Problem**: `UnicodeDecodeError` or garbled text

**Solution**:

1. **Set UTF-8 encoding**:

   ```bash
   export LC_ALL=en_US.UTF-8
   export LANG=en_US.UTF-8
   ```

2. **Use proper LaTeX packages**:

   ```latex
   \usepackage[utf8]{inputenc}
   \usepackage[T1]{fontenc}
   ```

3. **Clean problematic characters**:

   ```bash
   studiorum convert creature "Beholder" --clean-unicode --output beholder.tex
   ```

## Performance Issues

### Slow Conversion

**Problem**: Conversions take too long

**Solution**:

1. **Enable caching**:

   ```yaml
   # ~/.studiorum/config.yaml
   cache:
     enabled: true
     type: file
     directory: ~/.studiorum/cache/
   ```

2. **Use parallel processing**:

   ```bash
   studiorum convert creatures --cr 1-20 --parallel --workers 4
   ```

3. **Optimize sources**:

   ```yaml
   sources:
     enabled:
       - SRD
   ```

4. **Profile performance**:

   ```bash
   studiorum convert adventure "Campaign" --profile --output profile.json
   ```

### High Memory Usage

**Problem**: System becomes unresponsive during conversion

**Solution**:

1. **Monitor usage**:

   ```bash
   # Watch memory usage during conversion
   studiorum convert adventure "Large Campaign" &
   watch -n 1 'ps aux | grep studiorum'
   ```

2. **Tune garbage collection**:

   ```bash
   export PYTHONHASHSEED=0
   export MALLOC_ARENA_MAX=2
   ```

3. **Use incremental processing**:

   ```bash
   studiorum convert adventure "Campaign" --incremental --checkpoint-every 50
   ```

## Network Issues

### Content Download Failures

**Problem**: `Connection timeout` when downloading content

**Solution**:

1. **Check network connection**:

   ```bash
   ping github.com
   curl -I https://raw.githubusercontent.com/5etools-mirror-1/5etools-mirror-1.github.io/master/data/bestiary/bestiary-mm.json
   ```

2. **Configure proxy** (if needed):

   ```bash
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

3. **Use local content sources**:

   ```yaml
   # ~/.studiorum/config.yaml
   sources:
     local:
       path: /path/to/local/5etools-data
   ```

4. **Retry with backoff**:

   ```bash
   # Add remote repository with retry logic
   studiorum data add-url https://example.com/data.json --name "remote-source"
   ```

## Image Issues

### Images Not Appearing

**Problem**: Generated PDFs don't include expected images

**Solution**:

1. **Check image directory**:

   ```bash
   # Verify image directory is set
   echo $STUDIORUM_IMAGE__IMAGE_DIRECTORY

   # Check if directory exists
   ls "$STUDIORUM_IMAGE__IMAGE_DIRECTORY"
   ```

2. **Enable images explicitly**:

   ```bash
   studiorum convert adventure cos --images
   ```

3. **Test image processing**:

   ```bash
   # Convert single item with images
   STUDIORUM_LOGGING_LEVEL=DEBUG studiorum convert items "Bag of Holding" --images --fluff --with-fluff-images

   # Look for "Successfully processed image" messages
   ```

### Image Conversion Failures

**Problem**: WebP images fail to convert to PNG

**Solution**:

1. **Install Pillow with WebP support**:

   ```bash
   pip install --upgrade Pillow[webp]
   ```

2. **Check format support**:

   ```bash
   python -c "from PIL import Image; print(Image.EXTENSION)"
   ```

3. **Test single image conversion**:

   ```bash
   # Manual conversion test
   python -c "from PIL import Image; Image.open('test.webp').save('test.png')"
   ```

### Image Layout Problems

**Problem**: Images break column layout or extend off pages

**Solution**:

1. **Use column-aware sizing**:

   ```bash
   # Items use smaller sizing for columns
   studiorum convert items --images --image-quality digital
   ```

2. **Check for oversized images**:

   ```bash
   # Enable debug logging to see image processing
   STUDIORUM_LOGGING_LEVEL=DEBUG studiorum convert creatures --images
   ```

3. **Use intelligent placement**:

   ```bash
   studiorum convert adventure cos --images --image-placement intelligent
   ```

## MCP Server Issues

!!! warning "Experimental Feature"
    MCP features are experimental and may not work as expected. Report issues on GitHub.

### Connection Problems

**Problem**: Claude Desktop can't connect to MCP server

**Solution**:

1. **Check configuration**:

   ```json
   {
     "mcpServers": {
       "studiorum": {
         "command": "uv",
         "args": ["run", "studiorum", "mcp", "run"],
         "cwd": "/correct/path/to/project"
       }
     }
   }
   ```

2. **Test server manually**:

   ```bash
   cd /correct/path/to/project
   uv run studiorum mcp run --debug
   ```

3. **Check logs**:

   ```bash
   # Claude Desktop logs
   tail -f ~/.claude/logs/claude_desktop.log

   # Studiorum MCP logs
   tail -f ~/.studiorum/logs/mcp-server.log
   ```

### Tool Execution Errors

**Problem**: MCP tools fail with errors

**Solution**:

1. **Test tools directly**:

   ```bash
   studiorum mcp test lookup_creature "Ancient Red Dragon"
   ```

2. **Check permissions**:

   ```bash
   # Ensure studiorum can write temporary files
   touch ~/.studiorum/temp/test.txt
   rm ~/.studiorum/temp/test.txt
   ```

3. **Validate input**:

   ```bash
   # Check exact content names
   studiorum list content --type creature | grep -i "red dragon"
   ```

## Configuration Issues

### Invalid Configuration

**Problem**: `Invalid configuration` error on startup

**Solution**:

1. **Validate YAML syntax**:

   ```bash
   python -c "import yaml; yaml.safe_load(open('~/.studiorum/config.yaml'))"
   ```

2. **Reset to defaults**:

   ```bash
   # Backup current config
   mv ~/.studiorum/config.yaml ~/.studiorum/config.yaml.backup

   # Generate new default config
   studiorum config init
   ```

3. **Use schema validation**:

   ```bash
   studiorum config validate ~/.studiorum/config.yaml
   ```

### Path Issues

**Problem**: `FileNotFoundError` for configuration or content files

**Solution**:

1. **Check environment variables**:

   ```bash
   echo $STUDIORUM_CONFIG_DIR
   echo $STUDIORUM_DATA_DIR
   ```

2. **Create missing directories**:

   ```bash
   mkdir -p ~/.studiorum/{config,data,logs,temp,cache}
   ```

3. **Fix permissions**:

   ```bash
   chmod 755 ~/.studiorum
   chmod 644 ~/.studiorum/config.yaml
   ```

## Getting Help

### Collecting Debug Information

When reporting issues, include:

```bash
# System information
studiorum version --detailed

# Configuration
studiorum config show --sanitized

# Environment
env | grep STUDIORUM

# Recent logs
studiorum logs --tail 100 --level ERROR
```

### Performance Profiling

For performance issues:

```bash
# Generate performance profile
studiorum convert creature "Beholder" --profile --output beholder-profile.json

# Analyze profile
studiorum profile analyze beholder-profile.json
```

### Community Support

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/sargeant/studiorum/issues)
- **Discussions**: [Community Q&A and troubleshooting](https://github.com/sargeant/studiorum/discussions)
- **Discord**: Join our community server for real-time help

## Prevention

### Regular Maintenance

Prevent common issues:

```bash
#!/bin/bash
# ~/.studiorum/maintenance.sh

# Clean old temporary files
find ~/.studiorum/temp -type f -mtime +7 -delete

# Check data repositories status
studiorum data status

# Rebuild index if needed
if [ -z "$(find ~/.studiorum/index -name '*.db' -mtime -30)" ]; then
    studiorum index rebuild --quiet
fi

# Clean cache if too large
cache_size=$(du -sm ~/.studiorum/cache | cut -f1)
if [ "$cache_size" -gt 1000 ]; then
    studiorum cache clear --keep-recent 100
fi
```

Run monthly with cron:

```bash
# Add to crontab
0 2 1 * * /home/user/.studiorum/maintenance.sh
```

### Health Checks

Monitor studiorum health:

```bash
# Quick health check
studiorum health check

# Detailed system check
studiorum health check --detailed --fix-issues
```
