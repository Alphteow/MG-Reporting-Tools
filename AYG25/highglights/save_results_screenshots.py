import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_DIR = Path('highglights/output')
IMAGES_ROOT = Path('highglights/result_images')
IMAGES_ROOT.mkdir(exist_ok=True)

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

async def capture_results():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT})

        for html_file in sorted(OUTPUT_DIR.glob('highlights_*.html')):
            day = html_file.stem.replace('highlights_', '')
            day_dir = IMAGES_ROOT / day
            day_dir.mkdir(exist_ok=True)

            await page.goto(html_file.resolve().as_uri(), wait_until='networkidle')

            slides = await page.query_selector_all('.results-carousel .carousel-slide')
            if slides:
                for idx in range(len(slides)):
                    await page.evaluate(
                        "(index) => {const slides = Array.from(document.querySelectorAll('.results-carousel .carousel-slide')); slides.forEach((slide, i) => {slide.style.display = i === index ? 'block' : 'none';}); window.scrollTo(0,0);}",
                        idx,
                    )
                    await page.wait_for_timeout(120)
                    filename = day_dir / f'slide_{idx + 1:02d}.png'
                    await page.locator('.results-carousel .carousel-slide').nth(idx).screenshot(path=str(filename))
                    print(f'Saved {filename}')
            else:
                section = await page.query_selector('.results-section')
                if section:
                    await page.evaluate("window.scrollTo(0,0);")
                    await page.wait_for_timeout(120)
                    filename = day_dir / 'slide_01.png'
                    await section.screenshot(path=str(filename))
                    print(f'Saved {filename}')

        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_results())
