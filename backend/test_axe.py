import asyncio
from playwright.async_api import async_playwright
from axe_playwright_python.async_playwright import Axe

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://example.com")
        axe = Axe()
        results = await axe.run(page)
        print(type(results))
        if isinstance(results, dict):
            print(results.keys())
        else:
            print(dir(results))
        await browser.close()

asyncio.run(main())
