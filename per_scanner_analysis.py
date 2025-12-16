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

def analyze_per_scanner_patterns():
    """
    Analyze arrival patterns on a per-scanner basis to understand capacity distribution.
    """
    print("PER-SCANNER ANALYSIS: WHERE DO ADDITIONAL SCANS OCCUR?")
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
    
    # Convert to per-scanner basis
    baseline_per_scanner = baseline_avg_daily / NUM_SCANNERS
    rovis_per_scanner = rovis_avg_daily / NUM_SCANNERS
    additional_per_scanner = additional_daily / NUM_SCANNERS
    
    print(f"SUMMARY ({num_days} days average - PER SCANNER):")
    print(f"Baseline daily scans per scanner: {baseline_per_scanner:.1f}")
    print(f"Rovis daily scans per scanner: {rovis_per_scanner:.1f}")
    print(f"Additional daily scans per scanner: {additional_per_scanner:.1f}")
    print(f"Percentage increase per scanner: {(additional_per_scanner/baseline_per_scanner)*100:.1f}%")
    
    print(f"\nHOURLY BREAKDOWN (per scanner averages):")
    print(f"{'Hour':<6} {'Period':<12} {'Baseline':<12} {'Rovis':<12} {'Additional':<12} {'% Increase':<12}")
    print("-" * 85)
    
    total_additional_per_scanner = 0
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
            
        baseline_avg_per_scanner = (baseline_hourly_totals[hour] / num_days) / NUM_SCANNERS
        rovis_avg_per_scanner = (rovis_hourly_totals[hour] / num_days) / NUM_SCANNERS
        additional_per_scanner_hour = rovis_avg_per_scanner - baseline_avg_per_scanner
        total_additional_per_scanner += additional_per_scanner_hour
        
        pct_increase = ((rovis_avg_per_scanner / baseline_avg_per_scanner - 1) * 100) if baseline_avg_per_scanner > 0 else 0
        
        # Add to period data
        for period_name, data in period_data.items():
            if hour in data['hours']:
                data['baseline'] += baseline_avg_per_scanner
                data['rovis'] += rovis_avg_per_scanner
        
        print(f"{hour:02d}:00 {period:<12} {baseline_avg_per_scanner:<12.2f} {rovis_avg_per_scanner:<12.2f} "
              f"{additional_per_scanner_hour:+8.2f} {pct_increase:9.1f}%")
    
    print("-" * 85)
    print(f"{'TOTAL':<19} {baseline_per_scanner:<12.1f} {rovis_per_scanner:<12.1f} {total_additional_per_scanner:+8.1f}")
    
    print(f"\nPERIOD SUMMARIES (per scanner):")
    print(f"{'Period':<20} {'Baseline':<12} {'Rovis':<12} {'Additional':<12} {'% of Daily Add\'l':<16}")
    print("-" * 85)
    
    for period_name, data in period_data.items():
        additional_period = data['rovis'] - data['baseline']
        pct_of_additional = (additional_period / total_additional_per_scanner * 100) if total_additional_per_scanner > 0 else 0
        
        print(f"{period_name:<20} {data['baseline']:<12.1f} {data['rovis']:<12.1f} "
              f"{additional_period:+8.1f} {pct_of_additional:12.1f}%")

def analyze_scanner_utilization():
    """
    Show scanner utilization rates and capacity analysis.
    """
    print(f"\n\nSCANNER UTILIZATION ANALYSIS:")
    print("=" * 60)
    
    # Calculate theoretical maximum capacity per scanner
    # Assuming minimum 12-minute scan time + minimal prep
    min_scan_time = 12  # minutes
    max_scans_per_hour_per_scanner = 60 / min_scan_time
    max_scans_per_day_per_scanner = max_scans_per_hour_per_scanner * 24
    
    print(f"Theoretical maximum capacity per scanner:")
    print(f"  Minimum scan time: {min_scan_time} minutes")
    print(f"  Maximum scans/hour/scanner: {max_scans_per_hour_per_scanner:.0f}")
    print(f"  Maximum scans/day/scanner: {max_scans_per_day_per_scanner:.0f}")
    
    # Calculate actual utilization
    baseline_per_scanner = 145.4 / NUM_SCANNERS  # From simulation results
    rovis_per_scanner = 168.8 / NUM_SCANNERS
    
    baseline_utilization = (baseline_per_scanner / max_scans_per_day_per_scanner) * 100
    rovis_utilization = (rovis_per_scanner / max_scans_per_day_per_scanner) * 100
    
    print(f"\nActual utilization per scanner:")
    print(f"  Baseline scans/day/scanner: {baseline_per_scanner:.1f}")
    print(f"  Baseline utilization: {baseline_utilization:.1f}%")
    print(f"  Rovis scans/day/scanner: {rovis_per_scanner:.1f}")
    print(f"  Rovis utilization: {rovis_utilization:.1f}%")
    print(f"  Utilization increase: {rovis_utilization - baseline_utilization:.1f} percentage points")

def analyze_financial_impact_per_scanner():
    """
    Break down financial impact on a per-scanner basis.
    """
    print(f"\n\nFINANCIAL IMPACT PER SCANNER:")
    print("=" * 50)
    
    # Constants
    cm_per_scan = 484
    days_per_month = 30
    additional_scans_per_scanner_per_day = 3.9
    
    print(f"Additional scans per scanner per day: {additional_scans_per_scanner_per_day}")
    print(f"Contribution margin per scan: ${cm_per_scan}")
    
    # Calculate financial impact per scanner
    daily_cm_per_scanner = additional_scans_per_scanner_per_day * cm_per_scan
    monthly_cm_per_scanner = daily_cm_per_scanner * days_per_month
    annual_cm_per_scanner = monthly_cm_per_scanner * 12
    
    print(f"\nPer scanner financial impact:")
    print(f"  Daily additional CM: ${daily_cm_per_scanner:,.0f}")
    print(f"  Monthly additional CM: ${monthly_cm_per_scanner:,.0f}")
    print(f"  Annual additional CM: ${annual_cm_per_scanner:,.0f}")
    
    # ROI calculation per scanner (assuming robot cost)
    robot_cost_per_scanner = 150000  # Estimated cost allocation per scanner
    roi_months = robot_cost_per_scanner / monthly_cm_per_scanner
    
    print(f"\nROI per scanner (assuming ${robot_cost_per_scanner:,} robot cost allocation):")
    print(f"  Payback period: {roi_months:.1f} months")
    print(f"  Annual ROI: {(annual_cm_per_scanner/robot_cost_per_scanner)*100:.0f}%")


if __name__ == "__main__":
    analyze_per_scanner_patterns()
    analyze_scanner_utilization()
    analyze_financial_impact_per_scanner()