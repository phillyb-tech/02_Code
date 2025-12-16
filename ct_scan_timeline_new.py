import matplotlib.pyplot as plt
import pandas as pd

plt.close('all')  # close any open figures

# =============================================================================
# ORIGINAL DETAILED VERSION - All 8 individual steps
# =============================================================================

# Data — updated to match the workflow table with corrected 75% B3 reduction
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
    ['Rovis Only', 'B1. Request → Assigned',              79.4, 3.0],
    ['Rovis Only', 'B2. Assigned → Acknowledged',         82.4, 1.0],
    ['Rovis Only', 'B3. Acknowledged → Pickup',           83.4, 1.6],
    ['Rovis Only', 'C1. Transport start → end',           85.0, 5.0],
    ['Rovis Only', 'C2. Transport end → CT start',        90.0, 1.6],
    ['Rovis Only', 'C3. CT start → CT end',               91.6, 12.1],

    # Rovis + Workflow Redesign
    ['Rovis + Workflow Redesign', 'P. CT ordered → CT scheduled',        0.0, 27.4],
    ['Rovis + Workflow Redesign', 'A. CT scheduled → Transport request', 27.4, 35.0],
    ['Rovis + Workflow Redesign', 'B1. Request → Assigned',              62.4, 3.0],
    ['Rovis + Workflow Redesign', 'B2. Assigned → Acknowledged',         65.4, 1.0],
    ['Rovis + Workflow Redesign', 'B3. Acknowledged → Pickup',           66.4, 1.6],
    ['Rovis + Workflow Redesign', 'C1. Transport start → end',           68.0, 5.0],
    ['Rovis + Workflow Redesign', 'C2. Transport end → CT start',        73.0, 1.6],
    ['Rovis + Workflow Redesign', 'C3. CT start → CT end',               74.6, 12.1],
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

# Vertical offsets for P, A and B steps so they don't overlap
scheduling_offsets = {
    'Baseline':  0.27,
    'Rovis Only': -0.07,
    'Rovis + Workflow Redesign': -0.43,
}

# Label vertical offsets so labels sit comfortably above bars
label_y_offsets = {
    'Baseline': 0.02,
    'Rovis Only': 0.02,
    'Rovis + Workflow Redesign': 0.02,
}

fig1, ax1 = plt.subplots(figsize=(14, 6))

for scen in scenarios:
    sub = ct_df[ct_df['Scenario'] == scen]
    for _, row in sub.iterrows():
        base_y = y_positions[row['Step']]
        y = base_y
        height = bar_height

        # Shift P, A, B steps vertically by scenario so they don't overlap
        if row['Step'] in ['P. CT ordered → CT scheduled',
                           'A. CT scheduled → Transport request',
                           'B1. Request → Assigned',
                           'B2. Assigned → Acknowledged',
                           'B3. Acknowledged → Pickup',
                           'C1. Transport start → end',
                           'C2. Transport end → CT start',
                           'C3. CT start → CT end']:
            y = base_y + scheduling_offsets[scen]

        # Draw bar
        ax1.barh(
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

        # Place all labels to the right of bar end
        x_pos = row['Start'] + row['Duration'] + 1.0  # offset to the right
        label_y = y  # use actual bar y position

        ax1.text(
            x_pos,
            label_y,
            label_text,
            va='center',
            ha='left',
            fontsize=7,
            color='black',
        )

# Axes formatting
yticks = list(y_positions.values())
yticklabels = step_order_internal[::-1]
ax1.set_yticks(yticks)
ax1.set_yticklabels(yticklabels, fontsize=9)

ax1.set_xlabel('Minutes', fontsize=11)
ax1.set_xlim(left=0, right=135)
ax1.grid(axis='x', linestyle='--', alpha=0.4)

# Updated title
ax1.set_title('CT Transport Timeline by Scenario - Detailed View', fontsize=12, fontweight='bold')

# Deduplicate legend entries
handles, labels = ax1.get_legend_handles_labels()
by_label = dict(zip(labels, handles))
# Move legend to bottom left inside the graph area
ax1.legend(
    by_label.values(),
    by_label.keys(),
    title='Scenario',
    loc='center left',
    bbox_to_anchor=(0.12, 0.5),
    frameon=True,
)

plt.tight_layout()

# =============================================================================
# CONDENSED VERSION - Grouped B and C steps
# =============================================================================

# Condensed data — grouping B1+B2+B3 and C1+C2+C3
# Format: [Scenario, Step, Start, Duration]
ct_data_condensed = [
    # Baseline
    ['Baseline', 'P. CT ordered → CT scheduled',           0.0, 27.4],
    ['Baseline', 'A. CT scheduled → Transport request',    27.4, 52.0],
    ['Baseline', 'B. Transport coordination (B1+B2+B3)',   79.4, 22.1],  # 11.8+3.8+6.5
    ['Baseline', 'C. Patient movement & scan (C1+C2+C3)',  101.5, 18.7], # 5.0+1.6+12.1

    # Rovis Only
    ['Rovis Only', 'P. CT ordered → CT scheduled',           0.0, 27.4],
    ['Rovis Only', 'A. CT scheduled → Transport request',    27.4, 52.0],
    ['Rovis Only', 'B. Transport coordination (B1+B2+B3)',   79.4, 5.6],  # 3.0+1.0+1.6
    ['Rovis Only', 'C. Patient movement & scan (C1+C2+C3)',  85.0, 18.7], # 5.0+1.6+12.1

    # Rovis + Workflow Redesign
    ['Rovis + Workflow Redesign', 'P. CT ordered → CT scheduled',           0.0, 27.4],
    ['Rovis + Workflow Redesign', 'A. CT scheduled → Transport request',    27.4, 35.0],
    ['Rovis + Workflow Redesign', 'B. Transport coordination (B1+B2+B3)',   62.4, 5.6],  # 3.0+1.0+1.6
    ['Rovis + Workflow Redesign', 'C. Patient movement & scan (C1+C2+C3)',  68.0, 18.7], # 5.0+1.6+12.1
]

ct_df_condensed = pd.DataFrame(ct_data_condensed, columns=['Scenario', 'Step', 'Start', 'Duration'])

# Order steps top-to-bottom on the condensed chart
step_order_condensed = [
    'P. CT ordered → CT scheduled',
    'A. CT scheduled → Transport request',
    'B. Transport coordination (B1+B2+B3)',
    'C. Patient movement & scan (C1+C2+C3)',
]

# Map each step to a y-position
y_positions_condensed = {step: i for i, step in enumerate(step_order_condensed[::-1])}

bar_height_condensed = 0.25

# Vertical offsets for scenarios so they don't overlap
scheduling_offsets_condensed = {
    'Baseline':  0.2,
    'Rovis Only': 0.0,
    'Rovis + Workflow Redesign': -0.2,
}

# Special adjustment for green A bar (Rovis + Workflow Redesign, Step A)
special_offsets = {
    ('Rovis + Workflow Redesign', 'A. CT scheduled → Transport request'): -0.16,  # Move down 4 pixels (was -0.08)
    ('Rovis Only', 'P. CT ordered → CT scheduled'): -0.07,  # Move yellow P bar down 3 pixels
    ('Rovis + Workflow Redesign', 'P. CT ordered → CT scheduled'): -0.14,  # Move green P bar down 3 pixels
    ('Rovis Only', 'A. CT scheduled → Transport request'): -0.08,  # Move yellow A bar down 4 pixels
    # Move yellow and green B bars down by 5 pixels
    ('Rovis Only', 'B. Transport coordination (B1+B2+B3)'): -0.08,  # Move yellow B bar down 5 pixels
    ('Rovis + Workflow Redesign', 'B. Transport coordination (B1+B2+B3)'): -0.1,  # Move green B bar down 5 pixels
    # Move yellow and green C bars down by 5 pixels
    ('Rovis Only', 'C. Patient movement & scan (C1+C2+C3)'): -0.07,  # Move yellow C bar down 5 pixels
    ('Rovis + Workflow Redesign', 'C. Patient movement & scan (C1+C2+C3)'): -0.14,  # Move green C bar down 5 pixels
}

fig2, ax2 = plt.subplots(figsize=(14, 5))

for scen in scenarios:
    sub = ct_df_condensed[ct_df_condensed['Scenario'] == scen]
    for _, row in sub.iterrows():
        base_y = y_positions_condensed[row['Step']]
        y = base_y + scheduling_offsets_condensed[scen]
        
        # Apply special offset for green A bar
        if (scen, row['Step']) in special_offsets:
            y += special_offsets[(scen, row['Step'])]
        
        height = bar_height_condensed

        # Draw bar
        ax2.barh(
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

        # Place labels to the right of bar end
        x_pos = row['Start'] + row['Duration'] + 1.0
        label_y = y

        ax2.text(
            x_pos,
            label_y,
            label_text,
            va='center',
            ha='left',
            fontsize=8,
            color='black',
        )

# Axes formatting
yticks_condensed = list(y_positions_condensed.values())
yticklabels_condensed = step_order_condensed[::-1]
ax2.set_yticks(yticks_condensed)
ax2.set_yticklabels(yticklabels_condensed, fontsize=10)

ax2.set_xlabel('Minutes', fontsize=11)
ax2.set_xlim(left=0, right=130)
ax2.grid(axis='x', linestyle='--', alpha=0.4)

# Updated title
ax2.set_title('CT Transport Timeline by Scenario - Condensed View', fontsize=12, fontweight='bold')

# Deduplicate legend entries and move to top right
handles2, labels2 = ax2.get_legend_handles_labels()
by_label2 = dict(zip(labels2, handles2))
ax2.legend(
    by_label2.values(),
    by_label2.keys(),
    title='Scenario',
    loc='upper right',
    bbox_to_anchor=(0.98, 0.98),
    frameon=True,
)

plt.tight_layout()
plt.show()