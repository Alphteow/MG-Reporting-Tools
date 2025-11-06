#!/usr/bin/env python3
"""
Extract competition schedules from SEAG25 technical handbooks.
Searches pages 4-8 for sections containing the exact phrase "Competition Schedule".
"""

import os
import re
from pathlib import Path
import pdfplumber
import pandas as pd
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_sport_name(filename):
    """Extract sport name from filename (first word before underscore or first word)."""
    # Remove extension
    name = Path(filename).stem
    # Split by underscore and take first part, or split by space
    if '_' in name:
        first_part = name.split('_')[0]
    else:
        first_part = name.split()[0] if name.split() else name
    
    # Clean up common prefixes
    first_part = first_part.replace('Attachment', '').replace('for', '').strip()
    # Handle special cases
    if 'Aquatic' in first_part:
        # Check the full name for specific aquatic sports
        if 'Diving' in name:
            return 'Aquatic_Diving'
        elif 'Swimming' in name:
            return 'Aquatic_Swimming'
        elif 'Water Polo' in name:
            return 'Aquatic_WaterPolo'
        elif 'Artistic Swimming' in name:
            return 'Aquatic_ArtisticSwimming'
        elif 'OWS' in name:
            return 'Aquatic_OWS'
    elif 'Canoe' in first_part:
        if 'Slalom' in name:
            return 'Canoe_Slalom'
        elif 'Sprint' in name:
            return 'Canoe_Sprint'
    elif 'Basketball' in first_part:
        if '3X3' in name:
            return 'Basketball_3X3'
        else:
            return 'Basketball'
    elif 'Shotgun' in first_part:
        if 'Skeet Trap' in name:
            return 'Shotgun_SkeetTrap'
        elif 'Sporting Compak' in name:
            return 'Shotgun_SportingCompak'
    elif 'Pistol and Rifle' in name:
        return 'Shooting_PistolRifle'
    elif 'Triathlon' in name:
        return 'Triathlon_Duathlon_Aquathlon'
    
    return first_part

def is_schedule_table(table):
    """Check if a table looks like a schedule table."""
    if not table or len(table) < 2:
        return False
    
    # Check first row for schedule-like headers
    first_row = [str(cell).lower() if cell else '' for cell in table[0]]
    first_row_text = ' '.join(first_row)
    
    # Look for schedule-related column headers
    schedule_headers = ['date', 'time', 'event', 'events', 'gender', 'phase', 'day', 'remarks']
    has_schedule_header = any(header in first_row_text for header in schedule_headers)
    
    # Strong indicator: has both Date and Time columns
    has_date_and_time = 'date' in first_row_text and 'time' in first_row_text
    
    # Check if table has date-like patterns in cells
    has_date_pattern = False
    for row in table[:5]:  # Check first 5 rows
        row_text = ' '.join([str(cell) if cell else '' for cell in row])
        if re.search(r'\d{1,2}\s+(dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov)', row_text, re.IGNORECASE):
            has_date_pattern = True
            break
        if re.search(r'\d{1,2}[/-]\d{1,2}', row_text):
            has_date_pattern = True
            break
    
    # Return True if: has Date AND Time, OR has schedule header with date pattern, OR strong date pattern
    return has_date_and_time or (has_schedule_header and has_date_pattern) or (has_date_pattern and len(table) > 3)

def find_schedule_section(pdf_path, max_pages_to_check=10):
    """Find and extract schedule section from PDF pages 4-8 (or nearby).
    Looks for variations of 'Competition Schedule' phrase and schedule-like tables."""
    schedule_texts = []
    schedule_tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            # Check pages 2-10 to be safe
            start_page = max(1, 0)
            end_page = min(9, total_pages - 1)
            
            logger.info(f"Checking pages {start_page+1} to {end_page+1} of {total_pages} in {Path(pdf_path).name}")
            
            for page_num in range(start_page, end_page + 1):
                page = pdf.pages[page_num]
                
                # Extract text
                text = page.extract_text()
                if not text:
                    continue
                
                text_lower = text.lower()
                
                # Check for various schedule-related phrases
                schedule_phrases = [
                    'competition schedule',
                    'competition and training schedule',
                    'competition and training',
                    'competition\nschedule',
                    'competition \nschedule',
                ]
                
                has_schedule_phrase = any(phrase in text_lower for phrase in schedule_phrases)
                
                # Also check if "competition" and "schedule" appear close together
                comp_idx = text_lower.find('competition')
                sched_idx = text_lower.find('schedule')
                has_close_match = False
                if comp_idx >= 0 and sched_idx >= 0:
                    distance = abs(sched_idx - comp_idx)
                    # Allow up to 50 characters between them (handles "Competition and Training Schedule")
                    if distance < 50:
                        has_close_match = True
                
                # Check for schedule-like tables
                tables = page.extract_tables()
                has_schedule_table = False
                if tables:
                    for table in tables:
                        if is_schedule_table(table):
                            has_schedule_table = True
                            break
                
                # If we found a schedule indicator
                # Accept if: has phrase, OR (close match AND schedule table), OR (schedule table AND has "competition" or "schedule" text)
                has_schedule_keyword = 'competition' in text_lower or 'schedule' in text_lower
                is_schedule_page = has_schedule_phrase or (has_close_match and has_schedule_table) or (has_schedule_table and has_schedule_keyword)
                
                if is_schedule_page:
                    match_type = []
                    if has_schedule_phrase:
                        found_phrase = next((p for p in schedule_phrases if p in text_lower), 'schedule phrase')
                        match_type.append(f"'{found_phrase}'")
                    if has_close_match:
                        match_type.append("close match")
                    if has_schedule_table:
                        match_type.append("schedule table")
                    
                    logger.info(f"Found schedule on page {page_num + 1} ({', '.join(match_type) if match_type else 'schedule table'})")
                    
                    # Extract all tables from this page
                    if tables:
                        for table in tables:
                            # Include if it's a schedule table or (has reasonable size and we found phrase)
                            if is_schedule_table(table) or (has_schedule_phrase and len(table) > 2):
                                schedule_tables.append({
                                    'page': page_num + 1,
                                    'table': table
                                })
                    
                    # Capture text around schedule keywords
                    schedule_texts.append({
                        'page': page_num + 1,
                        'text': text
                    })
            
            # If we found schedule on a page, check pages before and after for continuation
            # Also check pages between schedule pages to ensure we capture all consecutive pages
            if schedule_texts or schedule_tables:
                captured_pages = set([s['page'] for s in schedule_texts + schedule_tables])
                first_schedule_page = min(captured_pages)
                last_schedule_page = max(captured_pages)
                
                # Check pages BETWEEN first and last schedule pages (in case we missed some)
                for page_num in range(first_schedule_page, last_schedule_page + 1):
                    if page_num in captured_pages:
                        continue  # Already captured
                    
                    # Check if this intermediate page should be included
                    page_idx = page_num - 1  # Convert to 0-indexed
                    if page_idx < 0 or page_idx >= total_pages:
                        continue
                    
                    page = pdf.pages[page_idx]
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    text_lower = text.lower()
                    has_date_pattern = bool(re.search(r'\d{1,2}\s+(dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov)', text_lower, re.IGNORECASE) or 
                                           re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text_lower))
                    tables = page.extract_tables()
                    has_schedule_table = any(is_schedule_table(table) for table in tables) if tables else False
                    
                    # Check if table has Date and Time columns
                    has_date_time_cols = False
                    if tables:
                        for table in tables:
                            if table and len(table) > 0:
                                first_row = [str(cell).lower() if cell else '' for cell in table[0]]
                                first_row_text = ' '.join(first_row)
                                if 'date' in first_row_text and 'time' in first_row_text:
                                    has_date_time_cols = True
                                    break
                    
                    if has_schedule_table or has_date_time_cols or has_date_pattern:
                        logger.info(f"Found schedule continuation on page {page_num} (between schedule pages)")
                        schedule_texts.append({
                            'page': page_num,
                            'text': text
                        })
                        if tables:
                            for table in tables:
                                if is_schedule_table(table) or has_date_time_cols or len(table) > 2:
                                    schedule_tables.append({
                                        'page': page_num,
                                        'table': table
                                    })
                        captured_pages.add(page_num)
                
                # Update first and last after checking intermediate pages
                first_schedule_page = min([s['page'] for s in schedule_texts + schedule_tables])
                last_schedule_page = max([s['page'] for s in schedule_texts + schedule_tables])
                
                # Check pages BEFORE the first schedule page (in case schedule starts earlier)
                for offset in range(1, 3):  # Check up to 2 pages before
                    prev_page_num = first_schedule_page - offset - 1  # Convert to 0-indexed
                    if prev_page_num < 0:
                        break
                    
                    # Skip if we already captured this page or it's before our search range
                    if prev_page_num < start_page:
                        break
                    already_captured = any(s['page'] == prev_page_num + 1 for s in schedule_texts)
                    if already_captured:
                        continue
                    
                    page = pdf.pages[prev_page_num]
                    text = page.extract_text()
                    if not text:
                        break
                    
                    text_lower = text.lower()
                    
                    # Check if this page looks like schedule continuation
                    has_date_pattern = bool(re.search(r'\d{1,2}\s+(dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov)', text_lower, re.IGNORECASE) or 
                                           re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text_lower))
                    
                    tables = page.extract_tables()
                    has_schedule_table = any(is_schedule_table(table) for table in tables) if tables else False
                    
                    has_schedule_keywords = any(keyword in text_lower for keyword in 
                                               ['schedule', 'competition', 'event', 'time', 'date', 'day', 'session'])
                    
                    if has_schedule_table or (has_date_pattern and has_schedule_keywords):
                        logger.info(f"Found schedule continuation on page {prev_page_num + 1} (before main schedule)")
                        schedule_texts.insert(0, {  # Insert at beginning to maintain page order
                            'page': prev_page_num + 1,
                            'text': text
                        })
                        if tables:
                            for table in tables:
                                if is_schedule_table(table) or len(table) > 2:
                                    schedule_tables.insert(0, {
                                        'page': prev_page_num + 1,
                                        'table': table
                                    })
                        first_schedule_page = prev_page_num + 1
                    else:
                        break
                
                # Now check pages AFTER the last schedule page
                # Check up to 5 more pages for continuation (handles schedules spanning multiple pages)
                for offset in range(1, 6):
                    next_page_num = last_schedule_page + offset - 1  # Convert to 0-indexed
                    if next_page_num >= total_pages:
                        break
                    
                    # Skip if we already captured this page
                    already_captured = any(s['page'] == next_page_num + 1 for s in schedule_texts)
                    if already_captured:
                        continue
                    
                    page = pdf.pages[next_page_num]
                    text = page.extract_text()
                    if not text:
                        break
                    
                    text_lower = text.lower()
                    
                    # Check if this page looks like schedule continuation
                    has_date_pattern = bool(re.search(r'\d{1,2}\s+(dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov)', text_lower, re.IGNORECASE) or 
                                           re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text_lower))
                    
                    # Check for schedule-like tables
                    tables = page.extract_tables()
                    has_schedule_table = any(is_schedule_table(table) for table in tables) if tables else False
                    
                    # Check for schedule-related keywords
                    has_schedule_keywords = any(keyword in text_lower for keyword in 
                                               ['schedule', 'competition', 'event', 'time', 'date', 'day', 'session'])
                    
                    # If page has schedule-like content, include it
                    # Also include if it's immediately consecutive and has dates/times (likely continuation)
                    is_consecutive = (next_page_num + 1) == (last_schedule_page + 1)
                    
                    # Check if table has Date and Time columns (strong indicator of schedule continuation)
                    has_date_time_cols = False
                    if tables:
                        for table in tables:
                            if table and len(table) > 0:
                                first_row = [str(cell).lower() if cell else '' for cell in table[0]]
                                first_row_text = ' '.join(first_row)
                                if 'date' in first_row_text and 'time' in first_row_text:
                                    has_date_time_cols = True
                                    break
                    
                    if has_schedule_table or has_date_time_cols or (has_date_pattern and has_schedule_keywords) or \
                       (is_consecutive and (has_date_pattern or has_date_time_cols)):
                        logger.info(f"Found schedule continuation on page {next_page_num + 1}")
                        schedule_texts.append({
                            'page': next_page_num + 1,
                            'text': text
                        })
                        if tables:
                            for table in tables:
                                if is_schedule_table(table) or has_date_time_cols or len(table) > 2:
                                    schedule_tables.append({
                                        'page': next_page_num + 1,
                                        'table': table
                                    })
                        last_schedule_page = next_page_num + 1  # Update last schedule page
                    else:
                        # If we don't find schedule content, stop checking
                        break
    
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        return None, None
    
    return schedule_texts, schedule_tables

def process_all_handbooks(directory):
    """Process all PDF handbooks in the directory."""
    pdf_dir = Path(directory)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    
    # Track sports and their schedules
    sports_data = defaultdict(list)
    duplicate_sports = defaultdict(list)
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    for pdf_file in pdf_files:
        filename = pdf_file.name
        sport_name = extract_sport_name(filename)
        
        logger.info(f"\nProcessing: {filename}")
        logger.info(f"Identified sport: {sport_name}")
        
        # Check for duplicates
        if sport_name in sports_data:
            duplicate_sports[sport_name].append(filename)
            logger.warning(f"DUPLICATE: {sport_name} already processed. This file: {filename}")
        
        # Extract schedule
        schedule_texts, schedule_tables = find_schedule_section(pdf_file)
        
        if not schedule_texts and not schedule_tables:
            logger.warning(f"No schedule found in {filename}")
            sports_data[sport_name].append({
                'source_file': filename,
                'sport': sport_name,
                'schedule_text': 'NO SCHEDULE FOUND',
                'schedule_table': None,
                'pages': []
            })
        else:
            # Combine all text from schedule pages
            combined_text = '\n\n--- Page Break (Page {}) ---\n\n'.join(
                [f"Page {st['page']}: {st['text']}" for st in schedule_texts]
            ) if schedule_texts else ""
            
            sports_data[sport_name].append({
                'source_file': filename,
                'sport': sport_name,
                'schedule_text': combined_text,
                'schedule_table': schedule_tables,
                'pages': [st['page'] for st in schedule_texts] + [st['page'] for st in schedule_tables]
            })
    
    # Log duplicates
    if duplicate_sports:
        logger.warning("\n" + "="*80)
        logger.warning("DUPLICATE SPORTS DETECTED:")
        for sport, files in duplicate_sports.items():
            logger.warning(f"  {sport}: {', '.join(files)}")
        logger.warning("="*80 + "\n")
    
    return sports_data, duplicate_sports

def create_excel_output(sports_data, duplicate_sports, output_file):
    """Create Excel file with all schedules."""
    
    # Prepare data for Excel
    excel_data = []
    
    for sport_name, schedules in sports_data.items():
        for schedule_info in schedules:
            # Format tables if available
            table_info = ""
            if schedule_info['schedule_table']:
                table_info = f"\n\n--- TABLES FOUND ---\n"
                for table_data in schedule_info['schedule_table']:
                    table_info += f"\nTable from Page {table_data['page']}:\n"
                    # Convert table to string representation
                    table = table_data['table']
                    if table:
                        # Try to create a readable format
                        for row in table:
                            if row:
                                table_info += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
                        table_info += "\n"
            
            excel_data.append({
                'Sport': sport_name,
                'Source File': schedule_info['source_file'],
                'Pages Found': ', '.join([str(p) for p in schedule_info['pages']]) if schedule_info['pages'] else 'N/A',
                'Schedule Text': schedule_info['schedule_text'] + table_info,
                'Has Duplicate': 'Yes' if sport_name in duplicate_sports else 'No'
            })
    
    # Create DataFrame
    df = pd.DataFrame(excel_data)
    
    # Write to Excel with formatting
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Schedules', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Schedules']
        worksheet.column_dimensions['A'].width = 25  # Sport
        worksheet.column_dimensions['B'].width = 50  # Source File
        worksheet.column_dimensions['C'].width = 20  # Pages Found
        worksheet.column_dimensions['D'].width = 100  # Schedule Text
        worksheet.column_dimensions['E'].width = 15  # Has Duplicate
        
        # Wrap text in Schedule Text column
        from openpyxl.styles import Alignment
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, min_col=4, max_col=4):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
    
    logger.info(f"\nExcel file created: {output_file}")
    logger.info(f"Total sports processed: {len(sports_data)}")
    logger.info(f"Total entries: {len(excel_data)}")

def main():
    """Main function."""
    script_dir = Path(__file__).parent
    handbooks_dir = script_dir / "Techhandbooks_SEAG25"
    output_file = script_dir / "SEAG25_Schedules_Extracted.xlsx"
    
    if not handbooks_dir.exists():
        logger.error(f"Directory not found: {handbooks_dir}")
        return
    
    logger.info(f"Starting extraction from: {handbooks_dir}")
    
    # Process all handbooks
    sports_data, duplicate_sports = process_all_handbooks(handbooks_dir)
    
    # Create Excel output
    create_excel_output(sports_data, duplicate_sports, output_file)
    
    logger.info("\nExtraction complete!")

if __name__ == "__main__":
    main()

