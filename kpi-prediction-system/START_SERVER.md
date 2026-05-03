# How to Start the KPI Prediction System

## Quick Start (Simplified - No Wizard)

```bash
cd /Users/kerisan/BOB_Kerisan/kpi-prediction-system
source venv/bin/activate
python main_simple.py
```

This will start the server without the interactive wizard.

## Access Points

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Monitoring API**: http://localhost:8000/api/v1/monitoring

## With Interactive Wizard

```bash
python main.py
```

This will run the startup wizard to configure KPIs interactively.

## API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed system stats

### Training
- `POST /api/v1/train` - Train a new model
- `GET /api/v1/models` - List all models
- `GET /api/v1/models/{dataset_name}` - Get model info

### Prediction
- `POST /api/v1/predict` - Make a prediction
- `POST /api/v1/compare` - Compare actual vs predicted

### Monitoring
- `POST /api/v1/monitoring/start` - Start monitoring
- `POST /api/v1/monitoring/stop` - Stop monitoring
- `GET /api/v1/monitoring/status` - Get monitoring status
- `GET /api/v1/monitoring/data/{kpi_name}` - Get recent data

### Alerts
- `POST /api/v1/alerts/config` - Configure alerts
- `GET /api/v1/alerts` - List all alerts
- `GET /api/v1/alerts/active` - Get active alerts

## Data Storage

Each KPI stores data in its own CSV file:
- `data/datasets/traffic_count.csv`
- `data/datasets/orders.csv`
- `data/datasets/shipping.csv`
- etc.

New data is appended to existing files automatically.

## Stopping the Server

Press `CTRL+C` in the terminal where the server is running.
