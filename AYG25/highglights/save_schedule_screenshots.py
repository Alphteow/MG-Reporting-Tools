import asyncio
import argparse
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / 'output'
IMAGES_ROOT = BASE_DIR / 'schedule_images'
IMAGES_ROOT.mkdir(parents=True, exist_ok=True)

CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080

async def capture_schedules(date_filter=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
            device_scale_factor=2,
        )
        page = await context.new_page()
        await page.emulate_media(media="screen")

        for html_file in sorted(OUTPUT_DIR.glob('schedule_*.html')):
            # Extract date from filename (schedule_YYYY_MM_DD.html)
            filename_parts = html_file.stem.replace('schedule_', '').split('_')
            if len(filename_parts) >= 3:
                day = '_'.join(filename_parts[:3])  # YYYY_MM_DD
            else:
                day = html_file.stem.replace('schedule_', '')
            
            # Filter by date if specified
            if date_filter and day != date_filter:
                continue
            
            safe_day = day.replace(' ', '_')
            day_dir = IMAGES_ROOT / safe_day
            day_dir.mkdir(parents=True, exist_ok=True)

            await page.goto(html_file.resolve().as_uri(), wait_until='networkidle')
            await page.add_style_tag(content=".carousel-dots { display: none !important; }")

            slides = await page.query_selector_all('.schedule-carousel .carousel-slide')
            canvas = await page.query_selector('.schedule-canvas')
            
            if slides:
                for idx in range(len(slides)):
                    await page.evaluate(
                        """
                        (index) => {
                            const slides = Array.from(document.querySelectorAll('.schedule-carousel .carousel-slide'));
                            slides.forEach((slide, i) => {
                                const isActive = i === index;
                                slide.style.display = isActive ? 'block' : 'none';
                                slide.classList.toggle('active', isActive);
                            });
                            window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
                        }
                        """,
                        idx,
                    )
                    await page.wait_for_timeout(120)
                    filename = day_dir / f'slide_{idx + 1:02d}.png'
                    if canvas:
                        await canvas.screenshot(path=str(filename))
                        print(f'Saved {filename}')
                    else:
                        print(f'Canvas not found for {html_file.name}, skipped {filename}')
            elif canvas:
                await page.evaluate("window.scrollTo(0,0);")
                await page.wait_for_timeout(120)
                filename = day_dir / 'slide_01.png'
                await canvas.screenshot(path=str(filename))
                print(f'Saved {filename}')
            else:
                print(f'Canvas not found for {html_file.name}, no screenshot captured.')

        await context.close()
        await browser.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate screenshots from schedule HTML files')
    parser.add_argument('--date', type=str, default=None,
                       help='Filter by specific date (e.g., 2025_10_28). If not specified, processes all dates.')
    args = parser.parse_args()
    asyncio.run(capture_schedules(date_filter=args.date))

