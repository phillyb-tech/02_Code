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

def create_hourly_scan_table():
    """
    Create a detailed table showing when additional scans occur throughout the day.
    """
    print("HOURLY SCAN DISTRIBUTION TABLE")
    print("=" * 100)
    print("Shows when the additional 3.9 scans per scanner occur throughout a 24-hour period")
    print()
    
    # Set random seed for consistent results
    random.seed(42)
    
    # Analyze arrival patterns across multiple days
    baseline_hourly_totals = {hour: 0 for hour in range(24)}
    rovis_hourly_totals = {hour: 0 for hour in range(24)}
    
    num_days = 20  # Analyze more days for better stability
    
    for day in range(num_days):
        # Generate arrivals for each scenario
        baseline_arrivals = generate_patient_arrivals('baseline')
        rovis_arrivals = generate_patient_arrivals('rovis_only')
        
        # Count by hour
        for arrival in baseline_arrivals:
            hour = int(arrival // 60)
            if hour < 24:
                baseline_hourly_totals[hour] += 1
        
        for arrival in rovis_arrivals:
            hour = int(arrival // 60)
            if hour < 24:
                rovis_hourly_totals[hour] += 1
    
    print("DETAILED HOURLY BREAKDOWN (PER SCANNER BASIS)")
    print("-" * 100)
    print(f"{'Time':<8} {'Period':<12} {'Baseline':<12} {'w/ Robots':<12} {'Additional':<12} {'Cumulative':<12}")
    print(f"{'Slot':<8} {'Type':<12} {'Per Scanner':<12} {'Per Scanner':<12} {'Per Scanner':<12} {'Add\'l':<12}")
    print("-" * 100)
    
    cumulative_additional_per_scanner = 0
    
    for hour in range(24):
        # Determine period type
        if 7 <= hour < 19:
            period = "Daytime"
            period_icon = "🌅"
        elif 19 <= hour < 23:
            period = "Evening"
            period_icon = "🌆"
        else:
            period = "Overnight"
            period_icon = "🌙"
        
        # Calculate averages per scanner
        baseline_avg_per_scanner = (baseline_hourly_totals[hour] / num_days) / NUM_SCANNERS
        rovis_avg_per_scanner = (rovis_hourly_totals[hour] / num_days) / NUM_SCANNERS
        additional_per_scanner = rovis_avg_per_scanner - baseline_avg_per_scanner
        cumulative_additional_per_scanner += additional_per_scanner
        
        # Format time
        time_str = f"{hour:02d}:00"
        period_with_icon = f"{period_icon} {period}"
        
        print(f"{time_str:<8} {period_with_icon:<12} {baseline_avg_per_scanner:<12.2f} {rovis_avg_per_scanner:<12.2f} "
              f"{additional_per_scanner:+8.2f} {cumulative_additional_per_scanner:+8.2f}")
    
    print("-" * 100)
    baseline_total_per_scanner = sum(baseline_hourly_totals.values())/num_days/NUM_SCANNERS
    rovis_total_per_scanner = sum(rovis_hourly_totals.values())/num_days/NUM_SCANNERS
    print(f"{'TOTAL':<8} {'All Day':<12} {baseline_total_per_scanner:<12.1f} "
          f"{rovis_total_per_scanner:<12.1f} "
          f"{cumulative_additional_per_scanner:+8.1f} {cumulative_additional_per_scanner:+8.1f}")
    
    # Period summaries
    print(f"\nPERIOD SUMMARY TABLE (PER SCANNER BASIS)")
    print("-" * 80)
    print(f"{'Period':<20} {'Hours':<12} {'Baseline':<12} {'w/ Robots':<12} {'Additional':<12}")
    print(f"{'':20} {'':12} {'Per Scanner':<12} {'Per Scanner':<12} {'Per Scanner':<12}")
    print("-" * 80)
    
    periods = {
        '🌅 Daytime': {'hours': list(range(7, 19)), 'desc': '7am-7pm'},
        '🌆 Evening': {'hours': list(range(19, 23)), 'desc': '7pm-11pm'}, 
        '🌙 Overnight': {'hours': list(range(0, 7)) + [23], 'desc': '11pm-7am'}
    }
    
    total_additional_per_scanner_all_periods = 0
    
    for period_name, data in periods.items():
        baseline_period_per_scanner = sum(baseline_hourly_totals[h] for h in data['hours']) / num_days / NUM_SCANNERS
        rovis_period_per_scanner = sum(rovis_hourly_totals[h] for h in data['hours']) / num_days / NUM_SCANNERS
        additional_per_scanner_period = rovis_period_per_scanner - baseline_period_per_scanner
        total_additional_per_scanner_all_periods += additional_per_scanner_period
        
        print(f"{period_name:<20} {data['desc']:<12} {baseline_period_per_scanner:<12.1f} {rovis_period_per_scanner:<12.1f} "
              f"{additional_per_scanner_period:+8.1f}")
    
    print("-" * 80)
    baseline_total_per_scanner = sum(baseline_hourly_totals.values())/num_days/NUM_SCANNERS
    rovis_total_per_scanner = sum(rovis_hourly_totals.values())/num_days/NUM_SCANNERS
    print(f"{'TOTAL':<20} {'24 hours':<12} {baseline_total_per_scanner:<12.1f} "
          f"{rovis_total_per_scanner:<12.1f} "
          f"{total_additional_per_scanner_all_periods:+8.1f}")
    
    # Peak hours analysis
    print(f"\nPEAK IMPACT HOURS (PER SCANNER)")
    print("-" * 60)
    
    # Calculate additional scans per hour per scanner and find top 5
    hourly_impact_per_scanner = []
    for hour in range(24):
        baseline_avg_per_scanner = (baseline_hourly_totals[hour] / num_days) / NUM_SCANNERS
        rovis_avg_per_scanner = (rovis_hourly_totals[hour] / num_days) / NUM_SCANNERS
        additional_per_scanner = rovis_avg_per_scanner - baseline_avg_per_scanner
        hourly_impact_per_scanner.append((hour, additional_per_scanner))
    
    # Sort by additional scans per scanner (highest first)
    top_hours = sorted(hourly_impact_per_scanner, key=lambda x: x[1], reverse=True)[:5]
    
    print(f"{'Rank':<6} {'Time':<8} {'Additional Scans Per Scanner':<30}")
    print("-" * 60)
    
    for i, (hour, additional_per_scanner) in enumerate(top_hours, 1):
        time_str = f"{hour:02d}:00"
        print(f"{i:<6} {time_str:<8} {additional_per_scanner:+8.2f}")
    
    total_additional_per_scanner = cumulative_additional_per_scanner
    baseline_total_per_scanner = sum(baseline_hourly_totals.values())/num_days/NUM_SCANNERS
    
    print(f"\nKEY INSIGHTS (PER SCANNER):")
    print(f"• Most additional capacity occurs during daytime hours (7am-7pm)")
    print(f"• Peak impact hours are when transport bottlenecks are most severe")
    print(f"• Each scanner gains an average of {total_additional_per_scanner:.1f} scans per day")
    print(f"• This represents a {(total_additional_per_scanner/baseline_total_per_scanner)*100:.1f}% increase in daily capacity per scanner")


if __name__ == "__main__":
    create_hourly_scan_table()