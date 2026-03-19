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
        print(type(results.response))
        if isinstance(results.response, dict):
            print(results.response.keys())
        await browser.close()

asyncio.run(main())
