import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
from scipy.stats import lognorm, norm
from matplotlib.ticker import FuncFormatter
import time  # Import the time module

# Monte Carlo simulation parameters
num_simulations = 10000  # Increased number of simulations for more stable results

# Log-normal distribution parameters for transporter wage rate
transporter_wage_rate_mean = 25.08
transporter_wage_rate_min = 15.58
transporter_wage_rate_max = 40.39

# Estimate mu and sigma for the log-normal distribution of transporter wage rate
mu_transporter_wage_rate = np.log(transporter_wage_rate_mean)
sigma_transporter_wage_rate = (np.log(transporter_wage_rate_max) - np.log(transporter_wage_rate_min)) / 6  # Increased sigma for more right skew

# Log-normal distribution parameters for OT wage rate
ot_wage_rate_mean = 37.62
ot_wage_rate_min = 23.70
ot_wage_rate_max = 60.5850

# Estimate mu and sigma for the log-normal distribution of OT wage rate
mu_ot_wage_rate = np.log(ot_wage_rate_mean)
sigma_ot_wage_rate = (np.log(ot_wage_rate_max) - np.log(ot_wage_rate_min)) / 4  # Example: change from /6 to /4

# Log-normal distribution parameters for OT hours per transporter
mean_ot_hours = 1.33
std_dev_ot_hours = 0.4 * mean_ot_hours  # Restored to original value

# Estimate mu and sigma for the log-normal distribution of OT hours per transporter
sigma_ln_ot_hours = np.sqrt(np.log(1 + (std_dev_ot_hours / mean_ot_hours)**2))
mu_ln_ot_hours = np.log(mean_ot_hours) - 0.5 * sigma_ln_ot_hours**2

# Log-normal distribution parameters for benefits rate
mean_benefits_rate = 0.30
std_dev_benefits_rate = 0.5 * mean_benefits_rate  # Restored to original value

# Estimate mu and sigma for the log-normal distribution of benefits rate
sigma_ln_benefits_rate = np.sqrt(np.log(1 + (std_dev_benefits_rate / mean_benefits_rate)**2))
mu_ln_benefits_rate = np.log(mean_benefits_rate) - 0.5 * sigma_ln_benefits_rate**2

# Log-normal distribution parameters for turnover cost
mean_turnover_cost = 8100
std_dev_turnover_cost = 0.75 * mean_turnover_cost  # Restored to original value

# Estimate mu and sigma for the log-normal distribution of turnover cost
sigma_ln_turnover_cost = np.sqrt(np.log(1 + (std_dev_turnover_cost / mean_turnover_cost)**2))
mu_ln_turnover_cost = np.log(mean_turnover_cost) - 0.5 * sigma_ln_turnover_cost**2

# Log-normal distribution parameters for turnover rate
mean_turnover_rate = 0.25
std_dev_turnover_rate = 0.75 * mean_turnover_rate  # Restored to original value

# Estimate mu and sigma for the log-normal distribution of turnover rate
sigma_ln_turnover_rate = np.sqrt(np.log(1 + (std_dev_turnover_rate / mean_turnover_rate)**2))
mu_ln_turnover_rate = np.log(mean_turnover_rate) - 0.5 * sigma_ln_turnover_rate**2

# Set a random seed for reproducibility
np.random.seed(42)

# Input variables
avg_transporters_baseline = 18
avg_transporters_automation = 12
shifts_per_day = 3
hours_per_shift = 8

rovex_opex = -618553

# Lists to store simulation results
yearly_cost_savings_list = []

# Start tracking time
start_time = time.time()

for _ in range(num_simulations):
    # Sample transporter_wage_rate from a log-normal distribution
    transporter_wage_rate = lognorm(sigma_transporter_wage_rate, scale=np.exp(mu_transporter_wage_rate)).rvs()
    # Ensure the sampled value is within the specified range
    transporter_wage_rate = max(transporter_wage_rate_min, min(transporter_wage_rate, transporter_wage_rate_max))

    # Sample ot_wage_rate from a log-normal distribution
    ot_wage_rate = lognorm(sigma_ot_wage_rate, scale=np.exp(mu_ot_wage_rate)).rvs()
    # Ensure the sampled value is within the specified range
    ot_wage_rate = max(ot_wage_rate_min, min(ot_wage_rate, ot_wage_rate_max))

    # Sample ot_hours_per_transporter from a log-normal distribution
    ot_hours_per_transporter = lognorm(sigma_ln_ot_hours, scale=np.exp(mu_ln_ot_hours)).rvs()

    # Sample benefits_rate from a log-normal distribution
    benefits_rate = lognorm(sigma_ln_benefits_rate, scale=np.exp(mu_ln_benefits_rate)).rvs()

    # Sample turnover_cost_average from a log-normal distribution
    turnover_cost_average = lognorm(sigma_ln_turnover_cost, scale=np.exp(mu_ln_turnover_cost)).rvs()

    # Sample turnover_rate from a log-normal distribution
    turnover_rate = lognorm(sigma_ln_turnover_rate, scale=np.exp(mu_ln_turnover_rate)).rvs()

    # Baseline calculations
    avg_transporter_hours_per_day_baseline = hours_per_shift * shifts_per_day * avg_transporters_baseline 
    total_transporter_hours_per_year_baseline = avg_transporter_hours_per_day_baseline * 5 * 52
    total_transporter_wage_baseline = total_transporter_hours_per_year_baseline * transporter_wage_rate
    total_benefits_baseline = benefits_rate * total_transporter_wage_baseline
    staffing_cost_baseline = total_transporter_wage_baseline + total_benefits_baseline

    # Calculate OT hours per week for baseline
    ot_hour_per_week_baseline = ot_hours_per_transporter * avg_transporters_baseline
    ot_cost_baseline = ot_hour_per_week_baseline * 52 * ot_wage_rate

    # Automation calculations
    avg_transporter_hours_per_day_automation = hours_per_shift * shifts_per_day * avg_transporters_automation
    total_transporter_hours_per_year_automation = avg_transporter_hours_per_day_automation * 5 * 52
    total_transporter_wage_automation = total_transporter_hours_per_year_automation * transporter_wage_rate
    total_benefits_automation = benefits_rate * total_transporter_wage_automation
    staffing_cost_automation = total_transporter_wage_automation + total_benefits_automation

    # Calculate OT hours per week for automation
    ot_hour_per_week_automation = ot_hours_per_transporter * avg_transporters_automation
    ot_cost_automation = ot_hour_per_week_automation * 52 * ot_wage_rate

    # Creating and displaying hospital sizing table
    large_sample_hospital_transporters = round(1111 * (70 / 1109), 5)
    large_sample_hospital_ratio = 70 / avg_transporters_baseline  # Dynamically computed ratio

    hospital_sizing_data = {
        "Hospital": ["UPenn", "Large Sample Hospital"],
        "# of Hospital Beds": [1109, 1111],
        "Average # of Transporters per Shift": [18, 18],
        "# Transporters on Payroll": [round(70, 5), large_sample_hospital_transporters],
        "Transporters on Payroll / # Hospital Beds": [round(70/1109, 5), round(large_sample_hospital_transporters/1111, 5)],
        "Transporters on Payroll / Transporters per Shift": [round(70/18, 5), round(large_sample_hospital_transporters/18, 5)]
    }

    hospital_sizing_df = pd.DataFrame(hospital_sizing_data)

    # Using the value from the Hospital Sizing Table for Transporters on Payroll / Transporters per Shift at a Large Sample Hospital
    large_sample_hospital_ratio = hospital_sizing_df.loc[1, "Transporters on Payroll / Transporters per Shift"]

    # Creating and displaying Patient Transportation Operational Data table
    average_transporters_per_shift = list(range(18, -1, -1))
    transporters_on_payroll = [i * large_sample_hospital_ratio for i in average_transporters_per_shift]
    turnovers_per_year = [turnover_rate * payroll for payroll in transporters_on_payroll]

    operational_data = {
        "Average # of Transporters per Shift": average_transporters_per_shift,
        "# of Transporters on Payroll": [f"{payroll:.5f}" for payroll in transporters_on_payroll],
        "Rovex Unit qty per shift per hospital": ["" for _ in range(19)],
        "Trips per shift, total": ["" for _ in range(19)],
        "Hybrid trips per shift, total": ["" for _ in range(19)],
        "Trips per shift, manual": ["" for _ in range(19)],
        "Trips per shift, automated": ["" for _ in range(19)],
        "Manual trip rate, trips per shift per transporter": ["" for _ in range(19)],
        "Automated trip rate, trip per shift per bot": ["" for _ in range(19)],
        "Automation, %": ["" for _ in range(19)],
        "# of turnovers per year": [f"{turnover:.5f}" for turnover in turnovers_per_year],
        "Automation Ratio (bots to transporter)": ["" for _ in range(19)],
        "Charging Stations": ["" for _ in range(19)]
    }

    # Convert the # of Transporters on Payroll column to float with 5 decimal places
    operational_df = pd.DataFrame(operational_data)
    operational_df["# of Transporters on Payroll"] = operational_df["# of Transporters on Payroll"].astype(float).map("{:.5f}".format)

    # Look up the # of Transporters on Payroll value for baseline and automation
    num_transporters_payroll_baseline = operational_df.loc[operational_df["Average # of Transporters per Shift"] == 18, "# of Transporters on Payroll"].astype(float).values[0]
    num_transporters_payroll_automation = operational_df.loc[operational_df["Average # of Transporters per Shift"] == 12, "# of Transporters on Payroll"].astype(float).values[0]

    # Look up the # of turnovers per year value for baseline and automation
    num_turnovers_baseline = operational_df.loc[operational_df["Average # of Transporters per Shift"] == 18, "# of turnovers per year"].astype(float).values[0]
    num_turnovers_automation = operational_df.loc[operational_df["Average # of Transporters per Shift"] == 12, "# of turnovers per year"].astype(float).values[0]

    # Calculate turnover costs
    turnover_cost_baseline = num_turnovers_baseline * turnover_cost_average
    turnover_cost_automation = num_turnovers_automation * turnover_cost_average

    # Operating expenses
    transporter_opex_baseline = staffing_cost_baseline + ot_cost_baseline + turnover_cost_baseline
    transporter_opex_automation = staffing_cost_automation + ot_cost_automation + turnover_cost_automation
    transporter_opex_savings = transporter_opex_baseline - transporter_opex_automation

    # Final yearly cost savings calculation
    yearly_cost_savings = transporter_opex_savings + rovex_opex
    yearly_cost_savings_list.append(yearly_cost_savings)

# End tracking time
end_time = time.time()
elapsed_time = end_time - start_time

# Convert the results to a DataFrame for analysis
results_df = pd.DataFrame(yearly_cost_savings_list, columns=["Yearly Cost Savings"])

# Set the display format for floating-point numbers
pd.options.display.float_format = '{:,.2f}'.format

# Print summary statistics
print("\nMonte Carlo Simulation Results:")
print(results_df.describe())

# Calculate the 95% confidence interval for the yearly cost savings
mean_savings = results_df["Yearly Cost Savings"].mean()
std_savings = results_df["Yearly Cost Savings"].std()
confidence_interval = norm.interval(0.95, loc=mean_savings, scale=std_savings / np.sqrt(num_simulations))

# Convert confidence interval to regular floats and format
confidence_interval = (float(confidence_interval[0]), float(confidence_interval[1]))

print(f"\n95% Confidence Interval for Yearly Cost Savings: ({confidence_interval[0]:,.2f}, {confidence_interval[1]:,.2f})")

# Print the elapsed time
print(f"\nElapsed Time for Simulation: {elapsed_time:.2f} seconds")

# Enable interactive mode
plt.ion()

# Plot the distribution of yearly cost savings
fig, ax = plt.subplots()
ax.hist(results_df["Yearly Cost Savings"], bins=50, edgecolor='k', alpha=0.7)
ax.set_title("Distribution of Yearly Cost Savings")
ax.set_xlabel("YR1 Cost Savings ($XXXK)")
ax.set_ylabel("Frequency")

# Set the axis to use the format of only the first three digits of hundred thousand
formatter = FuncFormatter(lambda x, pos: f'{int(x/1000):03}')
ax.xaxis.set_major_formatter(formatter)
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{int(x):,}'))

# Show the plot and block the script until the plot window is closed
plt.show(block=True)

# Display the hospital sizing table
print("\nHospital Sizing Table:")
print(hospital_sizing_df.to_string(index=False))

# Display the Patient Transportation Operational Data table
print("\nPatient Transportation Operational Data:")
print(operational_df.to_string(index=False))

# Creating and displaying A6 Hospital Savings Summary table
data = {
    "Variable": [
        "Avg Transporters", "Shifts per Day", "Hours per Shift", "Avg Transporter Hours per Day", 
        "Total Transporter Hours per Year", "Total Transporter Wage", "Total Benefits", "Staffing Cost",
        "OT Hours per Transporter", "OT Hour per Week", "OT Cost", "# Turnovers", "Turnover Cost",
        "Transporter OPEX", "Transporter Savings", "Rovex OPEX", "Yearly Cost Savings"
    ],
    "Baseline": [
        avg_transporters_baseline, shifts_per_day, hours_per_shift, round(avg_transporter_hours_per_day_baseline, 2),
        f"{total_transporter_hours_per_year_baseline:,.2f}", f"{total_transporter_wage_baseline:,.2f}", f"{total_benefits_baseline:,.2f}", f"{staffing_cost_baseline:,.2f}",
        round(ot_hours_per_transporter, 2), round(ot_hour_per_week_baseline, 2), f"{ot_cost_baseline:,.2f}", f"{num_turnovers_baseline:.6f}", f"{turnover_cost_baseline:,.2f}",
        f"{transporter_opex_baseline:,.2f}", "-", "-", "-"
    ],
    "Automation": [
        avg_transporters_automation, shifts_per_day, hours_per_shift, round(avg_transporter_hours_per_day_automation, 2),
        f"{total_transporter_hours_per_year_automation:,.2f}", f"{total_transporter_wage_automation:,.2f}", f"{total_benefits_automation:,.2f}", f"{staffing_cost_automation:,.2f}",
        round(ot_hours_per_transporter, 2), round(ot_hour_per_week_automation, 2), f"{ot_cost_automation:,.2f}", f"{num_turnovers_automation:.6f}", f"{turnover_cost_automation:,.2f}",
        f"{transporter_opex_automation:,.2f}", f"{transporter_opex_savings:,.2f}", f"{rovex_opex:,.2f}", f"{yearly_cost_savings:,.2f}"
    ]
}

df = pd.DataFrame(data)
print("\nA6 Hospital Savings Summary:")
print(df.to_string(index=False))