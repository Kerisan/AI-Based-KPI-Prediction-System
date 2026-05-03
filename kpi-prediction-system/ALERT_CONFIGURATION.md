# Alert Configuration Guide

## Overview

The KPI Prediction System uses a **dynamic threshold-based alerting system** that triggers alerts only after consecutive violations are detected. This prevents false alarms from temporary spikes or dips.

## Configuration Parameters

### 1. Threshold Percentage (DEFAULT_THRESHOLD_PERCENTAGE)

**Default:** `30.0` (30%)

Defines the acceptable deviation range between actual and predicted values:
- **Above threshold:** Alert if actual value is >30% higher than predicted
- **Below threshold:** Alert if actual value is >30% lower than predicted

**Example:**
- Predicted: 100 orders
- Threshold: 30%
- Alert triggers if actual is <70 or >130

### 2. Consecutive Violations (DEFAULT_CONSECUTIVE_VIOLATIONS)

**Default:** `5`

Number of consecutive threshold violations required before triggering an alert. This prevents false alarms from temporary anomalies.

**Example:**
- If threshold is violated 4 times in a row: No alert
- If threshold is violated 5 times in a row: Alert triggered
- If violation stops before reaching 5: Counter resets

### 3. Check Interval (ALERT_CHECK_INTERVAL)

**Default:** `60` seconds (1 minute)

How often the system checks for deviations and potential alerts.

## Configuration Methods

### Method 1: Environment Variables (.env file)

Edit your `.env` file:

```env
# Alert Configuration
DEFAULT_THRESHOLD_PERCENTAGE=30.0
DEFAULT_CONSECUTIVE_VIOLATIONS=5
ALERT_CHECK_INTERVAL=60
```

**Custom Examples:**

```env
# More sensitive (triggers alerts faster)
DEFAULT_THRESHOLD_PERCENTAGE=20.0
DEFAULT_CONSECUTIVE_VIOLATIONS=3

# Less sensitive (fewer false alarms)
DEFAULT_THRESHOLD_PERCENTAGE=40.0
DEFAULT_CONSECUTIVE_VIOLATIONS=7

# Very strict monitoring
DEFAULT_THRESHOLD_PERCENTAGE=15.0
DEFAULT_CONSECUTIVE_VIOLATIONS=10
```

### Method 2: Per-KPI Configuration (API)

You can set different thresholds for each KPI using the API:

```bash
# Set custom threshold for 'orders' KPI
curl -X POST "http://localhost:8000/alerts/config" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "orders",
    "threshold_percentage": 25.0,
    "consecutive_violations": 4,
    "enabled": true,
    "severity": "HIGH"
  }'
```

**Python Example:**

```python
import requests

# Configure different thresholds for different KPIs
configs = {
    "traffic_count": {"threshold": 35.0, "consecutive": 6},
    "orders": {"threshold": 25.0, "consecutive": 4},
    "shipped": {"threshold": 30.0, "consecutive": 5},
    "delivered": {"threshold": 30.0, "consecutive": 5},
    "newcustomer": {"threshold": 40.0, "consecutive": 7}
}

for kpi, config in configs.items():
    response = requests.post(
        "http://localhost:8000/alerts/config",
        json={
            "dataset_name": kpi,
            "threshold_percentage": config["threshold"],
            "consecutive_violations": config["consecutive"],
            "enabled": True
        }
    )
    print(f"{kpi}: {response.json()}")
```

## Alert Severity Levels

Configure alert severity per KPI:

- **LOW**: Minor deviations, informational
- **MEDIUM**: Moderate deviations, requires attention (default)
- **HIGH**: Significant deviations, immediate action needed
- **CRITICAL**: Severe deviations, urgent response required

## How Alerts Work

### Alert Lifecycle

1. **Monitoring**: System checks every 60 seconds (configurable)
2. **Deviation Detection**: Compares actual vs predicted values
3. **Violation Tracking**: Counts consecutive threshold violations
4. **Alert Trigger**: After N consecutive violations, alert is created
5. **Alert Active**: Alert remains active while violations continue
6. **Alert Resolution**: Alert auto-resolves when deviation returns to normal

### Example Scenario

**Configuration:**
- Threshold: 30%
- Consecutive Violations: 5
- KPI: orders

**Timeline:**

| Time | Actual | Predicted | Deviation | Violations | Status |
|------|--------|-----------|-----------|------------|--------|
| 10:00 | 100 | 100 | 0% | 0 | ✓ Normal |
| 10:01 | 140 | 100 | 40% | 1 | ⚠️ Violation 1/5 |
| 10:02 | 145 | 100 | 45% | 2 | ⚠️ Violation 2/5 |
| 10:03 | 150 | 100 | 50% | 3 | ⚠️ Violation 3/5 |
| 10:04 | 155 | 100 | 55% | 4 | ⚠️ Violation 4/5 |
| 10:05 | 160 | 100 | 60% | 5 | 🚨 **ALERT TRIGGERED** |
| 10:06 | 165 | 100 | 65% | 6 | 🚨 Alert Active |
| 10:07 | 120 | 100 | 20% | 0 | ✅ **ALERT RESOLVED** |

## Email Notifications

Configure email alerts in `.env`:

```env
# Email Configuration
EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
ALERT_RECIPIENT_EMAILS=["admin@company.com", "ops@company.com"]
```

**Email Content Includes:**
- Alert status (STARTED/RESOLVED)
- KPI name
- Actual vs Predicted values (as whole numbers)
- Deviation percentage
- Threshold percentage
- Timestamp
- Alert ID

## Best Practices

### 1. Choose Appropriate Thresholds

- **High-volume KPIs** (traffic_count, orders): 25-35%
- **Low-volume KPIs** (newcustomer): 35-50%
- **Critical KPIs** (delivered, shipped): 20-30%

### 2. Balance Sensitivity

- **Too sensitive** (low threshold + few violations): Many false alarms
- **Too lenient** (high threshold + many violations): Miss real issues
- **Recommended**: Start with defaults (30%, 5 violations) and adjust

### 3. Monitor Alert Patterns

- Review alert history regularly
- Adjust thresholds if too many/few alerts
- Consider time-of-day patterns (business hours vs off-hours)

### 4. Test Configuration

```bash
# Get current alert config for a KPI
curl "http://localhost:8000/alerts/config/orders"

# List all active alerts
curl "http://localhost:8000/alerts/active"

# Get alert history
curl "http://localhost:8000/alerts/history?limit=50"
```

## Troubleshooting

### Too Many Alerts

**Problem:** Alerts triggering too frequently

**Solutions:**
1. Increase threshold percentage (e.g., 30% → 40%)
2. Increase consecutive violations (e.g., 5 → 7)
3. Check if model needs retraining with recent data

### Missing Alerts

**Problem:** Not detecting real anomalies

**Solutions:**
1. Decrease threshold percentage (e.g., 30% → 20%)
2. Decrease consecutive violations (e.g., 5 → 3)
3. Verify models are trained and loaded correctly

### Alerts Not Resolving

**Problem:** Alerts stay active indefinitely

**Solutions:**
1. Check if actual values are returning to normal range
2. Verify monitoring service is running
3. Review logs for errors: `tail -f logs/app.log`

## API Endpoints

### Get Alert Configuration
```bash
GET /alerts/config/{dataset_name}
```

### Update Alert Configuration
```bash
POST /alerts/config
Content-Type: application/json

{
  "dataset_name": "orders",
  "threshold_percentage": 30.0,
  "consecutive_violations": 5,
  "enabled": true,
  "severity": "MEDIUM"
}
```

### List Active Alerts
```bash
GET /alerts/active
```

### Get Alert History
```bash
GET /alerts/history?limit=100
```

### Disable Alerts for KPI
```bash
POST /alerts/disable/{dataset_name}
```

### Enable Alerts for KPI
```bash
POST /alerts/enable/{dataset_name}
```

## Summary

The dynamic threshold system provides:
- ✅ Configurable deviation thresholds (default 30%)
- ✅ Consecutive violation tracking (default 5)
- ✅ Per-KPI customization
- ✅ Automatic alert resolution
- ✅ Email notifications
- ✅ Multiple severity levels
- ✅ False alarm prevention

**Quick Start:**
1. Edit `.env` to set global defaults
2. Start system: `python main.py`
3. Monitor logs for predictions and alerts
4. Adjust thresholds per KPI as needed via API
