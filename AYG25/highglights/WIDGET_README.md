# Highlights Widget - Developer Integration Guide

This widget allows developers to easily embed highlights from a Google Sheet into their web pages. The widget is constrained to a **1920x1080** container and displays sports highlights in a carousel format.

## Quick Start

### 1. Start the Widget Server

```bash
cd /path/to/highglights
python3 widget_server.py
```

The server will start on `http://localhost:5000` by default.

### 2. Embed in Your Page

Choose one of three methods:

#### Method 1: Simple HTML (Recommended)

```html
<!-- Include the embed script -->
<script src="http://your-server.com/embed.js"></script>

<!-- Create a container element with data attributes -->
<div id="highlights-widget"
     data-spreadsheet-id="YOUR_SPREADSHEET_ID"
     data-sheet-name="YOUR_SHEET_NAME"
     data-credentials-file="path/to/credentials.json"  <!-- Optional -->
     data-date="2025-10-27"  <!-- Optional: filter by date -->
     data-sport="Swimming"  <!-- Optional: filter by sport -->
     data-base-url="http://your-server.com">  <!-- Optional: server URL -->
</div>
```

#### Method 2: JavaScript API

```html
<!-- Include the embed script -->
<script src="http://your-server.com/embed.js"></script>

<!-- Create a container element -->
<div id="highlights-widget"></div>

<!-- Initialize the widget -->
<script>
    HighlightsWidget.create({
        containerId: 'highlights-widget',
        spreadsheet_id: 'YOUR_SPREADSHEET_ID',
        sheet_name: 'YOUR_SHEET_NAME',
        credentials_file: 'path/to/credentials.json',  // Optional
        date: '2025-10-27',  // Optional: filter by date
        sport: 'Swimming',  // Optional: filter by sport
        baseUrl: 'http://your-server.com'  // Optional: server URL
    });
</script>
```

#### Method 3: Direct iframe

```html
<iframe 
    src="http://your-server.com/widget?spreadsheet_id=YOUR_SPREADSHEET_ID&sheet_name=YOUR_SHEET_NAME&date=2025-10-27"
    width="1920"
    height="1080"
    style="border: none; max-width: 100%; aspect-ratio: 1920/1080; height: auto;"
    frameborder="0"
    scrolling="no">
</iframe>
```

## Required Google Sheet Columns

Your Google Sheet must contain the following columns (case-sensitive):

| Column Name | Required | Description |
|------------|----------|-------------|
| `SPORT` | Yes | Name of the sport |
| `EVENT` | Yes | Event name |
| `EVENT GENDER` | Yes | Gender category (Boys, Girls, Mixed) |
| `STAGE / ROUND OF COMPETITION` | Yes | Round/Stage information |
| `NAME OF ATHLETE (SGP)` | Yes | Singapore athlete name |
| `COUNTRY NAME (SGP)` | Yes | Country (usually "SGP") |
| `TIMING (SGP)\nhh:mm:ss.ms` | Conditional | Timing for non-H2H sports |
| `SCORE/DISTANCE/HEIGHT\n(SGP)` | Conditional | Score/distance/height for SGP athlete |
| `NAME OF ATHLETE (COMPETITOR)` | H2H only | Opponent name (for H2H sports) |
| `COUNTRY NAME (COMPETITOR)` | H2H only | Opponent country (for H2H sports) |
| `SCORE (COMPETITOR)` | H2H only | Opponent score (for H2H sports) |
| `MEDALS` | No | "Gold", "Silver", or "Bronze" |
| `PB/NR` | No | Personal Best or National Record indicator |
| `DATE (SGP)` | Yes | Date in YYYY-MM-DD format |

## API Parameters

### Query Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `spreadsheet_id` | Yes | Google Sheets spreadsheet ID (found in the URL) |
| `sheet_name` | Yes | Name of the worksheet/tab in the spreadsheet |
| `credentials_file` | No | Path to Google service account credentials JSON file (or use `GOOGLE_CREDENTIALS_JSON` env var) |
| `date` | No | Filter highlights by specific date (YYYY-MM-DD format) |
| `sport` | No | Filter highlights by specific sport name |

### API Endpoint

```
GET /api/highlights?spreadsheet_id=YOUR_ID&sheet_name=YOUR_SHEET
```

**Response:**
```json
{
    "highlights": [...],
    "h2h_groups": [...],
    "non_h2h_groups": [...],
    "total": 31,
    "h2h_count": 15,
    "non_h2h_count": 16
}
```

## Widget Features

- ✅ **Fixed 1920x1080 container** (responsive, maintains aspect ratio)
- ✅ **Carousel navigation** for multiple results
- ✅ **Automatic detection** of H2H vs non-H2H sports
- ✅ **Medal icons** (Gold 🥇, Silver 🥈, Bronze 🥉)
- ✅ **PB/NR badges** for personal bests and national records
- ✅ **Red header** with "RESULTS" text
- ✅ **Red-bordered sections** for visual organization
- ✅ **Light pink result cards** (#FDE9E9)

## Styling

The widget maintains its 1920x1080 aspect ratio and will scale responsively:

```css
/* The widget container automatically adjusts */
iframe {
    width: 1920px;
    height: 1080px;
    max-width: 100%;
    aspect-ratio: 1920 / 1080;
    height: auto;
}
```

## Examples

### Example 1: Show all highlights for a date

```html
<div id="highlights-widget"
     data-spreadsheet-id="1xzFo8qBtGGSqW9V9UyaPVGqT6w5UIypw9hIgV3JZmto"
     data-sheet-name="AYG2025 Competition Schedule"
     data-date="2025-10-27">
</div>
<script src="http://localhost:5000/embed.js"></script>
```

### Example 2: Show highlights for a specific sport

```html
<div id="highlights-widget"
     data-spreadsheet-id="1xzFo8qBtGGSqW9V9UyaPVGqT6w5UIypw9hIgV3JZmto"
     data-sheet-name="AYG2025 Competition Schedule"
     data-sport="Swimming">
</div>
<script src="http://localhost:5000/embed.js"></script>
```

### Example 3: Show all highlights (no filters)

```html
<div id="highlights-widget"
     data-spreadsheet-id="1xzFo8qBtGGSqW9V9UyaPVGqT6w5UIypw9hIgV3JZmto"
     data-sheet-name="AYG2025 Competition Schedule">
</div>
<script src="http://localhost:5000/embed.js"></script>
```

## Troubleshooting

### Widget not loading

1. Check that the server is running: `python3 widget_server.py`
2. Verify the spreadsheet ID is correct (found in Google Sheets URL)
3. Ensure the sheet name matches exactly (case-sensitive)
4. Check browser console for JavaScript errors

### No highlights displayed

1. Verify your Google Sheet has data in the required columns
2. Check that the `DATE (SGP)` column is in YYYY-MM-DD format
3. Ensure at least one of the required columns has data for each row

### Credentials error

1. Make sure `GOOGLE_CREDENTIALS_JSON` environment variable is set, OR
2. Provide the correct path to `credentials_file` parameter
3. Verify the service account has access to the Google Sheet

## Development

### Running the server

```bash
# Default port 5000
python3 widget_server.py

# Custom port
PORT=8080 python3 widget_server.py
```

### Testing locally

1. Start the server: `python3 widget_server.py`
2. Open `http://localhost:5000` in your browser
3. Test the widget with your Google Sheet configuration

## Support

For issues or questions, please check:
1. The widget server logs for error messages
2. Browser console for JavaScript errors
3. The `/api/highlights` endpoint directly to verify data is loading

