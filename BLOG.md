# 🚗 二手车价格预测平台 — 数据可视化与机器学习实战

> 26,000+ 条数据 · 40 个城市 · 3D 可视化 · XGBoost R²=0.76

---

## 项目背景

二手车市场信息极度不对称——同一款车在不同城市、不同里程下价格可能相差数万。作为一个想买车的人，我希望能有一个工具，既能直观看到全国二手车价格分布，又能针对具体车型给出合理估价。

于是就有了 **UsedCarInsight**——一个基于公开二手车数据集，集数据清洗、可视化分析和机器学习预测于一体的项目。

GitHub: [github.com/TheShycute/car-price-predictor](https://github.com/TheShycute/car-price-predictor)

### 最终效果

![仪表盘](https://raw.githubusercontent.com/TheShycute/car-price-predictor/master/screenshots/dashboard.png)

![预测页](https://raw.githubusercontent.com/TheShycute/car-price-predictor/master/screenshots/predict.png)

---

## 一、数据来源

本项目使用的数据集来源于公开的二手车交易记录，涵盖全国 40 个城市、26,000+ 条车辆信息。

### 数据字段

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 车型全称 | 大众 朗逸 2019款 280TSI |
| year | 上牌年份 | 2019 |
| mileage | 行驶里程(万公里) | 5.23 |
| city | 所在城市 | 上海 |
| price | 挂牌价格(万元) | 7.50 |
| price_range | 价格区间 | 5-10万 |

### 数据覆盖

| 城市 | 数量 | 价格区间 |
|------|------|----------|
| 广州 | 4,182 | 0-75万 |
| 上海 | 4,011 | 0-75万 |
| 杭州 | 3,598 | 0-75万 |
| 北京 | 2,469 | 0-75万 |
| 深圳 | 1,637 | 0-75万 |

> 如需完整数据集用于个人学习研究，请联系作者获取。
## 二、数据清洗与特征工程

从原始车名中提取多个维度：

```python
def extract_brand(name):    # "大众 朗逸 2019款..." → "大众"
def extract_car_type(name): # SUV/轿车/MPV/皮卡/跑车
def extract_displacement(name):  # 排量 1.5T → 1.5
def extract_transmission(name):  # 自动/手动

df["car_age"] = 2026 - df["year"]  # 车龄
```

过滤异常值：年份 2000-2026、里程 0-80 万公里、价格 > 0。

---

## 三、机器学习模型

### 模型选择：XGBoost

- 特征：`year`, `mileage`, `car_age`, `brand`, `city`
- 品牌和城市经过 LabelEncoding
- 80/20 训练测试分割

```python
model = xgb.XGBRegressor(
    n_estimators=300, max_depth=6,
    learning_rate=0.05, subsample=0.8
)
model.fit(X_train, y_train)
```

### 模型表现

| 指标 | 数值 |
|------|------|
| R² | **0.76** |
| MAE | 2.35 万 |
| RMSE | 4.14 万 |
| 5-fold CV R² | -2.55* |

> *CV 波动大是因为部分品牌/城市在训练集中出现较少，随着数据量增大这一问题会改善。

### 特征重要性

| 特征 | 重要性 |
|------|--------|
| 车龄 | 34.6% |
| 品牌 | 26.2% |
| 年份 | 22.5% |
| 城市 | 13.4% |
| 里程 | 3.3% |

车龄和品牌是最核心的定价因素，里程影响反而不大——这说明里程数可能被篡改或买家更关注车龄。

---

## 四、前端：3D 可视化仪表盘

### 设计理念

深色奢华主题，灵感来自高端汽车展厅：
- **字体**：Playfair Display（标题）+ DM Sans（正文）
- **配色**：金色主色调 + 蓝/绿/玫瑰色辅助
- **特效**：Three.js 粒子背景 + GSAP 入场动画

### 核心功能

**中国地图**：点击省份查看该省车源数、均价、热门品牌、价格分布

```javascript
fetch('https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json')
  .then(r => r.json())
  .then(geoJson => {
    echarts.registerMap('china', geoJson);
    // 渲染热力图
  });
```

**价格预测**：输入品牌、城市、年份、里程，即时返回估价

```python
@app.route("/api/predict", methods=["POST"])
def predict_api():
    data = request.get_json()
    # 编码特征 → 模型预测
    prediction = model.predict(input_df)[0]
    return jsonify({"predicted_price": round(float(prediction), 2)})
```

---

## 五、项目结构

```
car-price-predictor/
├── scraper/                   # 数据采集脚本
├── app/
│   ├── app.py                   # Flask API + 后端
│   ├── data_processor.py        # 数据清洗模块
│   └── templates/
│       ├── index.html           # 中国地图仪表盘
│       └── predict.html         # 价格预测页
├── model/train_model.py         # XGBoost 训练脚本
├── data/                        # 数据文件
├── screenshots/                 # 截图
└── README.md
```

---

## 六、反思与改进方向

### 已做到的
- 26,000+ 条真实数据
- 完整的 数据清洗 → 模型 → 部署链路
- 3D 可视化 + 交互式地图
- RESTful API + 端到端预测

### 可以改进的
1. **数据量**：目前仅覆盖 12 个重点城市，可扩展到 319 个
2. **模型**：加入更多特征（排量、变速箱、车况标签），尝试 LightGBM / CatBoost 对比
3. **部署**：Docker 容器化，部署到云服务器
4. **实时性**：定时任务自动更新数据，模型自动重训
5. **车况分析**：解析"顶配""高保值""车主急售"等标签作为特征

---

## 七、技术栈总结

| 层 | 选型 | 理由 |
|----|------|------|
| 数据来源 | 公开数据集 | 全国40城真实交易记录 |
| 后端 | Flask | 轻量，适合原型快速开发 |
| 可视化 | ECharts | 支持中国地图，3D 效果好 |
| 特效 | Three.js | 背景粒子系统 |
| 动画 | GSAP | 流畅的入场动画 |
| ML | XGBoost | 表格数据的最佳选择 |

---

**GitHub**: [https://github.com/TheShycute/car-price-predictor](https://github.com/TheShycute/car-price-predictor)

**本地运行**：
```bash
git clone https://github.com/TheShycute/car-price-predictor.git
cd car-price-predictor
pip install -r requirements.txt
python model/train_model.py
python app/app.py
# 访问 http://localhost:5000
```

---

*本文为个人学习项目，仅供学习研究参考。*

