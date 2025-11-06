#!/usr/bin/env python3
"""
Export Widgets to Images for Canva
Exports each widget HTML file as a PNG or PDF image
"""

import os
import sys
from pathlib import Path
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_playwright():
    """Check if Playwright is installed"""
    try:
        import playwright
        return True
    except ImportError:
        return False

def install_playwright():
    """Install Playwright and browsers"""
    logger.info("Installing Playwright and browsers...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    logger.info("Playwright installed successfully")

def export_widget_to_image(html_file, output_dir, format='png'):
    """
    Export a widget HTML file to an image
    
    Args:
        html_file: Path to HTML file
        output_dir: Directory to save images
        format: 'png' or 'pdf'
    """
    try:
        from playwright.sync_api import sync_playwright
        
        html_path = Path(html_file).resolve()
        output_path = Path(output_dir) / f"{html_path.stem}.{format}"
        
        logger.info(f"Exporting {html_path.name} to {format.upper()}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=2  # Higher quality
            )
            
            # Load the HTML file
            page.goto(f"file://{html_path}")
            
            # Wait for content to load
            page.wait_for_timeout(2000)  # Wait 2 seconds for flags/JS to load
            
            # Take screenshot or save as PDF
            if format == 'png':
                page.screenshot(
                    path=str(output_path),
                    full_page=False,  # Only visible viewport (1920x1080)
                    type='png'
                )
            else:  # PDF
                page.pdf(
                    path=str(output_path),
                    width='1920px',
                    height='1080px',
                    print_background=True
                )
            
            browser.close()
        
        logger.info(f"✅ Exported: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error exporting {html_file}: {str(e)}")
        return None

def export_all_widgets(widgets_dir, output_dir, format='png'):
    """
    Export all widget HTML files to images
    
    Args:
        widgets_dir: Directory containing HTML widget files
        output_dir: Directory to save images
        format: 'png' or 'pdf'
    """
    widgets_path = Path(widgets_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Find all HTML files
    html_files = list(widgets_path.glob('widget_*.html'))
    
    if not html_files:
        logger.warning(f"No widget HTML files found in {widgets_dir}")
        return
    
    logger.info(f"Found {len(html_files)} widget files to export")
    
    # Check if Playwright is installed
    if not check_playwright():
        logger.info("Playwright not found. Installing...")
        try:
            install_playwright()
        except Exception as e:
            logger.error(f"Failed to install Playwright: {str(e)}")
            logger.error("Please install manually: pip install playwright && playwright install chromium")
            return
    
    # Export each widget
    exported = 0
    for html_file in html_files:
        result = export_widget_to_image(html_file, output_path, format)
        if result:
            exported += 1
    
    logger.info(f"\n✅ Successfully exported {exported}/{len(html_files)} widgets to {format.upper()}")
    logger.info(f"📁 Output directory: {output_path}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export widgets to images for Canva')
    parser.add_argument('--widgets-dir', type=str, 
                       default='static_widgets',
                       help='Directory containing widget HTML files (default: static_widgets)')
    parser.add_argument('--output-dir', type=str,
                       default='exported_images',
                       help='Directory to save exported images (default: exported_images)')
    parser.add_argument('--format', type=str,
                       choices=['png', 'pdf'],
                       default='png',
                       help='Export format: png or pdf (default: png)')
    parser.add_argument('--file', type=str,
                       default=None,
                       help='Export a specific HTML file only')
    
    args = parser.parse_args()
    
    # Check if Playwright is installed
    if not check_playwright():
        logger.info("Playwright not found. Would you like to install it? (y/n)")
        response = input().strip().lower()
        if response == 'y':
            try:
                install_playwright()
            except Exception as e:
                logger.error(f"Failed to install Playwright: {str(e)}")
                return
        else:
            logger.info("Install Playwright manually: pip install playwright && playwright install chromium")
            return
    
    if args.file:
        # Export single file
        html_file = Path(args.file)
        if not html_file.exists():
            logger.error(f"File not found: {html_file}")
            return
        
        export_widget_to_image(html_file, args.output_dir, args.format)
    else:
        # Export all widgets
        export_all_widgets(args.widgets_dir, args.output_dir, args.format)

if __name__ == '__main__':
    main()

