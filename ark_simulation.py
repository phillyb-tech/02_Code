
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

fig, ax = plt.subplots()
x = np.linspace(0, 2 * np.pi, 100)
line, = ax.plot(x, np.sin(x))

def update(frame):
    line.set_ydata(np.sin(x + frame / 10.0))
    return line,

ani = animation.FuncAnimation(fig, update, frames=100, interval=50)

try:
    ani.save("test_animation.mp4", writer="ffmpeg")
    print("Test animation saved successfully as test_animation.mp4")
except Exception as e:
    print(f"Error while saving test animation: {e}")
