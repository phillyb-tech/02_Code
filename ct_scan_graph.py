# This code builds a Gantt-style chart in Matplotlib
# - Step A (Scheduling) bars are vertically split by scenario (stacked)
# - Other steps show one horizontal row per step, with small per-scenario offsets for visibility
# - Colors/hatches are assigned per scenario and appear in the legend in a sensible order

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

def plot_gantt(gantt_df):
    """
    Draw a Gantt-style chart where Scheduling (Step A) shows scenario bars
    stacked vertically and other steps are grouped by step (with small
    offsets so multiple scenarios remain visible).
    Expects gantt_df with columns: 'Scenario', 'Step', 'Start', 'Duration'
    """
    required = {'Scenario', 'Step', 'Start', 'Duration'}
    if not required.issubset(set(gantt_df.columns)):
        raise ValueError(f"gantt_df must contain columns: {sorted(required)}")

    # keep a stable ordering
    gantt_df = gantt_df.sort_values(['Step', 'Scenario', 'Start'])

    scenarios = list(gantt_df['Scenario'].unique())
    # prefer a human-friendly step order if present, otherwise fall back to data order
    preferred_steps = [
        "A. Scheduling → Request",
        "B1. Request → Assigned",
        "B2. Assigned → Acknowledged",
        "B3. Acknowledged → Pickup",
        "C. Travel"
    ]
    steps_in_data = list(gantt_df['Step'].unique())
    # build final steps list: preferred steps that appear + any additional steps afterwards
    steps = [s for s in preferred_steps if s in steps_in_data]
    steps += [s for s in steps_in_data if s not in steps]

    # color / hatch palette (extendable)
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple']
    hatches = ['///', '\\\\', '...', 'xx', '++']

    color_map = {s: colors[i % len(colors)] for i, s in enumerate(scenarios)}
    hatch_map = {s: hatches[i % len(hatches)] for i, s in enumerate(scenarios)}

    # base y position per step (integer positions for y-ticks)
    # Increase spacing between step rows so bars for different steps do not touch.
    # Keep simple, conservative offsets for scenarios so bars within a step are visible
    # but do not overlap other steps.
    STEP_SPACING = 3.5
    step_to_y = {step: i * STEP_SPACING for i, step in enumerate(steps)}

    # find Scheduling step name if present
    step_a_name = None
    for st in steps:
        if 'Scheduling' in str(st):
            step_a_name = st
            break

    # offsets: conservative values relative to STEP_SPACING.
    # Smaller offsets and heights reduce overlap while keeping per-scenario separation.
    n_scen = max(1, len(scenarios))
    scenario_centered = {s: (idx - (n_scen - 1) / 2.0) for idx, s in enumerate(scenarios)}

    # Step A (stacked): modest vertical spread, height comfortably less than STEP_SPACING
    offset_scale_a = 0.30
    height_a = 0.9
    scenario_offset_a = {s: scenario_centered[s] * offset_scale_a for s in scenarios}

    # Other steps (grouped): very small offsets and smaller height
    offset_scale_other = 0.20
    height_other = 0.6
    scenario_offset_other = {s: scenario_centered[s] * offset_scale_other for s in scenarios}

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Draw bars
    for _, row in gantt_df.iterrows():
        step_name = row['Step']
        scen = row['Scenario']
        start = row['Start']
        dur = row['Duration']

        base_y = step_to_y[step_name]

        if step_a_name is not None and step_name == step_a_name:
            # stacked vertically per scenario (use defined height_a)
            y = base_y + scenario_offset_a.get(scen, 0.0)
            height = height_a
            hatch = hatch_map.get(scen)
        else:
            # grouped on one row, use smaller offsets/heights so items remain separate
            y = base_y + scenario_offset_other.get(scen, 0.0)
            height = height_other
            hatch = None

        ax.barh(
            y=y,
            width=dur,
            left=start,
            height=height,
            color=color_map.get(scen, 'grey'),
            edgecolor='black',
            hatch=hatch,
            alpha=0.95
        )

    # Y axis ticks at the base positions (labels from steps)
    ax.set_yticks([step_to_y[s] for s in steps])
    ax.set_yticklabels([s for s in steps], fontsize=12)
    ax.invert_yaxis()

    # Labels and title
    ax.set_xlabel("Time", fontsize=12)
    ax.set_title("Gantt: Step A with Scheduling split by Scenario; Others Grouped", fontsize=14, pad=14)

    # Legend: prefer ordering that makes sense for clinical scenarios if present
    desired_order = ["Baseline", "Rovis + Workflow Redesign", "Rovis Only"]
    legend_scenarios = [s for s in desired_order if s in scenarios] + [s for s in scenarios if s not in desired_order]

    handles = []
    for s in legend_scenarios:
        handles.append(Patch(facecolor=color_map.get(s, 'grey'),
                             edgecolor='black',
                             hatch=hatch_map.get(s, None),
                             label=s))
    ax.legend(handles=handles, title="Scenario", bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)

    ax.set_xlim(left=0)
    plt.tight_layout()
    plt.show()


# Example usage (run the module to check)
if __name__ == "__main__":
    import pandas as pd
    sample = pd.DataFrame([
        {'Scenario': 'Baseline', 'Step': 'A. Scheduling → Request', 'Start': 0,  'Duration': 72},
        {'Scenario': 'Rovis + Workflow Redesign', 'Step': 'A. Scheduling → Request', 'Start': 2,  'Duration': 45},
        {'Scenario': 'Rovis Only', 'Step': 'A. Scheduling → Request', 'Start': 1,  'Duration': 60},

        {'Scenario': 'Rovis + Workflow Redesign', 'Step': 'B1. Request → Assigned', 'Start': 35, 'Duration': 5},
        {'Scenario': 'Rovis Only', 'Step': 'B1. Request → Assigned', 'Start': 60, 'Duration': 5},
        {'Scenario': 'Baseline', 'Step': 'B1. Request → Assigned', 'Start': 62, 'Duration': 6},

        {'Scenario': 'Rovis + Workflow Redesign', 'Step': 'B2. Assigned → Acknowledged', 'Start': 40, 'Duration': 2},
        {'Scenario': 'Rovis Only', 'Step': 'B2. Assigned → Acknowledged', 'Start': 60, 'Duration': 2},
        {'Scenario': 'Baseline', 'Step': 'B2. Assigned → Acknowledged', 'Start': 62, 'Duration': 3},

        {'Scenario': 'Rovis + Workflow Redesign', 'Step': 'B3. Acknowledged → Pickup', 'Start': 43, 'Duration': 5},
        {'Scenario': 'Rovis Only', 'Step': 'B3. Acknowledged → Pickup', 'Start': 60, 'Duration': 5},
        {'Scenario': 'Baseline', 'Step': 'B3. Acknowledged → Pickup', 'Start': 66, 'Duration': 10},

        {'Scenario': 'Rovis + Workflow Redesign', 'Step': 'C. Travel', 'Start': 48, 'Duration': 8},
        {'Scenario': 'Rovis Only', 'Step': 'C. Travel', 'Start': 62, 'Duration': 12},
        {'Scenario': 'Baseline', 'Step': 'C. Travel', 'Start': 72, 'Duration': 8},
    ])
    plot_gantt(sample)