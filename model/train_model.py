"""
train_model.py - 二手车价格预测模型训练
使用 XGBoost + 特征工程
"""
import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import warnings
warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "model")

os.makedirs(MODEL_DIR, exist_ok=True)

def load_data():
    cleaned_path = os.path.join(DATA_DIR, "cars_cleaned.csv")
    raw_path = os.path.join(DATA_DIR, "cars_raw.csv")
    
    path = cleaned_path if os.path.exists(cleaned_path) else raw_path
    print(f"Loading: {path}")
    df = pd.read_csv(path, encoding="utf-8")
    
    # Basic cleaning
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["mileage"] = pd.to_numeric(df["mileage"], errors="coerce")
    df = df.dropna(subset=["price", "year", "mileage"])
    df = df[(df["price"] > 0) & (df["price"] < 200)]
    df = df[(df["year"] >= 2000) & (df["year"] <= 2026)]
    df = df[(df["mileage"] > 0) & (df["mileage"] < 80)]
    
    # Feature engineering
    df["car_age"] = 2026 - df["year"]
    
    # Extract brand (simple)
    def get_brand(name):
        brands = ["大众","丰田","本田","日产","别克","福特","现代","雪佛兰","起亚","奥迪",
                  "宝马","奔驰","比亚迪","吉利","长城","长安","奇瑞","荣威","名爵","广汽传祺",
                  "哈弗","红旗","领克","蔚来","小鹏","理想","特斯拉","保时捷","凯迪拉克",
                  "雷克萨斯","沃尔沃","斯柯达","马自达","标致","雪铁龙","Jeep","宝骏","五菱"]
        for b in sorted(brands, key=len, reverse=True):
            if b in str(name):
                return b
        return str(name).split()[0] if str(name).split() else str(name)[:4]
    
    df["brand"] = df["name"].apply(get_brand)
    if "city" not in df.columns and "location" in df.columns:
        df["city"] = df["location"]
    
    print(f"Cleaned: {len(df)} rows, {df['brand'].nunique()} brands")
    return df

def train_model(df):
    # Encode categorical features
    encoders = {}
    X = df[["year", "mileage", "car_age"]].copy()
    
    for col in ["brand", "city"]:
        if col in df.columns:
            le = LabelEncoder()
            X[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
    
    y = df["price"]
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # XGBoost model
    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluation
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print(f"\nModel Performance:")
    print(f"  MAE:  {mae:.4f}万  (平均误差)")
    print(f"  RMSE: {rmse:.4f}万")
    print(f"  R2:   {r2:.4f}")
    
    # Feature importance
    importance = pd.DataFrame({
        "feature": X.columns,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    print("\nFeature Importance:")
    for _, row in importance.iterrows():
        print(f"  {row['feature']:15s} : {row['importance']:.4f}")
    
    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
    print(f"\n5-fold CV R2: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    
    # Save model
    model_data = {
        "model": model,
        "encoders": encoders,
        "features": list(X.columns),
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2, "cv_r2_mean": cv_scores.mean()}
    }
    
    model_path = os.path.join(MODEL_DIR, "price_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)
    
    print(f"\nModel saved to: {model_path}")
    
    # For fun: predict some examples
    print("\nSample predictions:")
    samples = df.sample(5)
    for _, row in samples.iterrows():
        row_df = pd.DataFrame([row])
        for col in encoders:
            row_df[col] = row_df[col].astype(str)
            try:
                row_df[col] = encoders[col].transform(row_df[col])
            except:
                row_df[col] = -1
        pred = model.predict(row_df[X.columns])[0]
        print(f"  {row['name'][:30]:30s} | 实际: {row['price']:.2f}万 | 预测: {pred:.2f}万 | 误差: {abs(row['price']-pred):.2f}万")
    
    return model, encoders

if __name__ == "__main__":
    df = load_data()
    train_model(df)
