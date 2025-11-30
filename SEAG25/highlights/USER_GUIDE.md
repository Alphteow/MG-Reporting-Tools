# SEAG25 Highlights Generator - User Guide

## 🎯 Overview

This guide helps non-technical users generate daily highlights images for SEAG25 with just a few clicks in Google Sheets.

## 📋 Prerequisites

- Access to the SEAG25 Competition Schedule Google Sheet
- Google account with edit permissions to the sheet
- Internet connection

## 🚀 Quick Start (5 minutes)

### Step 1: Add the Script to Your Google Sheet

1. Open your Google Sheet: [SEAG25 Competition Schedule](https://docs.google.com/spreadsheets/d/15zXDQdkGeAN2AMMdrJ_qjkjReq_Y3mlU1-_7ciniyS4)
2. Click **Extensions** → **Apps Script**
3. Delete any existing code in the editor
4. Copy the entire contents of `highlights-generator.txt` from this folder
5. Paste it into the Apps Script editor
6. Click **Save** (💾 icon) and give it a name like "SEAG25 Highlights Generator"
7. Click **Run** (▶️ icon) - you'll be asked to authorize
8. Click **Review Permissions** → Select your Google account → **Advanced** → **Go to [Project Name] (unsafe)** → **Allow**

### Step 2: Verify Configuration

The script is pre-configured, but you can verify:

1. In Apps Script editor, look for the `HIGHLIGHTS_CONFIG` section (around line 20)
2. Make sure these values are correct:
   - `FIREBASE_FUNCTION_URL`: Should be `https://us-central1-major-e910d.cloudfunctions.net/generateHighlightsHttpV2`
   - `SPREADSHEET_ID`: Should be `15zXDQdkGeAN2AMMdrJ_qjkjReq_Y3mlU1-_7ciniyS4`
   - `SHEET_NAME`: Should be `SEAG25 Competition Schedule` (or `Com Schedule - Test` for testing)
   - `DRIVE_FOLDER_ID`: Should be `1OR1P9sp0JQz0UyYd8hyn2P3F3B08GUBW`

### Step 3: Test the Connection

1. Go back to your Google Sheet
2. Refresh the page (F5 or Cmd+R)
3. You should see a new menu: **🏆 SEAG Highlights**
4. Click **🏆 SEAG Highlights** → **🔗 Test Connection**
5. If successful, you'll see a green success message

## 📅 Daily Usage

### Generate Highlights for Today

1. Open your Google Sheet
2. Click **🏆 SEAG Highlights** → **📅 Generate Highlights (Today)**
3. Wait 1-2 minutes (you'll see a progress dialog)
4. When done, you'll see a success message with a link to the folder
5. Click the link to view the generated images in Google Drive

### Generate Highlights for a Specific Date

1. Open your Google Sheet
2. Click **🏆 SEAG Highlights** → **📆 Generate Highlights (Select Date)**
3. Select the date from the calendar picker
4. Click **Generate Highlights**
5. Wait 1-2 minutes
6. View the generated images in Google Drive

## 📁 Where to Find Generated Images

1. Go to your Google Drive
2. Navigate to the **Highlights** folder (or the folder ID specified in config)
3. Open the date folder (e.g., `2025-12-10`)
4. You'll see:
   - `highlights_YYYY-MM-DD.html` - The HTML file (for reference)
   - `highlights_YYYY-MM-DD_slide_01.png` - First page image
   - `highlights_YYYY-MM-DD_slide_02.png` - Second page image (if multiple pages)
   - And so on...

## ⚠️ Troubleshooting

### "Connection Failed" Error

- **Check internet connection**
- **Verify Firebase Function is deployed**: Ask your technical team to check Firebase Console
- **Try the "Test Connection" option** to diagnose the issue

### "No highlights found" Message

- **Check the date**: Make sure there are gold medal results for that date
- **Verify sheet name**: Make sure `SHEET_NAME` in config matches your sheet name
- **Check data**: Ensure the competition schedule has data with `MEDAL` column set to "Gold"

### Script Takes Too Long

- **Normal**: The function can take 1-3 minutes depending on:
  - Number of highlights to generate
  - Number of pages/slides
  - Server load
- **If it times out**: Contact technical team to increase timeout limit

### Images Not Appearing in Drive

- **Check folder permissions**: Make sure you have access to the Drive folder
- **Check folder ID**: Verify `DRIVE_FOLDER_ID` in config is correct
- **Check logs**: In Apps Script editor, go to **Executions** tab to see error details

## 🔧 Advanced: Updating Configuration

If you need to change settings:

1. Open Apps Script editor (Extensions → Apps Script)
2. Find the `HIGHLIGHTS_CONFIG` section
3. Update the values you need
4. Click **Save**
5. Test with "Test Connection"

### Common Config Changes

**Change Sheet Name:**
```javascript
SHEET_NAME: 'SEAG25 Competition Schedule', // Change this
```

**Change Drive Folder:**
1. Open the Google Drive folder you want to use
2. Copy the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
3. Update `DRIVE_FOLDER_ID` in config

**Change Timeout (if function takes too long):**
```javascript
TIMEOUT_MS: 300000 // 5 minutes (increase if needed)
```

## 📞 Support

If you encounter issues:

1. **Check the logs**: Apps Script editor → **Executions** tab
2. **Try "Test Connection"** first
3. **Contact technical team** with:
   - Date you tried to generate
   - Error message (if any)
   - Screenshot of the error

## 🎉 Tips

- **Best time to run**: After all results for the day are entered
- **Frequency**: Run once per day, typically in the evening
- **Multiple runs**: You can run it multiple times for the same date (it will create new files)
- **File organization**: Files are automatically organized by date in subfolders

## 📝 Notes

- Only **Gold medal** results generate highlights
- The function processes all gold medals for the selected date
- Each "page" of highlights can contain multiple cards
- Images are PNG format, optimized for sharing on social media

