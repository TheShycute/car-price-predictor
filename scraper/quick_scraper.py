# quick_scraper.py - 快速前台运行版本，方便调试
import asyncio, csv, re, os, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

CHROME_DATA = r"F:\Program Files\codex\codexwork\chrome_data"
DATA_DIR = r"F:\Program Files\codex\codexwork\car-price-predictor-project\data"
CSV_PATH = os.path.join(DATA_DIR, "cars_raw.csv")

STEALTH_JS = """
Object.defineProperty(navigator, "webdriver", {get: () => undefined});
window.chrome = {runtime: {}};
"""

FIELD_NAMES = ["city", "page", "name", "year", "mileage", "location", "price", "price_range"]

CITIES = [
    ("bj","北京"),("sh","上海"),("gz","广州"),("sz","深圳"),
    ("cd","成都"),("hz","杭州"),("wh","武汉"),("nj","南京"),
    ("tj","天津"),("su","苏州"),("xa","西安"),("cs","长沙"),
    ("cq","重庆"),("dg","东莞"),("qd","青岛"),("sy","沈阳"),
    ("nb","宁波"),("zz","郑州"),("fz","福州"),("hf","合肥"),
    ("jn","济南"),("dl","大连"),("xm","厦门"),("km","昆明"),
    ("wx","无锡"),("nc","南昌"),("gy","贵阳"),("nn","南宁"),
    ("hrb","哈尔滨"),("cc","长春"),
]

PRICE_RANGES = [
    ("0-3万","0%2C3"), ("3-5万","3%2C5"), ("5-10万","5%2C10"),
]

def parse_listings(text):
    results = []
    lines = [l.strip() for l in text.split("\n")]
    for i, line in enumerate(lines):
        m = re.match(r"^(\d+\.\d+)万", line)
        if m:
            price = m.group(1); name = year = mileage = location = ""
            j = i - 1
            while j >= 0:
                im = re.match(r"(\d{4})年\s*\|\s*([\d.]+)万公里\s*\|\s*(.+)", lines[j])
                if im:
                    year = im.group(1); mileage = im.group(2); location = im.group(3).strip()
                    if j > 0: name = lines[j-1]
                    break
                j -= 1
            if name:
                results.append({"name":name,"year":year,"mileage":mileage,"location":location,"price":price})
    return results

def load_all():
    results, seen = [], set()
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                k = f"{row.get('name','')}|{row.get('city','')}|{row.get('price','')}"
                if k not in seen:
                    seen.add(k); results.append(row)
    return results, seen

def save(results):
    tmp = CSV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in FIELD_NAMES})
    os.replace(tmp, CSV_PATH)

async def scrape_city(page, pinyin, name, max_pages=50):
    city_data = []; seen_local = set()
    for range_label, price_param in PRICE_RANGES:
        await page.goto(f"https://www.guazi.com/{pinyin}/?priceRange={price_param}#bread",
                        wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        pg = 1; no_more = False; empty = 0
        while not no_more and pg <= max_pages and empty < 2:
            text = await page.evaluate("() => document.body.innerText")
            for item in parse_listings(text):
                k = f"{item['name']}|{item['price']}"
                if k not in seen_local:
                    seen_local.add(k)
                    city_data.append({"city":name,"page":str(pg),"name":item["name"],
                        "year":item["year"],"mileage":item["mileage"],
                        "location":item["location"],"price":item["price"],"price_range":range_label})
                    empty = 0
                else: empty += 1
            pg += 1
            if empty < 2:
                btn = page.locator(f'[aria-label="Page {pg}"]')
                if await btn.count() > 0 and await btn.first.is_visible():
                    await btn.first.click(); await asyncio.sleep(3)
                else: no_more = True
            else: no_more = True
    return city_data

async def main():
    all_data, seen_all = load_all()
    print(f"Loaded {len(all_data)} records")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            CHROME_DATA, headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1366, "height": 768}
        )
        await context.add_init_script(STEALTH_JS)
        page = await context.new_page()
        
        for idx, (pinyin, name) in enumerate(CITIES):
            existing = sum(1 for r in all_data if r.get("city") == name)
            print(f"[{idx+1}/30] {name} (existing: {existing})", flush=True)
            
            try:
                city_data = await scrape_city(page, pinyin, name)
                added = 0
                for item in city_data:
                    k = f"{item['name']}|{item['city']}|{item['price']}"
                    if k not in seen_all:
                        seen_all.add(k); all_data.append(item); added += 1
                print(f"  +{added} new (total: {len(all_data)})", flush=True)
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
                save(all_data); break
            
            save(all_data)
            await asyncio.sleep(2)
        
        await context.close()
    
    print(f"\nDONE! Total: {len(all_data)} cars")

asyncio.run(main())
