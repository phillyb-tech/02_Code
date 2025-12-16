import matplotlib.pyplot as plt
import pandas as pd

plt.close('all')  # close any open figures

# Data — updated to match the workflow table
# Format: [Scenario, Step, Start, Duration]
ct_data = [
    # Baseline
    ['Baseline', 'P. CT ordered → CT scheduled',        0.0, 27.4],
    ['Baseline', 'A. CT scheduled → Transport request', 27.4, 52.0],
    ['Baseline', 'B1. Request → Assigned',              79.4, 11.8],
    ['Baseline', 'B2. Assigned → Acknowledged',         91.2, 3.8],
    ['Baseline', 'B3. Acknowledged → Pickup',           95.0, 6.5],
    ['Baseline', 'C1. Transport start → end',           101.5, 5.0],
    ['Baseline', 'C2. Transport end → CT start',        106.5, 1.6],
    ['Baseline', 'C3. CT start → CT end',               108.1, 12.1],

    # Rovis Only
    ['Rovis Only', 'P. CT ordered → CT scheduled',        0.0, 27.4],
    ['Rovis Only', 'A. CT scheduled → Transport request', 27.4, 52.0],
    ['Rovis Only', 'B1. Request → Assigned',              79.4, 5.9],
    ['Rovis Only', 'B2. Assigned → Acknowledged',         85.3, 1.9],
    ['Rovis Only', 'B3. Acknowledged → Pickup',           87.2, 3.3],
    ['Rovis Only', 'C1. Transport start → end',           90.5, 5.0],
    ['Rovis Only', 'C2. Transport end → CT start',        95.5, 1.6],
    ['Rovis Only', 'C3. CT start → CT end',               97.1, 12.1],

    # Rovis + Workflow Redesign
    ['Rovis + Workflow Redesign', 'P. CT ordered → CT scheduled',        0.0, 27.4],
    ['Rovis + Workflow Redesign', 'A. CT scheduled → Transport request', 27.4, 35.0],
    ['Rovis + Workflow Redesign', 'B1. Request → Assigned',              62.4, 5.9],
    ['Rovis + Workflow Redesign', 'B2. Assigned → Acknowledged',         68.3, 1.9],
    ['Rovis + Workflow Redesign', 'B3. Acknowledged → Pickup',           70.2, 3.3],
    ['Rovis + Workflow Redesign', 'C1. Transport start → end',           73.5, 5.0],
    ['Rovis + Workflow Redesign', 'C2. Transport end → CT start',        78.5, 1.6],
    ['Rovis + Workflow Redesign', 'C3. CT start → CT end',               80.1, 12.1],
]

ct_df = pd.DataFrame(ct_data, columns=['Scenario', 'Step', 'Start', 'Duration'])

# Order steps top-to-bottom on the chart
step_order_internal = [
    'P. CT ordered → CT scheduled',
    'A. CT scheduled → Transport request',
    'B1. Request → Assigned',
    'B2. Assigned → Acknowledged',
    'B3. Acknowledged → Pickup',
    'C1. Transport start → end',
    'C2. Transport end → CT start',
    'C3. CT start → CT end',
]

# Map each step to a y-position
y_positions = {step: i for i, step in enumerate(step_order_internal[::-1])}

scenarios = ['Baseline', 'Rovis Only', 'Rovis + Workflow Redesign']
colors = {
    'Baseline': '#DBDBDB',                    # gray
    'Rovis Only': '#FFE699',                  # light yellow
    'Rovis + Workflow Redesign': '#C6E0B4',   # light green
}
hatches = {
    'Baseline': '',
    'Rovis Only': 'xx',
    'Rovis + Workflow Redesign': '///',
}

bar_height = 0.35

# Vertical offsets for A and B steps so they don't overlap
scheduling_offsets = {
    'Baseline':  0.35,
    'Rovis Only': 0.0,
    'Rovis + Workflow Redesign': -0.35,
}

# Label vertical offsets so labels sit comfortably above bars
label_y_offsets = {
    'Baseline': 0.02,
    'Rovis Only': 0.02,
    'Rovis + Workflow Redesign': 0.02,
}

fig, ax = plt.subplots(figsize=(14, 6))

for scen in scenarios:
    sub = ct_df[ct_df['Scenario'] == scen]
    for _, row in sub.iterrows():
        base_y = y_positions[row['Step']]
        y = base_y
        height = bar_height

        # Shift A and B steps vertically by scenario so they do not overlap
        if row['Step'] in ['A. CT scheduled → Transport request',
                           'B1. Request → Assigned',
                           'B2. Assigned → Acknowledged',
                           'B3. Acknowledged → Pickup']:
            y = base_y + scheduling_offsets[scen]

        # Draw bar
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

        # Add duration labels on bars
        rounded_dur = int(round(row['Duration']))
        label_text = str(rounded_dur) + ' min'

        # Default: centered over the bar
        x_pos = row['Start'] + row['Duration'] / 2.0

        ax.text(
            x_pos,
            y + height / 2.0 + label_y_offsets[scen],
            label_text,
            va='center',
            ha='center',
            fontsize=7,
            color='black',
        )

# Axes formatting
yticks = list(y_positions.values())
yticklabels = step_order_internal[::-1]
ax.set_yticks(yticks)
ax.set_yticklabels(yticklabels, fontsize=9)

ax.set_xlabel('Minutes', fontsize=11)
ax.set_xlim(left=0)
ax.grid(axis='x', linestyle='--', alpha=0.4)

# Updated title
ax.set_title('CT Transport Timeline by Scenario (with P, A, B1–B3, C1–C3)', fontsize=12)

# Deduplicate legend entries
handles, labels = ax.get_legend_handles_labels()
by_label = dict(zip(labels, handles))
ax.legend(
    by_label.values(),
    by_label.keys(),
    title='Scenario',
    loc='lower right',
    frameon=True,
)

plt.tight_layout()
plt.show()