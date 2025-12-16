import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import os

# Input variables for max, min, and original cases
inputs = {
    "max": {
        "transporter_wage_rate": 40.39,
        "ot_wage_rate": 60.08,
        "ot_hours_per_week": 3.0,
        "benefits_rate": 0.40,
        "turnover_cost_average": 14910,
        "turnover_rate": 0.35,
        "rovex_opex": -624130.01
    },
    "min": {
        "transporter_wage_rate": 15.58,
        "ot_wage_rate": 23.18,
        "ot_hours_per_week": 0.5,
        "benefits_rate": 0.10,
        "turnover_cost_average": 1290,
        "turnover_rate": 0.15,
        "rovex_opex": -618214.58
    },
    "original": {
        "transporter_wage_rate": 17.00,
        "ot_wage_rate": 25.29,
        "ot_hours_per_week": 1.33,
        "benefits_rate": 0.30,
        "turnover_cost_average": 8100,
        "turnover_rate": 0.25,
        "rovex_opex": -618553
    }
}

# Common input variables
avg_transporters_baseline = 18
avg_transporters_automation = 12
shifts_per_day = 3
hours_per_shift = 8  # Corrected definition

def calculate_yearly_cost_savings(case):
    transporter_wage_rate = inputs[case]["transporter_wage_rate"]
    ot_wage_rate = inputs[case]["ot_wage_rate"]
    ot_hours_per_week = inputs[case]["ot_hours_per_week"]
    benefits_rate = inputs[case]["benefits_rate"]
    turnover_cost_average = inputs[case]["turnover_cost_average"]
    turnover_rate = inputs[case]["turnover_rate"]
    rovex_opex = inputs[case]["rovex_opex"]

    # Baseline calculations
    avg_transporter_hours_per_day_baseline = hours_per_shift * shifts_per_day * avg_transporters_baseline 
    total_transporter_hours_per_year_baseline = avg_transporter_hours_per_day_baseline * 5 * 52
    total_transporter_wage_baseline = total_transporter_hours_per_year_baseline * transporter_wage_rate
    total_benefits_baseline = benefits_rate * total_transporter_wage_baseline
    staffing_cost_baseline = total_transporter_wage_baseline + total_benefits_baseline

    ot_hour_per_week_baseline = ot_hours_per_week * avg_transporters_baseline
    ot_cost_baseline = ot_hour_per_week_baseline * 52 * ot_wage_rate

    # Automation calculations
    avg_transporter_hours_per_day_automation = hours_per_shift * shifts_per_day * avg_transporters_automation
    total_transporter_hours_per_year_automation = avg_transporter_hours_per_day_automation * 5 * 52
    total_transporter_wage_automation = total_transporter_hours_per_year_automation * transporter_wage_rate
    total_benefits_automation = benefits_rate * total_transporter_wage_automation
    staffing_cost_automation = total_transporter_wage_automation + total_benefits_automation

    ot_hour_per_week_automation = ot_hours_per_week * avg_transporters_automation
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
    YR1_savings = transporter_opex_savings + rovex_opex

    # Print intermediate values for debugging
    if case == "original":
        print(f"\nDebugging Original Case:")
        print(f"Total Transporter Hours per Year (Baseline): {total_transporter_hours_per_year_baseline}")
        print(f"Total Transporter Wage (Baseline): {total_transporter_wage_baseline}")
        print(f"Total Benefits (Baseline): {total_benefits_baseline}")
        print(f"Staffing Cost (Baseline): {staffing_cost_baseline}")
        print(f"OT Cost (Baseline): {ot_cost_baseline}")
        print(f"Total Transporter Hours per Year (Automation): {total_transporter_hours_per_year_automation}")
        print(f"Total Transporter Wage (Automation): {total_transporter_wage_automation}")
        print(f"Total Benefits (Automation): {total_benefits_automation}")
        print(f"Staffing Cost (Automation): {staffing_cost_automation}")
        print(f"OT Cost (Automation): {ot_cost_automation}")
        print(f"Turnover Cost (Baseline): {turnover_cost_baseline}")
        print(f"Turnover Cost (Automation): {turnover_cost_automation}")
        print(f"Transporter OPEX (Baseline): {transporter_opex_baseline}")
        print(f"Transporter OPEX (Automation): {transporter_opex_automation}")
        print(f"Transporter OPEX Savings: {transporter_opex_savings}")
        print(f"Rovex OPEX: {rovex_opex}")
        print(f"YR1 Savings: {YR1_savings}")

    # Creating and displaying A6 Hospital Savings Summary table
    data = {
        "Variable": [
            "Avg Transporters", "Shifts per Day", "Hours per Shift", "Avg Transporter Hours per Day", 
            "Total Transporter Hours per Year", "Total Transporter Wage", "Total Benefits", "Staffing Cost",
            "OT Hours per Transporter", "OT Hour per Week", "OT Cost", "# Turnovers", "Turnover Cost",
            "Transporter OPEX", "Transporter Savings", "Rovex OPEX", "YR1 Savings"
        ],
        "Baseline": [
            avg_transporters_baseline, shifts_per_day, hours_per_shift, round(avg_transporter_hours_per_day_baseline, 2),
            f"{total_transporter_hours_per_year_baseline:,.2f}", f"{total_transporter_wage_baseline:,.2f}", f"{total_benefits_baseline:,.2f}", f"{staffing_cost_baseline:,.2f}",
            round(ot_hours_per_week, 2), round(ot_hour_per_week_baseline, 2), f"{ot_cost_baseline:,.2f}", f"{num_turnovers_baseline:.6f}", f"{turnover_cost_baseline:,.2f}",
            f"{transporter_opex_baseline:,.2f}", "-", "-", "-"
        ],
        "Automation": [
            avg_transporters_automation, shifts_per_day, hours_per_shift, round(avg_transporter_hours_per_day_automation, 2),
            f"{total_transporter_hours_per_year_automation:,.2f}", f"{total_transporter_wage_automation:,.2f}", f"{total_benefits_automation:,.2f}", f"{staffing_cost_automation:,.2f}",
            round(ot_hours_per_week, 2), round(ot_hour_per_week_automation, 2), f"{ot_cost_automation:,.2f}", f"{num_turnovers_automation:.6f}", f"{turnover_cost_automation:,.2f}",
            f"{transporter_opex_automation:,.2f}", f"{transporter_opex_savings:,.2f}", f"{rovex_opex:,.2f}", f"{YR1_savings:,.2f}"
        ]
    }

    df = pd.DataFrame(data)
    return YR1_savings, df

# Calculate yearly cost savings for max, min, and original cases
YR1_savings_max, df_max = calculate_yearly_cost_savings("max")
YR1_savings_min, df_min = calculate_yearly_cost_savings("min")
YR1_savings_original, df_original = calculate_yearly_cost_savings("original")

print(f"YR1 Savings (Max Case): {YR1_savings_max}")
print(f"YR1 Savings (Min Case): {YR1_savings_min}")
print(f"YR1 Savings (Original Case): {YR1_savings_original}")

# Print the A6 Hospital Savings Summary tables for max, min, and original cases
print("\nA6 Hospital Savings Summary (Max Case):")
print(df_max.to_string(index=False))

print("\nA6 Hospital Savings Summary (Min Case):")
print(df_min.to_string(index=False))

print("\nA6 Hospital Savings Summary (Original Case):")
print(df_original.to_string(index=False))







