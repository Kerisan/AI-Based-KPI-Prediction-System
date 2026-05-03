"""
Interactive startup wizard for KPI configuration.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from services.data_service import DataService
from services.model_service import ModelService
from services.realtime_monitor import RealtimeMonitoringService
from util.config import settings
from util.logger import LoggerMixin


class StartupWizard(LoggerMixin):
    """Interactive wizard for configuring KPIs on startup."""
    
    def __init__(self):
        """Initialize startup wizard."""
        self.model_service = ModelService()
        self.data_service = DataService()
        self.monitoring_service = RealtimeMonitoringService()
        self.kpi_configs: List[Dict] = []
        self.logger.info("StartupWizard initialized")
    
    def run(self) -> RealtimeMonitoringService:
        """
        Run the interactive startup wizard.
        
        Returns:
            RealtimeMonitoringService: Configured monitoring service
        """
        print("\n" + "="*80)
        print("🚀 KPI PREDICTION SYSTEM - STARTUP WIZARD")
        print("="*80)
        
        # Check for existing models
        existing_models = self.model_service.list_models()
        
        if existing_models:
            print(f"\n✅ Found {len(existing_models)} existing trained models:")
            for model in existing_models:
                print(f"   - {model.dataset_name} (Status: {model.status.value})")
            
            use_existing = self._ask_yes_no(
                "\nDo you want to use existing models?",
                default=True
            )
            
            if use_existing:
                return self._setup_from_existing_models(existing_models)
        
        # No existing models or user wants to configure new ones
        print("\n📊 Let's configure your KPIs for monitoring...")
        return self._setup_new_kpis()
    
    def _setup_from_existing_models(self, models: List) -> RealtimeMonitoringService:
        """
        Setup monitoring from existing models.
        
        Args:
            models: List of existing models
            
        Returns:
            RealtimeMonitoringService: Configured service
        """
        print("\n🔧 Setting up monitoring from existing models...")
        
        for model in models:
            kpi_name = model.dataset_name
            
            # Ask for data source
            print(f"\n📈 KPI: {kpi_name}")
            data_source = self._configure_data_source(kpi_name)
            
            # Register KPI
            self.monitoring_service.register_kpi(
                kpi_name=kpi_name,
                data_source=data_source,
                check_interval=settings.alert_check_interval,
                flush_interval=3600
            )
            
            print(f"   ✅ Registered {kpi_name} for monitoring")
        
        return self.monitoring_service
    
    def _setup_new_kpis(self) -> RealtimeMonitoringService:
        """
        Setup new KPIs from scratch.
        
        Returns:
            RealtimeMonitoringService: Configured service
        """
        while True:
            print("\n" + "-"*80)
            kpi_name = input("Enter KPI name (or 'done' to finish): ").strip()
            
            if kpi_name.lower() == 'done':
                break
            
            if not kpi_name:
                print("❌ KPI name cannot be empty")
                continue
            
            # Configure KPI
            kpi_config = self._configure_kpi(kpi_name)
            self.kpi_configs.append(kpi_config)
            
            # Check if model exists
            model_path = self.model_service.get_model_path(kpi_name)
            
            if not model_path.exists():
                print(f"\n🔄 No trained model found for {kpi_name}")
                
                # Check for existing dataset
                dataset_path = Path(settings.dataset_storage_path) / f"{kpi_name}.csv"
                
                if dataset_path.exists():
                    train_now = self._ask_yes_no(
                        f"Found existing dataset. Train model now?",
                        default=True
                    )
                    
                    if train_now:
                        self._train_model(kpi_name, str(dataset_path), kpi_config['target_column'])
                else:
                    print(f"   ℹ️  Model will be trained automatically after collecting {settings.auto_train_threshold} data points")
            
            # Register for monitoring
            data_source = kpi_config['data_source']
            self.monitoring_service.register_kpi(
                kpi_name=kpi_name,
                data_source=data_source,
                check_interval=kpi_config['check_interval'],
                flush_interval=kpi_config['flush_interval']
            )
            
            print(f"   ✅ {kpi_name} configured and ready for monitoring")
        
        if not self.kpi_configs:
            print("\n⚠️  No KPIs configured. Using default configuration...")
            self._setup_default_kpis()
        
        return self.monitoring_service
    
    def _configure_kpi(self, kpi_name: str) -> Dict:
        """
        Configure a single KPI.
        
        Args:
            kpi_name: Name of the KPI
            
        Returns:
            Dict: KPI configuration
        """
        print(f"\n⚙️  Configuring {kpi_name}...")
        
        # Target column
        target_column = input(f"   Target column name (default: {kpi_name}_value): ").strip()
        if not target_column:
            target_column = f"{kpi_name}_value"
        
        # Check interval
        check_interval_str = input("   Check interval in seconds (default: 60): ").strip()
        check_interval = int(check_interval_str) if check_interval_str else 60
        
        # Flush interval
        flush_interval_str = input("   Data flush interval in seconds (default: 3600): ").strip()
        flush_interval = int(flush_interval_str) if flush_interval_str else 3600
        
        # Data source type
        print("\n   Data source options:")
        print("   1. Simulated (for testing)")
        print("   2. HTTP endpoint")
        print("   3. Database query")
        print("   4. Custom function")
        
        source_type = input("   Select data source type (1-4, default: 1): ").strip()
        
        data_source = self._create_data_source(kpi_name, source_type or "1")
        
        return {
            'kpi_name': kpi_name,
            'target_column': target_column,
            'check_interval': check_interval,
            'flush_interval': flush_interval,
            'data_source': data_source
        }
    
    def _configure_data_source(self, kpi_name: str) -> callable:
        """
        Configure data source for existing KPI.
        
        Args:
            kpi_name: KPI name
            
        Returns:
            callable: Data source function
        """
        print("   Data source options:")
        print("   1. Simulated (for testing)")
        print("   2. HTTP endpoint")
        print("   3. Database query")
        
        source_type = input("   Select data source type (1-3, default: 1): ").strip()
        
        return self._create_data_source(kpi_name, source_type or "1")
    
    def _create_data_source(self, kpi_name: str, source_type: str) -> callable:
        """
        Create data source function based on type.
        
        Args:
            kpi_name: KPI name
            source_type: Type of data source
            
        Returns:
            callable: Data source function
        """
        if source_type == "1":
            # Simulated data
            import random
            import math
            from datetime import datetime
            
            def simulated_source():
                now = datetime.now()
                base = 1500
                hour_factor = 1.0 + 0.5 * math.sin(2 * math.pi * now.hour / 24)
                noise = random.gauss(0, 0.1)
                return max(0, base * hour_factor * (1 + noise))
            
            return simulated_source
        
        elif source_type == "2":
            # HTTP endpoint
            endpoint = input("   Enter HTTP endpoint URL: ").strip()
            
            def http_source():
                import requests
                try:
                    response = requests.get(endpoint, timeout=5)
                    return float(response.json().get('value', 0))
                except Exception as e:
                    print(f"Error fetching from {endpoint}: {e}")
                    return 0.0
            
            return http_source
        
        elif source_type == "3":
            # Database query
            query = input("   Enter SQL query: ").strip()
            
            def db_source():
                # Placeholder - implement based on your database
                print(f"Executing query: {query}")
                return 0.0
            
            return db_source
        
        else:
            # Default to simulated
            return self._create_data_source(kpi_name, "1")
    
    def _train_model(self, kpi_name: str, dataset_path: str, target_column: str):
        """
        Train model for a KPI.
        
        Args:
            kpi_name: KPI name
            dataset_path: Path to dataset
            target_column: Target column name
        """
        print(f"\n🔄 Training model for {kpi_name}...")
        
        try:
            response = self.model_service.train_model(
                dataset_name=kpi_name,
                file_path=dataset_path,
                target_column=target_column,
                epochs=20,
                batch_size=32,
                sequence_length=60
            )
            
            if response.status.value == "TRAINED":
                print(f"   ✅ Model trained successfully!")
                if response.metrics:
                    print(f"   📊 Metrics: MAE={response.metrics.get('mae', 'N/A')}, "
                          f"RMSE={response.metrics.get('rmse', 'N/A')}")
            else:
                print(f"   ❌ Training failed: {response.message}")
        
        except Exception as e:
            print(f"   ❌ Training error: {e}")
    
    def _setup_default_kpis(self):
        """Setup default KPIs for demo."""
        default_kpis = [
            {
                'kpi_name': 'traffic_count',
                'target_column': 'traffic_count',
                'check_interval': 60,
                'flush_interval': 3600
            },
            {
                'kpi_name': 'orders',
                'target_column': 'orders',
                'check_interval': 60,
                'flush_interval': 3600
            }
        ]
        
        for kpi_config in default_kpis:
            data_source = self._create_data_source(kpi_config['kpi_name'], "1")
            kpi_config['data_source'] = data_source
            
            self.monitoring_service.register_kpi(
                kpi_name=kpi_config['kpi_name'],
                data_source=data_source,
                check_interval=kpi_config['check_interval'],
                flush_interval=kpi_config['flush_interval']
            )
            
            print(f"   ✅ Default KPI configured: {kpi_config['kpi_name']}")
    
    def _ask_yes_no(self, question: str, default: bool = True) -> bool:
        """
        Ask yes/no question.
        
        Args:
            question: Question to ask
            default: Default answer
            
        Returns:
            bool: User's answer
        """
        default_str = "Y/n" if default else "y/N"
        answer = input(f"{question} [{default_str}]: ").strip().lower()
        
        if not answer:
            return default
        
        return answer in ['y', 'yes']
