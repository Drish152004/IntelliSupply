
# 🚚 ETA Prediction System

## 📌 Overview

This project builds an end-to-end machine learning system for predicting delivery ETA (Estimated Time of Arrival).  
It integrates feature engineering, model training, optimization, and API deployment into a single pipeline.

---

## 🎯 Problem

Given delivery details such as location, time, and courier, predict the expected delivery time (in minutes).

---

## 📊 Data Used

- Delivery dataset (primary)
- AOI (area information)
- Courier behavior derived from delivery data

⚠️ Note:
The Pickup dataset was explored but excluded due to the absence of a common key to reliably join it with the delivery dataset.

---

## 🔧 Feature Engineering

An extensive feature engineering process was carried out, starting with a broad feature set (~25–30 features), followed by iterative pruning.

---

### ✅ Final Feature Categories

#### 📍 Spatial Features
- `distance_km` → computed from latitude and longitude  
- `distance_hour_interaction` → models congestion impact

---

#### ⏱ Time Features
- `hour` → captures traffic patterns  
- `weekday` → day-based variations  
- `ds` → day index (temporal trend)

---

#### 🚴 Courier Features
- `courier_avg_eta` → average performance  
- `courier_order_count` → experience proxy  

---

#### ⚡ Dynamic Workload Features (Key Innovation)
- `courier_daily_load` → deliveries handled per day  
- `courier_hourly_load` → deliveries handled per hour  

These features significantly improved performance by modeling operational load.

---

#### 🏙 Area (AOI) Features
- `aoi_mean_eta` → average delivery time in region  
- `aoi_count` → density / congestion proxy  

---

### ❌ Removed Feature Groups

| Feature Type | Reason |
|-------------|--------|
| Pickup features | No joinable key |
| Graph features | High error (~57 MAE) |
| Grid features | Weak signal |
| Hub features | Low importance |
| Raw coordinates | Redundant |
| Aggregates (avg_distance) | Overlapping signal |

---

## 📈 Feature Selection Strategy

- Built full feature pipeline ✅  
- Evaluated feature importance ✅  
- Iteratively removed low-impact / noisy features ✅  
- Finalized a compact, high-signal feature set ✅  

---

## 🤖 Model

- Model: **LightGBM Regressor**
- Parameters:
  - `n_estimators = 500`
  - `learning_rate = 0.03`
  - `num_leaves = 64`
  - `subsample = 0.8`
  - `colsample_bytree = 0.8`

---

## 📊 Performance

- MAE: ~31–33 minutes  
- R²: ~0.5  

---

## ⚠️ Challenges Solved

### ✅ 1. Dataset Alignment
- Identified and handled non-joinable datasets (Pickup)

### ✅ 2. Feature Redundancy
- Removed low-importance and overlapping features

### ✅ 3. Categorical Encoding
- Converted categorical IDs into stable numeric representations

### ✅ 4. Data Leakage Prevention
- Used only training data for aggregation features

---

## 🚀 API Design

The system is deployed using **FastAPI**, enabling real-time inference.

---

### ✅ Endpoint

```

POST /predict

````

---

### ✅ Input

```json
{
  "delivery_user_id": 12345,
  "from_dipan_id": 5678,
  "aoi_id": 3456,
  "receipt_time": "2024-10-12T14:30:00",
  "receipt_lat": 12.91,
  "receipt_lng": 77.62,
  "poi_lat": 12.97,
  "poi_lng": 77.59
}
````

***

### ✅ Output

```json
{
  "eta_minutes": 95.2
}
```

***

## ⚙️ How to Run

```bash
pip install -r requirements.txt
uvicorn src.api.app:app --reload
```

Open:

```
http://127.0.0.1:8000/docs
```

***

## 🧠 System Design

The API performs:

```
RAW INPUT → Feature Engineering → Model Prediction
```

***

### 🔁 Dynamic Feature Consideration

Currently, courier workload features (`daily_load`, `hourly_load`) are based on historical data.

In a production system, these would be computed dynamically using:

* active deliveries database
* real-time queries
* streaming updates

Example:

```
courier_hourly_load =
count(active_orders WHERE courier = X AND time window = 1 hour)
```

***

### 🔗 Future Extension (Advanced Systems)

The system can be extended with:

* Graph-based routing (road networks)
* RAG-style enrichment (external traffic APIs)
* Live delivery tracking
* Traffic-aware ETA adjustment

***

## ✅ What This Project Demonstrates

* End-to-end ML system design
* Feature engineering at scale
* Iterative model refinement
* Handling real-world data limitations
* Building production-like inference APIs

***

## 🚀 Future Improvements

* Real-time courier load calculation
* Better distance computation (Haversine)
* Traffic and weather features
* Model calibration for edge cases

***

## ✅ Conclusion

This project goes beyond model training to demonstrate a complete machine learning pipeline, combining data processing, feature engineering, model optimization, and deployment through an API.

```
