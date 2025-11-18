#!/usr/bin/env python3
"""
Daily Schedule Summary Generator for AYG25
Generates minimalistic daily schedule summaries from Google Sheets schedule data
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from jinja2 import Template

# Import config
try:
    from config import (
        GOOGLE_SPREADSHEET_ID,
        GOOGLE_CREDENTIALS_FILE,
        COLUMN_MAPPINGS
    )
except ImportError:
    GOOGLE_SPREADSHEET_ID = '1xzFo8qBtGGSqW9V9UyaPVGqT6w5UIypw9hIgV3JZmto'
    GOOGLE_CREDENTIALS_FILE = '../ayg-form-system/functions/google_credentials.json'
    COLUMN_MAPPINGS = {}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DailyScheduleGenerator:
    def __init__(self, spreadsheet_id=None, credentials_file=None):
        """
        Initialize the Daily Schedule Generator
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID (defaults to config)
            credentials_file: Path to Google credentials JSON file (defaults to config)
        """
        self.spreadsheet_id = spreadsheet_id or GOOGLE_SPREADSHEET_ID
        self.credentials_file = credentials_file or GOOGLE_CREDENTIALS_FILE
        self.gc = None
        self.worksheet = None
        self.output_dir = Path(__file__).parent / 'output'
        self.output_dir.mkdir(exist_ok=True)
        self.setup_google_sheets()
        
    def setup_google_sheets(self):
        """Setup Google Sheets connection"""
        try:
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Try to load credentials from environment variable first
            creds = None
            creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                try:
                    creds = Credentials.from_service_account_info(
                        json.loads(creds_json),
                        scopes=scope
                    )
                    logger.info("Loaded Google credentials from environment variable")
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}, trying file...")
                    creds = None
            
            # If not from environment variable, try to load from file
            if creds is None:
                creds_path = (Path(__file__).parent / self.credentials_file).resolve()
                if not creds_path.exists():
                    creds_path = Path(self.credentials_file).resolve()
                    if not creds_path.exists():
                        creds_path = (Path(__file__).parent.parent / self.credentials_file).resolve()
                        if not creds_path.exists():
                            raise FileNotFoundError(
                                f"Credentials file not found: {self.credentials_file}\n"
                                f"Set GOOGLE_CREDENTIALS_JSON environment variable or place credentials file."
                            )
                
                creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
                logger.info(f"Loaded Google credentials from: {creds_path}")
            
            self.gc = gspread.authorize(creds)
            spreadsheet = self.gc.open_by_key(self.spreadsheet_id)
            logger.info(f"Opened spreadsheet: {spreadsheet.title}")
            
            self.worksheet = spreadsheet.worksheet('AYG2025 Competition Schedule')
            logger.info(f"Found worksheet: {self.worksheet.title}")
            
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets: {str(e)}")
            raise e
    
    def load_schedule_data(self):
        """Load schedule data from Google Sheets"""
        try:
            all_values = self.worksheet.get_all_values()
            
            if not all_values or len(all_values) < 8:
                logger.warning("No data found or insufficient rows")
                return pd.DataFrame()
            
            # Headers are in row 8 (index 7)
            headers = all_values[7]
            
            # Data starts from row 9 (index 8)
            data_rows = all_values[8:]
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            logger.info(f"Total rows loaded: {len(df)}")
            logger.info(f"Total columns: {len(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading schedule data: {str(e)}")
            raise e
    
    def format_schedule_data(self, df):
        """Format and filter schedule data"""
        if df.empty:
            return []
        
        date_col = COLUMN_MAPPINGS.get('DATE_SGP', 'DATE (SGP)')
        time_col = COLUMN_MAPPINGS.get('TIME_START_SGP', 'TIME START (SGP) 24HR CLOCK')
        sport_col = COLUMN_MAPPINGS.get('SPORT', 'SPORT')
        discipline_col = COLUMN_MAPPINGS.get('DISCIPLINE', 'DISCIPLINE')
        event_col = COLUMN_MAPPINGS.get('EVENT', 'EVENT')
        stage_col = COLUMN_MAPPINGS.get('STAGE', 'STAGE / ROUND OF COMPETITION')
        athlete_col = COLUMN_MAPPINGS.get('ATHLETE_NAME', 'NAME OF ATHLETE (SGP)')
        
        schedule_items = []
        
        for _, row in df.iterrows():
            # Get date and time
            date_str = str(row.get(date_col, '')).strip()
            time_str = str(row.get(time_col, '')).strip()
            
            if not date_str or date_str.lower() in ('na', 'n/a', 'none', ''):
                continue
            
            # Parse date
            try:
                event_date = pd.to_datetime(date_str, errors='coerce')
                if pd.isna(event_date):
                    continue
            except:
                continue
            
            # Get sport and discipline
            sport = str(row.get(sport_col, '')).strip()
            discipline = str(row.get(discipline_col, '')).strip()
            
            if not sport:
                continue
            
            # Format sport header (sport - discipline if different, else just sport)
            if discipline and discipline.upper() != sport.upper():
                sport_header = f"{sport} - {discipline}"
            else:
                sport_header = sport
            
            # Get event and stage
            event = str(row.get(event_col, '')).strip()
            stage = str(row.get(stage_col, '')).strip()
            
            # Get athlete name
            athlete = str(row.get(athlete_col, '')).strip()
            
            schedule_items.append({
                'date': event_date,
                'date_str': date_str,
                'time': time_str,
                'sport': sport,
                'discipline': discipline,
                'sport_header': sport_header,
                'event': event if event and event.lower() not in ('na', 'n/a', 'none', '') else None,
                'stage': stage if stage and stage.lower() not in ('na', 'n/a', 'none', '') else None,
                'athlete': athlete if athlete and athlete.lower() not in ('na', 'n/a', 'none', '') else None
            })
        
        return schedule_items
    
    def filter_by_time_window(self, schedule_items, hours_ahead=24):
        """Filter schedule items to show events within the next N hours"""
        now = datetime.now()
        cutoff_time = now + timedelta(hours=hours_ahead)
        
        filtered = []
        for item in schedule_items:
            event_datetime = item['date']
            
            # If we have a time, try to parse it
            if item['time']:
                try:
                    # Try to parse time (format: HH:MM or HH:MM:SS)
                    time_parts = item['time'].split(':')
                    if len(time_parts) >= 2:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                        event_datetime = event_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except:
                    pass
            
            # Include if event is in the future and within the time window
            if event_datetime >= now and event_datetime <= cutoff_time:
                filtered.append(item)
        
        return filtered
    
    def group_by_sport(self, schedule_items):
        """Group schedule items by sport"""
        grouped = {}
        
        for item in schedule_items:
            sport_header = item['sport_header']
            if sport_header not in grouped:
                grouped[sport_header] = []
            grouped[sport_header].append(item)
        
        # Sort items within each sport by date/time
        for sport in grouped:
            grouped[sport].sort(key=lambda x: (x['date'], x['time'] or ''))
        
        return grouped
    
    def chunk_sports_into_slides(self, sports, grouped_items, max_sports_per_slide=9):
        """Split sports into multiple slides to fit on screen (3x3 grid = 9 sports per slide)"""
        slides = []
        current_slide = []
        
        for sport in sports:
            current_slide.append(sport)
            
            # 3x3 grid = 9 sports per slide (same as highlights)
            if len(current_slide) >= max_sports_per_slide:
                slides.append(current_slide)
                current_slide = []
        
        # Add remaining sports
        if current_slide:
            slides.append(current_slide)
        
        # If no slides, create at least one empty slide
        if not slides:
            slides.append([])
        
        return slides
    
    def generate_html(self, target_date=None, hours_ahead=24):
        """
        Generate HTML for daily schedule summary
        
        Args:
            target_date: Specific date to show (YYYY-MM-DD), or None for next 24 hours
            hours_ahead: Number of hours ahead to show (default 24)
        
        Returns:
            HTML string
        """
        df = self.load_schedule_data()
        schedule_items = self.format_schedule_data(df)
        
        # Filter by time window
        if target_date:
            # Filter to specific date
            try:
                target = pd.to_datetime(target_date)
                schedule_items = [item for item in schedule_items if item['date'].date() == target.date()]
            except:
                logger.warning(f"Invalid target_date: {target_date}")
        else:
            # Filter to next N hours
            schedule_items = self.filter_by_time_window(schedule_items, hours_ahead)
        
        # Group by sport
        grouped_by_sport = self.group_by_sport(schedule_items)
        
        # Sort sports alphabetically
        sorted_sports = sorted(grouped_by_sport.keys())
        
        # Chunk sports into slides
        slides = self.chunk_sports_into_slides(sorted_sports, grouped_by_sport, max_sports_per_slide=12)
        
        # Load template
        template_path = Path(__file__).parent / 'templates' / 'schedule_template.html'
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                html_template = Template(template_content)
        else:
            html_template = self.get_default_template()
        
        # Format date for title
        if target_date:
            try:
                target = pd.to_datetime(target_date)
                formatted_date = target.strftime('%d %B %Y')
            except:
                formatted_date = target_date
        else:
            formatted_date = datetime.now().strftime('%d %B %Y')
        
        html_content = html_template.render(
            date=formatted_date,
            sports=sorted_sports,
            grouped_items=grouped_by_sport,
            slides=slides,
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        return html_content
    
    def generate_all(self, target_date=None, hours_ahead=24):
        """Generate HTML file for schedule summary"""
        try:
            html_content = self.generate_html(target_date, hours_ahead)
            
            # Generate filename
            if target_date:
                filename = f"schedule_{target_date.replace('-', '_')}.html"
            else:
                filename = f"schedule_{datetime.now().strftime('%Y_%m_%d')}.html"
            
            output_file = self.output_dir / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Generated schedule summary: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating schedule: {str(e)}")
            raise e
    
    def get_default_template(self):
        """Return default HTML template as string"""
        return Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Schedule - {{ date }}</title>
</head>
<body>
    <h1>Daily Schedule - {{ date }}</h1>
    {% for sport in sports %}
    <h2>{{ sport }}</h2>
    <ul>
        {% for item in grouped_items[sport] %}
        <li>{{ item.time }} - {{ item.athlete or 'TBD' }}</li>
        {% endfor %}
    </ul>
    {% endfor %}
</body>
</html>
        """)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate daily schedule summaries from Google Sheets')
    parser.add_argument('--date', type=str, default=None,
                       help='Specific date to show (YYYY-MM-DD). If not specified, shows next 24 hours.')
    parser.add_argument('--hours', type=int, default=24,
                       help='Number of hours ahead to show (default: 24)')
    parser.add_argument('--spreadsheet-id', type=str, default=None,
                       help='Google Sheets spreadsheet ID (defaults to config.py)')
    parser.add_argument('--credentials', type=str, default=None,
                       help='Path to Google credentials JSON file (defaults to config.py)')
    
    args = parser.parse_args()
    
    try:
        generator = DailyScheduleGenerator(
            spreadsheet_id=args.spreadsheet_id,
            credentials_file=args.credentials
        )
        generator.generate_all(target_date=args.date, hours_ahead=args.hours)
    except Exception as e:
        logger.error(f"Failed to generate schedule: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

