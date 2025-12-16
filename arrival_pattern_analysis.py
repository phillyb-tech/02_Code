import math
import random
import statistics
import simpy

# Import the functions from the main simulation
import sys
sys.path.append('.')
from ct_scan_shands_des import (
    generate_patient_arrivals, NUM_SCANNERS, NUM_ROBOTS, 
    DAY_LENGTH_MIN, simulate_one_day
)

def analyze_arrival_patterns():
    """
    Analyze patient arrival patterns to understand when additional scans occur.
    """
    print("ARRIVAL PATTERN ANALYSIS: WHERE DO ADDITIONAL PATIENTS ARRIVE?")
    print("=" * 80)
    
    # Set random seed for consistent results
    random.seed(42)
    
    # Analyze arrival patterns across multiple days
    baseline_hourly_totals = {hour: 0 for hour in range(24)}
    rovis_hourly_totals = {hour: 0 for hour in range(24)}
    
    num_days = 10  # Analyze 10 days for better patterns
    
    baseline_daily_totals = []
    rovis_daily_totals = []
    
    for day in range(num_days):
        # Generate arrivals for each scenario
        baseline_arrivals = generate_patient_arrivals('baseline')
        rovis_arrivals = generate_patient_arrivals('rovis_only')
        
        baseline_daily_totals.append(len(baseline_arrivals))
        rovis_daily_totals.append(len(rovis_arrivals))
        
        # Count by hour
        for arrival in baseline_arrivals:
            hour = int(arrival // 60)
            if hour < 24:
                baseline_hourly_totals[hour] += 1
        
        for arrival in rovis_arrivals:
            hour = int(arrival // 60)
            if hour < 24:
                rovis_hourly_totals[hour] += 1
    
    # Calculate averages
    baseline_avg_daily = statistics.mean(baseline_daily_totals)
    rovis_avg_daily = statistics.mean(rovis_daily_totals)
    additional_daily = rovis_avg_daily - baseline_avg_daily
    
    print(f"SUMMARY ({num_days} days average):")
    print(f"Baseline daily arrivals: {baseline_avg_daily:.1f}")
    print(f"Rovis daily arrivals: {rovis_avg_daily:.1f}")
    print(f"Additional daily arrivals: {additional_daily:.1f}")
    print(f"Additional arrivals per scanner: {additional_daily/6:.1f}")
    
    print(f"\nHOURLY ARRIVAL BREAKDOWN (average per day):")
    print(f"{'Hour':<6} {'Period':<12} {'Baseline':<10} {'Rovis':<8} {'Additional':<12} {'% Increase':<12}")
    print("-" * 75)
    
    total_additional = 0
    period_data = {
        'Daytime (7am-7pm)': {'baseline': 0, 'rovis': 0, 'hours': list(range(7, 19))},
        'Evening (7pm-11pm)': {'baseline': 0, 'rovis': 0, 'hours': list(range(19, 23))},
        'Overnight (11pm-7am)': {'baseline': 0, 'rovis': 0, 'hours': list(range(0, 7)) + [23]}
    }
    
    for hour in range(24):
        if 7 <= hour < 19:
            period = "Daytime"
        elif 19 <= hour < 23:
            period = "Evening"
        else:
            period = "Overnight"
            
        baseline_avg = baseline_hourly_totals[hour] / num_days
        rovis_avg = rovis_hourly_totals[hour] / num_days
        additional = rovis_avg - baseline_avg
        total_additional += additional
        
        pct_increase = ((rovis_avg / baseline_avg - 1) * 100) if baseline_avg > 0 else 0
        
        # Add to period data
        for period_name, data in period_data.items():
            if hour in data['hours']:
                data['baseline'] += baseline_avg
                data['rovis'] += rovis_avg
        
        print(f"{hour:02d}:00 {period:<12} {baseline_avg:<10.1f} {rovis_avg:<8.1f} "
              f"{additional:+7.1f} {pct_increase:9.1f}%")
    
    print("-" * 75)
    print(f"{'TOTAL':<19} {baseline_avg_daily:<10.1f} {rovis_avg_daily:<8.1f} {total_additional:+7.1f}")
    
    print(f"\nPERIOD SUMMARIES:")
    print(f"{'Period':<20} {'Baseline':<10} {'Rovis':<8} {'Additional':<12} {'% of Add\'l':<12}")
    print("-" * 75)
    
    for period_name, data in period_data.items():
        additional_period = data['rovis'] - data['baseline']
        pct_of_additional = (additional_period / total_additional * 100) if total_additional > 0 else 0
        
        print(f"{period_name:<20} {data['baseline']:<10.1f} {data['rovis']:<8.1f} "
              f"{additional_period:+7.1f} {pct_of_additional:9.1f}%")

def analyze_capacity_impact():
    """
    Show the capacity calculation that drives additional scans.
    """
    print(f"\n\nCAPACITY MULTIPLIER CALCULATION:")
    print("=" * 50)
    
    # Calculate efficiency multipliers
    baseline_cycle = 119.5  # From step means calculation
    rovis_cycle = 103.2
    efficiency_multiplier = baseline_cycle / rovis_cycle
    
    print(f"Baseline cycle time: {baseline_cycle} minutes")
    print(f"Rovis cycle time: {rovis_cycle} minutes") 
    print(f"Efficiency multiplier: {efficiency_multiplier:.3f}x")
    print(f"This means {efficiency_multiplier:.1f}% capacity increase")
    
    # Base arrival rates
    print(f"\nBase hourly arrival rates (baseline scenario):")
    print(f"Daytime (7am-7pm): 9.0 patients/hour")
    print(f"Evening (7pm-11pm): 4.5 patients/hour")  
    print(f"Overnight (11pm-7am): 2.5 patients/hour")
    
    print(f"\nWith robots (scaled by {efficiency_multiplier:.3f}x):")
    print(f"Daytime: {9.0 * efficiency_multiplier:.1f} patients/hour")
    print(f"Evening: {4.5 * efficiency_multiplier:.1f} patients/hour")
    print(f"Overnight: {2.5 * efficiency_multiplier:.1f} patients/hour")
    
    # Calculate daily totals
    baseline_daily = (9.0 * 12) + (4.5 * 4) + (2.5 * 8)  # 12+4+8 = 24 hours
    rovis_daily = baseline_daily * efficiency_multiplier
    
    print(f"\nDaily arrival totals:")
    print(f"Baseline: {baseline_daily} patients/day")
    print(f"Rovis: {rovis_daily:.1f} patients/day")
    print(f"Additional: {rovis_daily - baseline_daily:.1f} patients/day")
    print(f"Additional per scanner: {(rovis_daily - baseline_daily)/6:.1f} patients/day")


if __name__ == "__main__":
    analyze_arrival_patterns()
    analyze_capacity_impact()