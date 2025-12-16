"""
Standalone visualization for CT scanner activity (baseline scenario).
Uses the same simulation logic from ct_scan_shands_des_WIP.py but keeps plotting separate.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from ct_scan_shands_des_WIP import (
    NUM_SCANNERS,
    DAY_LENGTH_MIN,
    simulate_one_day,
    run_many_simulations,
    ROBOT_UPTIME,
    NUM_ROBOTS,
)


def plot_scenario_day(scenario_key, scenario_label):
    """
    Run one scenario day, plot first 24h, and show stats from Table 1 (averages)
    plus robot utilization.
    """
    # Averages that match Table 1
    _, _, avg_idle, _, avg_completed_scans = run_many_simulations(scenario_key)

    # Compute robot utilization from averages (baseline -> 0)
    if scenario_key == "baseline":
        robot_util_pct = 0.0
    else:
        avg_robot_cycle_time = 20.4  # same assumption as main sim
        robot_hours_needed_per_day = (avg_completed_scans * avg_robot_cycle_time) / 60
        robot_hours_available_per_day = NUM_ROBOTS * 24 * ROBOT_UPTIME
        robot_util_pct = (robot_hours_needed_per_day / robot_hours_available_per_day) * 100

    # Single-day events for the Gantt (stochastic, truncated to 24h view)
    day = simulate_one_day(scenario_key)
    events = [e for e in day.get("scanner_events", []) if e.get("start", 0) < DAY_LENGTH_MIN]
    if not events:
        print(f"No events to plot for {scenario_label}.")
        return

    plot_end = DAY_LENGTH_MIN  # 24h window

    # Bucket by scanner
    events_by_scanner = {i: [] for i in range(NUM_SCANNERS)}
    for evt in events:
        events_by_scanner[evt.get("scanner", 0)].append(evt)
    for evts in events_by_scanner.values():
        evts.sort(key=lambda e: e["start"])

    fig, ax = plt.subplots(figsize=(14, 8))
    bar_height = 0.8

    for scanner_idx in range(NUM_SCANNERS):
        y = scanner_idx
        ax.barh(
            y,
            plot_end,
            left=0,
            height=bar_height,
            color="lightcoral",
            alpha=0.25,
            edgecolor="none",
        )
        for evt in events_by_scanner.get(scanner_idx, []):
            if evt["start"] >= plot_end:
                continue
            start = evt["start"]
            end = min(evt["end"], plot_end)
            duration = end - start
            if duration <= 0:
                continue
            ax.barh(
                y,
                duration,
                left=start,
                height=bar_height,
                color="mediumseagreen",
                edgecolor="none",
            )
            ax.text(
                start + duration / 2,
                y,
                f"P{evt['patient_id']}",
                ha="center",
                va="center",
                fontsize=8,
                color="black",
            )

    # Hour markers for 24h
    for h in range(0, 25):
        ax.axvline(h * 60, color="gray", linestyle="--", linewidth=0.5, alpha=0.5)
    ax.set_xlim(0, plot_end)
    ax.set_ylim(-0.5, NUM_SCANNERS - 0.5)
    ax.set_xlabel("Time of day (HH:MM)")
    ax.set_ylabel("CT scanner")
    hour_ticks = [h * 60 for h in range(0, 25)]
    ax.set_xticks(hour_ticks)
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25)])
    ax.set_yticks(range(NUM_SCANNERS))
    ax.set_yticklabels([f"Scanner {i+1}" for i in range(NUM_SCANNERS)])
    ax.set_title(f"CT Scanner Activity - {scenario_label}\n(Green=Active, Red=Idle)")

    legend_patches = [
        Patch(color="lightcoral", alpha=0.5, label="Idle"),
        Patch(color="mediumseagreen", label="Active"),
    ]
    ax.legend(handles=legend_patches, loc="upper right")

    # Use Table 1 averages for the stats box to match the main sim output
    utilization = (avg_completed_scans * 12.11) / (NUM_SCANNERS * DAY_LENGTH_MIN) * 100
    stats_text = "\n".join(
        [
            f"Total Patients (avg/day): {avg_completed_scans:.1f}",
            f"Avg Idle per Scanner: {avg_idle:.1f} min",
            f"Scanner Utilization: {utilization:.1f}%",
            f"Robot Utilization: {robot_util_pct:.1f}%",
        ]
    )
    ax.text(
        plot_end * 0.05,
        NUM_SCANNERS - 0.8,
        stats_text,
        fontsize=9,
        bbox=dict(facecolor="lightsteelblue", alpha=0.7, edgecolor="gray"),
        verticalalignment="top",
    )

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    figs = []
    for key, label in [
        ("baseline", "Baseline (Manual Transport)"),
        ("rovis_only", "9 Rovis - Transport Only"),
        ("rovis_workflow", "9 Rovis - Transport + Workflow"),
    ]:
        fig = plot_scenario_day(key, label)
        if fig:
            figs.append(fig)
    if figs:
        # Show and block so windows stay open until you close them
        plt.show()
