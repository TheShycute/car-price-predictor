"""
app.py - Flask 数据展示系统
"""
from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import os
import json

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model")

# Load data on startup
def load_data():
    csv_path = os.path.join(DATA_DIR, "cars_cleaned.csv")
    if not os.path.exists(csv_path):
        # Try raw
        csv_path = os.path.join(DATA_DIR, "cars_raw.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

df = load_data()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stats")
def stats():
    if df.empty:
        return jsonify({"error": "No data loaded"})
    
    return jsonify({
        "total_cars": int(len(df)),
        "avg_price": round(float(df["price"].mean()), 2),
        "min_price": round(float(df["price"].min()), 2),
        "max_price": round(float(df["price"].max()), 2),
        "avg_year": round(float(df["year"].mean()), 1),
        "avg_mileage": round(float(df["mileage"].mean()), 2),
        "cities": int(df["city"].nunique()) if "city" in df.columns else 0,
    })

@app.route("/api/price_by_brand")
def price_by_brand():
    if df.empty:
        return jsonify([])
    grouped = df.groupby("brand")["price"].agg(["mean", "count"]).reset_index()
    grouped = grouped[grouped["count"] >= 5].sort_values("mean")
    return jsonify(grouped.to_dict(orient="records"))

@app.route("/api/price_by_year")
def price_by_year():
    if df.empty:
        return jsonify([])
    grouped = df.groupby("year")["price"].agg(["mean", "count"]).reset_index()
    grouped = grouped.sort_values("year")
    return jsonify(grouped.to_dict(orient="records"))

@app.route("/api/price_by_city")
def price_by_city():
    if df.empty or "city" not in df.columns:
        return jsonify([])
    grouped = df.groupby("city")["price"].agg(["mean", "count"]).reset_index()
    grouped = grouped[grouped["count"] >= 10].sort_values("mean")
    return jsonify(grouped.to_dict(orient="records"))

@app.route("/api/price_by_mileage")
def price_by_mileage():
    if df.empty:
        return jsonify([])
    df_copy = df.copy()
    df_copy["mileage_bucket"] = (df_copy["mileage"] // 5) * 5
    grouped = df_copy.groupby("mileage_bucket")["price"].agg(["mean", "count"]).reset_index()
    grouped = grouped.sort_values("mileage_bucket")
    return jsonify(grouped.to_dict(orient="records"))

@app.route("/api/price_distribution")
def price_distribution():
    if df.empty:
        return jsonify([])
    bins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15]
    labels = [f"{bins[i]}-{bins[i+1]}万" for i in range(len(bins)-1)]
    df_copy = df.copy()
    df_copy["range"] = pd.cut(df_copy["price"], bins=bins, labels=labels)
    dist = df_copy["range"].value_counts().sort_index()
    return jsonify([{"range": k, "count": int(v)} for k, v in dist.items()])

@app.route("/api/car_types")
def car_types():
    if df.empty:
        return jsonify([])
    if "car_type" in df.columns:
        grouped = df.groupby("car_type")["price"].agg(["mean", "count"]).reset_index()
    else:
        grouped = pd.DataFrame([{"car_type": "轿车", "mean": df["price"].mean(), "count": len(df)}])
    return jsonify(grouped.to_dict(orient="records"))

@app.route("/api/recent_cars")
def recent_cars():
    if df.empty:
        return jsonify([])
    sample = df.sample(min(20, len(df)))
    cols = ["name", "year", "mileage", "price", "city"] if "city" in df.columns else ["name", "year", "mileage", "price"]
    return jsonify(sample[cols].to_dict(orient="records"))

@app.route("/predict", methods=["GET"])
def predict_page():
    return render_template("predict.html")

@app.route("/api/predict", methods=["POST"])
def predict_api():
    """Price prediction API"""
    data = request.get_json()
    try:
        year = int(data.get("year", 2020))
        mileage = float(data.get("mileage", 5))
        brand = data.get("brand", "大众")
        city = data.get("city", "北京")
        
        # Load model
        model_path = os.path.join(MODEL_DIR, "price_model.pkl")
        if os.path.exists(model_path):
            import pickle
            with open(model_path, "rb") as f:
                model_data = pickle.load(f)
            
            # Simple prediction using brand/city averages from training data
            model = model_data.get("model")
            encoders = model_data.get("encoders", {})
            
            input_df = pd.DataFrame([{
                "year": year,
                "mileage": mileage,
                "car_age": 2026 - year,
                "brand": brand,
                "city": city,
            }])
            
            # Encode categoricals
            for col, encoder in encoders.items():
                if col in input_df.columns:
                    try:
                        input_df[col] = encoder.transform(input_df[col])
                    except:
                        input_df[col] = -1
            
            prediction = model.predict(input_df[["year", "mileage", "car_age", "brand", "city"]])[0]
            return jsonify({"predicted_price": round(float(prediction), 2), "status": "ok"})
        else:
            # Fallback: simple heuristic
            avg = df[df["brand"] == brand]["price"].mean() if not df.empty and brand in df["brand"].values else 5.0
            age_penalty = max(0, (2026 - year)) * 0.3
            mileage_penalty = mileage * 0.05
            est = max(0.5, avg - age_penalty - mileage_penalty)
            return jsonify({"predicted_price": round(est, 2), "status": "heuristic"})
    
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
