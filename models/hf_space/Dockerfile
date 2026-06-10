FROM python:3.12-slim

WORKDIR /app

COPY models/hf_space/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY models/hf_space/inference.py .
COPY models/hf_space/api ./api
COPY models/lade_demand_forecaster.pkl ./models/lade_demand_forecaster.pkl

EXPOSE 7860
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "7860"]
