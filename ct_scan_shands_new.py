import math
import random
import statistics
import pandas as pd

# -----------------------------
# Global assumptions
# -----------------------------
random.seed(42)  # Fix the random number generator so the script produces the same "random" draws every run with options

NUM_SCANNERS = 6
EXAMS_PER_DAY_PER_SCANNER = 12          # ~72 inpatient CT/day total
DAY_LENGTH_MIN = 12 * 60                # 12-hour CT day
OPERATING_DAYS_PER_YEAR = 360

CT_CM_PER_HOUR = 2419                   # CT contribution margin per hour (USD)
BOOKING_CONVERSION = 0.40               # 40% of freed minutes become outpatient exams
ROBOT_UPTIME = 0.80                     # 80% of exams see improved delay; 20% baseline

N_SIM_DAYS = 1000                       # Monte Carlo replications

# -----------------------------
# Step mean assumptions (minutes)
# Updated from new workflow table: Baseline, Rovis Only, Rovis + Workflow
# -----------------------------
STEP_MEANS = {
    'P': {'baseline': 27.4, 'rovis_only': 27.4, 'rovis_workflow': 27.4},
    'A': {'baseline': 52.0, 'rovis_only': 52.0, 'rovis_workflow': 35.0},
    'B1': {'baseline': 11.8, 'rovis_only': 2.95, 'rovis_workflow': 2.95},
    'B2': {'baseline': 3.8, 'rovis_only': 0.95, 'rovis_workflow': 0.95},
    'B3': {'baseline': 6.5, 'rovis_only': 3.3, 'rovis_workflow': 3.3},
    'C1': {'baseline': 5.0, 'rovis_only': 5.0, 'rovis_workflow': 5.0},
    'C2': {'baseline': 1.6, 'rovis_only': 1.6, 'rovis_workflow': 1.6},
    'C3': {'baseline': 12.1, 'rovis_only': 12.1, 'rovis_workflow': 12.1},
}

# Sigmas for lognormal sampling (controls spread)
STEP_SIGMA = {
    'A': 0.35,
    'B1': 0.4,
    'B2': 0.4,
    'B3': 0.4,
    'C1': 0.2,
    'C2': 0.2,
    'C3': 0.25,
}

# -----------------------------
# Helper: one lognormal draw with a given average
# -----------------------------
def lognormal_with_mean(mean, sigma):
    # Return one positive random number whose average (over many draws)
    # will be about `mean`. `sigma` controls spread (bigger -> more variation)
    mu = math.log(mean) - 0.5 * sigma**2
    return random.lognormvariate(mu, sigma)

def draw_step(step, scenario):
    """Return one draw for the named step in the given scenario using lognormal_with_mean."""
    mean = STEP_MEANS[step].get(scenario, 1.0)
    sigma = STEP_SIGMA.get(step, 0.4)
    return lognormal_with_mean(mean, sigma)

# -----------------------------
# Define Delay Functions (in minutes)
# A + B1 + B2 + B3 + C1 + C2 (does NOT include exam duration C3)
# -----------------------------
def delay_baseline():
    # Baseline: all steps at baseline means
    return (draw_step('A', 'baseline') + draw_step('B1', 'baseline') +
            draw_step('B2', 'baseline') + draw_step('B3', 'baseline') +
            draw_step('C1', 'baseline') + draw_step('C2', 'baseline'))

def delay_rovex_transport_ideal():
    # Rovis Transport-only ideal: use rovis_only means (B1-B2 at 75% reduction, B3 at 50%)
    return (draw_step('A', 'rovis_only') + draw_step('B1', 'rovis_only') +
            draw_step('B2', 'rovis_only') + draw_step('B3', 'rovis_only') +
            draw_step('C1', 'rovis_only') + draw_step('C2', 'rovis_only'))

def delay_rovex_workflow_ideal():
    # Rovis + Workflow ideal: use rovis_workflow means (A reduced to 35, B1-B2 at 75% reduction, B3 at 50%)
    return (draw_step('A', 'rovis_workflow') + draw_step('B1', 'rovis_workflow') +
            draw_step('B2', 'rovis_workflow') + draw_step('B3', 'rovis_workflow') +
            draw_step('C1', 'rovis_workflow') + draw_step('C2', 'rovis_workflow'))

def delay_rovex_transport_uptime():
    # Transport-only scenario with 80% uptime.
    # With prob ROBOT_UPTIME: use improved (rovis_only), else use baseline
    if random.random() < ROBOT_UPTIME:
        return delay_rovex_transport_ideal()
    else:
        return delay_baseline()

def delay_rovex_workflow_uptime():
    # Workflow scenario with 80% uptime.
    # With prob ROBOT_UPTIME: use improved (rovis_workflow), else fallback
    if random.random() < ROBOT_UPTIME:
        return delay_rovex_workflow_ideal()
    else:
        # Fallback: A at reduced 35, B steps at baseline
        return (draw_step('A', 'rovis_workflow') + draw_step('B1', 'baseline') +
                draw_step('B2', 'baseline') + draw_step('B3', 'baseline') +
                draw_step('C1', 'baseline') + draw_step('C2', 'baseline'))

# -----------------------------
# Exam duration model (minutes)
# Shands-based: CT Start→End ≈ 12 min average
# -----------------------------
def exam_duration():
    # Draw a CT exam time ~ Normal(12,3) but keep it between 5 and 25 minutes
    while True:
        x = random.gauss(12, 3)
        if 5 <= x <= 25:
            return x

# -----------------------------
# Simulate one CT scanner for one day
# -----------------------------
def simulate_day(delay_fn):
    # Simulate a single day for one CT scanner using the provided delay function (baseline or Rovis scenario).
    # Returns the total idle minutes that day.
    schedule_interval = DAY_LENGTH_MIN / EXAMS_PER_DAY_PER_SCANNER  # 60 min
    ct_free = 0.0          # when the scanner becomes free
    idle = 0.0             # accumulated idle minutes for the day

    for i in range(EXAMS_PER_DAY_PER_SCANNER):
        sched = i * schedule_interval   # Planned schedule time (0, 60, 120, ..., 660)

        # Draw stochastic components
        delay = delay_fn()              # transport delay D_i (A+B1+B2+B3+C1+C2)
        dur   = exam_duration()         # exam duration T_i (C3)
        arrival = sched + delay         # Patient arrival time at CT
        start = max(arrival, ct_free)   # CT start time = max(arrival, when scanner is free)
      
        if start > ct_free:             # Idle time is any gap between ct_free and start
            idle += (start - ct_free)
      
        ct_free = start + dur           # Exam ends after duration

    return idle

# -----------------------------
# Run many simulated days and return the average idle minutes
# -----------------------------
def run_avg_idle(delay_fn, n_days=N_SIM_DAYS):
    # Run the single-day simulation n_days times and return the average idle minutes per day per scanner.
    idles = [simulate_day(delay_fn) for _ in range(n_days)]
    return statistics.mean(idles)

# -----------------------------
# Compute average idle for each scenario
# -----------------------------
baseline_idle = run_avg_idle(delay_baseline)
rovex_idle    = run_avg_idle(delay_rovex_transport_uptime)
workflow_idle = run_avg_idle(delay_rovex_workflow_uptime)

# -----------------------------
# Helper to convert freed minutes -> contribution margin (CM)
# -----------------------------
def annual_cm_from_freed(freed_min_per_scanner):
    # Convert 'freed' idle minutes per day per scanner into annual contribution margin (USD) from outpatient CTs.
    # Across all scanners
    freed_min_all = freed_min_per_scanner * NUM_SCANNERS

    # Only a fraction becomes booked outpatient time
    booked_min_per_day = freed_min_all * BOOKING_CONVERSION

    # Annual booked hours
    booked_hours_year = (booked_min_per_day / 60) * OPERATING_DAYS_PER_YEAR

    # Contribution margin
    return booked_hours_year * CT_CM_PER_HOUR

# -----------------------------
# Build summary table
# -----------------------------
rows = []

# Baseline (no freed idle)
rows.append({
    "Scenario": "Baseline – Manual Transport",
    "Freed Idle Min/Day per Scanner": 0.0,
    "Freed Idle Min/Day (6 CTs)": 0.0,
    "Monthly Imaging CM (CT)": 0
})

for name, idle in [
    ("Rovis – Transport Only (80% uptime)", rovex_idle),
    ("Rovis + Workflow (80% uptime)", workflow_idle)
]:
    freed_per_scanner = max(0.0, baseline_idle - idle)      # minutes freed per scanner
    freed_all = freed_per_scanner * NUM_SCANNERS            # minutes freed across all scanners
    annual_cm = annual_cm_from_freed(freed_per_scanner)     # dollars per year
    monthly_cm = annual_cm / 12.0                           # dollars per month

    rows.append({
        "Scenario": name,
        "Freed Idle Min/Day per Scanner": round(freed_per_scanner, 1),
        "Freed Idle Min/Day (6 CTs)": round(freed_all, 1),
        "Monthly Imaging CM (CT)": round(monthly_cm, 0)
    })

summary_df = pd.DataFrame(rows)
print("\nOutput Summary Table:")
print(summary_df.to_string(index=False))
