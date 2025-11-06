#!/usr/bin/env python3
"""
Export Highlights to Google Slides
Exports each section as a slide in a Google Slides presentation for manual rearrangement
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Google Slides Presentation ID
GOOGLE_SLIDES_ID = '1nK1Yx0EBO_OJ9jy7IrNep19yyv5SNm3-BQ6y77EjASY'

def check_google_slides_api():
    """Check if Google Slides API client is installed"""
    try:
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials
        return True
    except ImportError:
        return False

def install_google_slides_api():
    """Install Google Slides API client"""
    logger.info("Installing Google API Python client...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-api-python-client"])
    logger.info("Google API Python client installed successfully")

def export_highlights_to_slides(html_files_dir=None, presentation_id=None):
    """
    Export highlights sections to Google Slides
    
    Args:
        html_files_dir: Directory containing HTML highlight files (default: output/)
        presentation_id: Google Slides presentation ID (default: from constant)
    """
    if not check_google_slides_api():
        logger.info("Google Slides API not found. Installing...")
        try:
            install_google_slides_api()
        except Exception as e:
            logger.error(f"Failed to install Google Slides API: {str(e)}")
            logger.error("Please install manually: pip install google-api-python-client")
            return
    
    try:
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials
        from googleapiclient.http import MediaFileUpload
        import tempfile
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
    except ImportError as e:
        logger.error(f"Required packages not available: {e}")
        return
    
    # Set defaults
    if html_files_dir is None:
        html_files_dir = Path(__file__).parent / 'output'
    else:
        html_files_dir = Path(html_files_dir)
    
    if presentation_id is None:
        presentation_id = GOOGLE_SLIDES_ID
    
    if not html_files_dir.exists():
        logger.error(f"HTML files directory not found: {html_files_dir}")
        return
    
    # Load credentials
    try:
        from config import GOOGLE_CREDENTIALS_FILE
        creds_path = Path(GOOGLE_CREDENTIALS_FILE)
        if not creds_path.is_absolute():
            creds_path = Path(__file__).parent.parent.parent / creds_path
    except ImportError:
        # Try default location
        creds_path = Path(__file__).parent.parent / 'ayg-form-system' / 'functions' / 'google_credentials.json'
    
    if not creds_path.exists():
        logger.error(f"Google credentials not found at: {creds_path}")
        logger.error("Please ensure google_credentials.json exists and has Slides API access")
        return
    
    # Authenticate
    scopes = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
    slides_service = build('slides', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    logger.info(f"Connected to Google Slides: {presentation_id}")
    
    # Get presentation
    try:
        presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
        logger.info(f"Found presentation: {presentation.get('title', 'Untitled')}")
    except Exception as e:
        logger.error(f"Error accessing presentation: {e}")
        return
    
    # Find all HTML files
    html_files = sorted(html_files_dir.glob('highlights_*.html'))
    
    if not html_files:
        logger.warning(f"No highlight HTML files found in {html_files_dir}")
        return
    
    logger.info(f"Found {len(html_files)} highlight files to export")
    
    # Process each HTML file
    for html_file in html_files:
        logger.info(f"Processing {html_file.name}...")
        
        # Read HTML to find sections
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Count sections (each <div class="section">)
        soup = BeautifulSoup(html_content, 'html.parser')
        sections = soup.find_all('div', class_='section')
        
        logger.info(f"  Found {len(sections)} sections in {html_file.name}")
        
        if len(sections) == 0:
            logger.warning(f"  No sections found in {html_file.name}, skipping")
            continue
        
        # Export each section as an image and add to slides
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=2
            )
            
            # Load the HTML file
            page.goto(f"file://{html_file.resolve()}")
            page.wait_for_timeout(2000)  # Wait for content to load
            
            # Process each section
            for section_idx, section in enumerate(sections):
                # Scroll section into view
                section_element = page.locator(f'div.section').nth(section_idx)
                section_element.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                
                # Get section bounding box
                box = section_element.bounding_box()
                if not box:
                    continue
                
                # Take screenshot of section
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                page.screenshot(
                    path=tmp_path,
                    clip={
                        'x': box['x'],
                        'y': box['y'],
                        'width': box['width'],
                        'height': box['height']
                    },
                    type='png'
                )
                
                # Upload image to Google Drive
                file_metadata = {
                    'name': f"{html_file.stem}_section_{section_idx + 1}.png"
                }
                media = MediaFileUpload(tmp_path, mimetype='image/png', resumable=True)
                
                uploaded_file = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                file_id = uploaded_file.get('id')
                
                # Make file publicly viewable (required for Slides)
                drive_service.permissions().create(
                    fileId=file_id,
                    body={'role': 'reader', 'type': 'anyone'}
                ).execute()
                
                # Get image URL
                image_url = f"https://drive.google.com/uc?export=view&id={file_id}"
                
                # Get current number of slides
                presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
                current_slide_count = len(presentation.get('slides', []))
                
                # Create new slide
                requests = [{
                    'createSlide': {
                        'insertionIndex': current_slide_count,
                        'slideLayoutReference': {
                            'predefinedLayout': 'BLANK'
                        }
                    }
                }]
                
                # Add image to slide
                slide_id = None
                try:
                    response = slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': requests}
                    ).execute()
                    
                    slide_id = response['replies'][0]['createSlide']['objectId']
                    
                    # Get page dimensions (Google Slides default is 10x7.5 inches = 7200000 x 5400000 EMU)
                    # For 1920x1080 image, we need to scale it to fit
                    page_width = 7200000  # 10 inches in EMU
                    page_height = 5400000  # 7.5 inches in EMU
                    
                    # Calculate scale to fit image (maintain aspect ratio)
                    image_width = 1920
                    image_height = 1080
                    scale_x = page_width / image_width
                    scale_y = page_height / image_height
                    scale = min(scale_x, scale_y)  # Use smaller scale to fit
                    
                    scaled_width = int(image_width * scale)
                    scaled_height = int(image_height * scale)
                    
                    # Center the image
                    translate_x = (page_width - scaled_width) / 2
                    translate_y = (page_height - scaled_height) / 2
                    
                    # Add image to the slide
                    image_requests = [{
                        'createImage': {
                            'url': image_url,
                            'elementProperties': {
                                'pageObjectId': slide_id,
                                'size': {
                                    'width': {'magnitude': scaled_width, 'unit': 'EMU'},
                                    'height': {'magnitude': scaled_height, 'unit': 'EMU'}
                                },
                                'transform': {
                                    'scaleX': 1,
                                    'scaleY': 1,
                                    'translateX': translate_x,
                                    'translateY': translate_y,
                                    'unit': 'EMU'
                                }
                            }
                        }
                    }]
                    
                    slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': image_requests}
                    ).execute()
                    
                    logger.info(f"  Added section {section_idx + 1} as slide (ID: {slide_id})")
                    
                except Exception as e:
                    logger.error(f"  Error adding section {section_idx + 1}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                # Clean up temp file
                os.unlink(tmp_path)
            
            browser.close()
    
    logger.info(f"\n✅ Successfully exported highlights to Google Slides")
    logger.info(f"📊 Presentation: https://docs.google.com/presentation/d/{presentation_id}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export highlights to Google Slides')
    parser.add_argument('--html-dir', type=str,
                       default='output',
                       help='Directory containing HTML highlight files (default: output)')
    parser.add_argument('--presentation-id', type=str,
                       default=GOOGLE_SLIDES_ID,
                       help=f'Google Slides presentation ID (default: {GOOGLE_SLIDES_ID})')
    
    args = parser.parse_args()
    
    export_highlights_to_slides(args.html_dir, args.presentation_id)

if __name__ == '__main__':
    main()

