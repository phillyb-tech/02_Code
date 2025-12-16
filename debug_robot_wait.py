import math
import random
import statistics
import simpy

# Copy the relevant functions and constants from the main simulation
random.seed(42)

NUM_SCANNERS = 6
NUM_ROBOTS = 9
DAY_LENGTH_MIN = 24 * 60
ROBOT_UPTIME = 0.80

# Transport step timings
STEP_MEANS = {
    'A': {'baseline': 51.67, 'rovis_only': 51.67},
    'B1': {'baseline': 11.77, 'rovis_only': 2.94},
    'B2': {'baseline': 3.38, 'rovis_only': 0.85},
    'B3': {'baseline': 6.55, 'rovis_only': 1.64},
    'C1': {'baseline': 5.0, 'rovis_only': 5.0},
    'C2': {'baseline': 1.6, 'rovis_only': 1.6},
}

def calculate_robot_time(scenario_name):
    """Calculate robot occupation time (B1 + B2 + B3 + C1)"""
    return sum(STEP_MEANS[step][scenario_name] for step in ['B1', 'B2', 'B3', 'C1'])

def calculate_transport_time(scenario_name):
    """Calculate total patient transport time (A + B1 + B2 + B3 + C1 + C2)"""
    total_time = sum(STEP_MEANS[step][scenario_name] for step in ['A', 'B1', 'B2', 'B3', 'C1', 'C2'])
    return total_time

def generate_patient_arrivals(scenario_name='baseline'):
    """Generate patient arrivals - same demand across scenarios"""
    arrival_times = []
    
    for hour in range(24):
        if 7 <= hour < 19:  # 7am-7pm: Busy daytime
            arrivals_this_hour = 9.0
        elif 19 <= hour < 23:  # 7pm-11pm: Evening
            arrivals_this_hour = 4.5
        else:  # 11pm-7am: Overnight
            arrivals_this_hour = 2.5
        
        # Generate arrivals for this hour
        hour_start_min = hour * 60
        hour_end_min = (hour + 1) * 60
        current_time = hour_start_min
        
        while current_time < hour_end_min:
            if arrivals_this_hour > 0:
                avg_inter_arrival_min = 60.0 / arrivals_this_hour
                inter_arrival_time = random.expovariate(1.0 / avg_inter_arrival_min)
                current_time += inter_arrival_time
                
                if current_time < hour_end_min:
                    arrival_times.append(current_time)
            else:
                break
    
    return arrival_times

def debug_robot_utilization():
    """Debug robot utilization to understand wait times"""
    
    # Calculate patient arrival rates
    baseline_arrivals = generate_patient_arrivals('baseline')
    robot_arrivals = generate_patient_arrivals('rovis_only')
    
    print("=== PATIENT ARRIVAL ANALYSIS ===")
    print(f"Baseline patients per day: {len(baseline_arrivals)}")
    print(f"Robot scenario patients per day: {len(robot_arrivals)}")
    print(f"Increase: {len(robot_arrivals) - len(baseline_arrivals)} patients (+{((len(robot_arrivals)/len(baseline_arrivals))-1)*100:.1f}%)")
    
    # Calculate transport times
    baseline_transport = calculate_transport_time('baseline')
    robot_transport = calculate_transport_time('rovis_only')
    
    print("\n=== TRANSPORT TIME ANALYSIS ===")
    print(f"Baseline transport time: {baseline_transport:.1f} minutes")
    print(f"Robot transport time: {robot_transport:.1f} minutes")
    print(f"Time saved per patient: {baseline_transport - robot_transport:.1f} minutes")
    print(f"Reduction: {((baseline_transport - robot_transport)/baseline_transport)*100:.1f}%")
    
    # Calculate robot demand vs capacity
    robot_patients_per_day = len(robot_arrivals)
    robot_transport_minutes_per_day = robot_transport * robot_patients_per_day
    
    print("\n=== ROBOT CAPACITY ANALYSIS ===")
    print(f"Robot patients per day: {robot_patients_per_day}")
    print(f"Transport time per patient: {robot_transport:.1f} min")
    print(f"Total robot-minutes needed per day: {robot_transport_minutes_per_day:.0f}")
    print(f"Available robot-minutes per day (9 robots × 80% uptime × 24hr): {9 * 0.8 * 24 * 60:.0f}")
    
    # Calculate theoretical robot utilization
    available_robot_minutes = 9 * 0.8 * 24 * 60  # 9 robots, 80% uptime, 24 hours
    utilization = (robot_transport_minutes_per_day / available_robot_minutes) * 100
    
    print(f"Robot utilization: {utilization:.1f}%")
    
    if utilization > 100:
        print("⚠️  PROBLEM: Robot utilization > 100% - not enough robots!")
        print("⚠️  This explains the long wait times!")
    elif utilization > 80:
        print("⚠️  WARNING: Very high robot utilization - expect significant queuing")
    
    # Calculate peak hour demand
    print("\n=== PEAK HOUR ANALYSIS ===")
    peak_hour_patients = max(
        sum(1 for arrival in robot_arrivals if hour * 60 <= arrival < (hour + 1) * 60)
        for hour in range(24)
    )
    
    peak_robot_minutes = peak_hour_patients * robot_transport
    available_robot_minutes_per_hour = 9 * 0.8 * 60  # Per hour
    peak_utilization = (peak_robot_minutes / available_robot_minutes_per_hour) * 100
    
    print(f"Peak hour patients: {peak_hour_patients}")
    print(f"Peak hour robot utilization: {peak_utilization:.1f}%")
    
    if peak_utilization > 100:
        print("⚠️  PEAK OVERLOAD: Not enough robots during peak hours!")

if __name__ == "__main__":
    debug_robot_utilization()