# CT Transport Delay Timeline Gantt chart
# - Three scenarios (Baseline, Rovis Only, Rovis + Workflow Redesign)
# - Non-overlapping lanes for A. Scheduling → Request
# - Same bar thickness in all rows
# - Legend in lower-left inside the plot

import matplotlib.pyplot as plt
import pandas as pd

# 1. Data setup
ct_data = [
    ['Baseline', 'C. Travel',                          74.1, 5],
    ['Baseline', 'B3. Acknowledged → Pickup',          67.6, 6.5],
    ['Baseline', 'B2. Assigned → Acknowledged',        63.8, 3.8],
    ['Baseline', 'B1. Request → Assigned',             52.0, 11.8],
    ['Baseline', 'A. Scheduling → Request',             0.0, 52],

    ['Rovis Only', 'C. Travel',                        63.1, 5],
    ['Rovis Only', 'B3. Acknowledged → Pickup',        59.8, 3.3],
    ['Rovis Only', 'B2. Assigned → Acknowledged',      57.9, 1.9],
    ['Rovis Only', 'B1. Request → Assigned',           52.0, 5.9],
    ['Rovis Only', 'A. Scheduling → Request',           0.0, 52],

    ['Rovis + Workflow Redesign', 'C. Travel',                         46.1, 5],
    ['Rovis + Workflow Redesign', 'B3. Acknowledged → Pickup',         42.8, 3.3],
    ['Rovis + Workflow Redesign', 'B2. Assigned → Acknowledged',       40.9, 1.9],
    ['Rovis + Workflow Redesign', 'B1. Request → Assigned',            35.0, 5.9],
    ['Rovis + Workflow Redesign', 'A. Scheduling → Request',            0.0, 35],
]

ct_df = pd.DataFrame(ct_data, columns=['Scenario', 'Step', 'Start', 'Duration'])

# 2. Step order (top to bottom on chart)
step_order_internal = [
    'A. Scheduling → Request',
    'B1. Request → Assigned',
    'B2. Assigned → Acknowledged',
    'B3. Acknowledged → Pickup',
    'C. Travel'
]

# Map steps to y positions (0 at bottom, 4 at top)
# We'll reverse to make C. Travel appear at the top, A. Scheduling at the bottom
y_positions = {step: i for i, step in enumerate(step_order_internal[::-1])}

# 3. Scenario style
scenarios = ['Baseline', 'Rovis Only', 'Rovis + Workflow Redesign']
colors = {
    'Baseline': '#1f77b4',                  # blue
    'Rovis Only': '#ff7f0e',                # orange
    'Rovis + Workflow Redesign': '#2ca02c'  # green
}
hatches = {
    'Baseline': '',
    'Rovis Only': 'xx',
    'Rovis + Workflow Redesign': '///',
}

# 4. Vertical layout for Scheduling row so bars do NOT overlap

# All bars have the same thickness
bar_height = 0.4

# For Scheduling, separate centers more than half the bar height
# so there is visible space between bars:
# distance between centers ≈ 0.76 > 0.4 => they will not touch.
blue_offset   =  0.38   # Baseline up
orange_offset =  0.00   # Rovis Only center
green_offset  = -0.38   # Rovis + Workflow down

scheduling_offsets = {
    'Baseline': blue_offset,
    'Rovis Only': orange_offset,
    'Rovis + Workflow Redesign': green_offset,
}

# 5. Plot
fig, ax = plt.subplots(figsize=(10, 4))

for scen in scenarios:
    sub = ct_df[ct_df['Scenario'] == scen]
    for _, row in sub.iterrows():
        base_y = y_positions[row['Step']]
        y = base_y
        height = bar_height

        # Special vertical offsets ONLY for the Scheduling step
        if row['Step'] == 'A. Scheduling → Request':
            y = base_y + scheduling_offsets[scen]

        ax.barh(
            y=y,
            left=row['Start'],
            width=row['Duration'],
            color=colors[scen],
            edgecolor='black',
            hatch=hatches[scen],
            alpha=0.9,
            height=height,
            label=scen,
        )

# 6. Y-axis labels (with prefixes, top to bottom)
yticks = list(y_positions.values())
yticklabels = step_order_internal[::-1]  # reverse so C. Travel is at top
ax.set_yticks(yticks)
ax.set_yticklabels(yticklabels)

# 7. Axes, title, grid
ax.set_xlabel('Minutes')
ax.set_xlim(left=0)
ax.grid(axis='x', linestyle='--', alpha=0.4)
ax.set_title('CT Transport Delay Timeline')

# 8. Legend inside plot, lower-left
handles, labels = ax.get_legend_handles_labels()
by_label = dict(zip(labels, handles))  # dedupe
ax.legend(
    by_label.values(),
    by_label.keys(),
    title='Scenario',
    loc='lower left',
    bbox_to_anchor=(0.02, 0.02),
    frameon=True,
)

plt.tight_layout()
plt.show()