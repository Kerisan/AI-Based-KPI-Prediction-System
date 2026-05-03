#!/usr/bin/env python3
"""
Train models for all KPIs using the generated sample data.
"""

import sys
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services.model_service import ModelService
from services.data_service import DataService
from util.logger import get_logger

logger = get_logger(__name__)

# KPI configurations
KPIS = [
    {
        'dataset_name': 'traffic_count',
        'file_path': 'data/datasets/traffic_count.csv',
        'target_column': 'traffic_count'
    },
    {
        'dataset_name': 'orders',
        'file_path': 'data/datasets/orders.csv',
        'target_column': 'orders'
    },
    {
        'dataset_name': 'shipped',
        'file_path': 'data/datasets/shipped.csv',
        'target_column': 'shipped'
    },
    {
        'dataset_name': 'delivered',
        'file_path': 'data/datasets/delivered.csv',
        'target_column': 'delivered'
    },
    {
        'dataset_name': 'newcustomer',
        'file_path': 'data/datasets/newcustomer.csv',
        'target_column': 'newcustomer'
    }
]

def main():
    """Train all models."""
    print("\n" + "="*80)
    print("🤖 TRAINING ALL KPI MODELS")
    print("="*80)
    
    model_service = ModelService()
    results = []
    
    for i, kpi in enumerate(KPIS, 1):
        print(f"\n[{i}/{len(KPIS)}] Training {kpi['dataset_name']}...")
        print("-" * 80)
        
        start_time = time.time()
        
        try:
            response = model_service.train_model(
                dataset_name=kpi['dataset_name'],
                file_path=kpi['file_path'],
                target_column=kpi['target_column'],
                epochs=10,
                batch_size=32,
                validation_split=0.2,
                sequence_length=60
            )
            
            elapsed = time.time() - start_time
            
            if response.status.value == "TRAINED":
                print(f"✅ SUCCESS - Trained in {elapsed:.1f}s")
                if response.metrics:
                    print(f"   📊 Metrics:")
                    print(f"      MAE:  {response.metrics.get('mae', 'N/A'):.4f}")
                    print(f"      RMSE: {response.metrics.get('rmse', 'N/A'):.4f}")
                    print(f"      R²:   {response.metrics.get('r2', 'N/A'):.4f}")
                    print(f"      MAPE: {response.metrics.get('mape', 'N/A'):.2f}%")
                
                results.append({
                    'kpi': kpi['dataset_name'],
                    'status': 'SUCCESS',
                    'time': elapsed,
                    'metrics': response.metrics
                })
            else:
                print(f"❌ FAILED: {response.message}")
                results.append({
                    'kpi': kpi['dataset_name'],
                    'status': 'FAILED',
                    'time': elapsed,
                    'error': response.message
                })
        
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ ERROR: {str(e)}")
            results.append({
                'kpi': kpi['dataset_name'],
                'status': 'ERROR',
                'time': elapsed,
                'error': str(e)
            })
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TRAINING SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    failed = len(results) - successful
    total_time = sum(r['time'] for r in results)
    
    print(f"\nTotal KPIs: {len(results)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total time: {total_time:.1f}s")
    
    if successful > 0:
        print("\n📈 Model Performance:")
        print("-" * 80)
        print(f"{'KPI':<20} {'MAE':<10} {'RMSE':<10} {'R²':<10} {'MAPE':<10}")
        print("-" * 80)
        
        for result in results:
            if result['status'] == 'SUCCESS' and result.get('metrics'):
                m = result['metrics']
                print(f"{result['kpi']:<20} "
                      f"{m.get('mae', 0):<10.4f} "
                      f"{m.get('rmse', 0):<10.4f} "
                      f"{m.get('r2', 0):<10.4f} "
                      f"{m.get('mape', 0):<10.2f}")
    
    if failed > 0:
        print("\n❌ Failed Models:")
        for result in results:
            if result['status'] != 'SUCCESS':
                print(f"   - {result['kpi']}: {result.get('error', 'Unknown error')}")
    
    print("\n" + "="*80)
    
    if successful == len(results):
        print("✅ ALL MODELS TRAINED SUCCESSFULLY!")
        print("\nNext steps:")
        print("1. Start the server: python main_simple.py")
        print("2. Test predictions via API")
        print("3. Start real-time monitoring")
    else:
        print(f"⚠️  {failed} model(s) failed to train. Check errors above.")
    
    print("="*80 + "\n")
    
    return successful == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
