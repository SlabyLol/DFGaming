
import psutil
import platform
import tkinter as tk
from tkinter import messagebox
import GPUtil
import os
import ctypes
import json
import threading
import time
import winsound
import pygetwindow as gw
import pystray
from PIL import Image, ImageDraw
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# =========================================================
# GLOBAL CONFIG
# =========================================================

APP_NAME = "DFGaming ULTIMATE X"
LEARN_FILE = "learned_apps.json"

boost_active = False
warning_active = False
original_priority = None

system_blacklist = [
    "System", "System Idle Process", "Registry",
    "svchost.exe", "explorer.exe"
]

# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# =========================================================
# LOAD / SAVE LEARNING DATA
# =========================================================

def load_learning():
    if os.path.exists(LEARN_FILE):
        with open(LEARN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_learning():
    with open(LEARN_FILE, "w") as f:
        json.dump(list(learned_apps), f)

learned_apps = load_learning()

# =========================================================
# STARTUP OPTIMIZATION
# =========================================================

def startup_cleanup():
    auto_list = ["Skype.exe", "Teams.exe", "Discord.exe", "OneDrive.exe"]
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] in auto_list:
                p.terminate()
        except:
            pass

# =========================================================
# GAME BOOST
# =========================================================

def activate_boost():
    global boost_active, original_priority
    if not boost_active:
        p = psutil.Process(os.getpid())
        original_priority = p.nice()
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        boost_btn.config(text="GameBoost OFF", bg="red")
        boost_active = True

def deactivate_boost():
    global boost_active
    if boost_active:
        p = psutil.Process(os.getpid())
        p.nice(original_priority)
        boost_btn.config(text="GameBoost ON", bg="green")
        boost_active = False

def toggle_boost():
    if boost_active:
        deactivate_boost()
    else:
        activate_boost()

# =========================================================
# ACTIVE FULLSCREEN WINDOW
# =========================================================

def get_active_fullscreen_window():
    try:
        win = gw.getActiveWindow()
        if win:
            width = win.width
            height = win.height
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            if width >= screen_width and height >= screen_height:
                return win.title
    except:
        pass
    return None

# =========================================================
# HEAVY PROCESS DETECTION
# =========================================================

def get_heaviest_process():
    highest = 0
    heavy_name = "Unknown"
    for p in psutil.process_iter(['name','cpu_percent']):
        try:
            name = p.info['name']
            if name not in system_blacklist:
                cpu = p.cpu_percent(interval=0.1)
                if cpu > highest:
                    highest = cpu
                    heavy_name = name
        except:
            pass
    return heavy_name, highest

# =========================================================
# FPS ESTIMATION
# =========================================================

def estimate_fps(cpu_usage):
    if cpu_usage == 0:
        return 0
    return max(15, int(120 - cpu_usage))

# =========================================================
# PERFORMANCE WARNING
# =========================================================

def performance_warning(app_name, usage):
    global warning_active
    warning_active = True

    learned_apps.add(app_name)
    save_learning()

    winsound.Beep(1200, 400)

    popup = tk.Toplevel(root)
    popup.title("Performance Critical")
    popup.geometry("500x280")
    popup.configure(bg="black")

    tk.Label(
        popup,
        text=f"""
Application detected:

{app_name}

CPU Usage: {round(usage,1)} %

Performance is critical.
""",
        fg="red",
        bg="black",
        font=("Arial",12)
    ).pack(pady=20)

    tk.Button(
        popup,
        text="Activate GameBoost",
        bg="green",
        fg="white",
        width=30,
        command=lambda:[activate_boost(), popup.destroy()]
    ).pack(pady=5)

    tk.Button(
        popup,
        text="Do not activate (Not recommended)",
        bg="darkred",
        fg="white",
        width=30,
        command=popup.destroy
    ).pack(pady=5)

# =========================================================
# BACKGROUND MONITOR THREAD
# =========================================================

def monitor():
    global warning_active

    while True:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        active_game = get_active_fullscreen_window()

        name, usage = get_heaviest_process()

        if active_game and (usage > 85 or cpu > 90):
            if not warning_active:
                performance_warning(name, usage)
        else:
            warning_active = False

        time.sleep(3)

# =========================================================
# SYSTEM INFO
# =========================================================

def get_system_info():
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent()

    try:
        gpu = GPUtil.getGPUs()[0]
        gpu_load = round(gpu.load*100,1)
        gpu_temp = gpu.temperature
        gpu_name = gpu.name
    except:
        gpu_load = 0
        gpu_temp = "N/A"
        gpu_name = "Unknown"

    fps = estimate_fps(cpu)

    return f"""
CPU: {cpu} %
RAM: {ram.percent} %
GPU: {gpu_load} %
GPU Temp: {gpu_temp} °C
Estimated FPS: {fps}

System: {platform.system()} {platform.release()}
GPU: {gpu_name}
"""

# =========================================================
# UI REFRESH
# =========================================================

def refresh():
    system_box.config(state="normal")
    system_box.delete(1.0, tk.END)
    system_box.insert(tk.END, get_system_info())
    system_box.config(state="disabled")

    root.after(2000, refresh)

# =========================================================
# SYSTEM TRAY
# =========================================================

def create_tray():
    image = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((16,16,48,48), fill="green")

    def quit_app(icon, item):
        icon.stop()
        root.destroy()

    icon = pystray.Icon(APP_NAME, image, menu=pystray.Menu(
        pystray.MenuItem("Open", lambda: root.deiconify()),
        pystray.MenuItem("Quit", quit_app)
    ))

    threading.Thread(target=icon.run, daemon=True).start()

# =========================================================
# UI SETUP
# =========================================================

root = tk.Tk()
root.title(APP_NAME)
root.geometry("900x600")
root.configure(bg="black")

tk.Label(root, text=APP_NAME,
         fg="lime", bg="black",
         font=("Arial",22)).pack(pady=10)

system_box = tk.Text(root, height=12,
                     bg="black", fg="white")
system_box.pack()
system_box.config(state="disabled")

boost_btn = tk.Button(root,
                      text="GameBoost ON",
                      bg="green",
                      fg="white",
                      command=toggle_boost)
boost_btn.pack(pady=10)

refresh()

threading.Thread(target=monitor, daemon=True).start()

create_tray()

root.mainloop()
