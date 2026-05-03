"""
Real-time monitoring simulator for KPI Prediction System.

This script simulates continuous monitoring by:
1. Generating synthetic real-time data
2. Making predictions
3. Comparing actual vs predicted
4. Triggering alerts when thresholds are exceeded
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import requests

from util.config import settings
from util.logger import get_logger

logger = get_logger(__name__)


class MonitoringSimulator:
    """Simulator for real-time KPI monitoring."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        dataset_name: str = "traffic_data",
        check_interval: int = 60
    ):
        """
        Initialize monitoring simulator.
        
        Args:
            base_url: Base URL of the API
            dataset_name: Dataset to monitor
            check_interval: Check interval in seconds
        """
        self.base_url = base_url
        self.dataset_name = dataset_name
        self.check_interval = check_interval
        self.running = False
        self.iteration = 0
        
        logger.info(
            f"MonitoringSimulator initialized: "
            f"dataset={dataset_name}, interval={check_interval}s"
        )
    
    def generate_synthetic_value(self, timestamp: datetime) -> float:
        """
        Generate synthetic KPI value with patterns and anomalies.
        
        Args:
            timestamp: Current timestamp
            
        Returns:
            float: Synthetic value
        """
        # Base value
        base = 1500
        
        # Daily pattern (higher during business hours)
        hour_factor = 1.0 + 0.5 * np.sin(2 * np.pi * timestamp.hour / 24)
        
        # Weekly pattern (lower on weekends)
        weekday_factor = 1.2 if timestamp.weekday() < 5 else 0.8
        
        # Random noise
        noise = np.random.normal(0, 0.1)
        
        # Occasional anomalies (10% chance)
        anomaly = 0
        if random.random() < 0.1:
            anomaly = random.choice([-0.3, 0.3])  # ±30% spike
            logger.info(f"Injecting anomaly: {anomaly*100:.1f}%")
        
        value = base * hour_factor * weekday_factor * (1 + noise + anomaly)
        return max(0, value)
    
    def check_health(self) -> bool:
        """
        Check if API is healthy.
        
        Returns:
            bool: True if healthy
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def make_prediction(self, timestamp: datetime) -> Optional[float]:
        """
        Get prediction from API.
        
        Args:
            timestamp: Timestamp for prediction
            
        Returns:
            Optional[float]: Predicted value
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/predict",
                json={
                    "dataset_name": self.dataset_name,
                    "timestamp": timestamp.isoformat(),
                    "use_current_time": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("predicted_value")
            else:
                logger.warning(f"Prediction failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Prediction request failed: {e}")
            return None
    
    def compare_values(
        self,
        actual_value: float,
        timestamp: datetime
    ) -> Optional[dict]:
        """
        Compare actual vs predicted and check for alerts.
        
        Args:
            actual_value: Actual observed value
            timestamp: Timestamp
            
        Returns:
            Optional[dict]: Comparison result
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/compare",
                json={
                    "dataset_name": self.dataset_name,
                    "actual_value": actual_value,
                    "timestamp": timestamp.isoformat(),
                    "auto_predict": True
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Comparison failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Comparison request failed: {e}")
            return None
    
    def get_active_alerts(self) -> list:
        """
        Get active alerts.
        
        Returns:
            list: Active alerts
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/alerts",
                params={
                    "dataset_name": self.dataset_name,
                    "active_only": True
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("alerts", [])
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def print_status(
        self,
        timestamp: datetime,
        actual: float,
        predicted: Optional[float],
        comparison: Optional[dict]
    ):
        """
        Print monitoring status.
        
        Args:
            timestamp: Current timestamp
            actual: Actual value
            predicted: Predicted value
            comparison: Comparison result
        """
        print("\n" + "="*80)
        print(f"Iteration: {self.iteration} | Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*80)
        print(f"Actual Value:    {actual:.2f}")
        
        if predicted:
            print(f"Predicted Value: {predicted:.2f}")
        
        if comparison:
            deviation = comparison.get("deviation_percentage", 0)
            is_anomaly = comparison.get("is_anomaly", False)
            alert_triggered = comparison.get("alert_triggered", False)
            
            print(f"Deviation:       {deviation:.2f}%")
            print(f"Anomaly:         {'YES' if is_anomaly else 'NO'}")
            print(f"Alert Triggered: {'YES' if alert_triggered else 'NO'}")
            
            if alert_triggered:
                alert_id = comparison.get("alert_id")
                print(f"Alert ID:        {alert_id}")
        
        # Show active alerts
        active_alerts = self.get_active_alerts()
        if active_alerts:
            print("-"*80)
            print(f"Active Alerts: {len(active_alerts)}")
            for alert in active_alerts[:3]:  # Show first 3
                print(f"  - {alert.get('message', 'N/A')}")
        
        print("="*80)
    
    async def run_monitoring_loop(self, duration_minutes: Optional[int] = None):
        """
        Run continuous monitoring loop.
        
        Args:
            duration_minutes: Optional duration limit in minutes
        """
        logger.info("Starting monitoring loop")
        
        # Check health first
        if not self.check_health():
            logger.error("API is not healthy. Exiting.")
            return
        
        self.running = True
        start_time = time.time()
        
        try:
            while self.running:
                self.iteration += 1
                current_time = datetime.now()
                
                # Generate synthetic actual value
                actual_value = self.generate_synthetic_value(current_time)
                
                # Get prediction
                predicted_value = self.make_prediction(current_time)
                
                # Compare and check alerts
                comparison = self.compare_values(actual_value, current_time)
                
                # Print status
                self.print_status(
                    current_time,
                    actual_value,
                    predicted_value,
                    comparison
                )
                
                # Check duration limit
                if duration_minutes:
                    elapsed_minutes = (time.time() - start_time) / 60
                    if elapsed_minutes >= duration_minutes:
                        logger.info(f"Duration limit reached: {duration_minutes} minutes")
                        break
                
                # Wait for next iteration
                await asyncio.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info(f"Monitoring completed. Total iterations: {self.iteration}")
    
    def stop(self):
        """Stop monitoring loop."""
        self.running = False
        logger.info("Stopping monitoring loop")


async def main():
    """Main entry point for monitoring simulator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="KPI Monitoring Simulator")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API"
    )
    parser.add_argument(
        "--dataset",
        default="traffic_data",
        help="Dataset name to monitor"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Duration in minutes (optional)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("KPI PREDICTION SYSTEM - MONITORING SIMULATOR")
    print("="*80)
    print(f"Base URL:  {args.base_url}")
    print(f"Dataset:   {args.dataset}")
    print(f"Interval:  {args.interval}s")
    print(f"Duration:  {args.duration or 'Unlimited'} minutes")
    print("="*80)
    print("\nPress Ctrl+C to stop monitoring\n")
    
    simulator = MonitoringSimulator(
        base_url=args.base_url,
        dataset_name=args.dataset,
        check_interval=args.interval
    )
    
    await simulator.run_monitoring_loop(duration_minutes=args.duration)


if __name__ == "__main__":
    asyncio.run(main())
