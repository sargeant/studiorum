# Troubleshooting

```{note}
This page is under construction. Please check back later for comprehensive troubleshooting guidance.
```

## Common Issues

### Installation Problems

**Python Version Issues**
```bash
# Check Python version
python --version
# Should be 3.12+
```

**uv Installation**
```bash
# Install uv if missing
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### LaTeX Problems

**Missing LaTeX Distribution**
- macOS: Install MacTeX
- Ubuntu: `sudo apt-get install texlive-full`
- Windows: Install MiKTeX or TeX Live

**Font Issues**
- Ensure required fonts are installed
- Check LaTeX log files for missing dependencies

### Content Processing Errors

**Data Source Issues**
- Verify 5e.tools data accessibility
- Check network connectivity
- Validate data format versions

**Memory Problems**
- Reduce batch size for large datasets
- Increase system memory limits
- Use incremental processing

## Getting Help

1. Check this troubleshooting guide
2. Search existing [GitHub issues](https://github.com/sargeant/5e2pdf/issues)
3. Create a new issue with:
   - System information
   - Error messages
   - Steps to reproduce

## Debug Mode

```bash
# Enable verbose logging
uv run 5e2pdf --verbose

# Enable debug mode
uv run 5e2pdf --debug
```
