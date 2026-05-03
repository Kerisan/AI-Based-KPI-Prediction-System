# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Setup Environment

```bash
# Navigate to project directory
cd kpi-prediction-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### Step 2: Generate Sample Data

```bash
# Run Python to generate sample dataset
python -c "
from services.data_service import DataService
ds = DataService()
path = ds.generate_sample_dataset('traffic_data', num_records=1440, target_column='traffic_count')
print(f'Sample dataset created: {path}')
"
```

### Step 3: Start the API Server

```bash
# Start the FastAPI server
python main.py
```

The API will be available at `http://localhost:8000`

### Step 4: Train Your First Model

```bash
# Using curl
curl -X POST "http://localhost:8000/api/v1/train" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "traffic_data",
    "file_path": "data/datasets/traffic_data.csv",
    "target_column": "traffic_count",
    "epochs": 10,
    "batch_size": 32
  }'

# Or using Python
python -c "
import requests
response = requests.post('http://localhost:8000/api/v1/train', json={
    'dataset_name': 'traffic_data',
    'file_path': 'data/datasets/traffic_data.csv',
    'target_column': 'traffic_count',
    'epochs': 10,
    'batch_size': 32
})
print(response.json())
"
```

### Step 5: Make Predictions

```bash
# Get a prediction
curl -X POST "http://localhost:8000/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "traffic_data",
    "use_current_time": true
  }'
```

### Step 6: Configure Alerts

```bash
# Set alert threshold
curl -X POST "http://localhost:8000/api/v1/alerts/config/traffic_data?threshold_percentage=15&consecutive_minutes=3"
```

### Step 7: Compare Actual vs Predicted

```bash
# Compare actual value with prediction
curl -X POST "http://localhost:8000/api/v1/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "traffic_data",
    "actual_value": 2500,
    "auto_predict": true
  }'
```

### Step 8: Run Monitoring Simulator (Optional)

```bash
# Start real-time monitoring simulation
python -m util.monitoring_simulator --dataset traffic_data --interval 60
```

## 📊 View API Documentation

Open your browser and visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🐳 Using Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🧪 Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=.
```

## 📝 Example Workflow

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Check health
health = requests.get(f"{BASE_URL}/health").json()
print(f"Status: {health['status']}")

# 2. Train model
train_response = requests.post(f"{BASE_URL}/api/v1/train", json={
    "dataset_name": "my_kpi",
    "file_path": "data/datasets/my_data.csv",
    "target_column": "value",
    "epochs": 20
}).json()
print(f"Training: {train_response['status']}")

# 3. Make prediction
prediction = requests.post(f"{BASE_URL}/api/v1/predict", json={
    "dataset_name": "my_kpi",
    "use_current_time": True
}).json()
print(f"Predicted: {prediction['predicted_value']}")

# 4. Compare with actual
comparison = requests.post(f"{BASE_URL}/api/v1/compare", json={
    "dataset_name": "my_kpi",
    "actual_value": 1500
}).json()
print(f"Deviation: {comparison['deviation_percentage']}%")
print(f"Alert: {comparison['alert_triggered']}")

# 5. Get active alerts
alerts = requests.get(f"{BASE_URL}/api/v1/alerts?active_only=true").json()
print(f"Active alerts: {alerts['active_count']}")
```

## 🔧 Troubleshooting

### Port Already in Use
```bash
# Change port in .env file
PORT=8001
```

### Model Training Fails
- Ensure dataset has at least 100 records
- Check CSV format matches expected structure
- Verify target column exists in dataset

### Predictions Fail
- Ensure model is trained first
- Check that recent values cache has sufficient data
- Verify dataset_name matches trained model

## 📚 Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Explore API endpoints in Swagger UI
3. Customize alert thresholds for your use case
4. Add your own datasets and train models
5. Integrate with your monitoring tools

## 💡 Tips

- Start with small epochs (10-20) for testing
- Use the monitoring simulator to test alert system
- Check logs in `logs/app.log` for debugging
- Use `/health/detailed` for system statistics
