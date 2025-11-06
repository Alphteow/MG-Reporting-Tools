#!/usr/bin/env python3
"""
Analyze PDF structure to optimize schedule extraction.
"""

import pdfplumber
from pathlib import Path

# Sample PDFs to analyze
sample_pdfs = [
    "Badminton_30 AUG 2025_ver2.pdf",  # Working example
    "Athletics_4 AUG 2025_ver2.pdf",   # Failed
    "Gymnastics_22 AUG 2025_ver2.pdf", # Failed
    "Kickboxing_7 AUG 2025_ver2.pdf",  # Failed
    "Rugby_5 AUG 2025_ver2.pdf",       # Failed
    "Swimming_8 AUG 2025_ver2.pdf",    # Another working example
]

pdf_dir = Path("Techhandbooks_SEAG25")

for pdf_name in sample_pdfs:
    pdf_path = pdf_dir / pdf_name
    if not pdf_path.exists():
        print(f"\n{'='*80}")
        print(f"PDF NOT FOUND: {pdf_name}")
        continue
        
    print(f"\n{'='*80}")
    print(f"Analyzing: {pdf_name}")
    print(f"{'='*80}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Total pages: {total_pages}")
            
            # Check pages 2-10 for schedule-related content
            for page_num in range(1, min(11, total_pages)):  # Pages 2-10 (0-indexed: 1-9)
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                if not text:
                    continue
                
                text_lower = text.lower()
                
                # Check for various schedule-related phrases
                phrases_to_check = [
                    'competition schedule',
                    'competition\nschedule',
                    'competition \nschedule',
                    'schedule',
                    'competition',
                    'timetable',
                    'programme',
                    'program',
                ]
                
                found_phrases = []
                for phrase in phrases_to_check:
                    if phrase in text_lower:
                        found_phrases.append(phrase)
                
                # Also check for tables
                tables = page.extract_tables()
                has_tables = len(tables) > 0
                
                if found_phrases or has_tables:
                    print(f"\n--- Page {page_num + 1} ---")
                    print(f"Found phrases: {found_phrases}")
                    print(f"Has tables: {has_tables} ({len(tables)} tables)")
                    
                    # Show first 500 chars of text
                    if text:
                        preview = text[:500].replace('\n', ' ')
                        print(f"Text preview: {preview}...")
                    
                    # Show table structure if exists
                    if tables:
                        for i, table in enumerate(tables[:2]):  # Show first 2 tables
                            print(f"\nTable {i+1} structure:")
                            if table and len(table) > 0:
                                print(f"  Rows: {len(table)}")
                                print(f"  Cols: {len(table[0]) if table[0] else 0}")
                                if len(table) <= 5:
                                    for row in table:
                                        print(f"    {row}")
                                else:
                                    print(f"    First row: {table[0]}")
                                    print(f"    Last row: {table[-1]}")
                    
                    # Check if "competition schedule" appears together or split
                    if 'competition' in text_lower and 'schedule' in text_lower:
                        comp_idx = text_lower.find('competition')
                        sched_idx = text_lower.find('schedule')
                        distance = abs(sched_idx - comp_idx)
                        print(f"\n'competition' and 'schedule' found - distance: {distance} chars")
                        if distance < 30:
                            context = text[max(0, min(comp_idx, sched_idx)-50):min(len(text), max(comp_idx, sched_idx)+100)]
                            print(f"Context: ...{context}...")
    
    except Exception as e:
        print(f"ERROR: {str(e)}")

