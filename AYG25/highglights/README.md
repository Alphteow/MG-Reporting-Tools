# AYG25 Highlights Generator

Automated system for generating beautiful highlights pages from Google Sheets competition data. Each sport gets its own highlights page with both Head-to-Head (H2H) and Individual highlights.

## Features

- 📊 **Automated Data Loading**: Reads directly from Google Sheets
- 🏆 **Sport-Based Grouping**: Generates one highlights page per sport
- ⚔️ **H2H Highlights**: Displays head-to-head competition results
- 🎯 **Individual Highlights**: Shows individual performance highlights
- 🎨 **Beautiful UI**: Modern, responsive design with gradient backgrounds
- 📱 **Mobile Friendly**: Responsive design that works on all devices

## Prerequisites

1. **Python 3.8+** installed
2. **Google Sheets API Access**:
   - Google Cloud Project with Sheets API enabled
   - Service Account credentials JSON file
   - Spreadsheet shared with service account email

## Setup

### 1. Install Dependencies

```bash
cd highglights
pip install -r requirements.txt
```

### 2. Google Sheets Setup

If you haven't already set up Google Sheets integration:

1. **Create Service Account**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable Google Sheets API
   - Create a Service Account
   - Download JSON key file

2. **Place Credentials**:
   - Place the JSON file as `google_credentials.json` in the `highglights` directory
   - OR place it in the parent directory (project root)
   - OR set environment variable `GOOGLE_CREDENTIALS_JSON`

3. **Share Spreadsheet**:
   - Open your Google Spreadsheet
   - Click "Share"
   - Add the service account email (found in JSON file) with "Editor" permissions

### 3. Configure Settings

Edit `config.py` if needed:
- `GOOGLE_SPREADSHEET_ID`: Your spreadsheet ID
- `GOOGLE_SHEET_NAME`: Worksheet name (default: 'Data Collection')
- `DATA_START_ROW`: Row number where headers are (default: 8)

## Usage

### Basic Usage

```bash
python generate_highlights.py
```

### With Custom Settings

```bash
python generate_highlights.py \
    --spreadsheet-id YOUR_SPREADSHEET_ID \
    --sheet-name "Data Collection" \
    --credentials google_credentials.json
```

### Command Line Options

- `--spreadsheet-id`: Google Sheets spreadsheet ID (default: from config)
- `--sheet-name`: Worksheet name (default: 'Data Collection')
- `--credentials`: Path to credentials JSON file (default: 'google_credentials.json')

## Output

Generated HTML files will be saved in the `output/` directory:
- `SportName_highlights.html` - One file per sport
- CSS file: `styles.css` (linked from output directory)

## Data Requirements

The script expects the following columns in your Google Sheet (starting at row 8):

- **SPORT**: Sport name
- **DISCIPLINE**: Discipline name
- **EVENT**: Event name
- **STAGE / ROUND OF COMPETITION**: Competition stage
- **NAME OF ATHLETE (SGP)**: Singapore athlete name
- **NAME OF ATHLETE (COMPETITOR)**: Competitor name (for H2H)
- **SCORE/DISTANCE/HEIGHT (SGP)**: Singapore score/result
- **SCORE (COMPETITOR)**: Competitor score (for H2H)
- **WIN/DRAW/LOSE**: H2H result
- **MEDALS**: Medal won
- **HIGHLIGHTS**: Highlight text (required - only rows with this filled will be included)
- **PB/NR**: Personal Best / National Record
- **ADVANCED**: Whether athlete advanced
- And other columns as defined in `columns.txt`

## How It Works

1. **Data Loading**: Reads data from Google Sheets starting at row 8
2. **Filtering**: Only includes rows where HIGHLIGHTS column is not empty
3. **Categorization**: 
   - H2H: Has competitor information (name, country, score)
   - Non-H2H: Individual performance without competitor
4. **Grouping**: Groups highlights by SPORT
5. **Generation**: Creates HTML pages using Jinja2 templates
6. **Output**: Saves one HTML file per sport in `output/` directory

## H2H vs Non-H2H Highlights

### Head-to-Head (H2H) Highlights
Displayed when:
- Competitor name is present
- Competitor country is present
- Score or timing comparison available

Format: Shows athlete vs competitor with scores and result

### Individual Highlights
Displayed when:
- No competitor information
- Individual performance results

Format: Shows athlete performance with position, score, and achievements

## Styling

The highlights pages use a modern design with:
- Gradient backgrounds
- Card-based layout
- Color-coded badges (medals, records, advancement)
- Responsive grid layout
- Hover effects

Customize styles in `styles.css`.

## Troubleshooting

### "Credentials file not found"
- Ensure `google_credentials.json` is in the `highglights` directory or parent directory
- Or set `GOOGLE_CREDENTIALS_JSON` environment variable

### "No highlights data found"
- Check that HIGHLIGHTS column has data in your sheet
- Verify DATA_START_ROW is correct (should be 8)
- Check column names match expected format

### "Permission denied" errors
- Ensure spreadsheet is shared with service account email
- Check service account has Editor permissions

### "Module not found" errors
```bash
pip install -r requirements.txt
```

## File Structure

```
highglights/
├── generate_highlights.py    # Main generator script
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── styles.css                 # CSS styling
├── templates/
│   └── highlights_template.html  # HTML template
├── output/                    # Generated HTML files (created automatically)
├── examples/                  # Example images
└── README.md                  # This file
```

## Example Output

After running the script, you'll get HTML files like:
- `Athletics_highlights.html`
- `Swimming_highlights.html`
- `Badminton_highlights.html`
- etc.

Open these files in a web browser to view the highlights.

## Integration

You can integrate this into your workflow:
- Run as a scheduled task (cron job)
- Call from other scripts
- Use in CI/CD pipelines
- Deploy to web server

## License

Part of the AYG25 Major Games Reporting system.

