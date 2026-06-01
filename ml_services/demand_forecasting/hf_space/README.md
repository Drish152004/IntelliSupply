---
title: IntelliSupply Demand Forecasting
emoji: 📦
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# IntelliSupply — demand forecasting (inference)

Regional package demand predictions from a trained scikit-learn pipeline.

- **POST** `/predict` — same JSON body as local FastAPI
- **GET** `/meta` — feature columns and holdout metrics
- **GET** `/health` — liveness check

Python 3.12 · FastAPI · scikit-learn
