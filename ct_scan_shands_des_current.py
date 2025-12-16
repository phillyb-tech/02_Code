import math
import random
import statistics
import simpy

# =============================================================================
# SIMULATION SETUP - What we're testing
# =============================================================================
# This simulation models CT scan operations in a hospital to see if robots
# can help reduce wait times and increase scanner capacity.
#
# Three scenarios:
# 1. Baseline: Manual patient transport (current state)
# 2. Rovis Only: Robots help with transport coordination
# 3. Rovis + Workflow: Robots + improved hospital workflows

random.seed(42)  # Makes results repeatable

# =============================================================================
# HOSPITAL CONFIGURATION - How many resources we have
# =============================================================================
NUM_SCANNERS = 6                    # Total CT scanners available
NUM_ROBOTS = 9                      # Number of transport robots
DAY_LENGTH_MIN = 24 * 60           # 24-hour operation in minutes
OPERATING_DAYS_PER_YEAR = 360      # Days hospital operates per year

# =============================================================================
# FINANCIAL ASSUMPTIONS - Money calculations
# =============================================================================
CT_CM_PER_SCAN = 484               # Contribution margin per CT scan
BOOKING_CONVERSION = 0.60          # 60% of freed time converts to new scans (moderate absorption)
ROBOT_UPTIME = 0.80                # Robots work 80% of the time (20% downtime)

N_SIM_DAYS = 100                  # Run simulation 100 times for testing (change back to 1000 for final results)

# =============================================================================
# WORKFLOW-DERIVED CAPACITY MODEL - Calculate capacity from actual workflow times
# =============================================================================
# No artificial demand constraints - let workflow efficiency determine capacity
# Baseline capacity calculated from actual Shands workflow times
SCANNER_HOURS_PER_DAY = 24 * 60       # Minutes available per scanner per day
AVG_SCAN_DURATION = 12.11             # Minutes per scan (from C3 step)

# =============================================================================
# WORKFLOW TIMINGS - How long each step takes (in minutes)
# =============================================================================
# Data from Shands TaT Report - Real measured times
# Steps explained:
# P = CT order placed to CT scheduled (protocoling)
# A = CT scheduled to transport requested (waiting for transport queue)
# B1 = Transport requested to assigned (waiting for transporter)
# B2 = Transport assigned to acknowledged (transporter acknowledges)
# B3 = Transport acknowledge to start (delays before moving patient)
# C1 = Transport start to Transport end (moving patient)
# C2 = Transport end to CT start (arrival to scanner prep)
# C3 = CT start to CT end (actual scan)
STEP_MEANS = {
    'P': {'baseline': 27.43, 'rovis_only': 27.43, 'rovis_workflow': 27.43},    # P: CT order placed → CT scheduled (protocoling)
    'A': {'baseline': 51.67, 'rovis_only': 51.67, 'rovis_workflow': 35.0},     # A: CT scheduled → transport requested (queue wait)
    'B1': {'baseline': 11.77, 'rovis_only': 2.94, 'rovis_workflow': 2.94},     # B1: Transport requested → transporter assigned
    'B2': {'baseline': 3.38, 'rovis_only': 0.85, 'rovis_workflow': 0.85},      # B2: Transport assigned → transporter acknowledges
    'B3': {'baseline': 6.55, 'rovis_only': 1.64, 'rovis_workflow': 1.64},      # B3: Acknowledge → transport start (patient prep delay)
    'C1': {'baseline': 5.0, 'rovis_only': 5.0, 'rovis_workflow': 5.0},         # C1: Transport start → transport end (movement)
    'C2': {'baseline': 1.6, 'rovis_only': 1.6, 'rovis_workflow': 1.6},         # C2: Transport end → CT start (scanner prep)
    'C3': {'baseline': 12.11, 'rovis_only': 12.11, 'rovis_workflow': 12.11},   # C3: CT start → CT end (scan time)
}
# Variability in timing (standard deviation estimates)
# These values are std‑dev factors used with the log‑normal generator.
# Rationale:
#  - Admin/queue steps (P, A, B1, B3) show higher variability due to staffing/queueing.
#  - Operational acknowledgements (B2) are moderately variable.
#  - Movement/scan prep (C1, C2) are more consistent (lower variability).
#  - Scan time (C3) has clinical variability but is tighter than queueing steps.
STEP_SIGMA = {
    'P': 0.30,  # Protocoling (CT order → scheduled) - moderate variability
    'A': 0.35,  # CT scheduled → transport requested (queue wait) - moderate/high
    'B1': 0.40, # Transport requested → transporter assigned - high variability
    'B2': 0.30, # Transport assigned → transport acknowledged - moderate variability
    'B3': 0.40, # Acknowledge → transport start (patient readiness delays) - high
    'C1': 0.20, # Transport start → transport end (movement) - lower variability
    'C2': 0.15, # Transport end → CT start (scanner prep) - low variability
    'C3': 0.25, # CT start → CT end (scan time) - clinical variability
}

# Order of steps for calculating totals
STEP_ORDER = ['P', 'A', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3']

def get_theoretical_total(scenario_name):
    """
    Return the theoretical total used for reporting based on STEP_MEANS.
    Uses the precise STEP_MEANS values and returns a single-decimal rounded value
    for display (no forced/display-only map).
    """
    return round(sum(STEP_MEANS[step][scenario_name] for step in STEP_ORDER), 1)

# =============================================================================
# HELPER FUNCTIONS - Small utility functions
# =============================================================================

def generate_random_time_with_average(average_time, variability):
    """
    Generate a random time that averages to a specific value.
    Uses log-normal distribution (realistic for medical processes).
    
    Example: If average is 10 minutes, might return 9.2, 10.5, 11.3, etc.
    """
    mu = math.log(average_time) - 0.5 * variability**2
    return random.lognormvariate(mu, variability)


def get_step_duration(step_name, scenario_name):
    """
    Return duration for a step using stochastic draws for ALL scenarios.
    - Uses STEP_MEANS as the mean and STEP_SIGMA for variability.
    """
    average_time = STEP_MEANS[step_name][scenario_name]
    variability = STEP_SIGMA.get(step_name, 0.3)
    return generate_random_time_with_average(average_time, variability)


def generate_exam_duration():
    """
    Generate a realistic CT exam duration.
    Average is 12 minutes, but can vary from 5 to 25 minutes.
    
    Returns:
        Exam duration in minutes
    """
    while True:
        duration = random.gauss(12, 3)  # Mean=12, std dev=3
        if 5 <= duration <= 25:         # Keep only realistic values
            return duration


def generate_patient_arrivals_workflow_derived(scenario_name='baseline',
                                              deterministic=False,
                                              deterministic_daily_patients=None):
    """
    Generate patient arrivals based on workflow-derived processing capacity.
    
    Logic:
    - Calculate how many patients can be processed based on workflow times
    - No artificial demand constraints - workflow efficiency determines capacity
    - Baseline: 25 scans/day (known from your data)
    - Robot scenarios: Improved efficiency allows more throughput
    
    Args:
        scenario_name: Which scenario we're simulating
    
    Returns:
        List of arrival times (in minutes from start of day)
    """
    
    # Calculate daily processing capacity from workflow times
    # Start with known baseline: 25 CT scans per day
    baseline_daily_capacity = 25.0
    
    if deterministic_daily_patients is not None:
        daily_patients = deterministic_daily_patients
    elif scenario_name == 'baseline':
        daily_patients = baseline_daily_capacity
    else:
        # Calculate transport time improvement
        baseline_transport_time = (
            get_theoretical_total('baseline') - 
            27.43 - 12.11  # Subtract P and C3 (non-transport steps)
        )
        scenario_transport_time = (
            get_theoretical_total(scenario_name) - 
            27.43 - 12.11  # Subtract P and C3 (non-transport steps) 
        )
        
        # Calculate capacity improvement factor from transport efficiency
        if baseline_transport_time > 0:
            capacity_improvement = baseline_transport_time / scenario_transport_time
        else:
            capacity_improvement = 1.0
        
        # Improved capacity = baseline capacity * transport efficiency gain
        theoretical_improved_capacity = baseline_daily_capacity * capacity_improvement
        
        # Apply booking conversion factor - not all efficiency gains convert to actual patients
        improved_daily_capacity = baseline_daily_capacity + ((theoretical_improved_capacity - baseline_daily_capacity) * BOOKING_CONVERSION)
        
        # Limited only by maximum scanner capacity (not artificial demand limits)
        max_scanner_capacity = (SCANNER_HOURS_PER_DAY * NUM_SCANNERS) / AVG_SCAN_DURATION
        
        # Actual capacity = min(workflow-derived capacity, physical scanner limit)
        daily_patients = min(improved_daily_capacity, max_scanner_capacity)
    
    arrival_times = []
    
    # Distribute patients across 24 hours with realistic hospital patterns
    carry = 0.0
    for hour in range(24):
        if 7 <= hour < 19:  # 7am-7pm: Busy daytime period (70% of patients)
            hour_fraction = 0.70 / 12
        elif 19 <= hour < 23:  # 7pm-11pm: Evening period (20% of patients)
            hour_fraction = 0.20 / 4  
        else:  # 11pm-7am: Overnight period (10% of patients)
            hour_fraction = 0.10 / 8
            
        expected_arrivals = daily_patients * hour_fraction
        hour_start_min = hour * 60
        hour_end_min = (hour + 1) * 60

        if deterministic:
            # Convert expected arrivals to an integer count with carry to preserve totals
            count = int(expected_arrivals + carry)
            carry = (expected_arrivals + carry) - count
            if count > 0:
                spacing = 60.0 / (count + 1)
                for i in range(count):
                    arrival_times.append(hour_start_min + spacing * (i + 1))
        else:
            # Generate arrivals for this hour using Poisson process
            current_time = hour_start_min
            while current_time < hour_end_min and expected_arrivals > 0:
                if expected_arrivals > 0:
                    avg_inter_arrival_min = 60.0 / expected_arrivals
                    inter_arrival_time = random.expovariate(1.0 / avg_inter_arrival_min)
                    current_time += inter_arrival_time
                    
                    if current_time < hour_end_min:
                        arrival_times.append(current_time)
                else:
                    break
    
    return arrival_times


def generate_robot_repositioning_time():
    """
    Generate robot repositioning time after dropping off a patient.
    Robots need to travel from CT area back to patient pickup locations.
    Shands is a large hospital with significant travel distances.
    
    Returns:
        Repositioning time in minutes (5-15 minutes)
    """
    # Average 10 minutes, range 5-15 minutes for large hospital
    while True:
        reposition_time = random.gauss(10.0, 2.0)  # Mean=10, std dev=2.0
        if 5.0 <= reposition_time <= 15.0:  # Keep realistic range
            return reposition_time


def calculate_robot_time(scenario_name):
    """
    Calculate time robot is occupied (B1 + B2 + B3 + C1 + repositioning).
    After repositioning, robot is free to help another patient.
    
    Args:
        scenario_name: Which scenario we're simulating
    
    Returns:
        Robot occupation time in minutes
    """
    return (
        get_step_duration('B1', scenario_name) +
        get_step_duration('B2', scenario_name) +
        get_step_duration('B3', scenario_name) +
        get_step_duration('C1', scenario_name) +
        generate_robot_repositioning_time()  # Add repositioning time
    )

def calculate_patient_transport_time(scenario_name):
    """
    Calculate total patient transport time (A + B1 + B2 + B3 + C1 + C2).
    This is how long patient waits from scheduling to reaching scanner.
    
    Args:
        scenario_name: Which scenario we're simulating
    
    Returns:
        Total patient transport time in minutes
    """
    total_time = (
        get_step_duration('A', scenario_name) +
        get_step_duration('B1', scenario_name) +
        get_step_duration('B2', scenario_name) +
        get_step_duration('B3', scenario_name) +
        get_step_duration('C1', scenario_name) +
        get_step_duration('C2', scenario_name)
    )
    return total_time

# =============================================================================
# SIMULATION CORE - The actual patient flow simulation
# =============================================================================

def simulate_one_patient(env, patient_id, scheduled_time, scanners, robots, 
                        scenario_name, collected_metrics, scanner_events):
    """
    Simulate one patient's journey from request to completed CT scan.
    
    This function represents what happens to ONE patient:
    1. Wait until their scheduled time
    2. Get transported to CT (with or without robot)
    3. Wait for available CT scanner
    4. Complete the CT exam
    
    Args:
        env: SimPy environment (keeps track of time)
        patient_id: Unique ID for this patient
        scheduled_time: When this patient is scheduled
        scanners: Pool of available CT scanners
        robots: Pool of available robots (None for baseline)
        scenario_name: Which scenario we're running
        collected_metrics: Dictionary to store wait times
        scanner_events: List to track when scanners are used
    """
    # STEP 1: Wait until this patient's scheduled time
    yield env.timeout(scheduled_time)

    # STEP 2: Transport patient to CT area
    if scenario_name == "baseline":
        # Baseline = manual transport, no robot needed
        transport_time = calculate_patient_transport_time('baseline')
        yield env.timeout(transport_time)
    else:
        # Step A: Queue wait (happens before robot is needed)
        step_a_time = get_step_duration('A', scenario_name)
        yield env.timeout(step_a_time)
        
        # Steps B1-B3+C1: Robot-assisted transport
        time_when_robot_requested = env.now
        
        # Request a robot (might have to wait if all robots are busy)
        with robots.request() as robot_request:
            yield robot_request  # Wait for robot to become available
            time_when_robot_available = env.now
            
            # Record how long we waited for a robot
            robot_wait_time = time_when_robot_available - time_when_robot_requested
            collected_metrics['robot_waits'].append(robot_wait_time)

            # Robots have 80% uptime - 20% of time they fail and we revert to manual
            if random.random() < ROBOT_UPTIME:
                robot_time = calculate_robot_time(scenario_name)
            else:
                # Robot failed - use manual times for B1-B3+C1+repositioning
                robot_time = (
                    get_step_duration('B1', 'baseline') +
                    get_step_duration('B2', 'baseline') +
                    get_step_duration('B3', 'baseline') +
                    get_step_duration('C1', 'baseline') +
                    generate_robot_repositioning_time()  # Even failed robots need to reposition
                )

            yield env.timeout(robot_time)
            # Robot is now free to help another patient after repositioning!
        
        # Step C2: Scanner prep (no robot needed)
        step_c2_time = get_step_duration('C2', scenario_name)
        yield env.timeout(step_c2_time)

    # STEP 3: Request a CT scanner (might have to wait if all scanners busy)
    time_when_ct_requested = env.now
    
    with scanners.request() as scanner_request:
        yield scanner_request  # Wait for scanner to become available
        time_when_ct_starts = env.now
        
        # Record how long we waited for a scanner
        ct_wait_time = time_when_ct_starts - time_when_ct_requested
        collected_metrics['ct_waits'].append(ct_wait_time)

        # Record when this scanner started being used
        scanner_events.append({
            'patient_id': patient_id,
            'sched': scheduled_time,
            'start': time_when_ct_starts
        })
        
        # STEP 4: Perform the actual CT exam
        exam_time = generate_exam_duration()
        scanner_events[-1]['end'] = time_when_ct_starts + exam_time
        yield env.timeout(exam_time)


def simulate_one_day(scenario_name):
    """
    Simulate one complete day of CT operations.
    Creates all patients, runs the simulation, calculates idle time.
    
    Args:
        scenario_name: Which scenario to simulate
    
    Returns:
        Dictionary with metrics from this day:
        - robot_waits: List of robot wait times
        - ct_waits: List of CT scanner wait times
        - idle_per_scanner: Average idle time per scanner
        - total_patients: Number of patients who arrived
        - completed_scans: Number of scans completed
    """
    # Set up the simulation environment
    env = simpy.Environment()
    scanners = simpy.Resource(env, capacity=NUM_SCANNERS)
    
    # Robots only exist in non-baseline scenarios
    robots = None if scenario_name == "baseline" else simpy.Resource(env, capacity=NUM_ROBOTS)

    # Storage for collected data
    collected_metrics = {'robot_waits': [], 'ct_waits': []}
    scanner_events = []

    # Generate patient arrivals based on workflow-derived processing capacity
    arrival_times = generate_patient_arrivals_workflow_derived(scenario_name)
    
    # Schedule all patients based on their arrival times
    for patient_id, arrival_time in enumerate(arrival_times):
        env.process(simulate_one_patient(
            env, patient_id, arrival_time, scanners, robots,
            scenario_name, collected_metrics, scanner_events
        ))

    # Run the simulation (go through the whole day + 4 hours buffer)
    env.run(until=DAY_LENGTH_MIN + 240)

    # Calculate scanner idle time using "pooled scheduling" approach
    # This assigns each exam to whichever scanner becomes free first
    completed_exams = [e for e in scanner_events if 'start' in e and 'end' in e]
    completed_exams.sort(key=lambda x: x['start'])  # Sort by start time

    # Track when each scanner will be free
    scanner_free_times = [0.0] * NUM_SCANNERS
    total_idle_time = 0.0
    
    for exam in completed_exams:
        # Find which scanner is free earliest
        earliest_free_scanner = scanner_free_times.index(min(scanner_free_times))
        
        # Calculate idle gap before this exam
        idle_gap = max(0.0, exam['start'] - scanner_free_times[earliest_free_scanner])
        total_idle_time += idle_gap
        
        # Update when this scanner will be free again
        scanner_free_times[earliest_free_scanner] = exam['end']
        exam['scanner'] = earliest_free_scanner
    # Add tail idle time up to the 24h mark (ignore buffer beyond the day)
    for ft in scanner_free_times:
        total_idle_time += max(0.0, DAY_LENGTH_MIN - ft)

    average_idle_per_scanner = total_idle_time / NUM_SCANNERS

    return {
        'robot_waits': collected_metrics['robot_waits'],
        'ct_waits': collected_metrics['ct_waits'],
        'idle_per_scanner': average_idle_per_scanner,
        'total_patients': len(arrival_times),
        'completed_scans': len(completed_exams),
        'scanner_events': completed_exams,
    }

# =============================================================================
# ANALYSIS FUNCTIONS - Calculate results from many simulation runs
# =============================================================================

def run_many_simulations(scenario_name):
    """
    Run the simulation many times and average the results.
    This gives us reliable estimates by reducing random variation.
    
    Args:
        scenario_name: Which scenario to simulate
    
    Returns:
        Tuple of (avg_robot_wait, avg_ct_wait, avg_idle_time, avg_total_patients, avg_completed_scans)
    """
    all_robot_waits = []
    all_ct_waits = []
    all_idle_times = []
    all_total_patients = []
    all_completed_scans = []
    
    # Run simulation N_SIM_DAYS times
    for day_num in range(N_SIM_DAYS):
        day_result = simulate_one_day(scenario_name)
        all_robot_waits.extend(day_result['robot_waits'])
        all_ct_waits.extend(day_result['ct_waits'])
        all_idle_times.append(day_result['idle_per_scanner'])
        all_total_patients.append(day_result['total_patients'])
        all_completed_scans.append(day_result['completed_scans'])
    
    # Calculate averages
    avg_robot_wait = statistics.mean(all_robot_waits) if all_robot_waits else 0.0
    avg_ct_wait = statistics.mean(all_ct_waits) if all_ct_waits else 0.0
    avg_idle = statistics.mean(all_idle_times)
    avg_total_patients = statistics.mean(all_total_patients)
    avg_completed_scans = statistics.mean(all_completed_scans)
    
    return avg_robot_wait, avg_ct_wait, avg_idle, avg_total_patients, avg_completed_scans








def calculate_annual_revenue(freed_minutes_per_scanner_per_day):
    """
    Calculate annual revenue from freed scanner capacity.
    
    Logic:
    1. Convert freed minutes to number of scans per year
    2. Only 60% converts to actual new scans (BOOKING_CONVERSION)
    3. Multiply by contribution margin per scan and number of scanners
    
    Args:
        freed_minutes_per_scanner_per_day: How many minutes freed per scanner per day
    
    Returns:
        Annual contribution margin in dollars
    """
    avg_scan_duration_minutes = 12.11
    scans_per_scanner_per_year = (freed_minutes_per_scanner_per_day / avg_scan_duration_minutes) * OPERATING_DAYS_PER_YEAR
    billable_scans = scans_per_scanner_per_year * BOOKING_CONVERSION
    annual_revenue = billable_scans * NUM_SCANNERS * CT_CM_PER_SCAN
    return annual_revenue


def calculate_new_scans_per_day(freed_minutes_per_scanner_per_day):
    """
    Calculate how many additional CT scans we can do per day.
    
    Args:
        freed_minutes_per_scanner_per_day: Freed capacity per scanner per day
    
    Returns:
        Number of new scans per day (float)
    """
    avg_scan_duration_minutes = 12.0
    billable_minutes_per_day = freed_minutes_per_scanner_per_day * BOOKING_CONVERSION
    new_scans = (billable_minutes_per_day * NUM_SCANNERS) / avg_scan_duration_minutes
    return new_scans

# =============================================================================
# MAIN PROGRAM - Run simulations and print results
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*100)
    print("CT SCANNER CAPACITY SIMULATION")
    print("="*100)
    
    # Calculate theoretical (perfect world) time savings from workflow table
    theoretical_baseline_time = get_theoretical_total('baseline')
    theoretical_rovis_only_time = get_theoretical_total('rovis_only')
    theoretical_rovis_workflow_time = get_theoretical_total('rovis_workflow')
    
    # Calculate theoretical savings (if everything was perfect)
    theoretical_savings = {
        "rovis_only": theoretical_baseline_time - theoretical_rovis_only_time,
        "rovis_workflow": theoretical_baseline_time - theoretical_rovis_workflow_time,
    }
    
    # RUN BASELINE SIMULATION
    print(f"\nRunning baseline simulation ({N_SIM_DAYS} days)...")
    baseline_robot_wait, baseline_ct_wait, baseline_idle, baseline_patients, baseline_scans = run_many_simulations("baseline")
    print(f"Baseline idle time per scanner: {baseline_idle:.1f} min/day")
    print(f"Baseline average patients/day: {baseline_patients:.1f} (arriving), {baseline_scans:.1f} (completed)")
    print(f"Theoretical baseline transport time: {theoretical_baseline_time:.1f} min\n")

    # Prepare data for summary tables
    financial_table_data = []
    efficiency_table_data = []
    
    # Add baseline row (no improvements)
    financial_table_data.append({
        "Scenario": "Baseline - Manual Transport",
        "Daily Scans (All 6)": f"{baseline_scans:.1f}",
        "Scans per Day (per scanner)": f"{baseline_scans/6:.1f}",
        "Add'l Scans/Day (per scanner)": "0.0",
        "Add'l Scans/Day (Total)": "0.0",
        "Monthly Add'l CM": "$0",
        "Annual Add'l CM": "$0",
        "Robot Util %": "0.0%",
        "Scanner Util %": f"{(baseline_scans/713.5)*100:.1f}%",
        "Idle per Scanner (min/day)": f"{baseline_idle:.1f}",
    })

    efficiency_table_data.append({
        "Scenario": "Baseline - Manual Transport",
        "Time Saved (min/exam)": "0.0",
        "Daily Scans (All 6)": f"{baseline_scans:.1f}",
        "Add'l Daily Scans": "0.0",
        "Idle per Scanner (min/day)": f"{baseline_idle:.1f}",
        "Scanner Util %": f"{(baseline_scans/713.5)*100:.1f}%",
    })

    # RUN IMPROVEMENT SCENARIOS
    scenarios_to_test = [
        ("rovis_only", "9 Rovis - Transport Only"),
        ("rovis_workflow", "9 Rovis - Transport + Workflow"),
    ]

    for scenario_key, scenario_label in scenarios_to_test:
        print(f"Running {scenario_label} simulation ({N_SIM_DAYS} days)...")
        robot_wait, ct_wait, idle_time, total_patients, completed_scans = run_many_simulations(scenario_key)
        print(f"{scenario_label} idle time per scanner: {idle_time:.1f} min/day")
        print(f"Average patients/day: {total_patients:.1f} (arriving), {completed_scans:.1f} (completed)")
        
        # Calculate actual additional scans from simulation (not theoretical capacity)
        theoretical_time_saved_per_exam = theoretical_savings[scenario_key]
        actual_additional_scans = completed_scans - baseline_scans

        # Financial impact from actual additional scans completed
        daily_additional_cm = actual_additional_scans * CT_CM_PER_SCAN
        monthly_additional_cm = daily_additional_cm * 30  # Monthly estimate

        # Calculate robot utilization
        avg_robot_cycle_time = 20.4  # B1+B2+B3+C1+repositioning (updated with 10min repositioning)
        robot_hours_needed_per_day = (completed_scans * avg_robot_cycle_time) / 60
        robot_hours_available_per_day = NUM_ROBOTS * 24 * ROBOT_UPTIME
        robot_utilization = robot_hours_needed_per_day / robot_hours_available_per_day
        
        # Calculate robot idle time between trsentence to add in brackets that simplifes prior sentnece and dumbs it down for audianeceansports
        transports_per_robot_per_day = completed_scans / NUM_ROBOTS
        if transports_per_robot_per_day > 0:
            minutes_per_transport_cycle = (24 * 60) / transports_per_robot_per_day
            idle_time_between_transports = minutes_per_transport_cycle - avg_robot_cycle_time
        else:
            idle_time_between_transports = 0

        # Add to financial table - showing ACTUAL simulation results
        financial_table_data.append({
            "Scenario": scenario_label,
            "Daily Scans (All 6)": f"{completed_scans:.1f}",
            "Scans per Day (per scanner)": f"{completed_scans/6:.1f}",
            "Add'l Scans/Day (per scanner)": f"{actual_additional_scans/6:.1f}",
            "Add'l Scans/Day (Total)": f"{actual_additional_scans:.1f}",
            "Monthly Add'l CM": f"${monthly_additional_cm:,.0f}",
            "Annual Add'l CM": f"${monthly_additional_cm * 12:,.0f}",
            "Robot Util %": f"{robot_utilization*100:.1f}%",
            "Scanner Util %": f"{(completed_scans/713.5)*100:.1f}%",
            "Idle per Scanner (min/day)": f"{idle_time:.1f}",
        })

        # Show actual simulation results vs theoretical potential
        # Add to efficiency table (actuals only)
        efficiency_table_data.append({
            "Scenario": scenario_label,
            "Time Saved (min/exam)": f"{theoretical_time_saved_per_exam:.1f}",
            "Daily Scans (All 6)": f"{completed_scans:.1f}",
            "Add'l Daily Scans": f"{actual_additional_scans:.1f}",
            "Idle per Scanner (min/day)": f"{idle_time:.1f}",
            "Scanner Util %": f"{(completed_scans/713.5)*100:.1f}%",
        })

    # PRINT SUMMARY TABLES WITH CUSTOM FORMATTING
    print("\n" + "="*171)
    print("TABLE 1: DES-Lite Simulation Results")
    print("="*171)
    print("Note: Baseline 25 scans/day derived from Shands workflow data; transport efficiency improvements calculated from actual workflow timing reductions.")
    print()
    
    # Custom header formatting for Table 1 (throughput/financial/utilization)
    print(f"{'Scenario':<42} {'Daily Scans':<12} {'Scans/Day':<12} {'Add\'l/Day':<15} {'Add\'l/Day':<15} {'Monthly':<12} {'Annual':<13} {'Robot':<8} {'Scanner':<10} {'Idle per':<16}")
    print(f"{'':42} {'(All 6)':<12} {'(per scan)':<12} {'(per scan)':<15} {'(Total)':<15} {'Add\'l':<12} {'Add\'l':<13} {'Util %':<8} {'Util %':<10} {'Scanner (min/day)':<16}")
    print("-"*150)
    
    for row in financial_table_data:
        print(f"{row['Scenario']:<42} {row['Daily Scans (All 6)']:<12} {row['Scans per Day (per scanner)']:<12} {row['Add\'l Scans/Day (per scanner)']:<15} {row['Add\'l Scans/Day (Total)']:<15} {row['Monthly Add\'l CM']:<12} {row['Annual Add\'l CM']:<13} {row['Robot Util %']:<8} {row['Scanner Util %']:<10} {row['Idle per Scanner (min/day)']:<16}")
    
    print("\n" + "="*115)
    print("TABLE 2: WORKFLOW EFFICIENCY & CAPACITY ANALYSIS")
    print("="*115)
    print("(Shows capacity improvements calculated directly from Shands workflow timing data)")
    
    # Custom header formatting for Table 2 with proper column widths
    print(f"{'Scenario':<42} {'Time Saved':<12} {'Daily Scans':<13} {'Add\'l Daily':<12} {'Scanner':<10}")
    print(f"{'':42} {'(min/exam)':<12} {'(All 6)':<13} {'Scans':<12} {'Util %':<10}")
    print("-"*115)
    
    for row in efficiency_table_data:
        print(f"{row['Scenario']:<42} {row['Time Saved (min/exam)']:<12} {row['Daily Scans (All 6)']:<13} {row['Add\'l Daily Scans']:<12} {row['Scanner Util %']:<10}")
    
    print("="*115 + "\n")
