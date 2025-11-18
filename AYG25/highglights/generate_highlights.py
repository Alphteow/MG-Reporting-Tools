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
    
    def _create_medal_tally_card(self, highlights):
        """Create a medal tally card showing total medals for the day."""
        gold_count = 0
        silver_count = 0
        bronze_count = 0
        
        for highlight in highlights:
            medals = (highlight.get('medals') or '').strip()
            if not medals:
                continue
            medal_key = str(medals).lower()
            if medal_key in ('na', 'n/a', 'none', 'no medal', 'nil'):
                continue
            if 'gold' in medal_key:
                gold_count += 1
            elif 'silver' in medal_key:
                silver_count += 1
            elif 'bronze' in medal_key:
                bronze_count += 1
        
        total_medals = gold_count + silver_count + bronze_count
        
        # Only create tally card if there are medals
        if total_medals == 0:
            return None
        
        tally_text = []
        if gold_count > 0:
            tally_text.append(f"{gold_count} 🥇")
        if silver_count > 0:
            tally_text.append(f"{silver_count} 🥈")
        if bronze_count > 0:
            tally_text.append(f"{bronze_count} 🥉")
        
        return {
            'index': 0,  # Will be re-indexed
            'sport': 'MEDAL TALLY',
            'sport_icon': '🏅',
            'sport_tags': [],
            'medal_label': '',
            'medal_icon': '',
            'athletes': '',
            'event_details': f"Total: {total_medals} Medals",
            'result_summary': ' | '.join(tally_text) if tally_text else 'No medals',
            'result_badge': '',
            'competitors': [],
            'is_tally_card': True
        }
    
    def build_result_cards(self, group_key, highlights):
        """
        Prepare the list of card dictionaries for rendering.
        Includes sample placeholders only if no highlights are available.
        """
        cards = []
        
        for highlight in highlights:
            card = self._card_from_highlight(highlight, len(cards) + 1, group_key)
            cards.append(card)
        
        if not cards:
            sample_cards = self._example_cards()
            for idx, example in enumerate(sample_cards, start=1):
                card_copy = dict(example)
                card_copy['index'] = idx
                cards.append(card_copy)
        
        # Sort cards alphabetically by sport header
        cards.sort(key=lambda x: x.get('sport', '').upper())
        
        # Re-index cards after sorting
        for idx, card in enumerate(cards, start=1):
            card['index'] = idx
        
        return cards
    
    def chunk_cards(self, cards, chunk_size=6):
        """Split cards into fixed-size chunks for carousel slides."""
        if chunk_size <= 0:
            return [cards]
        
        slides = []
        for i in range(0, len(cards), chunk_size):
            slides.append(cards[i:i + chunk_size])
        
        if not slides:
            slides.append([])
        
        return slides
    
    def _card_from_highlight(self, highlight, index, group_key=None):
        """Build a single card dictionary from a highlight entry."""
        sport = (highlight.get('sport') or group_key or 'Sport Name').strip() or 'Sport Name'
        discipline = (highlight.get('discipline') or '').strip()
        
        # Format header as "SPORT - DISCIPLINE" if discipline exists and is different from sport, otherwise just "SPORT"
        if discipline and discipline.upper() != sport.upper():
            sport_header = f"{sport} - {discipline}"
        else:
            sport_header = sport
        athletes = (highlight.get('athlete_name') or highlight.get('athletes') or '').strip()
        if not athletes and highlight.get('type') == 'h2h':
            athletes = f"{(highlight.get('athlete_name') or 'Athlete Name').strip()} vs {(highlight.get('competitor_name') or 'Opponent Name').strip()}"
        if not athletes:
            athletes = "Athlete or Team Name"
        
        event = (highlight.get('event') or '').strip()
        stage = (highlight.get('stage') or '').strip()
        event_details_parts = [part for part in [event, stage] if part]
        event_details = " · ".join(event_details_parts) if event_details_parts else "Event Details"
        
        score_sgp = (highlight.get('score_sgp') or '').strip()
        score_competitor = (highlight.get('score_competitor') or '').strip()
        timing = (highlight.get('timing_sgp') or '').strip()
        medals = (highlight.get('medals') or '').strip()
        
        primary_score = ""
        opponent_score = ""
        if score_sgp and score_competitor:
            primary_score = score_sgp
            opponent_score = score_competitor
        elif score_sgp:
            primary_score = score_sgp
        elif timing:
            primary_score = timing
        
        result_summary = (highlight.get('highlights_text') or '').strip()
        if not result_summary:
            result_parts = []
            if primary_score and opponent_score:
                result_parts.append(f"{primary_score} - {opponent_score}")
            elif primary_score:
                result_parts.append(primary_score)
            if medals:
                result_parts.append(medals)
            result_summary = " | ".join(result_parts) if result_parts else "Result summary will appear here."
        
        medal_label, medal_icon = self._normalize_medal(medals)
        
        competitors = []
        primary_name = (highlight.get('athlete_name') or '').strip() or "Athlete Name"
        primary_country = (highlight.get('country_sgp') or 'SGP').strip() or 'SGP'
        def resolve_flag(country_value):
            if not country_value:
                return ''
            country = str(country_value).strip()
            if not country:
                return ''
            upper = country.upper()
            flag_map = {
                'SGP': '🇸🇬', 'SINGAPORE': '🇸🇬',
                'MAS': '🇲🇾', 'MALAYSIA': '🇲🇾',
                'THA': '🇹🇭', 'THAILAND': '🇹🇭',
                'PHI': '🇵🇭', 'PHILIPPINES': '🇵🇭',
                'VIE': '🇻🇳', 'VIETNAM': '🇻🇳',
                'INA': '🇮🇩', 'INDONESIA': '🇮🇩',
                'MYA': '🇲🇲', 'MYANMAR': '🇲🇲',
                'CAM': '🇰🇭', 'CAMBODIA': '🇰🇭',
                'LAO': '🇱🇦', 'LAOS': '🇱🇦',
                'BRU': '🇧🇳', 'BRUNEI': '🇧🇳',
                'TLS': '🇹🇱', 'TIMOR-LESTE': '🇹🇱',
                'CHN': '🇨🇳', 'CHINA': '🇨🇳',
                'JPN': '🇯🇵', 'JAPAN': '🇯🇵',
                'KOR': '🇰🇷', 'SOUTH KOREA': '🇰🇷', 'KOREA': '🇰🇷',
                'HKG': '🇭🇰', 'HONG KONG': '🇭🇰',
                'TPE': '🇹🇼', 'TAIWAN': '🇹🇼',
                'IND': '🇮🇳', 'INDIA': '🇮🇳',
                'AUS': '🇦🇺', 'AUSTRALIA': '🇦🇺',
                'NZL': '🇳🇿', 'NEW ZEALAND': '🇳🇿',
                'USA': '🇺🇸', 'UNITED STATES': '🇺🇸',
                'GBR': '🇬🇧', 'UNITED KINGDOM': '🇬🇧', 'UK': '🇬🇧',
                'FRA': '🇫🇷', 'FRANCE': '🇫🇷',
                'GER': '🇩🇪', 'GERMANY': '🇩🇪',
                'ITA': '🇮🇹', 'ITALY': '🇮🇹',
                'ESP': '🇪🇸', 'SPAIN': '🇪🇸',
                'MGL': '🇲🇳', 'MONGOLIA': '🇲🇳',
                'KAZ': '🇰🇿', 'KAZAKHSTAN': '🇰🇿',
            }
            if upper in flag_map:
                return flag_map[upper]
            for key, icon in flag_map.items():
                if upper in key or key in upper:
                    return icon
            return ''
        
        def resolve_flag_image(country_value):
            flags_dir = Path(__file__).parent / "flags"
            if not country_value:
                return ""
            country_clean = str(country_value).strip().upper()
            if not country_clean:
                return ""
            mapping = {
                "SGP": "SIN.png",
                "SINGAPORE": "SIN.png",
                "SIN": "SIN.png",
                "THA": "THA.png",
                "THAILAND": "THA.png",
                "VIE": "VIE.png",
                "VIETNAM": "VIE.png",
                "INA": "INA.png",
                "INDONESIA": "INA.png",
                "MAS": "MAS.png",
                "MALAYSIA": "MAS.png",
                "PHI": "PHI.png",
                "PHILIPPINES": "PHI.png",
                "MYA": "MYA.png",
                "MYANMAR": "MYA.png",
                "LAO": "LAO.png",
                "LAOS": "LAO.png",
                "CAM": "CAM.png",
                "CAMBODIA": "CAM.png",
                "BRU": "BRU.jpg",
                "BRUNEI": "BRU.jpg",
                "TIMOR-LESTE": "TLS.png",
            }
            file_name = mapping.get(country_clean)
            if file_name:
                candidate = flags_dir / file_name
                if candidate.exists():
                    return f"../flags/{file_name}"
            # try using the country code directly
            for suffix in (".png", ".jpg", ".jpeg"):
                candidate = flags_dir / f"{country_clean}{suffix}"
                if candidate.exists():
                    return f"../flags/{country_clean}{suffix}"
            return ""
        
        competitors.append({
            'flag_src': '#',
            'flag_alt': f"{primary_country} flag placeholder",
            'flag_image': resolve_flag_image(primary_country),
            'flag_icon': resolve_flag(primary_country),
            'name': primary_name,
            'country': primary_country,
            'score': primary_score
        })
        
        opponent_name = (highlight.get('competitor_name') or '').strip()
        opponent_country = (highlight.get('competitor_country') or '').strip()
        if opponent_name or opponent_country or opponent_score:
            competitors.append({
                'flag_src': '#',
                'flag_alt': f"{opponent_country or 'Opponent'} flag placeholder",
                'flag_image': resolve_flag_image(opponent_country),
                'flag_icon': resolve_flag(opponent_country),
                'name': opponent_name or "Opponent Name",
                'country': opponent_country or "Opponent Country",
                'score': opponent_score
            })
        
        sport_tags = highlight.get('sport_tags') or ['#OneTeamOneDream', '#GoTeamSG']
        result_badge = (highlight.get('win_draw_lose') or '').strip()
        if not result_badge and medal_label:
            result_badge = medal_label
        
        if result_badge.lower() in ('na', 'n/a', 'none'):
            result_badge = ''
        
        card = {
            'index': index,
            'sport': sport_header,
            'sport_icon': highlight.get('sport_icon') or '🏅',
            'sport_tags': sport_tags,
            'medal_label': medal_label,
            'medal_icon': medal_icon if medal_label else '',
            'athletes': athletes,
            'event_details': event_details,
            'result_summary': result_summary,
            'result_badge': result_badge,
            'competitors': competitors
        }
        
        return card
    
    def _placeholder_card(self, index):
        """Return placeholder card content."""
        return {
            'index': index,
            'sport': "Sport Name",
            'sport_icon': '🏅',
            'sport_tags': ['#OneTeamOneDream', '#GoTeamSG'],
            'medal_label': "",
            'medal_icon': "",
            'athletes': "Athlete or Team Name",
            'event_details': "Event Details",
            'result_summary': "Result information will appear here.",
            'result_badge': "",
            'competitors': [
                {
                    'flag_src': '#',
                    'flag_alt': "Flag placeholder",
                    'name': "Competitor Name",
                    'country': "Country",
                    'score': "15"
                },
                {
                    'flag_src': '#',
                    'flag_alt': "Flag placeholder",
                    'name': "Opponent Name",
                    'country': "Opponent Country",
                    'score': "8"
                }
            ]
        }
    
    def _normalize_medal(self, medal_value):
        """Return medal label and icon based on medal text."""
        if not medal_value:
            return "", ""
        
        medal_text = str(medal_value).strip()
        if not medal_text:
            return "", ""
        
        medal_key = medal_text.lower()
        if medal_key in ('na', 'n/a', 'none', 'no medal', 'nil'):
            return "", ""
        
        for keyword, icon in (('gold', '🥇'), ('silver', '🥈'), ('bronze', '🥉')):
            if keyword in medal_key:
                return medal_text.title(), icon
        
        return "", ""
    
    def _example_cards(self):
        """Provide example cards to populate the grid when no data is available."""
        example_cards = [
            {
                'index': 1,
                'sport': "Jiu-Jitsu",
                'sport_icon': '🥋',
                'sport_tags': ['#OneTeamOneDream', '#SEA2025', '#APG2026'],
                'medal_label': "Gold Medal",
                'medal_icon': '🥇',
                'athletes': "Nur Hanifah Qisya Mohammad Hanis",
                'event_details': "Girls' 52kg Final",
                'result_summary': "SGP beat THA 15-8. SGP won the Gold Medal.",
                'result_badge': "Gold Medal",
                'competitors': [
                    {
                        'flag_src': '#',
                        'flag_alt': "Singapore flag placeholder",
                        'name': "Nur Hanifah Qisya Mohammad Hanis",
                        'country': "SGP",
                        'score': "15"
                    },
                    {
                        'flag_src': '#',
                        'flag_alt': "Thailand flag placeholder",
                        'name': "Thailand Athlete",
                        'country': "THA",
                        'score': "8"
                    }
                ]
            },
            {
                'index': 2,
                'sport': "Swimming",
                'sport_icon': '🏊‍♀️',
                'sport_tags': ['#OneTeamOneDream', '#SEA2025', '#APG2026'],
                'medal_label': "Gold Medal",
                'medal_icon': '🥇',
                'athletes': "Ashley Wong · Chew En Vivienne · Keira Chew · Yo Ee Xin Megan Janice",
                'event_details': "Girls' 400m Breaststroke Finals",
                'result_summary': "Time: 4:05.75. Finished 1st out of 15 overall. SGP won the Gold Medal.",
                'result_badge': "Gold Medal",
                'competitors': [
                    {
                        'flag_src': '#',
                        'flag_alt': "Singapore flag placeholder",
                        'name': "Team Singapore",
                        'country': "SGP",
                        'score': "4:05.75"
                    }
                ]
            },
            {
                'index': 3,
                'sport': "Table Tennis",
                'sport_icon': '🏓',
                'sport_tags': ['#OneTeamOneDream', '#SEA2025', '#APG2026'],
                'medal_label': "",
                'medal_icon': "",
                'athletes': "Loy Ming Ying",
                'event_details': "Singles · Round of 16",
                'result_summary': "SGP beat HKG 3-1.",
                'result_badge': "3-1 Win",
                'competitors': [
                    {
                        'flag_src': '#',
                        'flag_alt': "Singapore flag placeholder",
                        'name': "Loy Ming Ying",
                        'country': "SGP",
                        'score': "3"
                    },
                    {
                        'flag_src': '#',
                        'flag_alt': "Hong Kong flag placeholder",
                        'name': "Hong Kong Opponent",
                        'country': "HKG",
                        'score': "1"
                    }
                ]
            },
            {
                'index': 4,
                'sport': "Jiu-Jitsu",
                'sport_icon': '🥋',
                'sport_tags': ['#OneTeamOneDream', '#SEA2025', '#APG2026'],
                'medal_label': "",
                'medal_icon': "",
                'athletes': "Sofia Anabel Rivas",
                'event_details': "Girls' 52kg Final",
                'result_summary': "SGP won by 3 to 1 advantages.",
                'result_badge': "3-1 Advantages",
                'competitors': [
                    {
                        'flag_src': '#',
                        'flag_alt': "Singapore flag placeholder",
                        'name': "Sofia Anabel Rivas",
                        'country': "SGP",
                        'score': "3"
                    },
                    {
                        'flag_src': '#',
                        'flag_alt': "Opponent flag placeholder",
                        'name': "Opponent Athlete",
                        'country': "Opponent Country",
                        'score': "1"
                    }
                ]
            },
            {
                'index': 5,
                'sport': "Athletics",
                'sport_icon': '🏃‍♀️',
                'sport_tags': ['#OneTeamOneDream', '#SEA2025', '#APG2026'],
                'medal_label': "",
                'medal_icon': "",
                'athletes': "Team Singapore",
                'event_details': "Girls' 4x100m Relay Finals",
                'result_summary': "Time: 46.82s. Season best finish for Team Singapore.",
                'result_badge': "Season Best",
                'competitors': [
                    {
                        'flag_src': '#',
                        'flag_alt': "Singapore flag placeholder",
                        'name': "Team Singapore",
                        'country': "SGP",
                        'score': "46.82"
                    },
                    {
                        'flag_src': '#',
                        'flag_alt': "Opponent flag placeholder",
                        'name': "Opposition Team",
                        'country': "Opponent Country",
                        'score': "47.10"
                    }
                ]
            },
            {
                'index': 6,
                'sport': "Basketball",
                'sport_icon': '🏀',
                'sport_tags': ['#OneTeamOneDream', '#SEA2025', '#APG2026'],
                'medal_label': "",
                'medal_icon': "",
                'athletes': "Singapore U17 Girls",
                'event_details': "3x3 Quarterfinal",
                'result_summary': "SGP beat PHI 21-18 to reach the semifinals.",
                'result_badge': "21-18 Win",
                'competitors': [
                    {
                        'flag_src': '#',
                        'flag_alt': "Singapore flag placeholder",
                        'name': "Singapore U17 Girls",
                        'country': "SGP",
                        'score': "21"
                    },
                    {
                        'flag_src': '#',
                        'flag_alt': "Philippines flag placeholder",
                        'name': "Philippines U17",
                        'country': "PHI",
                        'score': "18"
                    }
                ]
            }
        ]
        return example_cards
    
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
        Generate HTML section for results grouped by date or sport.
        Produces a responsive 2x4 grid of result cards.
        
        Args:
            group_key: Date or sport name
            highlights: List of highlight dictionaries
        
        Returns:
            HTML string
        """
        template_path = Path(__file__).parent / 'templates' / 'highlights_template.html'
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                html_template = Template(template_content)
        else:
            html_template = self.get_default_template()
        
        cards = self.build_result_cards(group_key, highlights)
        slides = self.chunk_cards(cards, chunk_size=9)
        
        # Calculate gold medal count for header
        gold_count = 0
        for highlight in highlights:
            medals = (highlight.get('medals') or '').strip()
            if medals:
                medal_key = str(medals).lower()
                if medal_key not in ('na', 'n/a', 'none', 'no medal', 'nil') and 'gold' in medal_key:
                    gold_count += 1
        
        # Format date for title
        if GROUP_BY_DATE and group_key:
            # Format date nicely
            try:
                from datetime import datetime as dt
                parsed_date = dt.strptime(str(group_key), '%Y-%m-%d')
                formatted_date = parsed_date.strftime('%d %B %Y')
            except:
                formatted_date = str(group_key)
        else:
            formatted_date = group_key or ''
        
        subtitle = "AYG25 Competition Results"
        if group_key and not GROUP_BY_DATE:
            subtitle = f"{group_key} Competition Results"
        
        section_title = f"GOLD MEDALS FOR {formatted_date}" if formatted_date else "GOLD MEDALS FOR THE DAY"
        
        html_content = html_template.render(
            section_title=section_title,
            subtitle=subtitle,
            group_label=group_key,
            cards=cards,
            slides=slides,
            generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            gold_medal_count=gold_count
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
    <title>{{ section_title }} | {{ group_label or 'AYG25' }}</title>
    <link rel="stylesheet" href="styles.css">
    <style>
        :root {
            color-scheme: light;
        }
        body {
            margin: 0;
            padding: 48px;
            background: #f4f4f8;
            font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
            color: #1f1f1f;
        }
        .results-section {
            max-width: 1440px;
            margin: 0 auto;
        }
        .results-header {
            margin-bottom: 32px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .results-title {
            margin: 0;
            font-size: 36px;
            font-weight: 700;
            color: #bd1e2d;
        }
        .results-subtitle {
            margin: 8px 0 0;
            font-size: 14px;
            color: #4a4a4a;
        }
        .results-generated {
            margin: 6px 0 0;
            font-size: 12px;
            color: #6d6d6d;
        }
        .results-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(280px, 1fr));
            gap: 28px;
        }
        .result-card {
            display: flex;
            min-height: 265px;
            background: #fff;
            border-radius: 20px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.08);
            overflow: hidden;
            position: relative;
        }
        .card-side {
            width: 140px;
            background: linear-gradient(180deg, #d9382c 0%, #ba1b27 100%);
            color: #fff;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 24px 20px;
        }
        .side-top {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
        }
        .sport-icon {
            font-size: 36px;
            line-height: 1;
        }
        .side-label {
            margin: 0;
            font-size: 12px;
            letter-spacing: 0.18em;
            opacity: 0.7;
        }
        .side-sport {
            margin: 0;
            font-size: 18px;
            font-weight: 700;
            line-height: 1.2;
        }
        .side-bottom {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .side-tag {
            font-size: 11px;
            text-transform: uppercase;
            opacity: 0.85;
        }
        .card-main {
            flex: 1;
            padding: 26px 28px;
            position: relative;
            display: flex;
            flex-direction: column;
        }
        .medal-ribbon {
            position: absolute;
            top: 18px;
            right: 18px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 64px;
            height: 92px;
            background: linear-gradient(180deg, #f8d047 0%, #f2a800 100%);
            color: #6a3600;
            border-radius: 12px 12px 0 0;
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.06em;
        }
        .medal-ribbon::after {
            content: '';
            position: absolute;
            bottom: -12px;
            width: 0;
            height: 0;
            border-left: 32px solid transparent;
            border-right: 32px solid transparent;
            border-top: 12px solid #f2a800;
        }
        .medal-ribbon.muted {
            background: linear-gradient(180deg, #d3d3d3 0%, #adadad 100%);
            color: #ffffff;
        }
        .medal-symbol {
            font-size: 24px;
            margin-bottom: 6px;
        }
        .card-content {
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding-right: 72px;
        }
        .card-sport {
            margin: 0;
            font-size: 16px;
            font-weight: 700;
            text-transform: uppercase;
            color: #111;
        }
        .card-athletes {
            margin: 0;
            font-size: 15px;
            font-weight: 600;
            color: #ba1b27;
        }
        .card-event {
            margin: 0;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #4b4b4b;
        }
        .card-scoreboard {
            border-radius: 12px;
            background: #f9f9fb;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .score-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }
        .score-row[data-role="primary"] {
            font-weight: 700;
        }
        .score-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .flag-circle {
            width: 42px;
            height: 28px;
            border-radius: 6px;
            background: #ffffff;
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .flag-circle img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .flag-placeholder {
            display: inline-block;
            width: 60%;
            height: 60%;
            border-radius: 50%;
            background: #d3d3d3;
        }
        .score-meta {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .competitor-name {
            font-size: 13px;
            color: #1b1b1b;
        }
        .competitor-country {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7a7a7a;
        }
        .score-value {
            font-size: 20px;
            font-weight: 700;
            min-width: 36px;
            text-align: right;
            color: #0f172a;
        }
        .card-result {
            margin: 0;
            font-size: 13px;
            line-height: 1.6;
            color: #333;
        }
        .result-badge {
            align-self: flex-start;
            padding: 4px 10px;
            border-radius: 999px;
            background: #ba1b27;
            color: #fff;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        @media (max-width: 1280px) {
            .results-grid {
                grid-template-columns: repeat(3, minmax(260px, 1fr));
            }
        }
        @media (max-width: 1024px) {
            body {
                padding: 32px;
            }
            .results-grid {
                grid-template-columns: repeat(2, minmax(260px, 1fr));
            }
        }
        @media (max-width: 640px) {
            body {
                padding: 24px 16px;
            }
            .results-grid {
                grid-template-columns: 1fr;
            }
            .result-card {
                flex-direction: column;
            }
            .card-side {
                flex-direction: row;
                align-items: center;
                width: 100%;
                gap: 20px;
                padding: 20px;
            }
            .card-main {
                padding: 24px 20px;
            }
        }
    </style>
</head>
<body>
    <section class="results-section" aria-labelledby="results-title">
        <header class="results-header">
            <h2 class="results-title" id="results-title">{{ section_title }}</h2>
            <p class="results-subtitle">{{ subtitle }}</p>
            <p class="results-generated">Generated: {{ generation_date }}</p>
        </header>
        <div class="results-grid" data-layout="2x4">
            {% for card in cards %}
            <article class="result-card" data-card-index="{{ card.index }}">
                <aside class="card-side">
                    <div class="side-top">
                        <div class="sport-icon">{{ card.sport_icon }}</div>
                        <p class="side-label">Sport</p>
                        <h3 class="side-sport">{{ card.sport }}</h3>
                    </div>
                    <div class="side-bottom">
                        {% for tag in card.sport_tags %}
                        <span class="side-tag">{{ tag }}</span>
                        {% endfor %}
                    </div>
                </aside>
                <div class="card-main">
                    <div class="medal-ribbon{% if not card.medal_label %} muted{% endif %}">
                        <span class="medal-symbol">{{ card.medal_icon }}</span>
                        <span class="medal-text">{% if card.medal_label %}{{ card.medal_label }}{% else %}Result{% endif %}</span>
                    </div>
                    <div class="card-content">
                        <h4 class="card-sport">{{ card.sport }}</h4>
                        <p class="card-athletes">{{ card.athletes }}</p>
                        <p class="card-event">{{ card.event_details }}</p>
                        <div class="card-scoreboard">
                            {% for competitor in card.competitors %}
                            <div class="score-row" data-role="{% if loop.index0 == 0 %}primary{% else %}opponent{% endif %}">
                                <div class="score-info">
                                    <div class="flag-circle">
                                        {% if competitor.flag_src and competitor.flag_src != '#' %}
                                        <img src="{{ competitor.flag_src }}" alt="{{ competitor.flag_alt }}" />
                                        {% else %}
                                        <span class="flag-placeholder"></span>
                                        {% endif %}
                                    </div>
                                    <div class="score-meta">
                                        <span class="competitor-name">{{ competitor.name }}</span>
                                        <span class="competitor-country">{{ competitor.country }}</span>
                                    </div>
                                </div>
                                {% if competitor.score %}
                                <span class="score-value">{{ competitor.score }}</span>
                                {% endif %}
                            </div>
                            {% endfor %}
                        </div>
                        <p class="card-result">{{ card.result_summary }}</p>
                        {% if card.result_badge %}
                        <span class="result-badge">{{ card.result_badge }}</span>
                        {% endif %}
                    </div>
                </div>
            </article>
            {% endfor %}
        </div>
    </section>
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

