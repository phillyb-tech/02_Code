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
# Four scenarios (all modeled on eligible patients; eligibility baked into demand cap):
# 1. Baseline: Manual patient transport (current state)
# 2. Rovis Only: Robots help with transport coordination
# 3. Rovis + Workflow: Robots + improved hospital workflows
# 4. Workflow Only: Human transport, but faster workflow step A

random.seed(42)  # Makes results repeatable

# =============================================================================
# HOSPITAL CONFIGURATION - How many resources we have
# =============================================================================
NUM_SCANNERS = 3                    # Total CT scanners available
NUM_ROBOTS = 6                      # Number of transport robots (2:1 bots to scanners)
DAY_LENGTH_MIN = 24 * 60           # 24-hour operation in minutes
OPERATING_DAYS_PER_YEAR = 360      # Days hospital operates per year
LOW_ACUITY_FRACTION = 1.0          # Eligibility already baked into demand cap (263/day reflects 86.9% eligible)
SCANNER_UPTIME = 0.90              # Scanners available 90% of the day (10% downtime for QA/cleaning/maintenance)
TURNOVER_MINUTES = 4.0             # Turnover/setup time per exam while scanner is occupied

# =============================================================================
# FINANCIAL ASSUMPTIONS - Money calculations
# =============================================================================
CT_CM_PER_SCAN = 331               # Contribution margin per CT scan (ED + inpatient only)
BOOKING_CONVERSION = 0.60          # 60% of freed time converts to new scans (moderate absorption)
ROBOT_UPTIME = 0.80                # Robots work 80% of the time (20% downtime)

N_SIM_DAYS = 100                  # Run simulation 100 times for testing (change back to 1000 for final results)

# =============================================================================
# WORKFLOW-DERIVED CAPACITY MODEL - Calculate capacity from actual workflow times
# =============================================================================
# No artificial demand constraints - let workflow efficiency determine capacity
# Baseline capacity calculated from actual Shands workflow times
SCANNER_HOURS_PER_DAY = DAY_LENGTH_MIN       # Nominal minutes per scanner per day
AVG_SCAN_DURATION = 12.11                    # Minutes per scan (from C3 step)
# Max capacity per day using full 24h clock (downtime effects reflected in numerator via blocked time)
MAX_SCANNER_CAPACITY = (SCANNER_HOURS_PER_DAY * NUM_SCANNERS) / AVG_SCAN_DURATION

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
    'B3': {'baseline': 6.55, 'rovis_only': 4.39, 'rovis_workflow': 4.39},      # B3: Acknowledge → transport start (patient prep delay)
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

# Add workflow-only scenario: copy baseline timings and set A to 35 minutes
for _step_name in STEP_ORDER:
    STEP_MEANS[_step_name]['wf_only'] = STEP_MEANS[_step_name]['baseline']
STEP_MEANS['A']['wf_only'] = 35.0

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
    - Baseline: 150 scans/day cap (eligible ED + inpatient)
    - Robot scenarios: Improved efficiency allows more throughput
    
    Args:
        scenario_name: Which scenario we're simulating
    
    Returns:
        List of arrival times (in minutes from start of day)
    """
    
    # Calculate daily processing capacity from workflow times
    # Start with known baseline: 150 CT scans per day (eligible ED + inpatient cap)
    baseline_daily_capacity = 150.0
    
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
        # Actual capacity = min(workflow-derived capacity, physical scanner limit)
        daily_patients = min(improved_daily_capacity, MAX_SCANNER_CAPACITY)

    # Apply low-acuity eligibility filter (apples-to-apples across all scenarios)
    daily_patients *= LOW_ACUITY_FRACTION
    
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
# SCANNER DOWNTIME MODEL - Simple fixed downtime per scanner
# =============================================================================

def apply_scanner_downtime(env, scanners, downtime_minutes):
    """
    Block one scanner for a contiguous downtime window within the day.
    Downtime start is randomized; duration is fixed.
    """
    if downtime_minutes <= 0:
        return
    start = random.uniform(0, max(0.0, DAY_LENGTH_MIN - downtime_minutes))
    yield env.timeout(start)
    with scanners.request() as req:
        yield req
        yield env.timeout(downtime_minutes)

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
    if scenario_name in ("baseline", "wf_only"):
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
            robot_use_start = env.now
            
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
            # Track robot busy time
            collected_metrics.setdefault('robot_busy', 0.0)
            collected_metrics['robot_busy'] += robot_time
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
        total_scanner_time = exam_time + TURNOVER_MINUTES  # include turnover/setup while scanner is occupied
        scanner_events[-1]['end'] = time_when_ct_starts + total_scanner_time
        yield env.timeout(total_scanner_time)


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
    robots = None if scenario_name in ("baseline", "wf_only") else simpy.Resource(env, capacity=NUM_ROBOTS)

    # Storage for collected data
    collected_metrics = {'robot_waits': [], 'ct_waits': []}
    scanner_events = []
    robot_busy_minutes = 0.0

    # Generate patient arrivals based on workflow-derived processing capacity
    arrival_times = generate_patient_arrivals_workflow_derived(scenario_name)

    # Block each scanner for planned/unplanned downtime (10% of day) at a random time
    downtime_minutes = DAY_LENGTH_MIN * (1.0 - SCANNER_UPTIME)
    for _ in range(NUM_SCANNERS):
        env.process(apply_scanner_downtime(env, scanners, downtime_minutes))
    
    # Schedule all patients based on their arrival times
    for patient_id, arrival_time in enumerate(arrival_times):
        env.process(simulate_one_patient(
            env, patient_id, arrival_time, scanners, robots,
            scenario_name, collected_metrics, scanner_events
        ))

    # Run the simulation (full day + 4 hours buffer)
    env.run(until=DAY_LENGTH_MIN + 240)

    # Calculate scanner idle time using "pooled scheduling" approach
    # This assigns each exam to whichever scanner becomes free first
    completed_exams = [e for e in scanner_events if 'start' in e and 'end' in e]
    completed_exams.sort(key=lambda x: x['start'])  # Sort by start time

    # Track when each scanner will be free
    scanner_free_times = [0.0] * NUM_SCANNERS
    total_idle_time = 0.0
    busy_minutes = [0.0] * NUM_SCANNERS
    
    for exam in completed_exams:
        # Find which scanner is free earliest
        earliest_free_scanner = scanner_free_times.index(min(scanner_free_times))
        
        # Calculate idle gap before this exam
        idle_gap = max(0.0, exam['start'] - scanner_free_times[earliest_free_scanner])
        total_idle_time += idle_gap
        
        # Update when this scanner will be free again
        scanner_free_times[earliest_free_scanner] = exam['end']
        exam['scanner'] = earliest_free_scanner
        busy_minutes[earliest_free_scanner] += (exam['end'] - exam['start'])
    # Add tail idle time up to the 24h mark (ignore buffer beyond the day)
    for ft in scanner_free_times:
        total_idle_time += max(0.0, DAY_LENGTH_MIN - ft)

    average_idle_per_scanner = total_idle_time / NUM_SCANNERS
    available_time_per_scanner = max(0.0, DAY_LENGTH_MIN - downtime_minutes)
    util_per_scanner = []
    for b in busy_minutes:
        util_per_scanner.append((b / available_time_per_scanner) * 100 if available_time_per_scanner > 0 else 0.0)
    avg_scanner_util_percent = statistics.mean(util_per_scanner) if util_per_scanner else 0.0

    return {
        'robot_waits': collected_metrics['robot_waits'],
        'ct_waits': collected_metrics['ct_waits'],
        'idle_per_scanner': average_idle_per_scanner,
        'total_patients': len(arrival_times),
        'completed_scans': len(completed_exams),
        'scanner_events': completed_exams,
        'avg_scanner_util': avg_scanner_util_percent,
        'robot_busy_minutes': collected_metrics.get('robot_busy', 0.0) if robots else 0.0,
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
    all_scanner_utils = []
    all_robot_busy = []
    
    # Run simulation N_SIM_DAYS times
    for day_num in range(N_SIM_DAYS):
        day_result = simulate_one_day(scenario_name)
        all_robot_waits.extend(day_result['robot_waits'])
        all_ct_waits.extend(day_result['ct_waits'])
        all_idle_times.append(day_result['idle_per_scanner'])
        all_total_patients.append(day_result['total_patients'])
        all_completed_scans.append(day_result['completed_scans'])
        all_scanner_utils.append(day_result['avg_scanner_util'])
        all_robot_busy.append(day_result['robot_busy_minutes'])
    
    # Calculate averages
    avg_robot_wait = statistics.mean(all_robot_waits) if all_robot_waits else 0.0
    avg_ct_wait = statistics.mean(all_ct_waits) if all_ct_waits else 0.0
    avg_idle = statistics.mean(all_idle_times)
    avg_total_patients = statistics.mean(all_total_patients)
    avg_completed_scans = statistics.mean(all_completed_scans)
    avg_scanner_util = statistics.mean(all_scanner_utils) if all_scanner_utils else 0.0
    avg_robot_busy = statistics.mean(all_robot_busy) if all_robot_busy else 0.0
    scenario_has_robots = scenario_name.startswith("rovis")
    robot_available = DAY_LENGTH_MIN * NUM_ROBOTS if scenario_has_robots else 0.0
    avg_robot_util = (avg_robot_busy / robot_available) * 100 if robot_available > 0 else 0.0
    
    return avg_robot_wait, avg_ct_wait, avg_idle, avg_total_patients, avg_completed_scans, avg_scanner_util, avg_robot_util








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
    theoretical_wf_only_time = get_theoretical_total('wf_only')
    
    # Calculate theoretical savings (if everything was perfect)
    theoretical_savings = {
        "rovis_only": theoretical_baseline_time - theoretical_rovis_only_time,
        "rovis_workflow": theoretical_baseline_time - theoretical_rovis_workflow_time,
        "wf_only": theoretical_baseline_time - theoretical_wf_only_time,
    }
    
    # RUN BASELINE SIMULATION
    print(f"\nRunning baseline simulation ({N_SIM_DAYS} days)...")
    baseline_robot_wait, baseline_ct_wait, baseline_idle, baseline_patients, baseline_scans, baseline_scanner_util, baseline_robot_util = run_many_simulations("baseline")
    print(f"Baseline idle time per scanner: {baseline_idle:.1f} min/day")
    print(f"Baseline average patients/day: {baseline_patients:.1f} (arriving), {baseline_scans:.1f} (completed)")
    print(f"Theoretical baseline transport time: {theoretical_baseline_time:.1f} min\n")

    # Column labels and shared helpers
    daily_scans_label = f"Daily Scans (All {NUM_SCANNERS})"
    per_scanner_label = "Scans per Day (per scanner)"
    addl_per_scanner_label = "Add'l Scans/Day (per scanner)"
    all_scanners_header = f"(All {NUM_SCANNERS})"

    # Prepare data for summary tables
    financial_table_data = []
    efficiency_table_data = []
    
    # Add baseline row (no improvements)
    financial_table_data.append({
        "Scenario": "Baseline - Manual Transport",
        daily_scans_label: f"{baseline_scans:.1f}",
        per_scanner_label: f"{baseline_scans/NUM_SCANNERS:.1f}",
        addl_per_scanner_label: "0.0",
        "Add'l Scans/Day (Total)": "0.0",
        "Monthly Add'l CM": "$0",
        "Annual Add'l CM": "$0",
        "Robot Util %": "0.0%",
        "Scanner Util %": f"{baseline_scanner_util:.1f}%",
        "Idle per Scanner (min/day)": f"{baseline_idle:.1f}",
    })

    efficiency_table_data.append({
        "Scenario": "Baseline - Manual Transport",
        "Time Saved (min/exam)": "0.0",
        daily_scans_label: f"{baseline_scans:.1f}",
        "Add'l Daily Scans": "0.0",
        "Idle per Scanner (min/day)": f"{baseline_idle:.1f}",
        "Scanner Util %": f"{(baseline_scans/MAX_SCANNER_CAPACITY)*100:.1f}%",
    })

    # RUN IMPROVEMENT SCENARIOS
    scenarios_to_test = [
        ("rovis_only", "6 Bots - Transport Only"),
        ("rovis_workflow", "6 Bots - Transport + Workflow"),
        ("wf_only", "Workflow Only (A faster)"),
    ]

    for scenario_key, scenario_label in scenarios_to_test:
        # Run scenario (suppress per-scenario chatter; results go into tables below)
        robot_wait, ct_wait, idle_time, total_patients, completed_scans, scanner_util, robot_util = run_many_simulations(scenario_key)
        
        # Calculate actual additional scans from simulation (not theoretical capacity)
        theoretical_time_saved_per_exam = theoretical_savings[scenario_key]
        actual_additional_scans = completed_scans - baseline_scans

        # Financial impact from actual additional scans completed
        daily_additional_cm = actual_additional_scans * CT_CM_PER_SCAN
        monthly_additional_cm = daily_additional_cm * 30  # Monthly estimate

        # Add to financial table - showing ACTUAL simulation results
        financial_table_data.append({
            "Scenario": scenario_label,
            daily_scans_label: f"{completed_scans:.1f}",
            per_scanner_label: f"{completed_scans/NUM_SCANNERS:.1f}",
            addl_per_scanner_label: f"{actual_additional_scans/NUM_SCANNERS:.1f}",
            "Add'l Scans/Day (Total)": f"{actual_additional_scans:.1f}",
            "Monthly Add'l CM": f"${monthly_additional_cm:,.0f}",
            "Annual Add'l CM": f"${monthly_additional_cm * 12:,.0f}",
            "Robot Util %": f"{robot_util:.1f}%",
            "Scanner Util %": f"{scanner_util:.1f}%",
            "Idle per Scanner (min/day)": f"{idle_time:.1f}",
        })

        # Show actual simulation results vs theoretical potential
        # Add to efficiency table (actuals only)
        efficiency_table_data.append({
            "Scenario": scenario_label,
            "Time Saved (min/exam)": f"{theoretical_time_saved_per_exam:.1f}",
            daily_scans_label: f"{completed_scans:.1f}",
            "Add'l Daily Scans": f"{actual_additional_scans:.1f}",
            "Idle per Scanner (min/day)": f"{idle_time:.1f}",
            "Scanner Util %": f"{scanner_util:.1f}%",
        })

    # PRINT SUMMARY TABLES WITH CUSTOM FORMATTING
    print("\n" + "="*110)
    print("TABLE 1: DES-Lite Simulation Results")
    print("="*110)
    print("Note: Baseline 150 scans/day cap (eligible ED + inpatient) with 86.9% standard-transport eligibility; transport efficiency improvements calculated from actual workflow timing reductions.")
    print()

    # Column widths to keep table aligned even with large dollar figures
    w = {
        "scenario": 32,
        "daily": 10,
        "per_scan": 13,
        "addl_per": 13,
        "addl_total": 12,
        "monthly": 13,
        "annual": 15,
        "robot": 8,
        "scanner": 9,
        "idle": 10,
    }
    # Two-line header for readability while keeping rows tight
    print(
        f"{'Scenario':<{w['scenario']}}"
        f"{'Daily':>{w['daily']}}"
        f"{'Scans/Day':>{w['per_scan']}}"
        f"{'Addl/Day':>{w['addl_per']}}"
        f"{'Addl/Day':>{w['addl_total']}}"
        f"{'Monthly':>{w['monthly']}}"
        f"{'Annual':>{w['annual']}}"
        f"{'Robot':>{w['robot']}}"
        f"{'Scanner':>{w['scanner']}}"
        f"{'Idle':>{w['idle']}}"
    )
    print(
        f"{'':<{w['scenario']}}"
        f"{all_scanners_header:>{w['daily']}}"
        f"{'(per scanner)':>{w['per_scan']}}"
        f"{'(per scanner)':>{w['addl_per']}}"
        f"{'(Total)':>{w['addl_total']}}"
        f"{'Addl CM':>{w['monthly']}}"
        f"{'Addl CM':>{w['annual']}}"
        f"{'Util %':>{w['robot']}}"
        f"{'Util %':>{w['scanner']}}"
        f"{'min/day':>{w['idle']}}"
    )
    print('-'*140)

    for row in financial_table_data:
        scenario = row["Scenario"]
        daily = row[daily_scans_label]
        per_scanner = row[per_scanner_label]
        addl_per = row[addl_per_scanner_label]
        addl_total = row["Add'l Scans/Day (Total)"]
        monthly = row["Monthly Add'l CM"]
        annual = row["Annual Add'l CM"]
        robot = row["Robot Util %"]
        scanner = row["Scanner Util %"]
        idle = row["Idle per Scanner (min/day)"]
        print(
            f"{scenario:<{w['scenario']}}"
            f"{daily:>{w['daily']}}"
            f"{per_scanner:>{w['per_scan']}}"
            f"{addl_per:>{w['addl_per']}}"
            f"{addl_total:>{w['addl_total']}}"
            f"{monthly:>{w['monthly']}}"
            f"{annual:>{w['annual']}}"
            f"{robot:>{w['robot']}}"
            f"{scanner:>{w['scanner']}}"
            f"{idle:>{w['idle']}}"
        )
    print("\n" + "="*110)
    print("TABLE 2: WORKFLOW EFFICIENCY & CAPACITY ANALYSIS")
    print("="*110)
    print("(Shows capacity improvements calculated directly from Shands workflow timing data; all scenarios use eligibility baked into demand cap)") 
    
    # Custom header formatting for Table 2 with proper column widths
    print(f"{'Scenario':<42} {'Time Saved':<12} {'Daily Scans':<13} {'Add\'l Daily':<12} {'Scanner':<10}")
    print(f"{'':42} {'(min/exam)':<12} {all_scanners_header:<13} {'Scans':<12} {'Util %':<10}")
    print("-"*130)
    
    for row in efficiency_table_data:
        print(f"{row['Scenario']:<42} {row['Time Saved (min/exam)']:<12} {row[daily_scans_label]:<13} {row['Add\'l Daily Scans']:<12} {row['Scanner Util %']:<10}")
    
    print("="*130 + "\n")
