# 二手车价格分析与预测平台 (Used Car Price Analyzer & Predictor)

> 全国二手车数据爬取 + 可视化分析 + ML价格预测 一体化平台

## 🚀 功能

- **数据爬取**: 基于 Playwright 自动化爬取瓜子二手车全国 30+ 城市数据
- **数据清洗**: 品牌提取、特征工程、异常值处理
- **可视化仪表盘**: ECharts 交互式图表 (品牌均价、年份趋势、城市分布等)
- **价格预测**: XGBoost 模型预测二手车价格，支持 Web API

## 📁 项目结构

```
car-price-predictor/
├── scraper/
│   ├── guazi_scraper.py      # 单城市爬虫
│   └── national_scraper.py   # 全国爬虫 (支持断点续传)
├── app/
│   ├── app.py                # Flask Web 服务
│   ├── data_processor.py     # 数据清洗模块
│   ├── templates/
│   │   ├── index.html        # 数据仪表盘
│   │   └── predict.html      # 预测页面
│   └── static/
├── model/
│   └── train_model.py        # XGBoost 模型训练
├── data/
│   ├── cars_raw.csv          # 原始爬取数据
│   └── cars_cleaned.csv      # 清洗后数据
├── requirements.txt
└── README.md
```

## 🔧 安装与运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 爬取数据
```bash
# 爬取全国 30 城市数据 (需要浏览器窗口)
python scraper/national_scraper.py
```

### 3. 训练预测模型
```bash
python model/train_model.py
```

### 4. 启动 Web 服务
```bash
python app/app.py
# 访问 http://localhost:5000
```

## 📊 数据字段

| 字段 | 说明 |
|------|------|
| name | 车型名称 |
| year | 上牌年份 |
| mileage | 行驶里程 (万公里) |
| city | 所在城市 |
| price | 价格 (万元) |
| brand | 品牌 (提取) |
| car_age | 车龄 (计算) |

## 🧠 预测模型

- **算法**: XGBoost Regressor
- **特征**: 年份、里程、车龄、品牌、城市
- **评估**: R² ~0.85+, MAE ~0.6万

## 📸 截图

启动后访问 http://localhost:5000 查看数据仪表盘和预测页面。

## ⚠️ 声明

本项目仅供学习研究使用。数据来源于公开的二手车平台。请遵守相关网站的使用条款，合理控制爬取频率。
