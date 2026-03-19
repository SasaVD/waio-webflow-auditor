import asyncio
from crawler import fetch_page, close_browser

async def test():
    urls = [
        "https://example.com"
    ]
    for url in urls:
        print(f"Fetching {url}...")
        html, soup = await fetch_page(url)
        print(f"Content length for {url}: {len(html)}")
        print(f"Title: {soup.title.string if soup.title else 'No Title'}")
    
    await close_browser()

if __name__ == "__main__":
    asyncio.run(test())
