#!/usr/bin/env python3
"""
Highlights Generator for AYG25 Competition Results
Generates HTML highlights pages from Google Sheets data, grouped by sport
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from jinja2 import Template

# Import config
try:
    from config import (
        GOOGLE_SPREADSHEET_ID,
        GOOGLE_SHEET_NAME,
        GOOGLE_CREDENTIALS_FILE,
        DATA_START_ROW,
        COLUMN_MAPPINGS,
        GROUP_BY_DATE
    )
except ImportError:
    # Fallback if config.py doesn't exist
    GOOGLE_SPREADSHEET_ID = '1xzFo8qBtGGSqW9V9UyaPVGqT6w5UIypw9hIgV3JZmto'
    GOOGLE_SHEET_NAME = 'Data Collection'
    GOOGLE_CREDENTIALS_FILE = 'google_credentials.json'
    DATA_START_ROW = 8
    COLUMN_MAPPINGS = {}
    GROUP_BY_DATE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HighlightsGenerator:
    def __init__(self, spreadsheet_id=None, sheet_name=None, credentials_file=None):
        """
        Initialize the Highlights Generator
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID (defaults to config)
            sheet_name: Name of the worksheet to read from (defaults to config)
            credentials_file: Path to Google credentials JSON file (defaults to config)
        """
        self.spreadsheet_id = spreadsheet_id or GOOGLE_SPREADSHEET_ID
        self.sheet_name = sheet_name or GOOGLE_SHEET_NAME
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
            
            # Try to load credentials from environment variable first (like other parts of the system)
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
                # Try as relative path from highlights directory first
                creds_path = (Path(__file__).parent / self.credentials_file).resolve()
                if not creds_path.exists():
                    # Try as absolute path (if provided as absolute)
                    creds_path = Path(self.credentials_file).resolve()
                    if not creds_path.exists():
                        # Try from project root (parent of highlights directory)
                        creds_path = (Path(__file__).parent.parent / self.credentials_file).resolve()
                        if not creds_path.exists():
                            raise FileNotFoundError(
                                f"Credentials file not found: {self.credentials_file}\n"
                                f"Tried: {(Path(__file__).parent / self.credentials_file).resolve()}\n"
                                f"Tried: {Path(self.credentials_file).resolve()}\n"
                                f"Tried: {(Path(__file__).parent.parent / self.credentials_file).resolve()}\n"
                                f"Set GOOGLE_CREDENTIALS_JSON environment variable or place credentials file."
                            )
                
                creds = Credentials.from_service_account_file(str(creds_path), scopes=scope)
                logger.info(f"Loaded Google credentials from: {creds_path}")
            
            self.gc = gspread.authorize(creds)
            spreadsheet = self.gc.open_by_key(self.spreadsheet_id)
            logger.info(f"Opened spreadsheet: {spreadsheet.title}")
            
            self.worksheet = spreadsheet.worksheet(self.sheet_name)
            logger.info(f"Found worksheet: {self.sheet_name}")
            
        except Exception as e:
            logger.error(f"Error setting up Google Sheets: {str(e)}")
            raise e
    
    def load_data(self, start_row=None):
        """
        Load data from Google Sheets starting from specified row
        
        Args:
            start_row: Row number where data starts (defaults to DATA_START_ROW from config)
        
        Returns:
            DataFrame with the data
        """
        try:
            if start_row is None:
                start_row = DATA_START_ROW
            
            # Get all values starting from specified row (where headers are)
            all_values = self.worksheet.get_all_values()
            
            if len(all_values) < start_row:
                logger.warning(f"Sheet has fewer than {start_row} rows")
                return pd.DataFrame()
            
            # Row 8 (index 7) contains headers
            headers = all_values[start_row - 1]
            
            # Get data rows (starting from row 9, index 8)
            data_rows = all_values[start_row:]
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Clean up column names (remove extra spaces, handle special characters)
            df.columns = df.columns.str.strip()
            
            logger.info(f"Total rows loaded: {len(df)}")
            logger.info(f"Total columns: {len(df.columns)}")
            logger.info(f"Column names: {list(df.columns)[:10]}...")  # Show first 10 columns
            
            # Check for required columns and filter rows that have enough data to generate highlights
            # Get column mappings
            sport_col = COLUMN_MAPPINGS.get('SPORT', 'SPORT')
            event_col = COLUMN_MAPPINGS.get('EVENT', 'EVENT')
            stage_col = COLUMN_MAPPINGS.get('STAGE', 'STAGE / ROUND OF COMPETITION')
            athlete_col = COLUMN_MAPPINGS.get('ATHLETE_NAME', 'NAME OF ATHLETE (SGP)')
            competitor_name_col = COLUMN_MAPPINGS.get('COMPETITOR_NAME', 'NAME OF ATHLETE (COMPETITOR)')
            competitor_country_col = COLUMN_MAPPINGS.get('COMPETITOR_COUNTRY', 'COUNTRY NAME (COMPETITOR)')
            score_sgp_col = COLUMN_MAPPINGS.get('SCORE_SGP', 'SCORE/DISTANCE/HEIGHT\n(SGP)')
            score_competitor_col = COLUMN_MAPPINGS.get('SCORE_COMPETITOR', 'SCORE (COMPETITOR)')
            timing_sgp_col = COLUMN_MAPPINGS.get('TIMING_SGP', 'TIMING (SGP)\nhh:mm:ss.ms')
            
            # Check which columns exist
            available_cols = set(df.columns)
            
            # Filter rows that have enough data to generate highlights
            before_count = len(df)
            valid_rows = []
            
            def has_value(col, row):
                """Check if column exists and has a non-empty value"""
                if col not in available_cols:
                    return False
                val = row.get(col)
                return pd.notna(val) and str(val).strip() != ''
            
            for idx, row in df.iterrows():
                # Check if it's H2H (has competitor name and country)
                has_competitor_name = has_value(competitor_name_col, row)
                has_competitor_country = has_value(competitor_country_col, row)
                is_h2h = has_competitor_name and has_competitor_country
                
                if is_h2h:
                    # H2H sport requirements:
                    # - SPORT, EVENT, STAGE, ATHLETE(SGP), COMPETITOR_NAME, COMPETITOR_COUNTRY
                    # - At least one of: SCORE(SGP) or SCORE(COMPETITOR)
                    has_basic = (has_value(sport_col, row) and 
                                has_value(event_col, row) and 
                                has_value(stage_col, row) and 
                                has_value(athlete_col, row))
                    has_score = has_value(score_sgp_col, row) or has_value(score_competitor_col, row)
                    
                    if has_basic and has_score:
                        valid_rows.append(idx)
                else:
                    # Non-H2H sport requirements:
                    # - SPORT, EVENT, STAGE, ATHLETE(SGP)
                    # - At least one of: TIMING(SGP) or SCORE(SGP)
                    has_basic = (has_value(sport_col, row) and 
                                has_value(event_col, row) and 
                                has_value(stage_col, row) and 
                                has_value(athlete_col, row))
                    has_result = has_value(timing_sgp_col, row) or has_value(score_sgp_col, row)
                    
                    if has_basic and has_result:
                        valid_rows.append(idx)
            
            df = df.loc[valid_rows].copy()
            after_count = len(df)
            
            logger.info(f"Rows before filtering: {before_count}")
            logger.info(f"Rows after filtering (with enough data for highlights): {after_count}")
            
            if after_count == 0:
                logger.warning("No rows with enough data to generate highlights found")
            
            logger.info(f"Loaded {len(df)} rows with highlights data")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise e
    
    def categorize_highlight(self, row):
        """
        Determine if a highlight is H2H (head-to-head) or non-H2H
        
        Args:
            row: DataFrame row
        
        Returns:
            'h2h' or 'non-h2h'
        """
        # Check if there's competitor information using actual column names
        competitor_cols = [
            COLUMN_MAPPINGS.get('COMPETITOR_NAME', 'NAME OF ATHLETE (COMPETITOR)'),
            COLUMN_MAPPINGS.get('COMPETITOR_COUNTRY', 'COUNTRY NAME (COMPETITOR)'),
            COLUMN_MAPPINGS.get('SCORE_COMPETITOR', 'SCORE (COMPETITOR)'),
            COLUMN_MAPPINGS.get('WIN_DRAW_LOSE', 'H2H WIN/DRAW/LOSE')
        ]
        
        for col in competitor_cols:
            if col in row.index and pd.notna(row.get(col)) and str(row[col]).strip() != '':
                return 'h2h'
        
        return 'non-h2h'
    
    def format_timing(self, timing_str):
        """
        Remove "00:", "0:" at start and ":00:" if present
        Example: "00:02:00.94" -> "02:00.94", "0:2:00.94" -> "2:00.94", "00:00:23.45" -> "23.45"
        
        Args:
            timing_str: Timing string in format hh:mm:ss.ms or mm:ss.ms
        
        Returns:
            Formatted timing string with "00:", "0:", and ":00:" removed
        """
        if not timing_str or pd.isna(timing_str):
            return ''
        
        timing_str = str(timing_str).strip()
        if not timing_str:
            return ''
        
        result = timing_str
        
        # Remove "00:" from the start if present
        if result.startswith('00:'):
            result = result[3:]  # Remove "00:" (3 characters)
        # Remove "0:" from the start if present (after checking for "00:")
        elif result.startswith('0:'):
            result = result[2:]  # Remove "0:" (2 characters)
        
        # Remove ":00:" if present (zero minutes)
        result = result.replace(':00:', ':')
        
        return result
    
    def format_highlight_data(self, row):
        """
        Format a row of data into a structured highlight entry
        
        Args:
            row: DataFrame row
        
        Returns:
            Dictionary with formatted highlight data
        """
        # Use column mappings to get actual column names
        def get_col(key):
            col_name = COLUMN_MAPPINGS.get(key, key)
            return row.get(col_name, '')
        
        timing_raw = get_col('TIMING_SGP')
        
        highlight = {
            'sport': get_col('SPORT'),
            'discipline': get_col('DISCIPLINE'),
            'event': get_col('EVENT'),
            'event_gender': get_col('EVENT_GENDER'),
            'stage': get_col('STAGE'),
            'heat': get_col('HEAT'),
            'venue': get_col('VENUE'),
            'city': get_col('CITY'),
            'date_sgp': get_col('DATE_SGP'),
            'time_start_sgp': get_col('TIME_START_SGP'),
            'time_end_sgp': get_col('TIME_END_SGP'),
            'athlete_name': get_col('ATHLETE_NAME'),
            'country_sgp': get_col('COUNTRY_SGP'),
            'timing_sgp': self.format_timing(timing_raw),
            'personal_best': get_col('PERSONAL_BEST'),
            'national_record': get_col('NATIONAL_RECORD'),
            'pb_nr': get_col('PB_NR'),
            'score_sgp': get_col('SCORE_SGP'),
            'score_competitor': get_col('SCORE_COMPETITOR'),
            'competitor_name': get_col('COMPETITOR_NAME'),
            'competitor_country': get_col('COMPETITOR_COUNTRY'),
            'win_draw_lose': get_col('WIN_DRAW_LOSE'),
            'position': get_col('POSITION'),
            'total_competitors': get_col('TOTAL_COMPETITORS'),
            'final_position': get_col('FINAL_POSITION'),
            'total_in_event': get_col('TOTAL_IN_EVENT'),
            'advanced': get_col('ADVANCED'),
            'medals': get_col('MEDALS'),
            'highlights_text': self.generate_highlights_text(row),
            'remarks': get_col('REMARKS'),
            'type': self.categorize_highlight(row)
        }
        
        return highlight
    
    def generate_highlights_text(self, row):
        """
        Generate highlights text automatically based on available data
        
        Args:
            row: DataFrame row
        
        Returns:
            String with generated highlights text
        """
        def get_col(key):
            col_name = COLUMN_MAPPINGS.get(key, key)
            val = row.get(col_name, '')
            return str(val).strip() if pd.notna(val) else ''
        
        sport = get_col('SPORT')
        event = get_col('EVENT')
        stage = get_col('STAGE')
        athlete_name = get_col('ATHLETE_NAME')
        competitor_name = get_col('COMPETITOR_NAME')
        competitor_country = get_col('COMPETITOR_COUNTRY')
        score_sgp = get_col('SCORE_SGP')
        score_competitor = get_col('SCORE_COMPETITOR')
        timing_sgp = get_col('TIMING_SGP')
        
        # Determine if H2H
        is_h2h = competitor_name and competitor_country
        
        if is_h2h:
            # H2H format: SPORT, EVENT, STAGE, ATHLETE(SGP), COMPETITOR, COUNTRY, SCORE(SGP), SCORE(COMPETITOR)
            parts = []
            if sport:
                parts.append(sport)
            if event:
                parts.append(event)
            if stage:
                parts.append(stage)
            if athlete_name:
                parts.append(f"{athlete_name} (SGP)")
            if competitor_name:
                if competitor_country:
                    parts.append(f"vs {competitor_name} ({competitor_country})")
                else:
                    parts.append(f"vs {competitor_name}")
            
            result_parts = []
            if score_sgp and score_competitor:
                result_parts.append(f"{score_sgp}-{score_competitor}")
            elif score_sgp:
                result_parts.append(score_sgp)
            elif score_competitor:
                result_parts.append(f"Opponent: {score_competitor}")
            
            if result_parts:
                return " | ".join(parts + result_parts)
            else:
                return " | ".join(parts)
        else:
            # Non-H2H format: SPORT, EVENT, STAGE, ATHLETE(SGP), TIMING or SCORE
            parts = []
            if sport:
                parts.append(sport)
            if event:
                parts.append(event)
            if stage:
                parts.append(stage)
            if athlete_name:
                parts.append(f"{athlete_name} (SGP)")
            
            result_parts = []
            if timing_sgp:
                result_parts.append(f"Time: {timing_sgp}")
            elif score_sgp:
                result_parts.append(f"Score: {score_sgp}")
            
            if result_parts:
                return " | ".join(parts + result_parts)
            else:
                return " | ".join(parts)
    
    def group_highlights(self, df):
        """
        Group highlights data by date or sport (based on config)
        
        Args:
            df: DataFrame with highlights data
        
        Returns:
            Dictionary mapping date/sport names to lists of highlight entries
        """
        grouped_data = {}
        date_col = COLUMN_MAPPINGS.get('DATE_SGP', 'DATE (SGP)')
        sport_col = COLUMN_MAPPINGS.get('SPORT', 'SPORT')
        
        for _, row in df.iterrows():
            if GROUP_BY_DATE:
                # Group by date
                date_key = row.get(date_col, 'Unknown Date')
                if pd.isna(date_key) or str(date_key).strip() == '':
                    date_key = 'Unknown Date'
                else:
                    # Format date nicely (handle YYYY-MM-DD format)
                    try:
                        date_str = str(date_key).strip()
                        # Try to parse and format date if it's in a standard format
                        try:
                            from datetime import datetime as dt
                            parsed_date = dt.strptime(date_str, '%Y-%m-%d')
                            date_key = parsed_date.strftime('%Y-%m-%d')  # Keep consistent format
                        except ValueError:
                            # If parsing fails, use the string as-is
                            date_key = date_str
                    except:
                        date_key = 'Unknown Date'
                
                key = date_key
            else:
                # Group by sport
                sport = row.get(sport_col, 'Unknown')
                if pd.isna(sport) or str(sport).strip() == '':
                    sport = 'Unknown'
                key = sport
            
            if key not in grouped_data:
                grouped_data[key] = []
            
            highlight = self.format_highlight_data(row)
            grouped_data[key].append(highlight)
        
        if GROUP_BY_DATE:
            logger.info(f"Grouped highlights into {len(grouped_data)} dates")
            for date, highlights in sorted(grouped_data.items()):
                logger.info(f"   - {date}: {len(highlights)} highlights")
        else:
            logger.info(f"Grouped highlights into {len(grouped_data)} sports")
            for sport, highlights in grouped_data.items():
                logger.info(f"   - {sport}: {len(highlights)} highlights")
        
        return grouped_data
    
    def generate_html(self, group_key, highlights):
        """
        Generate HTML page for highlights grouped by date or sport
        
        Args:
            group_key: Date or sport name
            highlights: List of highlight dictionaries
        
        Returns:
            HTML string
        """
        # Load HTML template
        template_path = Path(__file__).parent / 'templates' / 'highlights_template.html'
        
        # Load template
        if not template_path.exists():
            logger.warning(f"Template not found at {template_path}, using default template")
            html_template = self.get_default_template()
        else:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                html_template = Template(template_content)
        
        # Separate H2H and non-H2H highlights
        h2h_highlights = [h for h in highlights if h['type'] == 'h2h']
        non_h2h_highlights = [h for h in highlights if h['type'] == 'non-h2h']
        
        # Group highlights by sport and gender for template
        def group_by_sport_gender(highlight_list):
            """Group highlights by sport and gender"""
            groups = {}
            for h in highlight_list:
                sport = h.get('sport', 'Unknown')
                gender = h.get('event_gender', 'Mixed')
                key = f"{sport}|{gender}"
                
                if key not in groups:
                    groups[key] = {
                        'sport': sport,
                        'gender': gender,
                        'highlights': []
                    }
                groups[key]['highlights'].append(h)
            
            # Group each sport's highlights by event
            for key, group in groups.items():
                events = {}
                for h in group['highlights']:
                    event = h.get('event', 'Unknown')
                    stage = h.get('stage', '')
                    event_key = f"{event}|{stage}"
                    
                    if event_key not in events:
                        events[event_key] = {
                            'event': event,
                            'stage': stage,
                            'highlights': []
                        }
                    events[event_key]['highlights'].append(h)
                
                group['events'] = list(events.values())
            
            return list(groups.values())
        
        h2h_groups = group_by_sport_gender(h2h_highlights)
        non_h2h_groups = group_by_sport_gender(non_h2h_highlights)
        
        # Combine groups into sections that fit within 1080px
        # Header is 60px, padding is 40px, so we have ~980px for content
        def estimate_group_height(group):
            """Estimate the height needed for a group"""
            num_events = len(group.get('events', []))
            # Sport title: 36.88px
            # Gender subtitle: ~30px (estimated, with margin-bottom: 20px)
            # Spacing between sections: ~20px
            # Each event-column: 160.12px (includes event title + all highlights in that column)
            # Events are arranged in a grid with minmax(350px, 1fr), so with 1920px width,
            # we can fit approximately 5 columns (1920 / 350 ≈ 5.5, so max 5 columns)
            # Grid has gap: 20px between items, and margin-bottom: 20px on events-row
            # Calculate number of rows: ceil(num_events / 5)
            sport_title_height = 36.88
            gender_subtitle_height = 30 + 20  # Subtitle + margin-bottom
            spacing_height = 20  # Margin between sport sections
            event_column_height = 160.12
            grid_gap = 20  # Gap between grid items
            events_row_margin = 20  # margin-bottom on events-row
            max_columns = 5  # Based on minmax(350px, 1fr) in 1920px width
            num_rows = (num_events + max_columns - 1) // max_columns  # Ceiling division
            
            base_height = sport_title_height + gender_subtitle_height + spacing_height
            # For grid rows: (num_rows - 1) gaps between rows + events_row_margin for last row
            grid_spacing = (num_rows - 1) * grid_gap if num_rows > 1 else 0
            events_height = (num_rows * event_column_height) + grid_spacing + events_row_margin
            
            # Add safety margin of 5% to account for any variations
            total_height = (base_height + events_height) * 1.05
            
            return total_height
        
        # Combine all groups into sections
        all_groups = []
        for group in non_h2h_groups:
            all_groups.append({'type': 'non_h2h', 'group': group})
        for group in h2h_groups:
            all_groups.append({'type': 'h2h', 'group': group})
        
        # Group into sections that fit within 1080px
        sections = []
        current_section = []
        current_height = 60  # Header height
        
        for group_data in all_groups:
            group = group_data['group']
            estimated_height = estimate_group_height(group)
            
            logger.debug(f"Group: {group.get('sport', 'Unknown')} - {group.get('gender', 'Unknown')}, "
                       f"Events: {len(group.get('events', []))}, "
                       f"Estimated height: {estimated_height:.2f}px, "
                       f"Current section height: {current_height:.2f}px, "
                       f"Would be: {current_height + estimated_height:.2f}px")
            
            # If adding this group would exceed 1080px, start a new section
            # Use a conservative threshold of 950px to leave buffer for padding and variations
            # Header is 60px, so we have ~1020px for content, but use 950px as safe limit
            if current_height + estimated_height > 950 and current_section:
                logger.debug(f"Starting new section. Previous section had {len(current_section)} groups")
                sections.append(current_section)
                current_section = []
                current_height = 60  # Reset to header height
            
            current_section.append(group_data)
            current_height += estimated_height
        
        # Add the last section if it has content
        if current_section:
            sections.append(current_section)
        
        # Check if next section has only 1 column total, merge it into previous section
        merged_sections = []
        i = 0
        while i < len(sections):
            current_section = sections[i]
            
            # Check if this section has only 1 group with 1 event (1 column total)
            if len(current_section) == 1:
                group_data = current_section[0]
                group = group_data['group']
                num_events = len(group.get('events', []))
                
                if num_events == 1:
                    # Check if we can merge with previous section
                    if merged_sections:
                        prev_section = merged_sections[-1]
                        # Estimate if adding this 1-column group would fit
                        # Calculate total height: header (60px) + sum of all group heights
                        estimated_height = estimate_group_height(group)
                        prev_height = 60  # Header height
                        prev_height += sum(estimate_group_height(g['group']) for g in prev_section)
                        
                        if prev_height + estimated_height <= 950:
                            # Merge into previous section
                            prev_section.append(group_data)
                            logger.debug(f"Merged 1-column section into previous section. New height: {prev_height + estimated_height:.2f}px")
                            i += 1
                            continue
            
            # Keep section as is
            merged_sections.append(current_section)
            i += 1
        
        sections = merged_sections
        
        # Determine title based on grouping mode
        if GROUP_BY_DATE:
            title = f"Highlights - {group_key}"
            subtitle = "AYG25 Competition Results"
        else:
            title = f"{group_key} Highlights"
            subtitle = "AYG25 Competition Results"
        
        # Render template
        html_content = html_template.render(
            sport=group_key,
            title=title,
            subtitle=subtitle,
            sections=sections,
            h2h_groups=h2h_groups,
            non_h2h_groups=non_h2h_groups,
            h2h_highlights=h2h_highlights,
            non_h2h_highlights=non_h2h_highlights,
            all_highlights=highlights,
            generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        return html_content
    
    def get_default_template(self):
        """Return default HTML template as string"""
        return Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ sport }} - Highlights</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ sport }} Highlights</h1>
            <p class="subtitle">AYG25 Competition Results</p>
            <p class="generated">Generated: {{ generation_date }}</p>
        </header>
        
        {% if h2h_highlights %}
        <section class="highlights-section h2h-section">
            <h2>Head-to-Head Highlights</h2>
            {% for highlight in h2h_highlights %}
            <div class="highlight-card h2h-card">
                <div class="highlight-header">
                    <h3>{{ highlight.event }} - {{ highlight.stage }}</h3>
                    {% if highlight.date_sgp %}
                    <span class="date">{{ highlight.date_sgp }}</span>
                    {% endif %}
                </div>
                <div class="highlight-content">
                    <div class="athlete-info">
                        <div class="athlete">
                            <strong>{{ highlight.athlete_name }}</strong>
                            <span class="country">({{ highlight.country_sgp }})</span>
                        </div>
                        <div class="vs">VS</div>
                        <div class="athlete">
                            <strong>{{ highlight.competitor_name }}</strong>
                            <span class="country">({{ highlight.competitor_country }})</span>
                        </div>
                    </div>
                    <div class="result">
                        {% if highlight.score_sgp and highlight.score_competitor %}
                        <div class="score">{{ highlight.score_sgp }} - {{ highlight.score_competitor }}</div>
                        {% elif highlight.timing_sgp %}
                        <div class="timing">{{ highlight.timing_sgp }}</div>
                        {% endif %}
                        {% if highlight.win_draw_lose %}
                        <div class="result-badge {{ highlight.win_draw_lose.lower() }}">{{ highlight.win_draw_lose }}</div>
                        {% endif %}
                    </div>
                    <div class="highlights-text">{{ highlight.highlights_text }}</div>
                    {% if highlight.medals %}
                    <div class="medal-badge">{{ highlight.medals }}</div>
                    {% endif %}
                    {% if highlight.pb_nr %}
                    <div class="record-badge">{{ highlight.pb_nr }}</div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </section>
        {% endif %}
        
        {% if non_h2h_highlights %}
        <section class="highlights-section non-h2h-section">
            <h2>Individual Highlights</h2>
            {% for highlight in non_h2h_highlights %}
            <div class="highlight-card non-h2h-card">
                <div class="highlight-header">
                    <h3>{{ highlight.event }} - {{ highlight.stage }}</h3>
                    {% if highlight.date_sgp %}
                    <span class="date">{{ highlight.date_sgp }}</span>
                    {% endif %}
                </div>
                <div class="highlight-content">
                    <div class="athlete-info-single">
                        <strong>{{ highlight.athlete_name }}</strong>
                        <span class="country">({{ highlight.country_sgp }})</span>
                    </div>
                    <div class="result">
                        {% if highlight.score_sgp %}
                        <div class="score">{{ highlight.score_sgp }}</div>
                        {% elif highlight.timing_sgp %}
                        <div class="timing">{{ highlight.timing_sgp }}</div>
                        {% endif %}
                        {% if highlight.position and highlight.total_competitors %}
                        <div class="position">Position: {{ highlight.position }}/{{ highlight.total_competitors }}</div>
                        {% endif %}
                    </div>
                    <div class="highlights-text">{{ highlight.highlights_text }}</div>
                    {% if highlight.medals %}
                    <div class="medal-badge">{{ highlight.medals }}</div>
                    {% endif %}
                    {% if highlight.pb_nr %}
                    <div class="record-badge">{{ highlight.pb_nr }}</div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </section>
        {% endif %}
    </div>
</body>
</html>
        """)
    
    def generate_all(self):
        """
        Generate highlights pages for all sports
        """
        try:
            # Load data from Google Sheets
            df = self.load_data(start_row=8)
            
            if df.empty:
                logger.warning("No highlights data found")
                return
            
            # Group highlights by date or sport
            grouped_data = self.group_highlights(df)
            
            # Copy CSS file to output directory if it doesn't exist (once)
            css_source = Path(__file__).parent / 'styles.css'
            css_dest = self.output_dir / 'styles.css'
            if css_source.exists() and not css_dest.exists():
                import shutil
                shutil.copy2(css_source, css_dest)
                logger.info(f"Copied styles.css to output directory")
            
            # Generate HTML for each group (date or sport)
            for group_key, highlights in grouped_data.items():
                # Sanitize key for filename
                if GROUP_BY_DATE:
                    # For dates, format as YYYY-MM-DD or keep original
                    safe_name = "".join(c for c in str(group_key) if c.isalnum() or c in (' ', '-', '_', '/')).strip()
                    safe_name = safe_name.replace(' ', '_').replace('/', '-')
                    filename = f"highlights_{safe_name}.html"
                else:
                    safe_name = "".join(c for c in group_key if c.isalnum() or c in (' ', '-', '_')).strip()
                    safe_name = safe_name.replace(' ', '_')
                    filename = f"{safe_name}_highlights.html"
                
                html_content = self.generate_html(group_key, highlights)
                
                # Save HTML file
                output_file = self.output_dir / filename
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                logger.info(f"Generated highlights page: {output_file}")
            
            logger.info(f"Successfully generated {len(grouped_data)} highlights pages")
            logger.info(f"Output directory: {self.output_dir}")
            
        except Exception as e:
            logger.error(f"Error generating highlights: {str(e)}")
            raise e


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate highlights pages from Google Sheets')
    parser.add_argument('--spreadsheet-id', type=str, 
                       default=None,
                       help='Google Sheets spreadsheet ID (defaults to config.py)')
    parser.add_argument('--sheet-name', type=str, default=None,
                       help='Worksheet name (defaults to config.py)')
    parser.add_argument('--credentials', type=str, default=None,
                       help='Path to Google credentials JSON file (defaults to config.py)')
    
    args = parser.parse_args()
    
    try:
        generator = HighlightsGenerator(
            spreadsheet_id=args.spreadsheet_id,
            sheet_name=args.sheet_name,
            credentials_file=args.credentials
        )
        generator.generate_all()
    except Exception as e:
        logger.error(f"Failed to generate highlights: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

