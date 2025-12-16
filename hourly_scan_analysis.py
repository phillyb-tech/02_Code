import math
import random
import statistics
import simpy

# Import the functions from the main simulation
import sys
sys.path.append('.')
from ct_scan_shands_des import (
    generate_patient_arrivals, NUM_SCANNERS, NUM_ROBOTS, 
    DAY_LENGTH_MIN, STEP_MEANS, STEP_SIGMA, STEP_ORDER,
    get_step_duration, generate_exam_duration, calculate_transport_time
)

random.seed(42)

def simulate_one_patient_with_timing(env, patient_id, scheduled_time, scanners, robots, 
                                   scenario_name, scanner_events):
    """
    Simulate one patient and track detailed timing for hourly analysis.
    """
    # STEP 1: Wait until scheduled time
    yield env.timeout(scheduled_time)

    # STEP 2: Transport patient to CT area
    if scenario_name == "baseline":
        transport_time = calculate_transport_time('baseline')
        yield env.timeout(transport_time)
    else:
        time_when_robot_requested = env.now
        with robots.request() as robot_request:
            yield robot_request
            time_when_robot_available = env.now
            
            # 80% uptime for robots
            if random.random() < 0.80:
                transport_time = calculate_transport_time(scenario_name)
            else:
                transport_time = calculate_transport_time('baseline')
            yield env.timeout(transport_time)

    # STEP 3: Request CT scanner
    time_when_ct_requested = env.now
    with scanners.request() as scanner_request:
        yield scanner_request
        time_when_ct_starts = env.now
        
        # Record detailed timing
        scanner_events.append({
            'patient_id': patient_id,
            'scheduled': scheduled_time,
            'arrived_ct': time_when_ct_requested,
            'scan_start': time_when_ct_starts,
            'scan_start_hour': int(time_when_ct_starts // 60)
        })
        
        # STEP 4: Perform CT exam
        exam_time = generate_exam_duration()
        scanner_events[-1]['scan_end'] = time_when_ct_starts + exam_time
        scanner_events[-1]['scan_end_hour'] = int((time_when_ct_starts + exam_time) // 60)
        yield env.timeout(exam_time)


def analyze_hourly_patterns(scenario_name):
    """
    Analyze when additional scans occur throughout the day.
    """
    print(f"\nHOURLY SCAN ANALYSIS - {scenario_name.upper()}")
    print("=" * 60)
    
    # Set up simulation
    env = simpy.Environment()
    scanners = simpy.Resource(env, capacity=NUM_SCANNERS)
    robots = None if scenario_name == "baseline" else simpy.Resource(env, capacity=NUM_ROBOTS)
    
    scanner_events = []
    
    # Generate patient arrivals
    arrival_times = generate_patient_arrivals(scenario_name)
    
    # Schedule all patients
    for patient_id, arrival_time in enumerate(arrival_times):
        env.process(simulate_one_patient_with_timing(
            env, patient_id, arrival_time, scanners, robots,
            scenario_name, scanner_events
        ))
    
    # Run simulation
    env.run(until=DAY_LENGTH_MIN + 240)
    
    # Filter completed scans
    completed_scans = [e for e in scanner_events if 'scan_end' in e]
    
    # Count scans by hour
    hourly_scans = {}
    hourly_arrivals = {}
    
    for hour in range(24):
        hourly_scans[hour] = 0
        hourly_arrivals[hour] = 0
    
    # Count arrivals by hour
    for arrival_time in arrival_times:
        hour = int(arrival_time // 60)
        if hour < 24:
            hourly_arrivals[hour] += 1
    
    # Count completed scans by start hour
    for scan in completed_scans:
        hour = scan['scan_start_hour']
        if hour < 24:
            hourly_scans[hour] += 1
    
    return hourly_scans, hourly_arrivals, len(completed_scans), len(arrival_times)


def compare_hourly_patterns():
    """
    Compare baseline vs rovis_only to see when additional scans occur.
    """
    print("HOURLY PATTERN ANALYSIS: WHERE DO THE ADDITIONAL 3.9 SCANS OCCUR?")
    print("=" * 80)
    
    # Run both scenarios
    baseline_scans, baseline_arrivals, baseline_total, baseline_arrivals_total = analyze_hourly_patterns("baseline")
    rovis_scans, rovis_arrivals, rovis_total, rovis_arrivals_total = analyze_hourly_patterns("rovis_only")
    
    print(f"\nSUMMARY:")
    print(f"Baseline total scans: {baseline_total}")
    print(f"Rovis total scans: {rovis_total}")
    print(f"Additional scans: {rovis_total - baseline_total}")
    print(f"Additional scans per scanner: {(rovis_total - baseline_total)/6:.1f}")
    
    print(f"\nHOURLY BREAKDOWN:")
    print(f"{'Hour':<6} {'Period':<12} {'Baseline':<10} {'Rovis':<8} {'Additional':<12} {'Arrival Inc':<12}")
    print("-" * 70)
    
    total_additional = 0
    for hour in range(24):
        if 7 <= hour < 19:
            period = "Daytime"
        elif 19 <= hour < 23:
            period = "Evening"
        else:
            period = "Overnight"
            
        additional_scans = rovis_scans[hour] - baseline_scans[hour]
        additional_arrivals = rovis_arrivals[hour] - baseline_arrivals[hour]
        total_additional += additional_scans
        
        print(f"{hour:02d}:00 {period:<12} {baseline_scans[hour]:<10} {rovis_scans[hour]:<8} "
              f"{additional_scans:+3d} {'(+' + str(additional_arrivals) + ' arr)':<12}")
    
    print("-" * 70)
    print(f"{'TOTAL':<19} {sum(baseline_scans.values()):<10} {sum(rovis_scans.values()):<8} {total_additional:+3d}")
    
    # Period summaries
    periods = {
        'Daytime (7am-7pm)': list(range(7, 19)),
        'Evening (7pm-11pm)': list(range(19, 23)), 
        'Overnight (11pm-7am)': list(range(0, 7)) + [23]
    }
    
    print(f"\nPERIOD SUMMARIES:")
    print(f"{'Period':<20} {'Baseline':<10} {'Rovis':<8} {'Additional':<12} {'% of Add\'l':<12}")
    print("-" * 70)
    
    for period_name, hours in periods.items():
        baseline_period = sum(baseline_scans[h] for h in hours)
        rovis_period = sum(rovis_scans[h] for h in hours)
        additional_period = rovis_period - baseline_period
        pct_of_additional = (additional_period / total_additional * 100) if total_additional > 0 else 0
        
        print(f"{period_name:<20} {baseline_period:<10} {rovis_period:<8} "
              f"{additional_period:+3d} {pct_of_additional:9.1f}%")


if __name__ == "__main__":
    compare_hourly_patterns()