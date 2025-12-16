"""
Generate a Gantt-style visualization for the baseline (manual transport) scenario.
Relies on the existing simulation inputs defined in ct_scan_shands_des_WIP.py.
"""

import matplotlib.pyplot as plt
import simpy
from matplotlib.patches import Patch

from ct_scan_shands_des_WIP import (
    NUM_SCANNERS,
    DAY_LENGTH_MIN,
    calculate_patient_transport_time,
    generate_exam_duration,
    generate_patient_arrivals_workflow_derived,
)


def simulate_baseline_day():
    """Run one baseline day and collect exam events with start/end times."""
    env = simpy.Environment()
    scanners = simpy.Resource(env, capacity=NUM_SCANNERS)
    events = []

    arrival_times = generate_patient_arrivals_workflow_derived(
        "baseline", deterministic=True
    )

    def patient_process(pid, scheduled_time):
        yield env.timeout(scheduled_time)
        transport_time = calculate_patient_transport_time("baseline")
        yield env.timeout(transport_time)

        request_time = env.now
        with scanners.request() as req:
            yield req
            start = env.now
            exam_time = generate_exam_duration()
            end = start + exam_time
            events.append(
                {
                    "patient_id": pid,
                    "start": start,
                    "end": end,
                    "ct_wait": start - request_time,
                }
            )
            yield env.timeout(exam_time)

    for pid, sched in enumerate(arrival_times):
        env.process(patient_process(pid, sched))

    env.run(until=DAY_LENGTH_MIN + 240)
    events.sort(key=lambda e: e["start"])
    return events


def assign_scanners(events, num_scanners):
    """
    Assign exams to specific scanners using earliest-available logic.
    Returns events with scanner ids and per-scanner idle totals.
    """
    free_times = [0.0] * num_scanners
    total_idle_per_scanner = [0.0] * num_scanners

    for event in events:
        scanner_idx = min(range(num_scanners), key=lambda i: free_times[i])
        idle_gap = max(0.0, event["start"] - free_times[scanner_idx])
        total_idle_per_scanner[scanner_idx] += idle_gap
        free_times[scanner_idx] = event["end"]
        event["scanner"] = scanner_idx

    return events, total_idle_per_scanner


def build_plot_data(events, num_scanners):
    """Organize events by scanner and compute summary stats."""
    events_by_scanner = {i: [] for i in range(num_scanners)}
    for evt in events:
        events_by_scanner[evt["scanner"]].append(evt)

    for evts in events_by_scanner.values():
        evts.sort(key=lambda e: e["start"])

    total_time = max(e["end"] for e in events) if events else 0
    total_active = sum(e["end"] - e["start"] for e in events)
    return events_by_scanner, total_time, total_active


def plot_baseline_schedule():
    """Run the baseline simulation and plot a timeline of scanner activity."""
    raw_events = simulate_baseline_day()
    events, idle_per_scanner = assign_scanners(raw_events, NUM_SCANNERS)
    events_by_scanner, total_time, total_active = build_plot_data(events, NUM_SCANNERS)

    if total_time <= 0:
        print("No events to plot.")
        return

    plot_end = min(total_time, 24 * 60)  # show only the first 24 hours
    avg_idle_per_scanner = sum(idle_per_scanner) / NUM_SCANNERS
    utilization = (total_active / (NUM_SCANNERS * total_time)) * 100 if total_time else 0
    avg_robot_wait = 0.0  # baseline is manual transport

    fig, ax = plt.subplots(figsize=(14, 8))

    bar_height = 0.8
    for scanner_idx in range(NUM_SCANNERS):
        y = scanner_idx
        # Idle background
        ax.barh(
            y,
            total_time,
            left=0,
            height=bar_height,
            color="lightcoral",
            alpha=0.25,
            edgecolor="none",
        )
        # Active segments
        for evt in events_by_scanner.get(scanner_idx, []):
            duration = evt["end"] - evt["start"]
            ax.barh(
                y,
                duration,
                left=evt["start"],
                height=bar_height,
                color="mediumseagreen",
                edgecolor="none",
            )
            ax.text(
                evt["start"] + duration / 2,
                y,
                f"P{evt['patient_id']}",
                ha="center",
                va="center",
                fontsize=8,
                color="black",
            )

    # Hour markers
    hours = 24
    for h in range(hours + 1):
        ax.axvline(h * 60, color="gray", linestyle="--", linewidth=0.5, alpha=0.5)
        ax.text(
            h * 60,
            NUM_SCANNERS + 0.2,
            f"{h}h",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax.set_xlim(0, plot_end)
    ax.set_ylim(-1, NUM_SCANNERS + 1)
    ax.set_xlabel("Time of day (HH:MM)")
    ax.set_ylabel("CT scanner")
    hour_ticks = [h * 60 for h in range(0, 25)]
    ax.set_xticks(hour_ticks)
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25)])
    ax.set_yticks(range(NUM_SCANNERS))
    ax.set_yticklabels([f"Scanner {i+1}" for i in range(NUM_SCANNERS)])
    ax.set_title(
        "CT Scanner Activity - Baseline (Manual Transport)\n(Green=Active, Red=Idle)"
    )

    legend_patches = [
        Patch(color="lightcoral", alpha=0.5, label="Idle"),
        Patch(color="mediumseagreen", label="Active"),
    ]
    ax.legend(handles=legend_patches, loc="upper right")

    stats_text = "\n".join(
        [
            f"Total Patients: {len(events)}",
            f"Avg Idle per Scanner: {avg_idle_per_scanner:.1f} min",
            f"Scanner Utilization: {utilization:.1f}%",
            f"Avg Robot Wait: {avg_robot_wait:.1f} min",
        ]
    )
    ax.text(
        total_time * 0.05,
        NUM_SCANNERS - 0.5,
        stats_text,
        fontsize=9,
        bbox=dict(facecolor="lightsteelblue", alpha=0.7, edgecolor="gray"),
        verticalalignment="top",
    )

    plt.tight_layout()
    plt.savefig("ct_baseline_schedule.png", dpi=200)
    plt.show()


if __name__ == "__main__":
    plot_baseline_schedule()
