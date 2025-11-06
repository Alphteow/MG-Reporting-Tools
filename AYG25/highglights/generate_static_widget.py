#!/usr/bin/env python3
"""
Generate Static Widget HTML Files
Creates standalone HTML files that developers can host themselves
No API deployment needed!
"""

from generate_highlights import HighlightsGenerator
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_static_widgets(spreadsheet_id=None, sheet_name=None, credentials_file=None, 
                           output_dir=None, date_filter=None, sport_filter=None):
    """
    Generate static widget HTML files that can be hosted by developers
    
    Args:
        spreadsheet_id: Google Sheets spreadsheet ID
        sheet_name: Worksheet name
        credentials_file: Path to credentials file
        output_dir: Output directory (defaults to 'static_widgets')
        date_filter: Optional date filter (YYYY-MM-DD)
        sport_filter: Optional sport filter
    """
    # Initialize generator
    generator = HighlightsGenerator(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        credentials_file=credentials_file
    )
    
    # Set output directory
    if output_dir:
        generator.output_dir = Path(output_dir)
    else:
        generator.output_dir = Path(__file__).parent / 'static_widgets'
    
    generator.output_dir.mkdir(exist_ok=True)
    
    # Load data
    df = generator.load_data()
    
    if df.empty:
        logger.warning("No highlights data found")
        return
    
    # Apply filters
    from config import COLUMN_MAPPINGS
    
    if date_filter:
        date_col = COLUMN_MAPPINGS.get('DATE_SGP', 'DATE (SGP)')
        if date_col in df.columns:
            df = df[df[date_col].astype(str).str.contains(date_filter, na=False)]
            logger.info(f"Filtered to date: {date_filter}, {len(df)} rows remaining")
    
    if sport_filter:
        sport_col = COLUMN_MAPPINGS.get('SPORT', 'SPORT')
        if sport_col in df.columns:
            df = df[df[sport_col].astype(str).str.contains(sport_filter, na=False)]
            logger.info(f"Filtered to sport: {sport_filter}, {len(df)} rows remaining")
    
    if df.empty:
        logger.warning("No highlights after filtering")
        return
    
    # Group highlights
    grouped_data = generator.group_highlights(df)
    
    # Generate HTML for each group
    for group_key, highlights in grouped_data.items():
        html_content = generator.generate_html(group_key, highlights)
        
        # Sanitize filename
        if isinstance(group_key, str) and group_key.startswith('2025-'):
            # Date format
            safe_name = group_key.replace(' ', '_').replace('/', '-')
            filename = f"widget_{safe_name}.html"
        else:
            safe_name = "".join(c for c in str(group_key) if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            filename = f"widget_{safe_name}.html"
        
        # Save HTML file
        output_file = generator.output_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Generated static widget: {output_file}")
    
    # Copy CSS file
    css_source = Path(__file__).parent / 'styles.css'
    css_dest = generator.output_dir / 'styles.css'
    if css_source.exists():
        import shutil
        shutil.copy2(css_source, css_dest)
        logger.info(f"Copied styles.css to {css_dest}")
    
    logger.info(f"\n✅ Static widgets generated in: {generator.output_dir}")
    logger.info(f"📦 Share these files with developers - they can host them anywhere!")
    logger.info(f"📄 Files: {', '.join([f.name for f in generator.output_dir.glob('*.html')])}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate static widget HTML files')
    parser.add_argument('--spreadsheet-id', type=str, default=None,
                       help='Google Sheets spreadsheet ID')
    parser.add_argument('--sheet-name', type=str, default=None,
                       help='Worksheet name')
    parser.add_argument('--credentials', type=str, default=None,
                       help='Path to Google credentials JSON file')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory (defaults to static_widgets)')
    parser.add_argument('--date', type=str, default=None,
                       help='Filter by date (YYYY-MM-DD)')
    parser.add_argument('--sport', type=str, default=None,
                       help='Filter by sport name')
    
    args = parser.parse_args()
    
    try:
        generate_static_widgets(
            spreadsheet_id=args.spreadsheet_id,
            sheet_name=args.sheet_name,
            credentials_file=args.credentials,
            output_dir=args.output_dir,
            date_filter=args.date,
            sport_filter=args.sport
        )
    except Exception as e:
        logger.error(f"Failed to generate static widgets: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

