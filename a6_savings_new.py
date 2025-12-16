import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import os

# Input variables
avg_transporters_baseline = 18
avg_transporters_automation = 12
shifts_per_day = 3
hours_per_shift = 8

transporter_wage_rate = 17.00
benefits_rate = 0.30
ot_wage_rate = 25.29
turnover_rate = 0.25
turnover_cost_average = 8100
rovex_opex = -618553

# Baseline calculations
avg_transporter_hours_per_day_baseline = hours_per_shift * shifts_per_day * avg_transporters_baseline 
total_transporter_hours_per_year_baseline = avg_transporter_hours_per_day_baseline * 5 * 52
total_transporter_wage_baseline = total_transporter_hours_per_year_baseline * transporter_wage_rate
total_benefits_baseline = benefits_rate * total_transporter_wage_baseline
staffing_cost_baseline = total_transporter_wage_baseline + total_benefits_baseline

ot_hours_per_transporter = 24 / avg_transporters_baseline  # Overtime hours per transporter
ot_hour_per_week_baseline = ot_hours_per_transporter * avg_transporters_baseline
ot_cost_baseline = ot_hour_per_week_baseline * 52 * ot_wage_rate

# Automation calculations
avg_transporter_hours_per_day_automation = hours_per_shift * shifts_per_day * avg_transporters_automation
total_transporter_hours_per_year_automation = avg_transporter_hours_per_day_automation * 5 * 52
total_transporter_wage_automation = total_transporter_hours_per_year_automation * transporter_wage_rate
total_benefits_automation = benefits_rate * total_transporter_wage_automation
staffing_cost_automation = total_transporter_wage_automation + total_benefits_automation

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
print("\nHospital Sizing Table:")
print(hospital_sizing_df.to_string(index=False))

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

# Print the exact values of the specified variables
print(f"staffing_cost_baseline: {staffing_cost_baseline}")
print(f"ot_cost_baseline: {ot_cost_baseline}")
print(f"turnover_cost_baseline: {turnover_cost_baseline}")
print(f"transporter_opex_baseline: {transporter_opex_baseline}")

print(f"staffing_cost_automation: {staffing_cost_automation}")
print(f"ot_cost_automation: {ot_cost_automation}")
print(f"turnover_cost_automation: {turnover_cost_automation}")
print(f"transporter_opex_automation: {transporter_opex_automation}")

# Final yearly cost savings calculation
yearly_cost_savings = transporter_opex_savings + rovex_opex

print("\nPatient Transportation Operational Data:")
print(operational_df.to_string(index=False))

# Save the Patient Transportation Operational Data table as a CSV file
csv_file_path = "Patient_Transportation_Operational_Data.csv"
operational_df.to_csv(csv_file_path, index=False)

# Open the saved CSV file in Excel
os.startfile(csv_file_path)

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







