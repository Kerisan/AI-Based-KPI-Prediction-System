# AI-Based KPI Prediction System - Real-Time Monitoring

## 🎯 Overview

A production-ready, real-time KPI monitoring and prediction system that uses LSTM deep learning models to predict metrics at per-minute intervals and detect anomalies automatically. Features an interactive startup wizard, threaded monitoring for multiple KPIs, and a live web dashboard.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Dashboard (UI)                        │
│              Real-time Charts & Monitoring                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  FastAPI Controllers                         │
│  /monitoring (start/stop) | /predict | /alerts | /train     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Real-Time Monitoring Service                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ KPI #1   │  │ KPI #2   │  │ KPI #3   │  (Threaded)      │
│  │ Monitor  │  │ Monitor  │  │ Monitor  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
┌───────▼─────────────▼─────────────▼────────────────────────┐
│              Services Layer                                  │
│  Model Service | Prediction Service | Alert Service         │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Key Features

### ✅ Real-Time Monitoring
- **Threaded Architecture**: Each KPI runs in its own thread for parallel monitoring
- **Auto Data Collection**: Continuously collects actual values and appends to datasets
- **Dynamic Flush**: Periodically saves collected data to CSV files
- **Live Predictions**: Generates predictions every minute for each KPI

### ✅ Interactive Startup Wizard
- **Auto-Detection**: Finds existing trained models on startup
- **KPI Configuration**: Interactive prompts to configure new KPIs
- **Data Source Options**: Simulated, HTTP endpoint, database, or custom
- **Auto-Training**: Trains models automatically when sufficient data is collected

### ✅ Web Dashboard
- **Real-Time Charts**: Live graphs showing actual vs predicted values
- **Multi-KPI View**: Monitor multiple KPIs simultaneously
- **Start/Stop Controls**: Easy monitoring control from UI
- **Auto-Refresh**: Configurable auto-refresh (default: 30s)
- **Time Range Selection**: View last 15min to 6 hours of data

### ✅ Intelligent Alerting
- **Consecutive Tracking**: Alerts only after N consecutive deviations
- **Auto-Resolution**: Automatically resolves when metrics normalize
- **Configurable Thresholds**: Set deviation % and consecutive minutes per KPI
- **Real-Time Notifications**: Immediate alert display in dashboard

### ✅ Production-Ready
- **LSTM Deep Learning**: Time series prediction with 60-minute sequences
- **Error Handling**: Comprehensive error handling and logging
- **Docker Support**: Full containerization with docker-compose
- **API Documentation**: Auto-generated OpenAPI/Swagger docs
- **Unit Tests**: Test suite with pytest

## 📋 Quick Start

### 1. Installation

```bash
cd kpi-prediction-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Start the Application

```bash
python main.py
```

The **interactive startup wizard** will guide you through:
1. Detecting existing models
2. Configuring KPIs to monitor
3. Setting up data sources
4. Training models (if needed)
5. Starting monitoring

### 3. Access the Dashboard

Open your browser: `http://localhost:8000`

The dashboard shows:
- Real-time charts for each KPI
- Current vs predicted values
- Deviation percentages
- Active alerts
- Start/Stop controls

## 🎮 Usage Examples

### Example 1: Monitor with Existing Models

```
🚀 KPI PREDICTION SYSTEM - STARTUP WIZARD
================================================================================

✅ Found 2 existing trained models:
   - traffic_count (Status: TRAINED)
   - orders (Status: TRAINED)

Do you want to use existing models? [Y/n]: y

🔧 Setting up monitoring from existing models...

📈 KPI: traffic_count
   Data source options:
   1. Simulated (for testing)
   2. HTTP endpoint
   3. Database query
   Select data source type (1-3, default: 1): 1
   ✅ Registered traffic_count for monitoring

📈 KPI: orders
   Data source options:
   1. Simulated (for testing)
   2. HTTP endpoint
   3. Database query
   Select data source type (1-3, default: 1): 2
   Enter HTTP endpoint URL: http://api.example.com/orders/current
   ✅ Registered orders for monitoring

================================================================================
Start monitoring now? [Y/n]: y
✅ Monitoring started!
================================================================================

🌐 Access the dashboard at: http://0.0.0.0:8000
📚 API documentation at: http://0.0.0.0:8000/docs
```

### Example 2: Configure New KPIs

```
📊 Let's configure your KPIs for monitoring...
--------------------------------------------------------------------------------
Enter KPI name (or 'done' to finish): website_traffic

⚙️  Configuring website_traffic...
   Target column name (default: website_traffic_value): traffic_count
   Check interval in seconds (default: 60): 60
   Data flush interval in seconds (default: 3600): 3600

   Data source options:
   1. Simulated (for testing)
   2. HTTP endpoint
   3. Database query
   4. Custom function
   Select data source type (1-4, default: 1): 2
   Enter HTTP endpoint URL: http://metrics.example.com/traffic

🔄 No trained model found for website_traffic
   ℹ️  Model will be trained automatically after collecting 1000 data points
   ✅ website_traffic configured and ready for monitoring

--------------------------------------------------------------------------------
Enter KPI name (or 'done' to finish): done
```

## 📊 API Endpoints

### Monitoring Control
```bash
# Start monitoring all KPIs
POST /api/v1/monitoring/start

# Start specific KPI
POST /api/v1/monitoring/start?kpi_name=traffic_count

# Stop monitoring
POST /api/v1/monitoring/stop

# Get status
GET /api/v1/monitoring/status

# List KPIs
GET /api/v1/monitoring/kpis

# Get recent data
GET /api/v1/monitoring/data/{kpi_name}?minutes=60
```

### Training & Models
```bash
# Train model
POST /api/v1/train

# List models
GET /api/v1/models

# Get model info
GET /api/v1/models/{dataset_name}

# Delete model
DELETE /api/v1/models/{dataset_name}
```

### Predictions
```bash
# Get prediction
POST /api/v1/predict

# Batch predictions
POST /api/v1/predict/batch

# Predict next N minutes
GET /api/v1/predict/next/{dataset_name}?n_minutes=10
```

### Alerts
```bash
# Get alerts
GET /api/v1/alerts?active_only=true

# Get alert config
GET /api/v1/alerts/config/{dataset_name}

# Update alert config
PUT /api/v1/alerts/config

# Enable/disable alerts
POST /api/v1/alerts/enable/{dataset_name}
POST /api/v1/alerts/disable/{dataset_name}
```

## 🔧 Configuration

Edit `.env` file:

```env
# Application
APP_NAME=KPI Prediction System
DEBUG=True
PORT=8000

# Model Configuration
SEQUENCE_LENGTH=60
HIDDEN_SIZE=128
EPOCHS=50

# Alert Configuration
DEFAULT_UPPER_THRESHOLD_PERCENTAGE=100
DEFAULT_LOWER_THRESHOLD_PERCENTAGE=30.0
DEFAULT_CONSECUTIVE_VIOLATIONS=5
ALERT_CHECK_INTERVAL=60

# Real-time Data Collection
DATA_COLLECTION_INTERVAL=60
DATA_FLUSH_INTERVAL=3600
AUTO_TRAIN_THRESHOLD=1000
```

## 📁 Project Structure

```
kpi-prediction-system/
├── services/
│   ├── data_service.py           # Data processing
│   ├── model_service.py          # ML model management
│   ├── prediction_service.py     # Predictions
│   ├── alert_service.py          # Alerting
│   ├── realtime_monitor.py       # Real-time monitoring (NEW)
│   └── startup_wizard.py         # Interactive wizard (NEW)
│
├── controller/
│   ├── health_controller.py
│   ├── training_controller.py
│   ├── prediction_controller.py
│   ├── alert_controller.py
│   └── monitoring_controller.py  # Monitoring control (NEW)
│
├── middleware/
│   ├── logging_middleware.py
│   ├── error_handler.py
│   └── auth_middleware.py
│
├── static/
│   └── index.html                # Web dashboard (NEW)
│
├── data/
│   ├── models/                   # Trained models
│   ├── datasets/                 # Training datasets
│   └── schema.py                 # Data models
│
├── util/
│   ├── config.py
│   ├── logger.py
│   ├── helpers.py
│   └── constants.py
│
├── main.py                       # Entry point with wizard
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔄 How It Works

### 1. Startup Process
```
Application Start
    ↓
Run Startup Wizard
    ↓
Detect Existing Models → Use existing
    ↓                  ↘
Configure New KPIs      Configure data sources
    ↓                      ↓
Register KPI Monitors ←────┘
    ↓
Start Monitoring (optional)
    ↓
Launch Web Server
```

### 2. Real-Time Monitoring Loop (Per KPI)
```
Every minute (configurable):
    ↓
1. Fetch current value from data source
    ↓
2. Generate prediction using trained model
    ↓
3. Calculate deviation percentage
    ↓
4. Check for anomaly (threshold exceeded?)
    ↓
5. Track consecutive deviations
    ↓
6. Trigger alert if threshold met
    ↓
7. Store data point in buffer
    ↓
8. Update UI cache for dashboard
    ↓
9. Periodically flush buffer to CSV
    ↓
10. Auto-train if data threshold reached
```

### 3. Data Collection & Storage
- Each KPI has its own CSV file: `{kpi_name}_realtime.csv`
- Data is buffered in memory and flushed periodically
- New data is appended to existing files
- Format includes: timestamp, actual_value, predicted_value, deviation, time features

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=.

# Test specific service
pytest tests/test_model_service.py -v
```

## 📈 Dashboard Features

### Real-Time Charts
- **Line Charts**: Actual vs Predicted values
- **Auto-Update**: Refreshes every 30 seconds
- **Time Range**: Select from 15min to 6 hours
- **Responsive**: Adapts to screen size

### Metrics Display
- **Current Value**: Latest actual measurement
- **Predicted Value**: Model prediction
- **Deviation %**: Color-coded (green/yellow/red)

### Controls
- **Start All**: Begin monitoring all KPIs
- **Stop All**: Pause all monitoring
- **Refresh**: Manual data refresh
- **Auto-Refresh**: Toggle automatic updates

## 🔐 Security

- Optional API key authentication
- Input validation on all endpoints
- SQL injection prevention
- Rate limiting (configurable)
- CORS configuration

## 📊 Monitoring Best Practices

1. **Start with Simulated Data**: Test the system before connecting real sources
2. **Collect Sufficient Data**: Wait for 1000+ data points before training
3. **Tune Thresholds**: Adjust deviation % based on your KPI characteristics
4. **Monitor Gradually**: Start with 1-2 KPIs, then scale up
5. **Review Alerts**: Check alert history to fine-tune consecutive minutes

## 🛠️ Troubleshooting

### Model Not Training
- Ensure dataset has at least 100 records
- Check CSV format matches expected structure
- Verify target column exists

### Predictions Fail
- Ensure model is trained first
- Check recent values cache has sufficient data (60 points)
- Verify dataset_name matches trained model

### Dashboard Not Updating
- Check monitoring is started (green status)
- Verify auto-refresh is enabled
- Check browser console for errors

### High Memory Usage
- Reduce `DATA_FLUSH_INTERVAL` to flush more frequently
- Limit number of concurrent KPIs
- Adjust `max_recent` in KPIMonitor

## 📝 License

MIT License

## 👥 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Built with ❤️ using Python, FastAPI, TensorFlow, and Chart.js**
