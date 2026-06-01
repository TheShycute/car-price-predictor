"""
data_processor.py - 数据清洗与特征提取
"""
import pandas as pd
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def extract_brand(name):
    """Extract brand from car name"""
    brands = ['大众','丰田','本田','日产','别克','福特','现代','雪佛兰','起亚','奥迪',
              '宝马','奔驰','比亚迪','吉利','长城','长安','奇瑞','荣威','名爵','传祺',
              '哈弗','红旗','领克','蔚来','小鹏','理想','特斯拉','保时捷','凯迪拉克',
              '雷克萨斯','沃尔沃','斯柯达','马自达','标致','雪铁龙','Jeep','三菱',
              '铃木','宝骏','五菱','众泰','江淮','北汽','奔腾','海马','中华',
              '力帆','野马','华晨','英菲尼迪','讴歌','捷豹','路虎','道奇','菲亚特',
              '克莱斯勒','smart','MINI','双龙','金杯','福田','江铃','大通','东风',
              '广汽吉奥','中兴','华泰','昌河','哈飞','凯翼','斯威','汉腾','哪吒',
              '零跑','威马','云度','枫叶','几何','欧拉','埃安','极氪','极星',
              '星途','捷途','欧尚','风行','风神','纳智捷','观致','宝沃','海马']
    for b in sorted(brands, key=len, reverse=True):
        if b in name:
            return b
    # fallback: first word
    return name.split()[0] if name.split() else name[:4]

def extract_car_type(name):
    """Extract car type from name: SUV, 轿车, MPV, etc."""
    name_lower = name.lower()
    if 'suv' in name_lower or '越野' in name:
        return 'SUV'
    if 'mpv' in name_lower or '商务' in name:
        return 'MPV'
    if '皮卡' in name or 'pickup' in name_lower:
        return '皮卡'
    if '跑车' in name or 'coupe' in name_lower:
        return '跑车'
    if '旅行' in name or 'wagon' in name_lower:
        return '旅行车'
    return '轿车'

def extract_displacement(name):
    """Extract engine displacement from name"""
    m = re.search(r'(\d+\.\d+)[LT]', name)
    if m:
        val = m.group(1)
        # Filter: 1.0-6.0 range to avoid matching 2018.x etc.
        if 1.0 <= float(val) <= 6.0:
            return float(val)
    return None

def extract_transmission(name):
    """Extract transmission type"""
    if '自动' in name or 'CVT' in name.upper() or '双离合' in name or 'DSG' in name.upper() or 'AT' in name.upper():
        return '自动'
    if '手动' in name or 'MT' in name.upper():
        return '手动'
    return None

def load_and_clean(csv_path=None):
    """Load raw CSV and return cleaned DataFrame with features"""
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "cars_raw.csv")
    
    df = pd.read_csv(csv_path, encoding="utf-8")
    
    # Convert types
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["mileage"] = pd.to_numeric(df["mileage"], errors="coerce")
    
    # Drop rows with missing critical fields
    df = df.dropna(subset=["price", "year", "mileage"])
    
    # Filter valid ranges
    df = df[(df["price"] > 0) & (df["price"] < 200)]
    df = df[(df["year"] >= 2000) & (df["year"] <= 2026)]
    df = df[(df["mileage"] > 0) & (df["mileage"] < 80)]
    
    # Features
    df["car_age"] = 2026 - df["year"]
    df["brand"] = df["name"].apply(extract_brand)
    df["car_type"] = df["name"].apply(extract_car_type)
    df["displacement"] = df["name"].apply(extract_displacement)
    df["transmission"] = df["name"].apply(extract_transmission)
    
    # Log transform for skewed features
    df["log_price"] = df["price"].apply(lambda x: __import__("numpy").log1p(x))
    df["log_mileage"] = df["mileage"].apply(lambda x: __import__("numpy").log1p(x))
    
    return df

def get_brand_avg_price(df):
    """Calculate average price by brand"""
    return df.groupby("brand")["price"].agg(["mean", "count"]).sort_values("count", ascending=False)

def save_cleaned(df, path=None):
    if path is None:
        path = os.path.join(DATA_DIR, "cars_cleaned.csv")
    df.to_csv(path, index=False, encoding="utf-8")
    return path

if __name__ == "__main__":
    df = load_and_clean()
    print(f"Cleaned data: {len(df)} rows")
    print(f"Brands: {df['brand'].nunique()}")
    print(f"Price range: {df['price'].min():.2f} - {df['price'].max():.2f}万")
    print(get_brand_avg_price(df).head(10))
    save_cleaned(df)
