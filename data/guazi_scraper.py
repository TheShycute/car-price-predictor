import asyncio
import csv
import re
import os
from playwright.async_api import async_playwright

CSV_PATH = r"F:\Program Files\codex\codexwork\guazi_cars.csv"
CHROME_DATA = r"F:\Program Files\codex\codexwork\chrome_data"

STEALTH_JS = """
Object.defineProperty(navigator, "webdriver", {get: () => undefined});
Object.defineProperty(navigator, "plugins", {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, "languages", {get: () => ["zh-CN", "zh", "en"]});
window.chrome = {runtime: {}};
"""

FIELD_NAMES = ["page", "name", "year", "mileage", "city", "price", "price_range"]

def parse_listings(text):
    results = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        price_match = re.match(r"^(\d+\.\d+)万", line)
        if price_match:
            price = price_match.group(1)
            name = ""; year = ""; mileage = ""; city = ""
            j = i - 1
            while j >= 0:
                prev = lines[j].strip()
                info_match = re.match(r"(\d{4})年\s*\|\s*([\d.]+)万公里\s*\|\s*(.+)", prev)
                if info_match:
                    year = info_match.group(1)
                    mileage = info_match.group(2)
                    city = info_match.group(3).strip()
                    if j > 0:
                        name = lines[j-1].strip()
                    break
                j -= 1
            if name:
                results.append({"name": name, "year": year, "mileage": mileage, "city": city, "price": price})
    return results

async def scrape_cars():
    results = []
    seen = set()
    
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row.get('name','')}|{row.get('price','')}"
                if key not in seen:
                    seen.add(key)
                    results.append(row)
        print(f"Loaded {len(results)} existing records")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            CHROME_DATA, headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1366, "height": 768}
        )
        await context.add_init_script(STEALTH_JS)
        page = await context.new_page()
        
        price_ranges = [
            ("0-3万", "0%2C3"),
            ("3-5万", "3%2C5"),
            ("5-10万", "5%2C10"),
        ]
        
        for range_label, price_param in price_ranges:
            print(f"\n{'='*50}")
            print(f"Price range: {range_label}")
            print(f"{'='*50}")
            
            # Start from page 1
            await page.goto(f"https://www.guazi.com/mianyang/?priceRange={price_param}#bread", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(4)
            
            page_num = 1
            no_more = False
            empty_streak = 0
            
            while not no_more and page_num <= 100 and empty_streak < 3:
                print(f"  Page {page_num}...", end=" ")
                
                body_text = await page.evaluate("() => document.body.innerText")
                listings = parse_listings(body_text)
                
                page_new = 0
                for item in listings:
                    key = f"{item['name']}|{item['price']}"
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "page": str(page_num),
                            "name": item["name"],
                            "year": item["year"],
                            "mileage": item["mileage"],
                            "city": item["city"],
                            "price": item["price"],
                            "price_range": range_label,
                        })
                        page_new += 1
                
                print(f"{page_new} cars (total: {len(results)})")
                
                if page_new == 0:
                    empty_streak += 1
                else:
                    empty_streak = 0
                
                # Try clicking next page button
                page_num += 1
                next_aria = f"Page {page_num}"
                next_btn = page.locator(f'[aria-label="{next_aria}"]')
                
                if await next_btn.count() > 0 and await next_btn.first.is_visible():
                    await next_btn.first.click()
                    await asyncio.sleep(3)
                else:
                    # Check if there's a "next" button (下一页)
                    next_text_btn = page.locator('button:has-text("下一页"), button:has-text(">")')
                    if await next_text_btn.count() > 0 and await next_text_btn.first.is_visible():
                        await next_text_btn.first.click()
                        await asyncio.sleep(3)
                    else:
                        print(f"    No more pages for {range_label}")
                        no_more = True
                
                await asyncio.sleep(1)
            
            # Save after each range
            with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
                writer.writeheader()
                for r in results:
                    writer.writerow({k: r.get(k, "") for k in FIELD_NAMES})
            print(f"  Saved {len(results)} records")
        
        await context.close()
    
    print(f"\n{'='*50}")
    print(f"DONE! Total: {len(results)} cars")
    return results

asyncio.run(scrape_cars())
