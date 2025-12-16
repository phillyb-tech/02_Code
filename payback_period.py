import numpy as np

# Cash flows
cash_flows = [
    -625815, 8197, 16394, 24591, 32788, 40985, 49182, 57379, 65576, 73773, 
    73773, 73773, 73773, -295579, 73773, 73773, 73773, 73773, 73773, 73773, 
    73773, 73773, 73773, 73773, 73773, -295579, 73773, 73773, 73773, 73773, 
    73773, 73773, 73773, 73773, 73773, 73773, 73773
]

# Discount rate
discount_rate = 0.10

def calculate_simple_payback_period(cash_flows):
    cumulative_cash_flow = 0
    for month, cash_flow in enumerate(cash_flows):
        cumulative_cash_flow += cash_flow
        if cumulative_cash_flow >= 0:
            return round(month + (cumulative_cash_flow - cash_flow) / cash_flow, 2)
    return None

def calculate_discounted_payback_period(cash_flows, discount_rate):
    cumulative_cash_flow = 0
    for month, cash_flow in enumerate(cash_flows):
        discounted_cash_flow = cash_flow / (1 + discount_rate) ** (month / 12)
        cumulative_cash_flow += discounted_cash_flow
        if cumulative_cash_flow >= 0:
            return round(month + (cumulative_cash_flow - discounted_cash_flow) / discounted_cash_flow, 2)
    return None

def calculate_npv(cash_flows, discount_rate, years):
    npv = 0
    for month, cash_flow in enumerate(cash_flows[:years * 12 + 1]):
        npv += cash_flow / (1 + discount_rate) ** (month / 12)
    return round(npv, 2)

simple_payback_period = calculate_simple_payback_period(cash_flows)
discounted_payback_period = calculate_discounted_payback_period(cash_flows, discount_rate)
one_year_npv = calculate_npv(cash_flows, discount_rate, 1)
two_year_npv = calculate_npv(cash_flows, discount_rate, 2)
three_year_npv = calculate_npv(cash_flows, discount_rate, 3)

print(f"Simple Payback Period: {simple_payback_period} months")
print(f"Discounted Payback Period: {discounted_payback_period} months")
print(f"1-Year NPV: ${one_year_npv}")
print(f"2-Year NPV: ${two_year_npv}")
print(f"3-Year NPV: ${three_year_npv}")