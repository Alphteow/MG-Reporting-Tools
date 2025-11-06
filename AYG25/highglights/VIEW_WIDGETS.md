# How to View the Widgets as Carousels

## Method 1: Simple HTTP Server (Recommended)

Run this command in the `static_widgets` folder:

```bash
cd static_widgets
python3 -m http.server 8000
```

Then open in your browser:
- **http://localhost:8000/widget_2025-10-27.html** (or any date)
- **http://localhost:8000/**

You'll see all the widgets listed and can click to view them.

## Method 2: Open Directly in Browser

Simply double-click any HTML file in the `static_widgets` folder to open it in your default browser.

**Note:** Some browsers may have security restrictions when opening local files, so Method 1 is recommended.

## Method 3: Using the Widget Server

If you want to test the live API version:

```bash
python3 widget_server.py
```

Then visit:
- **http://localhost:5000/widget?spreadsheet_id=YOUR_ID&sheet_name=YOUR_SHEET&date=2025-10-27**

## What to Look For

When viewing the widgets, you should see:

1. **Red header** with "RESULTS" text
2. **Sections** grouped by sport and gender
3. **Carousel containers** with:
   - Navigation arrows (‹ and ›) on left and right
   - Result cards displayed horizontally (2 at a time)
   - Cards should scroll when clicking arrows
   
4. **Result cards** should be:
   - In a horizontal row (not stacked vertically)
   - Scrollable with arrow buttons
   - Showing 2 cards at a time

## Troubleshooting

If cards are still stacked vertically:
1. Hard refresh the page (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
2. Check browser console for JavaScript errors (F12)
3. Make sure `styles.css` is in the same folder as the HTML files

## Testing Carousel Functionality

1. Look for sections with multiple results (3+ cards)
2. Click the **right arrow (›)** to scroll forward
3. Click the **left arrow (‹)** to scroll back
4. Cards should slide smoothly horizontally
5. Arrows should disable at the start/end

