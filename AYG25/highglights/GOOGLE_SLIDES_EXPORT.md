# Google Slides Export

Export highlights sections to Google Slides for manual rearrangement and editing.

## Overview

This feature exports each carousel section as a separate slide in a Google Slides presentation. This allows you to:
- Manually rearrange slides
- Edit individual slides
- Share and collaborate on the presentation
- Export to other formats (PDF, PowerPoint, etc.)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Enable Google Slides API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create or select a project
   - Enable the Google Slides API and Google Drive API
   - Create service account credentials
   - Download the JSON credentials file
   - Place it in the location specified in `config.py` (or `ayg-form-system/functions/google_credentials.json`)

3. **Share the Google Slides presentation:**
   - Open the presentation: https://docs.google.com/presentation/d/1nK1Yx0EBO_OJ9jy7IrNep19yyv5SNm3-BQ6y77EjASY
   - Share it with the service account email (found in your credentials JSON file)
   - Give it "Editor" access

## Usage

### Export all highlights to Google Slides:

```bash
python3 export_to_slides.py
```

### Export from a specific directory:

```bash
python3 export_to_slides.py --html-dir output
```

### Use a different presentation:

```bash
python3 export_to_slides.py --presentation-id YOUR_PRESENTATION_ID
```

## How It Works

1. **Reads HTML files** from the `output/` directory (or specified directory)
2. **Finds all sections** in each HTML file (each `<div class="section">`)
3. **Takes screenshots** of each section using Playwright
4. **Uploads images** to Google Drive
5. **Creates slides** in the Google Slides presentation
6. **Inserts images** into each slide

Each section becomes a separate slide, allowing you to manually rearrange them in Google Slides.

## Notes

- Images are uploaded to Google Drive and made publicly viewable (required for Slides)
- Each section is exported as a 1920x1080px image
- Slides are added to the end of the presentation
- You can manually delete, reorder, or edit slides in Google Slides after export

## Troubleshooting

**Error: "Permission denied"**
- Make sure the service account email has Editor access to the Google Slides presentation
- Check that the credentials file path is correct

**Error: "API not enabled"**
- Enable Google Slides API and Google Drive API in Google Cloud Console

**No sections found**
- Make sure you've run `generate_highlights.py` first to create the HTML files
- Check that the HTML files contain sections with class "section"

