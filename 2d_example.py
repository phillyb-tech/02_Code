import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
import numpy as np
import random
import os
import time

# Set up figure with subplots
fig = plt.figure(figsize=(16, 10), constrained_layout=True)  # Use constrained_layout to avoid overlaps
gs = fig.add_gridspec(3, 3)
ax_map = fig.add_subplot(gs[:, 0])  # Map on the left
ax_collisions = fig.add_subplot(gs[0, 1])  # Collision graph on the top-right
ax_utilization = fig.add_subplot(gs[1, 1])  # Utilization graph in the middle-right
ax_tasks = fig.add_subplot(gs[2, 1])  # Task completion graph on the bottom-right

# Map setup
ax_map.set_xlim(0, 120)
ax_map.set_ylim(0, 80)
ax_map.set_title("Hospital Corridor Map", fontsize=12, pad=10)  # Add padding to the title
ax_map.axis('off')

# Add rooms and areas as rectangles
rooms = [
    {"xy": (0, 60), "width": 20, "height": 20, "label": "ED", "color": "lightgray"},
    {"xy": (20, 60), "width": 40, "height": 20, "label": "In-patients\nand\nED patients", "color": "white"},
    {"xy": (60, 60), "width": 30, "height": 20, "label": "CT scan room", "color": "yellow"},
    {"xy": (90, 60), "width": 30, "height": 20, "label": "Reception\nroom", "color": "white"},
    {"xy": (0, 40), "width": 20, "height": 20, "label": "ED patients\nwaiting room", "color": "white"},
    {"xy": (20, 40), "width": 40, "height": 20, "label": "General\nreport room", "color": "white"},
    {"xy": (60, 40), "width": 30, "height": 20, "label": "Reception\noffice", "color": "white"},
    {"xy": (90, 40), "width": 30, "height": 20, "label": "Waiting\narea", "color": "white"},
    {"xy": (0, 20), "width": 20, "height": 20, "label": "Charging\nStation", "color": "lightblue"},
]
for room in rooms:
    rect = patches.Rectangle(room["xy"], room["width"], room["height"], linewidth=1, edgecolor='black', facecolor=room["color"])
    ax_map.add_patch(rect)
    ax_map.text(
        room["xy"][0] + room["width"] / 2,
        room["xy"][1] + room["height"] / 2,
        room["label"],
        color="black",
        fontsize=8,
        ha="center",
        va="center",
    )

# Robot setup
num_robots = 3
colors = ['red', 'green', 'blue']
paths = [
    np.array([[10, 30], [50, 30], [50, 50], [10, 50], [10, 30]]),  # Robot 1
    np.array([[50, 70], [50, 50], [10, 50], [10, 30], [10, 30]]),  # Robot 2
    np.array([[90, 30], [50, 30], [50, 50], [90, 50], [90, 30]])   # Robot 3
]
positions = [np.copy(path[0]) for path in paths]
progress = [0.0] * num_robots
robot_circles = [plt.Circle(pos, 2, color=colors[i], label=f"Robot {i+1}") for i, pos in enumerate(positions)]
for circle in robot_circles:
    ax_map.add_patch(circle)

# Task setup
tasks = [{"location": (random.randint(20, 100), random.randint(20, 60)), "assigned": False} for _ in range(10)]
task_markers = []
for task in tasks:
    marker = ax_map.plot(task["location"][0], task["location"][1], 'kx', markersize=10, label="Task")[0]
    task_markers.append(marker)

# Collision tracking
collisions = [0] * num_robots
collision_history = [[] for _ in range(num_robots)]

# Initialize time_data
time_data = []  # Track frame numbers for graphs

# Graph setup
ax_collisions.set_xlim(0, 100)
ax_collisions.set_ylim(0, 10)
ax_collisions.set_title("Collisions Over Time", fontsize=12, pad=10)
ax_collisions.set_xlabel("Time (frames)", fontsize=10, labelpad=10)
ax_collisions.set_ylabel("Collisions", fontsize=10, labelpad=10)
collision_lines = [ax_collisions.plot([], [], color=colors[i])[0] for i in range(num_robots)]

ax_utilization.set_xlim(0, 100)
ax_utilization.set_ylim(0, 1)
ax_utilization.set_title("Robot Utilization Over Time", fontsize=12, pad=10)
ax_utilization.set_xlabel("Time (frames)", fontsize=10, labelpad=10)
ax_utilization.set_ylabel("Utilization (%)", fontsize=10, labelpad=10)
utilization_lines = [ax_utilization.plot([], [], color=colors[i])[0] for i in range(num_robots)]
utilization_data = [[] for _ in range(num_robots)]
active_time = [0] * num_robots
idle_time = [0] * num_robots

ax_tasks.set_xlim(0, 100)
ax_tasks.set_ylim(0, 10)
ax_tasks.set_title("Task Completion Over Time", fontsize=12, pad=10)
ax_tasks.set_xlabel("Time (frames)", fontsize=10, labelpad=10)
ax_tasks.set_ylabel("Tasks Completed", fontsize=10, labelpad=10)
task_lines = [ax_tasks.plot([], [], color=colors[i])[0] for i in range(num_robots)]
task_data = [0] * num_robots
task_history = [[] for _ in range(num_robots)]

# Path interpolation
def interpolate_path(path, t):
    if t >= len(path) - 1:
        return path[-1]
    i = int(t)
    alpha = t - i
    return (1 - alpha) * path[i] + alpha * path[i + 1]

# Collision detection
def check_collision(pos1, pos2, threshold=5):
    return np.linalg.norm(np.array(pos1) - np.array(pos2)) < threshold

# Update function
def update(frame):
    time_data.append(frame)
    for i in range(num_robots):
        # Update robot position along its path
        progress[i] += 0.02
        if progress[i] >= len(paths[i]) - 1:
            progress[i] = 0.0  # Reset progress to loop the animation
        pos = interpolate_path(paths[i], progress[i])
        robot_circles[i].center = pos

        # Check for task completion
        for task in tasks:
            if not task["assigned"] and np.linalg.norm(np.array(robot_circles[i].center) - np.array(task["location"])) < 5:
                task["assigned"] = True
                task_data[i] += 1

        # Check for collisions
        for j in range(num_robots):
            if i != j and check_collision(robot_circles[i].center, robot_circles[j].center):
                collisions[i] += 1

        # Update collision graph
        collision_history[i].append(collisions[i])
        collision_lines[i].set_data(time_data, collision_history[i])

        # Update utilization graph
        if any(task["assigned"] for task in tasks):
            active_time[i] += 1
        else:
            idle_time[i] += 1
        utilization = active_time[i] / (active_time[i] + idle_time[i])
        utilization_data[i].append(utilization)
        utilization_lines[i].set_data(time_data, utilization_data[i])

        # Update task completion graph
        task_history[i].append(task_data[i])
        task_lines[i].set_data(time_data, task_history[i])

    return robot_circles + collision_lines + utilization_lines + task_lines + task_markers

# Create the animation
ani = animation.FuncAnimation(fig, update, frames=500, interval=50, blit=False)

# Save the animation as a GIF
try:
    ani.save("hospital_simulation_with_collision_graph.gif", writer="pillow")
    print("Animation saved successfully as hospital_simulation_with_collision_graph.gif")
except Exception as e:
    print(f"Error while saving animation: {e}")

# Play the GIF file automatically
animation_file = "hospital_simulation_with_collision_graph.gif"
animation_path = os.path.join(os.path.dirname(__file__), animation_file)

# Wait for the GIF file to be created
wait_time = 5  # seconds
for _ in range(wait_time):
    if os.path.exists(animation_path):
        print(f"Playing animation: {animation_path}")
        os.startfile(animation_path)  # Opens the file with the default image viewer on Windows
        break
    else:
        print(f"Waiting for animation file to be created...")
        time.sleep(1)
else:
    print(f"Animation file not found after {wait_time} seconds: {animation_path}")
