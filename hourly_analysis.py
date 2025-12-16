import math
import random
import statistics
import simpy

# Same configuration as main simulation
NUM_SCANNERS = 6
NUM_ROBOTS = 9
DAY_LENGTH_MIN = 24 * 60
random.seed(42)

def generate_patient_arrivals_with_hourly_tracking(scenario_name='baseline'):
    """
    Generate patient arrivals and track them by hour for analysis.
    """
    # Calculate efficiency multiplier
    baseline_cycle = 119.5
    if scenario_name == 'rovis_only':
        scenario_cycle = 103.2
        efficiency_multiplier = baseline_cycle / scenario_cycle  # 1.158x
    elif scenario_name == 'rovis_workflow':
        scenario_cycle = 86.6  
        efficiency_multiplier = baseline_cycle / scenario_cycle  # 1.381x
    else:
        efficiency_multiplier = 1.0  # Baseline
    
    arrival_times = []
    hourly_arrivals = [0] * 24  # Track arrivals per hour
    
    for hour in range(24):
        if 7 <= hour < 19:  # 7am-7pm: Busy daytime period
            base_arrivals_this_hour = 9.0
        elif 19 <= hour < 23:  # 7pm-11pm: Evening period  
            base_arrivals_this_hour = 4.5
        else:  # 11pm-7am: Overnight period
            base_arrivals_this_hour = 2.5
            
        # Scale arrivals based on robot efficiency
        arrivals_this_hour = base_arrivals_this_hour * efficiency_multiplier
            
        # Generate arrivals for this hour using Poisson process
        hour_start_min = hour * 60
        hour_end_min = (hour + 1) * 60
        current_time = hour_start_min
        hour_count = 0
        
        while current_time < hour_end_min:
            if arrivals_this_hour > 0:
                avg_inter_arrival_min = 60.0 / arrivals_this_hour
                inter_arrival_time = random.expovariate(1.0 / avg_inter_arrival_min)
                current_time += inter_arrival_time
                
                if current_time < hour_end_min:
                    arrival_times.append(current_time)
                    hour_count += 1
            else:
                break
        
        hourly_arrivals[hour] = hour_count
    
    return arrival_times, hourly_arrivals

def simulate_hourly_scanner_usage(scenario_name='baseline'):
    """
    Simulate one day and track which hours scans are completed.
    """
    # Simple simulation - just track when scans complete
    arrival_times, hourly_arrivals = generate_patient_arrivals_with_hourly_tracking(scenario_name)
    
    # For simplicity, assume each scan takes 12 minutes average
    # and starts roughly when patient arrives (ignoring queuing for this analysis)
    hourly_completions = [0] * 24
    
    for arrival_time in arrival_times:
        # Add transport time (varies by scenario)
        if scenario_name == 'baseline':
            transport_time = 73.8  # Average baseline transport time
        elif scenario_name == 'rovis_only':
            transport_time = 57.5  # Average with robots
        else:  # rovis_workflow
            transport_time = 40.2  # Average with robots + workflow
        
        # Add scan time (12 minutes average)
        scan_completion_time = arrival_time + transport_time + 12
        
        # Determine which hour the scan completes
        completion_hour = int(scan_completion_time // 60)
        if completion_hour < 24:  # Only count scans that complete same day
            hourly_completions[completion_hour] += 1
    
    return hourly_arrivals, hourly_completions

# Analyze all three scenarios
scenarios = [
    ('baseline', 'Baseline - Manual Transport'),
    ('rovis_only', '9 Rovis - Transport Only'),
    ('rovis_workflow', '9 Rovis - Transport + Workflow')
]

print("\nHOURLY CT SCAN ANALYSIS")
print("="*80)
print("Shows patient arrivals and scan completions by hour over 24 hours")
print("="*80)

for scenario_key, scenario_label in scenarios:
    arrivals, completions = simulate_hourly_scanner_usage(scenario_key)
    
    print(f"\n{scenario_label}:")
    print(f"{'Hour':<6} {'Arrivals':<10} {'Completions':<12} {'Per Scanner':<12}")
    print("-" * 50)
    
    total_arrivals = 0
    total_completions = 0
    
    for hour in range(24):
        per_scanner = completions[hour] / NUM_SCANNERS
        total_arrivals += arrivals[hour]
        total_completions += completions[hour]
        
        # Format hour as time
        if hour == 0:
            time_str = "12am"
        elif hour < 12:
            time_str = f"{hour}am"
        elif hour == 12:
            time_str = "12pm"
        else:
            time_str = f"{hour-12}pm"
            
        print(f"{time_str:<6} {arrivals[hour]:<10} {completions[hour]:<12} {per_scanner:.1f}")
    
    print("-" * 50)
    print(f"Total: {total_arrivals:<10} {total_completions:<12} {total_completions/NUM_SCANNERS:.1f}/day")
    print(f"Average per hour: {total_completions/24:.1f} total ({total_completions/24/NUM_SCANNERS:.1f} per scanner)")

print("\n" + "="*80)
print("OBSERVATIONS:")
print("- Peak hours: 7am-7pm (daytime)")
print("- Each scanner averages 1-2 scans during busy hours")
print("- Overnight hours (11pm-7am) have 0-1 scans per scanner")
print("- Robots enable higher throughput during all hours")
print("="*80)