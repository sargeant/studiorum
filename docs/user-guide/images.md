# Images and Galleries

Studiorum provides comprehensive image support for creating visually rich 5e documents. This guide covers everything you need to know about including images in your generated PDFs.

## Quick Start

Enable images for any conversion using the `--images` flag:

```bash
# Convert adventure with images
studiorum convert adventure cos --images

# Convert bestiary with creature artwork
studiorum convert creatures --images --sources mm

# Convert items with illustrations
studiorum convert items --images --fluff --with-fluff-images
```

## Image Sources

### Configuring Image Directory

Set your image directory using an environment variable:

```bash
export STUDIORUM_IMAGE__IMAGE_DIRECTORY="/path/to/5etools-img"
```

Or configure it in your `studiorum.yaml`:

```yaml
images:
  image_directory: "/path/to/5etools-img"
```

### Supported Image Sources

Studiorum can pull images from multiple sources:

1. **5etools-img Repository** (recommended)
   - Official artwork from published sourcebooks
   - Organized by content type (bestiary, items, adventures)
   - WebP format automatically converted to PNG for LaTeX

2. **Local Image Directory**
   - Your custom artwork and assets
   - Supports PNG, JPG, WebP, PDF formats

3. **HTTP Sources**
   - Fallback to web-based image URLs
   - Cached locally for performance

## Image Types and Placement

### Creature Images

Creature images are automatically included with bestiary content:

```bash
# Include creature artwork in bestiary
studiorum convert creatures "Ancient Red Dragon" --images
```

**Placement Options:**
- **Smart placement**: Automatically positioned based on stat block size
- **Manual placement**: Fixed positioning for consistent layout

### Item Images

Item illustrations come from fluff content when available:

```bash
# Include item artwork from fluff descriptions
studiorum convert items --fluff --with-fluff-images --images
```

### Adventure Images

Adventures support multiple image types:

- **Chapter opening art**: Visual chapter introductions
- **Maps**: Dungeon layouts and regional maps
- **NPC portraits**: Key character artwork
- **Scene illustrations**: Atmospheric artwork

```bash
# Full adventure with all image types
studiorum convert adventure cos --images --chapter-art
```

### Galleries

Multi-image layouts with captions and intelligent spacing:

```bash
# Gallery layouts: grid, showcase, sequential, comparison
studiorum convert adventure --images --gallery-layout grid
```

## Image Quality and Optimization

### Quality Presets

Choose optimization level based on your output needs:

```bash
# Digital output (faster processing, smaller files)
studiorum convert adventure cos --images --image-quality digital

# Print output (higher quality, larger files)
studiorum convert adventure cos --images --image-quality print

# Hybrid (optimized for both digital and print)
studiorum convert adventure cos --images --image-quality hybrid
```

### Performance Options

Control processing speed and resource usage:

```bash
# Preload images for faster processing
studiorum convert adventure cos --images --preload-images

# Enable intelligent caching
studiorum convert adventure cos --images --image-cache

# Sync image sources before processing
studiorum convert adventure cos --images --sync-sources
```

## Configuration Options

### Basic Settings

```yaml
# studiorum.yaml
images:
  # Enable/disable image processing
  include_images: true

  # Quality optimization
  image_quality: "print"  # digital, print, hybrid

  # Placement strategy
  image_placement: "intelligent"  # intelligent, simple
```

### Advanced Settings

```yaml
images:
  # Performance options
  preload_images: true
  enable_image_cache: true
  max_concurrent_downloads: 5

  # Content-specific control
  bestiary_images: true
  item_images: true
  adventure_images: true
  chapter_art: true

  # Layout options
  gallery_layout: "grid"  # grid, showcase, sequential, comparison
```

### Source Configuration

```yaml
image_sources:
  - name: "5etools-official"
    source_type: "git_repo"
    git_repo_url: "https://github.com/5etools-mirror-3/5etools-img.git"
    priority: 10

  - name: "user-assets"
    source_type: "local_dir"
    local_path: "~/5e/custom-artwork"
    priority: 5  # Higher priority than official
```

## Content-Specific Image Control

### Bestiary Images

```bash
# Enable/disable creature artwork
studiorum convert creatures --bestiary-images
studiorum convert creatures --no-bestiary-images
```

### Item Images

```bash
# Control item illustrations
studiorum convert items --item-images
studiorum convert items --no-item-images
```

### Adventure Content

```bash
# Control adventure-specific images
studiorum convert adventure --adventure-images
studiorum convert adventure --no-adventure-images

# Control chapter opening artwork
studiorum convert adventure --chapter-art
studiorum convert adventure --no-chapter-art
```

## Troubleshooting

### Common Issues

**Images not appearing:**
1. Check that `STUDIORUM_IMAGE__IMAGE_DIRECTORY` is set correctly
2. Verify image files exist in the expected location
3. Ensure `--images` flag is included in command

**Layout problems:**
- Images too large: Use `--image-quality digital` for smaller images
- Images breaking columns: Check that source images aren't extremely wide
- Performance issues: Use `--preload-images` for faster processing

**Format issues:**
- WebP files: Automatically converted to PNG (no action needed)
- Unsupported formats: Only PNG, JPG, WebP, and PDF are supported

### Debug Information

Enable detailed logging to troubleshoot image processing:

```bash
STUDIORUM_LOGGING_LEVEL=DEBUG studiorum convert adventure cos --images
```

Look for messages like:
- `"Successfully processed image"` - Image converted and ready
- `"Image processing failed"` - Check file path and format
- `"Processed gallery with N images"` - Gallery layout successful

### Getting Help

**Check image processing status:**
```bash
# Test image conversion with single item
studiorum convert items "Bag of Holding" --images --fluff --with-fluff-images
```

**Validate configuration:**
```bash
# Show current image settings
studiorum config show --section images
```

For additional support, see [Troubleshooting](troubleshooting.md) or check the [Known Issues](known-issues.md) page.

## Advanced Features

### Multi-Layout Galleries

Create sophisticated image arrangements:

```yaml
# Custom gallery configurations
galleries:
  grid:
    columns: 2
    spacing: "1em"
  showcase:
    featured_size: "large"
    thumbnail_count: 4
```

### Content-Aware Placement

Studiorum intelligently positions images based on:
- Content type (creature, item, adventure)
- Available space on the page
- Surrounding text and layout
- Document structure and flow

### Batch Processing

Process large collections efficiently:

```bash
# Process entire bestiary with images
studiorum convert creatures --sources mm vgm mtf --images --output full-bestiary.pdf
```

### Integration with Other Features

Images work seamlessly with other Studiorum features:
- **Appendices**: Referenced creatures and items include their artwork
- **Cross-references**: Image captions link to relevant content
- **Templates**: Custom LaTeX templates support image placement
- **Fluff content**: Descriptive text enhanced with relevant illustrations

---

*For technical implementation details, see the [Developer Guide](../developer-guide/index.md).*
