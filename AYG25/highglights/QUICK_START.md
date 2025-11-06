# Quick Start - Highlights Widget

## Two Ways to Use the Widget

### Option A: Static HTML Files (Recommended - No API Needed!)

**Best for:** Simple hosting, no live updates needed

1. **Generate static HTML files:**
   ```bash
   python3 generate_static_widget.py
   ```

2. **Share the files** from `static_widgets/` folder with developers

3. **Developers host the files** on any static hosting (GitHub Pages, Netlify, etc.)

**✅ No API deployment needed!**

---

### Option B: Live API (For Real-Time Updates)

**Best for:** Live data that updates automatically from Google Sheets

### Step 1: Install Dependencies

```bash
cd /path/to/highglights
pip3 install -r requirements.txt
```

### Step 2: Start the Server (or Deploy)

**Local testing:**
```bash
python3 widget_server.py
```

Server will start on `http://localhost:5000`

**Production deployment:** See `DEPLOYMENT_OPTIONS.md`

### Step 3: Embed in Your Page (API Method Only)

Add this to your HTML:

```html
<!-- Include the embed script -->
<script src="http://localhost:5000/embed.js"></script>

<!-- Create a container -->
<div id="highlights-widget"
     data-spreadsheet-id="YOUR_SPREADSHEET_ID"
     data-sheet-name="YOUR_SHEET_NAME">
</div>
```

**Replace:**
- `YOUR_SPREADSHEET_ID` - Your Google Sheets ID (from the URL)
- `YOUR_SHEET_NAME` - The name of the worksheet/tab
- `http://localhost:5000` - Your server URL (change for production)

### Optional: Filter by Date or Sport

```html
<div id="highlights-widget"
     data-spreadsheet-id="YOUR_SPREADSHEET_ID"
     data-sheet-name="YOUR_SHEET_NAME"
     data-date="2025-10-27"       
     data-sport="Swimming">         <!-- Show only this sport -->
</div>
```

## Required Google Sheet Columns

Make sure your Google Sheet has these columns:

- `SPORT`
- `EVENT`
- `EVENT GENDER`
- `STAGE / ROUND OF COMPETITION`
- `NAME OF ATHLETE (SGP)`
- `COUNTRY NAME (SGP)`
- `TIMING (SGP)\nhh:mm:ss.ms` (for non-H2H)
- `SCORE/DISTANCE/HEIGHT\n(SGP)` (for non-H2H or H2H)
- `NAME OF ATHLETE (COMPETITOR)` (for H2H)
- `COUNTRY NAME (COMPETITOR)` (for H2H)
- `SCORE (COMPETITOR)` (for H2H)
- `MEDALS` (optional: "Gold", "Silver", "Bronze")
- `PB/NR` (optional)
- `DATE (SGP)` (YYYY-MM-DD format)

## Widget Features

- Fixed 1920x1080 container (responsive)
- Carousel navigation
- Automatic H2H vs non-H2H detection
- Medal icons (🥇🥈🥉)
- PB/NR badges

## Full Documentation

See `WIDGET_README.md` for complete documentation.

