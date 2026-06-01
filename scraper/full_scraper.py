# full_scraper_v7.py - FIXED: direct file write for save
import asyncio, csv, re, os, sys
from playwright.async_api import async_playwright

CHROME_DATA = r"F:\Program Files\codex\codexwork\chrome_data"
CSV_PATH = r"F:\Program Files\codex\codexwork\car-price-predictor-project\data\cars_raw.csv"

STEALTH_JS = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});window.chrome={runtime:{}};"
FIELD_NAMES = ["city","page","name","year","mileage","location","price","price_range"]

PRICE_RANGES = [
    ("0-3万","0%2C3"),("3-5万","3%2C5"),("5-10万","5%2C10"),
    ("10-15万","10%2C15"),("15-20万","15%2C20"),("20万以上","20%2C999"),
]

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

def parse_listings(text):
    results = []
    lines = [l.strip() for l in text.split("\n")]
    for i, line in enumerate(lines):
        m = re.match(r"^(\d+\.\d+)万(?:已减.*)?$", line)
        if m and i >= 2:
            price = m.group(1)
            j = i - 1
            while j >= 0:
                im = re.match(r"(\d{4})年\s*\|\s*([\d.]+)万公里\s*\|\s*(.+)", lines[j])
                if im:
                    if j > 0 and lines[j-1]:
                        results.append({"name":lines[j-1],"year":im.group(1),"mileage":im.group(2),"location":im.group(3).strip(),"price":price})
                    break
                j -= 1
    return results

def load_all():
    results, seen = [], set()
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH,"r",encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                k=f"{row.get('name','')}|{row.get('city','')}|{row.get('price','')}"
                if k not in seen: seen.add(k); results.append(row)
    return results, seen

def save(results):
    with open(CSV_PATH,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELD_NAMES); w.writeheader()
        w.writerows(results)

def log(msg):
    print(msg, flush=True)

async def main():
    all_data, seen_all = load_all()
    log(f"=== Loaded {len(all_data)} ===\n")
    
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            CHROME_DATA, headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width":1366,"height":768}
        )
        await ctx.add_init_script(STEALTH_JS)
        
        for idx, (pinyin, name) in enumerate(CITIES):
            existing = sum(1 for r in all_data if r.get("city")==name)
            log(f"[{idx+1}/30] {name} (haved: {existing})")
            city_total = 0
            
            for range_label, price_param in PRICE_RANGES:
                page = await ctx.new_page()
                url = f"https://www.guazi.com/{pinyin}/?priceRange={price_param}#bread"
                
                try:
                    await page.goto(url, wait_until="load", timeout=60000)
                    await asyncio.sleep(5)
                except Exception as e:
                    log(f"  [{range_label}] GOTO: {str(e)[:60]}")
                    await page.close()
                    continue
                
                pg = 1; no_more = False; empty = 0; range_count = 0
                while not no_more and pg <= 50 and empty < 3:
                    try:
                        text = await page.evaluate("()=>document.body.innerText")
                    except:
                        try: await page.reload(wait_until="load"); await asyncio.sleep(5)
                        except: pass
                        try: text = await page.evaluate("()=>document.body.innerText")
                        except: no_more=True; break
                    
                    page_new = 0
                    for item in parse_listings(text):
                        k = f"{item['name']}|{name}|{item['price']}"
                        if k not in seen_all:
                            seen_all.add(k)
                            all_data.append({"city":name,"page":str(pg),"name":item["name"],
                                "year":item["year"],"mileage":item["mileage"],
                                "location":item["location"],"price":item["price"],
                                "price_range":range_label})
                            page_new += 1
                        else:
                            empty += 1
                    
                    if page_new > 0: empty = 0
                    range_count += page_new
                    pg += 1
                    
                    if empty < 3:
                        btn = page.locator(f'[aria-label="Page {pg}"]')
                        if await btn.count() > 0 and await btn.first.is_visible():
                            await btn.first.click(); await asyncio.sleep(4)
                        else: no_more = True
                    else: no_more = True
                
                log(f"  [{range_label}] {pg-1}p +{range_count}")
                city_total += range_count
                await page.close()
            
            log(f"  ==> +{city_total} (total: {len(all_data)})")
            save(all_data)
        
        await ctx.close()
    
    log(f"\n=== DONE! {len(all_data)} cars ===")

asyncio.run(main())
