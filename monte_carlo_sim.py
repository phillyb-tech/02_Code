import random
import matplotlib.pyplot as plt
import statistics
import math
import numpy as np

def estimate_labor_savings(num_runs=1000, max_manual_hours=100, turnover_cost_mean=9000, turnover_cost_std=3000, turnover_rate_range=(0.05, 0.3)):
    """
    Simulates labor savings over multiple trials by incorporating 
    10 different operational and cost assumptions, including turnover costs using a normal distribution.

    Args:
        num_runs (int): Number of Monte Carlo simulations to run.
        max_manual_hours (int): Maximum hours required for manual work.
        turnover_cost_mean (float): Mean turnover cost per transporter.
        turnover_cost_std (float): Standard deviation of turnover cost per transporter.
        turnover_rate_range (tuple): Min and max transporter turnover rate.

    Returns:
        list: A list of labor savings (in dollars) for each trial.
    """
    savings_results = []

    for _ in range(num_runs):
        # Define 10 independent cost/operational assumptions with uncertainty

        hourly_wage = random.uniform(15, 30)  # Wage per hour ($15 - $30)
        task_time_manual = random.uniform(5, 15)  # Task time in hours (5-15)
        error_rate_manual = random.uniform(0.02, 0.1)  # Error rate (2%-10%)
        error_rate_auto = random.uniform(0.005, 0.03)  # Automated error rate (0.5%-3%)
        machine_downtime = random.uniform(0.01, 0.2)  # Probability of machine failure (1%-20%)
        maintenance_cost = random.uniform(500, 2000)  # Maintenance cost per year
        material_waste_manual = random.uniform(5, 15)  # Waste % in manual process
        material_waste_auto = random.uniform(1, 5)  # Waste % in automated process
        training_hours = random.uniform(10, 40)  # Training required for automation (10-40 hrs)
        energy_savings = random.uniform(0.1, 0.5)  # Energy reduction (10%-50%)
        
        # New: Transporter turnover costs using normal distribution
        turnover_cost_per_transporter = np.random.normal(turnover_cost_mean, turnover_cost_std)
        # Ensure turnover cost stays within realistic bounds
        turnover_cost_per_transporter = max(2000, min(16000, turnover_cost_per_transporter))
        turnover_rate = random.uniform(*turnover_rate_range)  # Turnover rate (5%-30%)
        turnover_savings = turnover_cost_per_transporter * (1 - turnover_rate)  # Savings from reducing turnover

        # Compute labor savings considering these assumptions
        manual_cost = hourly_wage * task_time_manual
        automated_cost = manual_cost * (1 - random.uniform(0.3, 0.8))  # Automation savings 30%-80%
        error_savings = (error_rate_manual - error_rate_auto) * 1000  # Scaled to impact
        downtime_penalty = machine_downtime * 500  # Downtime has a financial penalty
        waste_savings = (material_waste_manual - material_waste_auto) * 10  # Savings from reduced waste

        # Calculate total estimated labor savings including turnover savings
        labor_saved = (
            (manual_cost - automated_cost) + error_savings - downtime_penalty + 
            waste_savings - training_hours * 10 + energy_savings * 1000 + turnover_savings
        )
        savings_results.append(labor_saved)

    return savings_results

if __name__ == "__main__":
    # Number of Monte Carlo simulations
    simulations = 1000

    # Run the Monte Carlo simulation for labor savings with turnover costs modeled as a normal distribution
    labor_savings = estimate_labor_savings(num_runs=simulations)

    # Calculate statistics
    mean_savings = statistics.mean(labor_savings)
    stdev_savings = statistics.pstdev(labor_savings)

    # 95% Confidence Interval for labor savings
    ci_margin = 1.96 * (stdev_savings / math.sqrt(simulations))
    ci_lower = mean_savings - ci_margin
    ci_upper = mean_savings + ci_margin

    print(f"Out of {simulations} simulations:")
    print(f"  - Average Labor Savings: ${mean_savings:.2f}")
    print(f"  - Standard Deviation: ${stdev_savings:.2f}")
    print(f"  - 95% Confidence Interval for Savings: [${ci_lower:.2f}, ${ci_upper:.2f}]")

    # Create a histogram of labor savings
    plt.figure(figsize=(8, 5))
    plt.hist(labor_savings, bins=25, edgecolor="black", color="skyblue", density=True)
    plt.title("Monte Carlo Simulation: Distribution of Labor Savings (Including Turnover)")
    plt.xlabel("Labor Savings ($)")
    plt.ylabel("Probability Density")
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.show()