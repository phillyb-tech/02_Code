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
# Helper: one lognormal draw with a given average
# -----------------------------
def lognormal_with_mean(mean, sigma): 
    # Return one positive random number whose average (over many draws)
    # will be about `mean`. `sigma` controls spread (bigger -> more variation)
    mu = math.log(mean) - 0.5 * sigma**2
    return random.lognormvariate(mu, sigma)

# -----------------------------
# Define Delay Functions (in minutes)
# -----------------------------
def delay_baseline():
    # Baseline total delay ~ 79 minutes on average
    return lognormal_with_mean(79, 0.5)

def delay_rovex_transport_ideal():
    # Improved transport only: about 68 minutes on average
    return lognormal_with_mean(68, 0.4)

def delay_rovex_workflow_ideal():
    # Improved transport + workflow: about 51 minutes on average
    return lognormal_with_mean(51, 0.35)

def delay_rovex_transport_uptime():
    # Mixture for transport-only scenario with 80% uptime. With prob 0.8, use improved (68); with prob 0.2, use baseline (79).
    if random.random() < ROBOT_UPTIME:
        return delay_rovex_transport_ideal()
    else:
        return delay_baseline()

def delay_rovex_workflow_uptime():
    # Mixture for transport + workflow scenario with 80% uptime. With prob 0.8, use improved (51); with prob 0.2, use baseline (79).
    if random.random() < ROBOT_UPTIME:
        return delay_rovex_workflow_ideal()
    else:
        return delay_baseline()

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
  # Simulate a single day for one CT scanner using the provided delay function (baseline or Rovis scenario). Returns the total idle minutes that day.
    schedule_interval = DAY_LENGTH_MIN / EXAMS_PER_DAY_PER_SCANNER  # 60 min
    ct_free = 0.0          # when the scanner becomes free
    idle = 0.0             # accumulated idle minutes for the day

    for i in range(EXAMS_PER_DAY_PER_SCANNER):
        sched = i * schedule_interval   # Planned schedule time (0, 60, 120, ..., 660)

        # Draw stochastic components
        delay = delay_fn()              # transport delay D_i
        dur   = exam_duration()         # exam duration T_i
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
#  Run the single-day simulation n_days times and return the average idle minutes per day per scanner.
    idles = [simulate_day(delay_fn) for _ in range(n_days)]
    return statistics.mean(idles)

# -----------------------------
# Compute average idle for each scenario
# -----------------------------
baseline_idle = run_avg_idle(delay_baseline)
rovex_idle    = run_avg_idle(delay_rovex_transport_uptime)
workflow_idle = run_avg_idle(delay_rovex_workflow_uptime)

print("Average idle minutes per day per scanner:")
print(f"  Baseline:              {baseline_idle:.1f} min/day")
print(f"  6 Rovis – Transport:   {rovex_idle:.1f} min/day")
print(f"  6 Rovis + Workflow:    {workflow_idle:.1f} min/day")

# -----------------------------
# Helper to convert freed minutes -> contribution margin (CM)
# -----------------------------
def annual_cm_from_freed(freed_min_per_scanner):
# Convert 'freed' idle minutes per day per scanner into   annual contribution margin (USD) from outpatient CTs.
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
    ("6 Rovis – Transport Only (80% uptime)", rovex_idle),
    ("6 Rovis – Transport + Workflow (80% uptime)", workflow_idle)
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
