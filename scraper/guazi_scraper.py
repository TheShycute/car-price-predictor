# guazi_scraper.py - 瓜子二手车全国爬虫
import asyncio, csv, re, os, json, time, sys
from playwright.async_api import async_playwright

BASE_DIR = r"F:\Program Files\codex\codexwork\car-price-predictor"
DATA_DIR = os.path.join(BASE_DIR, "data")
CHROME_DATA = r"F:\Program Files\codex\codexwork\chrome_data"
CSV_PATH = os.path.join(DATA_DIR, "cars_raw.csv")

STEALTH_JS = """
Object.defineProperty(navigator, "webdriver", {get: () => undefined});
window.chrome = {runtime: {}};
"""

FIELD_NAMES = ["city", "page", "name", "year", "mileage", "location", "price", "price_range"]

# Top cities to scrape (by population/importance)
TOP_CITIES = [
    ("bj", "北京"), ("sh", "上海"), ("gz", "广州"), ("sz", "深圳"),
    ("cd", "成都"), ("hz", "杭州"), ("wh", "武汉"), ("nj", "南京"),
    ("tj", "天津"), ("su", "苏州"), ("xa", "西安"), ("cs", "长沙"),
    ("cq", "重庆"), ("dg", "东莞"), ("qd", "青岛"), ("sy", "沈阳"),
    ("nb", "宁波"), ("zz", "郑州"), ("fz", "福州"), ("hf", "合肥"),
    ("jn", "济南"), ("dl", "大连"), ("xm", "厦门"), ("km", "昆明"),
    ("wx", "无锡"), ("nc", "南昌"), ("gy", "贵阳"), ("nn", "南宁"),
    ("hrb", "哈尔滨"), ("cc", "长春"),
]

PRICE_RANGES = [
    ("0-3万", "0%2C3"),
    ("3-5万", "3%2C5"),
    ("5-10万", "5%2C10"),
]

def parse_listings(text):
    results = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        price_match = re.match(r"^(\d+\.\d+)万", line)
        if price_match:
            price = price_match.group(1)
            name = year = mileage = location = ""
            j = i - 1
            while j >= 0:
                prev = lines[j].strip()
                info_match = re.match(r"(\d{4})年\s*\|\s*([\d.]+)万公里\s*\|\s*(.+)", prev)
                if info_match:
                    year = info_match.group(1)
                    mileage = info_match.group(2)
                    location = info_match.group(3).strip()
                    if j > 0:
                        name = lines[j-1].strip()
                    break
                j -= 1
            if name:
                results.append({"name": name, "year": year, "mileage": mileage, "location": location, "price": price})
    return results

def load_existing():
    results, seen = [], set()
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                k = f"{row.get('name','')}|{row.get('city','')}|{row.get('price','')}"
                if k not in seen:
                    seen.add(k)
                    results.append(row)
    return results, seen

def save_results(results):
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in FIELD_NAMES})

async def scrape_city(page, city_pinyin, city_name):
    city_results = []
    seen_local = set()

    for range_label, price_param in PRICE_RANGES:
        print(f"  [{range_label}]", end=" ", flush=True)
        page_num = 1
        no_more = False
        empty_streak = 0

        # Navigate to first page
        url = f"https://www.guazi.com/{city_pinyin}/?priceRange={price_param}#bread"
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

        while not no_more and page_num <= 100 and empty_streak < 3:
            body_text = await page.evaluate("() => document.body.innerText")
            listings = parse_listings(body_text)

            page_new = 0
            for item in listings:
                k = f"{item['name']}|{item['price']}"
                if k not in seen_local:
                    seen_local.add(k)
                    city_results.append({
                        "city": city_name,
                        "page": str(page_num),
                        "name": item["name"],
                        "year": item["year"],
                        "mileage": item["mileage"],
                        "location": item["location"],
                        "price": item["price"],
                        "price_range": range_label,
                    })
                    page_new += 1

            if page_new == 0:
                empty_streak += 1
            else:
                empty_streak = 0

            page_num += 1
            if empty_streak < 3:
                next_btn = page.locator(f'[aria-label="Page {page_num}"]')
                if await next_btn.count() > 0 and await next_btn.first.is_visible():
                    await next_btn.first.click()
                    await asyncio.sleep(3)
                else:
                    no_more = True
            else:
                no_more = True

        pages_scraped = page_num - empty_streak - 1
        print(f"{pages_scraped} pages", end=" ", flush=True)

    return city_results

async def main():
    print("=" * 60)
    print("  Guazi National Car Price Scraper")
    print("=" * 60)

    all_results, seen_all = load_existing()
    print(f"Loaded {len(all_results)} existing records\n")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            CHROME_DATA, headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1366, "height": 768}
        )
        await context.add_init_script(STEALTH_JS)
        page = await context.new_page()

        total = len(TOP_CITIES)
        for idx, (pinyin, name) in enumerate(TOP_CITIES):
            key_prefix = f"{pinyin}|{name}"
            existing_count = sum(1 for r in all_results if r.get("city") == name)
            print(f"[{idx+1}/{total}] {name} ({pinyin}) - existing: {existing_count}", flush=True)

            try:
                city_data = await scrape_city(page, pinyin, name)

                new_added = 0
                for item in city_data:
                    k = f"{item['name']}|{item['city']}|{item['price']}"
                    if k not in seen_all:
                        seen_all.add(k)
                        all_results.append(item)
                        new_added += 1

                print(f"=> +{new_added} new (total: {len(all_results)})", flush=True)

            except Exception as e:
                print(f"=> ERROR: {e}", flush=True)

            # Save after each city
            save_results(all_results)

            # Polite delay
            await asyncio.sleep(2)

        await context.close()

    print(f"\n{'='*60}")
    print(f"  DONE! Total cars: {len(all_results)}")
    print(f"  Data saved to: {CSV_PATH}")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
