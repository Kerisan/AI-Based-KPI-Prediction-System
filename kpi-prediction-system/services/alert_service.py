"""
Alert service for managing anomaly detection and alerting.
"""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from data.schema import (
    Alert,
    AlertConfig,
    AlertConfigResponse,
    AlertListResponse,
    ComparisonRequest,
    ComparisonResponse
)
from services.prediction_service import PredictionService
from util.config import settings
from util.constants import AlertSeverity, AlertStatus
from util.helpers import (
    calculate_percentage_deviation,
    format_alert_message,
    is_anomaly
)
from util.logger import LoggerMixin


class AlertService(LoggerMixin):
    """Service for alert management and anomaly detection."""
    
    def __init__(self):
        """Initialize alert service."""
        self.prediction_service = PredictionService()
        
        # Alert configurations per dataset
        self.alert_configs: Dict[str, AlertConfig] = {}
        
        # Active alerts
        self.active_alerts: Dict[str, Alert] = {}
        
        # Alert history
        self.alert_history: List[Alert] = []
        
        # Consecutive deviation tracking
        self.consecutive_deviations: Dict[str, List[Dict]] = defaultdict(list)
        
        self.logger.info("AlertService initialized")
    
    def set_alert_config(
        self,
        dataset_name: str,
        threshold_percentage: Optional[float] = None,
        consecutive_violations: Optional[int] = None,
        enabled: Optional[bool] = None,
        severity: Optional[AlertSeverity] = None
    ) -> AlertConfigResponse:
        """
        Set or update alert configuration for a dataset.
        
        Args:
            dataset_name: Dataset identifier
            threshold_percentage: Deviation threshold
            consecutive_violations: Required consecutive violations
            enabled: Alert enabled status
            severity: Alert severity level
            
        Returns:
            AlertConfigResponse: Updated configuration
        """
        # Get existing config or create new
        if dataset_name in self.alert_configs:
            config = self.alert_configs[dataset_name]
            if threshold_percentage is not None:
                config.threshold_percentage = threshold_percentage
            if consecutive_violations is not None:
                config.consecutive_violations = consecutive_violations
            if enabled is not None:
                config.enabled = enabled
            if severity is not None:
                config.severity = severity
        else:
            config = AlertConfig(
                dataset_name=dataset_name,
                threshold_percentage=threshold_percentage or settings.default_threshold_percentage,
                consecutive_violations=consecutive_violations or settings.default_consecutive_violations,
                enabled=enabled if enabled is not None else True,
                severity=severity or AlertSeverity.MEDIUM
            )
        
        self.alert_configs[dataset_name] = config
        
        self.logger.info(
            f"Alert config updated for {dataset_name}: "
            f"threshold={config.threshold_percentage}%, "
            f"consecutive={config.consecutive_violations} violations"
        )
        
        return AlertConfigResponse(
            dataset_name=config.dataset_name,
            threshold_percentage=config.threshold_percentage,
            consecutive_violations=config.consecutive_violations,
            enabled=config.enabled,
            severity=config.severity
        )
    
    def get_alert_config(self, dataset_name: str) -> AlertConfig:
        """
        Get alert configuration for a dataset.
        
        Args:
            dataset_name: Dataset identifier
            
        Returns:
            AlertConfig: Alert configuration
        """
        if dataset_name not in self.alert_configs:
            # Return default config
            return AlertConfig(
                dataset_name=dataset_name,
                threshold_percentage=settings.default_threshold_percentage,
                consecutive_violations=settings.default_consecutive_violations,
                enabled=True,
                severity=AlertSeverity.MEDIUM
            )
        
        return self.alert_configs[dataset_name]
    
    def compare_and_alert(
        self,
        dataset_name: str,
        actual_value: float,
        timestamp: Optional[datetime] = None,
        predicted_value: Optional[float] = None
    ) -> ComparisonResponse:
        """
        Compare actual vs predicted value and trigger alert if needed.
        
        Args:
            dataset_name: Dataset identifier
            actual_value: Actual observed value
            timestamp: Timestamp (default: now)
            predicted_value: Optional pre-computed prediction
            
        Returns:
            ComparisonResponse: Comparison result with alert status
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Get or generate prediction
        if predicted_value is None:
            try:
                prediction = self.prediction_service.predict(
                    dataset_name=dataset_name,
                    timestamp=timestamp
                )
                predicted_value = prediction.predicted_value
            except Exception as e:
                self.logger.error(f"Failed to generate prediction: {e}")
                raise ValueError(f"Cannot generate prediction: {str(e)}")
        
        # Get alert configuration
        config = self.get_alert_config(dataset_name)
        
        # Calculate deviation
        deviation = calculate_percentage_deviation(actual_value, predicted_value)
        is_anomaly_detected = is_anomaly(
            actual_value,
            predicted_value,
            config.threshold_percentage
        )
        
        self.logger.info(
            f"Comparison for {dataset_name}: "
            f"actual={actual_value:.2f}, predicted={predicted_value:.2f}, "
            f"deviation={deviation:.2f}%"
        )
        
        # Update recent values for future predictions
        self.prediction_service.update_recent_values(dataset_name, actual_value)
        
        # Track consecutive deviations
        alert_triggered = False
        alert_id = None
        
        if config.enabled and is_anomaly_detected:
            alert_id = self._track_deviation(
                dataset_name=dataset_name,
                actual_value=actual_value,
                predicted_value=predicted_value,
                deviation=deviation,
                timestamp=timestamp,
                config=config
            )
            alert_triggered = alert_id is not None
        else:
            # Check if we should resolve any active alerts
            self._check_resolution(dataset_name, deviation, config.threshold_percentage)
        
        return ComparisonResponse(
            dataset_name=dataset_name,
            actual_value=actual_value,
            predicted_value=predicted_value,
            deviation_percentage=deviation,
            is_anomaly=is_anomaly_detected,
            threshold_percentage=config.threshold_percentage,
            timestamp=timestamp,
            alert_triggered=alert_triggered,
            alert_id=alert_id
        )
    
    def _track_deviation(
        self,
        dataset_name: str,
        actual_value: float,
        predicted_value: float,
        deviation: float,
        timestamp: datetime,
        config: AlertConfig
    ) -> Optional[str]:
        """
        Track consecutive deviations and trigger alert if threshold met.
        
        Args:
            dataset_name: Dataset identifier
            actual_value: Actual value
            predicted_value: Predicted value
            deviation: Deviation percentage
            timestamp: Timestamp
            config: Alert configuration
            
        Returns:
            Optional[str]: Alert ID if triggered, None otherwise
        """
        # Add to consecutive tracking
        self.consecutive_deviations[dataset_name].append({
            'timestamp': timestamp,
            'actual': actual_value,
            'predicted': predicted_value,
            'deviation': deviation
        })
        
        # Keep only recent deviations (within consecutive window)
        max_window = config.consecutive_violations + 5  # Keep a bit extra
        if len(self.consecutive_deviations[dataset_name]) > max_window:
            self.consecutive_deviations[dataset_name] = \
                self.consecutive_deviations[dataset_name][-max_window:]
        
        # Count consecutive deviations
        consecutive_count = len(self.consecutive_deviations[dataset_name])
        
        self.logger.debug(
            f"Consecutive violations for {dataset_name}: {consecutive_count}/{config.consecutive_violations}"
        )
        
        # Check if we should trigger an alert
        if consecutive_count >= config.consecutive_violations:
            # Check if alert already active
            active_key = f"{dataset_name}_active"
            
            if active_key not in self.active_alerts:
                # Trigger new alert
                alert_id = str(uuid.uuid4())
                
                alert = Alert(
                    alert_id=alert_id,
                    dataset_name=dataset_name,
                    status=AlertStatus.ACTIVE,
                    severity=config.severity,
                    actual_value=actual_value,
                    predicted_value=predicted_value,
                    deviation_percentage=deviation,
                    consecutive_violations=consecutive_count,
                    threshold_percentage=config.threshold_percentage,
                    required_consecutive_violations=config.consecutive_violations,
                    triggered_at=timestamp,
                    message=format_alert_message(
                        dataset_name,
                        actual_value,
                        predicted_value,
                        deviation,
                        timestamp
                    )
                )
                
                self.active_alerts[active_key] = alert
                self.alert_history.append(alert)
                
                self.logger.warning(
                    f"⚠️ ALERT STARTED [{dataset_name}] {alert.message} | "
                    f"Actual: {int(actual_value)} | Predicted: {int(predicted_value)} | "
                    f"Deviation: {deviation:.2f}%"
                )
                
                # Send email notification
                self._send_alert_email(alert, "STARTED")
                
                return alert_id
            else:
                # Update existing alert
                alert = self.active_alerts[active_key]
                alert.consecutive_count = consecutive_count
                alert.actual_value = actual_value
                alert.predicted_value = predicted_value
                alert.deviation_percentage = deviation
                
                self.logger.debug(f"Updated active alert for {dataset_name}")
                
                return alert.alert_id
        
        return None
    
    def _check_resolution(
        self,
        dataset_name: str,
        current_deviation: float,
        threshold: float
    ) -> None:
        """
        Check if active alert should be resolved.
        
        Args:
            dataset_name: Dataset identifier
            current_deviation: Current deviation percentage
            threshold: Threshold percentage
        """
        active_key = f"{dataset_name}_active"
        
        if active_key in self.active_alerts:
            # Clear consecutive tracking
            self.consecutive_deviations[dataset_name].clear()
            
            # Resolve alert
            alert = self.active_alerts[active_key]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            
            self.logger.info(
                f"✅ ALERT RESOLVED [{dataset_name}] deviation back to {current_deviation:.2f}% (threshold: {threshold}%)"
            )
            
            # Send email notification
            self._send_alert_email(alert, "RESOLVED")
            
            # Move to history and remove from active
            del self.active_alerts[active_key]
    
    def get_active_alerts(
        self,
        dataset_name: Optional[str] = None
    ) -> List[Alert]:
        """
        Get active alerts.
        
        Args:
            dataset_name: Optional dataset filter
            
        Returns:
            List[Alert]: Active alerts
        """
        alerts = list(self.active_alerts.values())
        
        if dataset_name:
            alerts = [a for a in alerts if a.dataset_name == dataset_name]
        
        return alerts
    
    def get_alert_history(
        self,
        dataset_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Get alert history.
        
        Args:
            dataset_name: Optional dataset filter
            limit: Maximum number of alerts to return
            
        Returns:
            List[Alert]: Historical alerts
        """
        alerts = self.alert_history
        
        if dataset_name:
            alerts = [a for a in alerts if a.dataset_name == dataset_name]
        
        # Return most recent first
        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)[:limit]
    
    def get_all_alerts(
        self,
        dataset_name: Optional[str] = None,
        active_only: bool = False
    ) -> AlertListResponse:
        """
        Get all alerts with statistics.
        
        Args:
            dataset_name: Optional dataset filter
            active_only: Return only active alerts
            
        Returns:
            AlertListResponse: Alerts with statistics
        """
        if active_only:
            alerts = self.get_active_alerts(dataset_name)
        else:
            active = self.get_active_alerts(dataset_name)
            history = self.get_alert_history(dataset_name)
            
            # Combine and deduplicate
            alert_dict = {a.alert_id: a for a in history}
            for a in active:
                alert_dict[a.alert_id] = a
            
            alerts = list(alert_dict.values())
        
        # Calculate statistics
        active_count = sum(1 for a in alerts if a.status == AlertStatus.ACTIVE)
        resolved_count = sum(1 for a in alerts if a.status == AlertStatus.RESOLVED)
        
        return AlertListResponse(
            alerts=alerts,
            total_count=len(alerts),
            active_count=active_count,
            resolved_count=resolved_count
        )
    
    def clear_alert_history(
        self,
        dataset_name: Optional[str] = None
    ) -> int:
        """
        Clear alert history.
        
        Args:
            dataset_name: Optional dataset to clear (clears all if None)
            
        Returns:
            int: Number of alerts cleared
        """
        if dataset_name:
            original_count = len(self.alert_history)
            self.alert_history = [
                a for a in self.alert_history 
                if a.dataset_name != dataset_name
            ]
            cleared = original_count - len(self.alert_history)
            self.logger.info(f"Cleared {cleared} alerts for {dataset_name}")
        else:
            cleared = len(self.alert_history)
            self.alert_history.clear()
            self.logger.info(f"Cleared all {cleared} alerts")
        
        return cleared
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """
        Get alert by ID.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            Optional[Alert]: Alert if found
        """
        # Check active alerts
        for alert in self.active_alerts.values():
            if alert.alert_id == alert_id:
                return alert
        
        # Check history
        for alert in self.alert_history:
            if alert.alert_id == alert_id:
                return alert
        
        return None
    
    def get_alert_statistics(
        self,
        dataset_name: Optional[str] = None
    ) -> Dict:
        """
        Get alert statistics.
        
        Args:
            dataset_name: Optional dataset filter
            
        Returns:
            Dict: Alert statistics
        """
        all_alerts = self.get_all_alerts(dataset_name)
        
        stats = {
            'total_alerts': all_alerts.total_count,
            'active_alerts': all_alerts.active_count,
            'resolved_alerts': all_alerts.resolved_count,
            'datasets_with_alerts': len(set(a.dataset_name for a in all_alerts.alerts))
        }
        
        # Calculate severity distribution
        severity_counts = defaultdict(int)
        for alert in all_alerts.alerts:
            severity_counts[alert.severity.value] += 1
        
        stats['severity_distribution'] = dict(severity_counts)
        
        # Calculate average deviation for active alerts
        active_alerts = [a for a in all_alerts.alerts if a.status == AlertStatus.ACTIVE]
        if active_alerts:
            avg_deviation = sum(a.deviation_percentage for a in active_alerts) / len(active_alerts)
            stats['average_active_deviation'] = round(avg_deviation, 2)
        else:
            stats['average_active_deviation'] = 0.0
        
        return stats
    
    def disable_alerts(self, dataset_name: str) -> None:
        """
        Disable alerts for a dataset.
        
        Args:
            dataset_name: Dataset identifier
        """
        config = self.get_alert_config(dataset_name)
        config.enabled = False
        self.alert_configs[dataset_name] = config
        self.logger.info(f"Alerts disabled for {dataset_name}")
    
    def enable_alerts(self, dataset_name: str) -> None:
        """
        Enable alerts for a dataset.
        Args:
            dataset_name: Dataset identifier
        """
        config = self.get_alert_config(dataset_name)
        config.enabled = True
        self.alert_configs[dataset_name] = config
        self.logger.info(f"Alerts enabled for {dataset_name}")


    def _send_alert_email(self, alert: Alert, status: str) -> None:
        """
        Send email notification for alert.
        
        Args:
            alert: Alert object
            status: Alert status (STARTED or RESOLVED)
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Email configuration from settings
            if not hasattr(settings, 'email_enabled') or not settings.email_enabled:
                self.logger.debug("Email notifications disabled")
                return
            
            smtp_server = getattr(settings, 'smtp_server', 'smtp.gmail.com')
            smtp_port = getattr(settings, 'smtp_port', 587)
            sender_email = getattr(settings, 'sender_email', '')
            sender_password = getattr(settings, 'sender_password', '')
            recipient_emails = getattr(settings, 'alert_recipient_emails', [])
            
            if not sender_email or not recipient_emails:
                self.logger.warning("Email configuration incomplete, skipping email notification")
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = f"KPI Alert {status}: {alert.dataset_name}"
            
            # Email body
            body = f"""
                    KPI Prediction System Alert

                    Status: {status}
                    KPI: {alert.dataset_name}
                    Severity: {alert.severity.value}
                    Timestamp: {alert.triggered_at}

                    Actual Value: {int(alert.actual_value)}
                    Predicted Value: {int(alert.predicted_value)}
                    Deviation: {alert.deviation_percentage:.2f}%
                    Threshold: {alert.threshold_percentage:.2f}%

                    Message: {alert.message}

                    Alert ID: {alert.alert_id}
                    """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if sender_password:
                    server.login(sender_email, sender_password)
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent for alert {status}: {alert.alert_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")

        