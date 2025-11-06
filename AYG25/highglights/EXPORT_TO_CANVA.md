# Export Widgets to Canva

This tool exports your widget HTML files as high-quality images (PNG or PDF) that you can import into Canva.

## Quick Start

### Step 1: Install Dependencies

```bash
pip install playwright
playwright install chromium
```

### Step 2: Export All Widgets

```bash
python3 export_to_images.py
```

This will:
- Export all widgets from `static_widgets/` folder
- Save as PNG images in `exported_images/` folder
- Each image is 1920x1080 pixels (perfect for Canva)

### Step 3: Import to Canva

1. Go to Canva
2. Create a new design (1920x1080)
3. Upload the PNG images
4. Use them in your designs!

## Options

### Export as PDF instead of PNG

```bash
python3 export_to_images.py --format pdf
```

### Export to Custom Directory

```bash
python3 export_to_images.py --output-dir my_canva_images
```

### Export Single Widget

```bash
python3 export_to_images.py --file static_widgets/widget_2025-10-27.html
```

### Export from Custom Widget Directory

```bash
python3 export_to_images.py --widgets-dir path/to/widgets
```

## Full Command Options

```bash
python3 export_to_images.py \
  --widgets-dir static_widgets \
  --output-dir exported_images \
  --format png
```

## Output

- **PNG files**: High-resolution 1920x1080 images (2x device scale for quality)
- **PDF files**: Vector format, 1920x1080 dimensions

Both formats are ready for Canva import!

## Troubleshooting

### Playwright Installation Issues

If you get errors installing Playwright:

```bash
# Install via pip
pip3 install playwright

# Install browser separately
python3 -m playwright install chromium
```

### Permission Errors

Make sure you have write permissions to the output directory.

### Missing Dependencies

```bash
pip install -r requirements.txt
```

## Tips for Canva

1. **PNG format** is recommended for best quality
2. Images are exactly 1920x1080 (standard presentation size)
3. You can use them as backgrounds or elements
4. All text and graphics are rendered as images (no editing needed)

## Example Workflow

```bash
# 1. Generate widgets
python3 generate_static_widget.py

# 2. Export to images
python3 export_to_images.py

# 3. Upload to Canva
# Go to Canva → Upload → Select exported_images/*.png
```

