"""
Real-time monitoring service with threading for each KPI.
"""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
import pandas as pd
import numpy as np

from services.model_service import ModelService
from services.prediction_service import PredictionService
from services.alert_service import AlertService
from util.config import settings
from util.helpers import ensure_directory_exists, generate_time_features
from util.logger import LoggerMixin


class KPIMonitor(LoggerMixin):
    """Monitor for a single KPI with its own thread."""
    
    def __init__(
        self,
        kpi_name: str,
        data_source: Callable[[], float],
        check_interval: int = 60,
        flush_interval: int = 3600
    ):
        """
        Initialize KPI monitor.
        
        Args:
            kpi_name: Name of the KPI
            data_source: Function to fetch current KPI value
            check_interval: Check interval in seconds
            flush_interval: Data flush interval in seconds
        """
        self.kpi_name = kpi_name
        self.data_source = data_source
        self.check_interval = check_interval
        self.flush_interval = flush_interval
        
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Services
        self.model_service = ModelService()
        self.prediction_service = PredictionService()
        self.alert_service = AlertService()
        
        # Data storage
        self.dataset_path = self._get_dataset_path()
        self.buffer: List[Dict] = []
        self.last_flush = time.time()
        
        # Real-time data for UI
        self.recent_data: List[Dict] = []
        self.max_recent = 60  # Keep last 60 minutes
        
        self.logger.info(f"KPIMonitor initialized for {kpi_name}")
    
    def _get_dataset_path(self) -> Path:
        """Get dataset file path for this KPI."""
        dataset_dir = ensure_directory_exists(settings.dataset_storage_path)
        return dataset_dir / f"{self.kpi_name}.csv"
    
    def start(self):
        """Start monitoring in a separate thread."""
        if self.running:
            self.logger.warning(f"Monitor for {self.kpi_name} already running")
            return
        
        # Initialize prediction cache with historical data from CSV
        self._initialize_prediction_cache()
        
        self.running = True
        self.thread = threading.Thread(
            target=self._monitor_loop,
            name=f"Monitor-{self.kpi_name}",
            daemon=True
        )
        self.thread.start()
        self.logger.info(f"Started monitoring {self.kpi_name}")
    
    def _initialize_prediction_cache(self):
        """Initialize prediction cache with last 60 values from CSV file."""
        try:
            if self.dataset_path.exists():
                df = pd.read_csv(self.dataset_path)
                
                # Get target column name (same as kpi_name)
                target_col = self.kpi_name
                
                if target_col in df.columns:
                    # Get last 60 non-null values
                    values = df[target_col].dropna().tail(60).tolist()
                    
                    # Initialize cache in prediction service
                    for value in values:
                        self.prediction_service.update_recent_values(self.kpi_name, value)
                    
                    self.logger.info(
                        f"Initialized prediction cache for {self.kpi_name} with {len(values)} historical values"
                    )
                else:
                    self.logger.warning(
                        f"Target column '{target_col}' not found in {self.dataset_path}"
                    )
            else:
                self.logger.info(f"No existing dataset found for {self.kpi_name}, starting fresh")
        except Exception as e:
            self.logger.error(f"Failed to initialize prediction cache for {self.kpi_name}: {e}")
    
    def stop(self):
        """Stop monitoring."""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        # Flush remaining data
        self._flush_data()
        
        self.logger.info(f"Stopped monitoring {self.kpi_name}")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        self.logger.info(f"Monitoring loop started for {self.kpi_name}")
        
        while self.running:
            try:
                # Collect current value
                timestamp = datetime.now()
                actual_value = self.data_source()
                
                # Generate prediction
                predicted_value = None
                deviation = None
                is_anomaly = False
                
                try:
                    prediction = self.prediction_service.predict(
                        dataset_name=self.kpi_name,
                        timestamp=timestamp
                    )
                    predicted_value = prediction.predicted_value
                    
                    # Calculate deviation
                    if predicted_value:
                        deviation = abs(actual_value - predicted_value) / predicted_value * 100
                        
                        # Check for anomaly
                        config = self.alert_service.get_alert_config(self.kpi_name)
                        # Use appropriate threshold based on whether actual is above or below predicted
                        threshold = config.upper_threshold_percentage if actual_value > predicted_value else config.lower_threshold_percentage
                        is_anomaly = deviation > threshold
                
                except Exception as e:
                    self.logger.warning(f"Prediction failed for {self.kpi_name}: {e}")
                
                # Store data point
                data_point = {
                    'timestamp': timestamp,
                    'actual_value': actual_value,
                    'predicted_value': predicted_value,
                    'deviation': deviation,
                    'is_anomaly': is_anomaly,
                    **generate_time_features(timestamp)
                }
                
                # Add to buffer
                self.buffer.append(data_point)
                
                # Add to recent data for UI
                self.recent_data.append(data_point)
                if len(self.recent_data) > self.max_recent:
                    self.recent_data.pop(0)
                
                # Update prediction service cache
                self.prediction_service.update_recent_values(self.kpi_name, actual_value)
                
                # Compare and alert
                if predicted_value:
                    try:
                        self.alert_service.compare_and_alert(
                            dataset_name=self.kpi_name,
                            actual_value=actual_value,
                            timestamp=timestamp,
                            predicted_value=predicted_value
                        )
                    except Exception as e:
                        self.logger.error(f"Alert check failed for {self.kpi_name}: {e}")
                
                # Log prediction and alert status only
                if predicted_value is not None:
                    deviation_str = f"{deviation:.2f}%" if deviation is not None else "N/A"
                    alert_status = "⚠️ ALERT" if is_anomaly else "✓"
                    self.logger.info(
                        f"[{self.kpi_name}] Actual: {int(actual_value)} | Predicted: {int(predicted_value)} | "
                        f"Deviation: {deviation_str} | Status: {alert_status}"
                    )
                
                # Flush data periodically
                if time.time() - self.last_flush >= self.flush_interval:
                    self._flush_data()
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop for {self.kpi_name}: {e}", exc_info=True)
                time.sleep(self.check_interval)
    
    def _flush_data(self):
        """Flush buffered data to CSV file."""
        if not self.buffer:
            return
        
        try:
            # Convert buffer to DataFrame
            df_new = pd.DataFrame(self.buffer)
            
            # Append to existing file or create new
            if self.dataset_path.exists():
                df_existing = pd.read_csv(self.dataset_path)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df_combined = df_new
            
            # Save to file
            df_combined.to_csv(self.dataset_path, index=False)
            
            self.logger.info(
                f"Flushed {len(self.buffer)} data points for {self.kpi_name} "
                f"to {self.dataset_path}"
            )
            
            # Clear buffer
            self.buffer.clear()
            self.last_flush = time.time()
            
        except Exception as e:
            self.logger.error(f"Failed to flush data for {self.kpi_name}: {e}", exc_info=True)
    
    def get_recent_data(self, minutes: int = 60) -> List[Dict]:
        """
        Get recent data for UI display.
        
        Args:
            minutes: Number of minutes to retrieve
            
        Returns:
            List[Dict]: Recent data points
        """
        return self.recent_data[-minutes:] if self.recent_data else []
    
    def get_status(self) -> Dict:
        """
        Get current monitoring status.
        
        Returns:
            Dict: Status information
        """
        active_alerts = self.alert_service.get_active_alerts(self.kpi_name)
        
        latest_data = self.recent_data[-1] if self.recent_data else None
        
        return {
            'kpi_name': self.kpi_name,
            'running': self.running,
            'data_points_collected': len(self.recent_data),
            'buffer_size': len(self.buffer),
            'active_alerts': len(active_alerts),
            'latest_value': latest_data.get('actual_value') if latest_data else None,
            'latest_prediction': latest_data.get('predicted_value') if latest_data else None,
            'latest_deviation': latest_data.get('deviation') if latest_data else None,
            'dataset_path': str(self.dataset_path)
        }


class RealtimeMonitoringService(LoggerMixin):
    """Service to manage multiple KPI monitors."""
    
    def __init__(self):
        """Initialize real-time monitoring service."""
        self.monitors: Dict[str, KPIMonitor] = {}
        self.data_sources: Dict[str, Callable] = {}
        self.logger.info("RealtimeMonitoringService initialized")
    
    def register_kpi(
        self,
        kpi_name: str,
        data_source: Callable[[], float],
        check_interval: int = 60,
        flush_interval: int = 3600
    ):
        """
        Register a new KPI for monitoring.
        
        Args:
            kpi_name: Name of the KPI
            data_source: Function to fetch current value
            check_interval: Check interval in seconds
            flush_interval: Data flush interval in seconds
        """
        if kpi_name in self.monitors:
            self.logger.warning(f"KPI {kpi_name} already registered")
            return
        
        monitor = KPIMonitor(
            kpi_name=kpi_name,
            data_source=data_source,
            check_interval=check_interval,
            flush_interval=flush_interval
        )
        
        self.monitors[kpi_name] = monitor
        self.data_sources[kpi_name] = data_source
        
        self.logger.info(f"Registered KPI: {kpi_name}")
    
    def start_monitoring(self, kpi_name: Optional[str] = None):
        """
        Start monitoring for specific KPI or all KPIs.
        
        Args:
            kpi_name: Optional specific KPI name
        """
        if kpi_name:
            if kpi_name in self.monitors:
                self.monitors[kpi_name].start()
            else:
                raise ValueError(f"KPI not registered: {kpi_name}")
        else:
            # Start all monitors
            for monitor in self.monitors.values():
                monitor.start()
            self.logger.info(f"Started monitoring {len(self.monitors)} KPIs")
    
    def stop_monitoring(self, kpi_name: Optional[str] = None):
        """
        Stop monitoring for specific KPI or all KPIs.
        
        Args:
            kpi_name: Optional specific KPI name
        """
        if kpi_name:
            if kpi_name in self.monitors:
                self.monitors[kpi_name].stop()
            else:
                raise ValueError(f"KPI not registered: {kpi_name}")
        else:
            # Stop all monitors
            for monitor in self.monitors.values():
                monitor.stop()
            self.logger.info(f"Stopped monitoring {len(self.monitors)} KPIs")
    
    def get_kpi_status(self, kpi_name: str) -> Dict:
        """
        Get status for specific KPI.
        
        Args:
            kpi_name: KPI name
            
        Returns:
            Dict: Status information
        """
        if kpi_name not in self.monitors:
            raise ValueError(f"KPI not registered: {kpi_name}")
        
        return self.monitors[kpi_name].get_status()
    
    def get_all_status(self) -> Dict:
        """
        Get status for all KPIs.
        
        Returns:
            Dict: Status for all KPIs
        """
        return {
            'total_kpis': len(self.monitors),
            'running_kpis': sum(1 for m in self.monitors.values() if m.running),
            'kpis': {name: monitor.get_status() for name, monitor in self.monitors.items()}
        }
    
    def get_recent_data(self, kpi_name: str, minutes: int = 60) -> List[Dict]:
        """
        Get recent data for a KPI.
        
        Args:
            kpi_name: KPI name
            minutes: Number of minutes
            
        Returns:
            List[Dict]: Recent data points
        """
        if kpi_name not in self.monitors:
            raise ValueError(f"KPI not registered: {kpi_name}")
        
        return self.monitors[kpi_name].get_recent_data(minutes)
    
    def list_kpis(self) -> List[str]:
        """
        List all registered KPIs.
        
        Returns:
            List[str]: KPI names
        """
        return list(self.monitors.keys())
