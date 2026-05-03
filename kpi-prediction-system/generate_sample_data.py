#!/usr/bin/env python3
"""
Generate realistic sample datasets for KPI prediction system.
Creates 1 year of hourly data with trends and patterns.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Ensure data directory exists
data_dir = Path("data/datasets")
data_dir.mkdir(parents=True, exist_ok=True)

# Generate timestamps for 1 year (hourly data)
start_date = datetime(2025, 1, 1, 0, 0, 0)
end_date = datetime(2025, 12, 31, 23, 0, 0)
timestamps = pd.date_range(start=start_date, end=end_date, freq='H')

print(f"Generating {len(timestamps)} data points (1 year of hourly data)...")
print(f"Date range: {start_date} to {end_date}")
print("="*80)

def generate_kpi_data(
    timestamps,
    base_value,
    growth_rate,
    daily_pattern_amplitude,
    weekly_pattern_amplitude,
    noise_level,
    seasonal_amplitude=0
):
    """
    Generate realistic KPI data with multiple patterns.
    
    Args:
        timestamps: DatetimeIndex
        base_value: Starting base value
        growth_rate: Annual growth rate (e.g., 0.2 for 20% growth)
        daily_pattern_amplitude: Strength of daily pattern (0-1)
        weekly_pattern_amplitude: Strength of weekly pattern (0-1)
        noise_level: Random noise level (0-1)
        seasonal_amplitude: Yearly seasonal variation (0-1)
    
    Returns:
        np.ndarray: Generated values
    """
    n = len(timestamps)
    values = np.zeros(n)
    
    for i, ts in enumerate(timestamps):
        # Progress through year (0 to 1)
        year_progress = i / n
        
        # 1. Base value with growth trend
        base = base_value * (1 + growth_rate * year_progress)
        
        # 2. Daily pattern (peak during business hours)
        hour = ts.hour
        daily_factor = 1.0 + daily_pattern_amplitude * np.sin(2 * np.pi * (hour - 6) / 24)
        daily_factor = max(0.3, daily_factor)  # Minimum 30% of base
        
        # 3. Weekly pattern (lower on weekends)
        day_of_week = ts.dayofweek
        if day_of_week >= 5:  # Weekend
            weekly_factor = 1.0 - weekly_pattern_amplitude * 0.3
        else:  # Weekday
            weekly_factor = 1.0 + weekly_pattern_amplitude * 0.1
        
        # 4. Seasonal pattern (yearly cycle)
        month = ts.month
        seasonal_factor = 1.0 + seasonal_amplitude * np.sin(2 * np.pi * (month - 1) / 12)
        
        # 5. Random noise
        noise = np.random.normal(0, noise_level)
        
        # Combine all factors
        value = base * daily_factor * weekly_factor * seasonal_factor * (1 + noise)
        
        # Ensure non-negative
        values[i] = max(0, value)
    
    return values


# 1. TRAFFIC COUNT - Website/App traffic
print("\n1. Generating traffic_count.csv...")
traffic_values = generate_kpi_data(
    timestamps=timestamps,
    base_value=1500,           # Base traffic
    growth_rate=0.25,          # 25% annual growth
    daily_pattern_amplitude=0.6,  # Strong daily pattern
    weekly_pattern_amplitude=0.2,  # Moderate weekly pattern
    noise_level=0.08,          # 8% noise
    seasonal_amplitude=0.15    # 15% seasonal variation
)

traffic_df = pd.DataFrame({
    'timestamp': timestamps,
    'traffic_count': traffic_values.round(2)
})
traffic_df.to_csv(data_dir / 'traffic_count.csv', index=False)
print(f"   ✅ Created: {len(traffic_df)} records")
print(f"   📊 Range: {traffic_df['traffic_count'].min():.2f} - {traffic_df['traffic_count'].max():.2f}")
print(f"   📈 Mean: {traffic_df['traffic_count'].mean():.2f}")


# 2. ORDERS - E-commerce orders
print("\n2. Generating orders.csv...")
orders_values = generate_kpi_data(
    timestamps=timestamps,
    base_value=250,            # Base orders
    growth_rate=0.30,          # 30% annual growth
    daily_pattern_amplitude=0.7,  # Very strong daily pattern
    weekly_pattern_amplitude=0.25, # Strong weekend effect
    noise_level=0.12,          # 12% noise
    seasonal_amplitude=0.20    # 20% seasonal (holiday peaks)
)

orders_df = pd.DataFrame({
    'timestamp': timestamps,
    'orders': orders_values.round(2)
})
orders_df.to_csv(data_dir / 'orders.csv', index=False)
print(f"   ✅ Created: {len(orders_df)} records")
print(f"   📊 Range: {orders_df['orders'].min():.2f} - {orders_df['orders'].max():.2f}")
print(f"   📈 Mean: {orders_df['orders'].mean():.2f}")


# 3. SHIPPED - Orders shipped
print("\n3. Generating shipped.csv...")
# Shipped should be slightly less than orders with a delay pattern
shipped_values = generate_kpi_data(
    timestamps=timestamps,
    base_value=240,            # Slightly less than orders
    growth_rate=0.28,          # Similar growth to orders
    daily_pattern_amplitude=0.5,  # Moderate daily pattern
    weekly_pattern_amplitude=0.15, # Less weekend effect
    noise_level=0.10,          # 10% noise
    seasonal_amplitude=0.18
)

shipped_df = pd.DataFrame({
    'timestamp': timestamps,
    'shipped': shipped_values.round(2)
})
shipped_df.to_csv(data_dir / 'shipped.csv', index=False)
print(f"   ✅ Created: {len(shipped_df)} records")
print(f"   📊 Range: {shipped_df['shipped'].min():.2f} - {shipped_df['shipped'].max():.2f}")
print(f"   📈 Mean: {shipped_df['shipped'].mean():.2f}")


# 4. DELIVERED - Orders delivered
print("\n4. Generating delivered.csv...")
# Delivered should be slightly less than shipped with more delay
delivered_values = generate_kpi_data(
    timestamps=timestamps,
    base_value=230,            # Slightly less than shipped
    growth_rate=0.27,          # Similar growth
    daily_pattern_amplitude=0.4,  # Lower daily pattern
    weekly_pattern_amplitude=0.10, # Minimal weekend effect
    noise_level=0.09,          # 9% noise
    seasonal_amplitude=0.17
)

delivered_df = pd.DataFrame({
    'timestamp': timestamps,
    'delivered': delivered_values.round(2)
})
delivered_df.to_csv(data_dir / 'delivered.csv', index=False)
print(f"   ✅ Created: {len(delivered_df)} records")
print(f"   📊 Range: {delivered_df['delivered'].min():.2f} - {delivered_df['delivered'].max():.2f}")
print(f"   📈 Mean: {delivered_df['delivered'].mean():.2f}")


# 5. NEW CUSTOMERS - New customer registrations
print("\n5. Generating newcustomer.csv...")
newcustomer_values = generate_kpi_data(
    timestamps=timestamps,
    base_value=80,             # Base new customers
    growth_rate=0.35,          # 35% annual growth (aggressive)
    daily_pattern_amplitude=0.65, # Strong daily pattern
    weekly_pattern_amplitude=0.20, # Moderate weekly pattern
    noise_level=0.15,          # 15% noise (more variable)
    seasonal_amplitude=0.25    # 25% seasonal (marketing campaigns)
)

newcustomer_df = pd.DataFrame({
    'timestamp': timestamps,
    'newcustomer': newcustomer_values.round(2)
})
newcustomer_df.to_csv(data_dir / 'newcustomer.csv', index=False)
print(f"   ✅ Created: {len(newcustomer_df)} records")
print(f"   📊 Range: {newcustomer_df['newcustomer'].min():.2f} - {newcustomer_df['newcustomer'].max():.2f}")
print(f"   📈 Mean: {newcustomer_df['newcustomer'].mean():.2f}")


# Generate summary statistics
print("\n" + "="*80)
print("📊 SUMMARY STATISTICS")
print("="*80)

summary_data = {
    'KPI': ['traffic_count', 'orders', 'shipped', 'delivered', 'newcustomer'],
    'Records': [len(df) for df in [traffic_df, orders_df, shipped_df, delivered_df, newcustomer_df]],
    'Min': [
        traffic_df['traffic_count'].min(),
        orders_df['orders'].min(),
        shipped_df['shipped'].min(),
        delivered_df['delivered'].min(),
        newcustomer_df['newcustomer'].min()
    ],
    'Max': [
        traffic_df['traffic_count'].max(),
        orders_df['orders'].max(),
        shipped_df['shipped'].max(),
        delivered_df['delivered'].max(),
        newcustomer_df['newcustomer'].max()
    ],
    'Mean': [
        traffic_df['traffic_count'].mean(),
        orders_df['orders'].mean(),
        shipped_df['shipped'].mean(),
        delivered_df['delivered'].mean(),
        newcustomer_df['newcustomer'].mean()
    ],
    'Std': [
        traffic_df['traffic_count'].std(),
        orders_df['orders'].std(),
        shipped_df['shipped'].std(),
        delivered_df['delivered'].std(),
        newcustomer_df['newcustomer'].std()
    ]
}

summary_df = pd.DataFrame(summary_data)
print(summary_df.to_string(index=False))

# Calculate growth rates
print("\n📈 GROWTH ANALYSIS (First Month vs Last Month)")
print("="*80)

for kpi_name, df, col in [
    ('traffic_count', traffic_df, 'traffic_count'),
    ('orders', orders_df, 'orders'),
    ('shipped', shipped_df, 'shipped'),
    ('delivered', delivered_df, 'delivered'),
    ('newcustomer', newcustomer_df, 'newcustomer')
]:
    first_month = df[df['timestamp'].dt.month == 1][col].mean()
    last_month = df[df['timestamp'].dt.month == 12][col].mean()
    growth = ((last_month - first_month) / first_month) * 100
    print(f"{kpi_name:15s}: {first_month:8.2f} → {last_month:8.2f} ({growth:+6.2f}%)")

print("\n" + "="*80)
print("✅ ALL DATASETS GENERATED SUCCESSFULLY!")
print("="*80)
print(f"\nFiles created in: {data_dir.absolute()}")
print("\nNext steps:")
print("1. Train models: Use the API to train models for each KPI")
print("2. Start monitoring: Begin real-time monitoring with these baselines")
print("3. Test predictions: Verify model accuracy with the generated data")
print("\nExample training command:")
print('curl -X POST "http://localhost:8000/api/v1/train" \\')
print('  -H "Content-Type: application/json" \\')
print('  -d \'{"dataset_name": "traffic_count", "file_path": "data/datasets/traffic_count.csv", "target_column": "traffic_count", "epochs": 50}\'')
