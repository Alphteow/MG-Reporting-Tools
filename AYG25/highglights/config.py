#!/usr/bin/env python3
"""
Configuration for Highlights Generator
"""

# Google Sheets Configuration
GOOGLE_SPREADSHEET_ID = '1xzFo8qBtGGSqW9V9UyaPVGqT6w5UIypw9hIgV3JZmto'
GOOGLE_SHEET_NAME = 'AYG2025 Competition Schedule'

# Credentials file path (relative to highlights directory or absolute path)
GOOGLE_CREDENTIALS_FILE = '../ayg-form-system/functions/google_credentials.json'

# Data configuration
DATA_START_ROW = 8  # Row where column headers are located

# Output configuration
OUTPUT_DIR = 'output'  # Directory where HTML files will be generated

# Column mappings (actual column names from Google Sheet)
COLUMN_MAPPINGS = {
    'SPORT': 'SPORT',
    'DISCIPLINE': 'DISCIPLINE',
    'EVENT': 'EVENT',
    'EVENT_GENDER': 'EVENT GENDER',
    'STAGE': 'STAGE / ROUND OF COMPETITION',
    'HEAT': 'HEAT NUMBER\n(e.g. Heat 3)',
    'VENUE': 'COMPETITION VENUE',
    'CITY': 'CITY / AREA',
    'DATE_SGP': 'DATE (SGP)',
    'TIME_START_SGP': 'TIME START (SGP) 24HR CLOCK',
    'TIME_END_SGP': 'TIME END (SGP) 24HR CLOCK',
    'ATHLETE_NAME': 'NAME OF ATHLETE (SGP)',
    'COUNTRY_SGP': 'COUNTRY NAME (SGP)',
    'TIMING_SGP': 'TIMING (SGP)\nhh:mm:ss.ms',
    'PERSONAL_BEST': 'PERSONAL BEST / BEST PERFORMANCE',
    'NATIONAL_RECORD': 'NATIONAL RECORD',
    'PB_NR': 'PB/NR',
    'SCORE_SGP': 'SCORE/DISTANCE/HEIGHT\n(SGP)',
    'SCORE_COMPETITOR': 'SCORE (COMPETITOR)',
    'COMPETITOR_NAME': 'NAME OF ATHLETE (COMPETITOR)',
    'COMPETITOR_COUNTRY': 'COUNTRY NAME (COMPETITOR)',
    'WIN_DRAW_LOSE': 'H2H WIN/DRAW/LOSE',
    'POSITION': 'POSITION IN ENTIRE ROUND',
    'TOTAL_COMPETITORS': 'NO OF COMPETITORS IN ENTIRE ROUND',
    'FINAL_POSITION': 'FINAL POSITION\nIN EVENT',
    'TOTAL_IN_EVENT': 'NUMBER OF COMPETITIORS\nIN EVENT',
    'ADVANCED': 'ADVANCED',
    'MEDALS': 'MEDALS',
    'HIGHLIGHTS': 'HIGHLIGHTS',
    'REMARKS': 'REMARKS'
}

# Grouping configuration
GROUP_BY_DATE = True  # Group highlights by date instead of sport

