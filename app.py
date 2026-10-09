import sys
import os
import json
import time
import random
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
import psutil

# Configuration file name
CONFIG_FILE = "config.json"

# Color Palette (8-Bit Retro Arcade Theme)
COLOR_BG = "#2b2b2b"          # Arcade midnight black
COLOR_SURFACE = "#333333"     # Retro console grey
COLOR_TEXT = "#ffffff"        # Neon matrix green
COLOR_TEXT_MUTED = "#aaaaaa"  # Dark grey
COLOR_ACCENT = "#1f6aa5"      # Cyan blue
COLOR_SUCCESS = "#2fa572"     # Neon green
COLOR_DANGER = "#c25e5e"      # Retro neon pink
COLOR_BORDER = "#555555"      # Cyan border

class ProductivityLockerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Productivity App Locker")
        self.root.geometry("500x880")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(True, True)

        # Queue to pass messages from background thread to main GUI thread
        self.message_queue = queue.Queue()

        # Load configuration
        self.load_config()
        self.load_tips()
        self.write_log("Application launched")

        # Keep track of active puzzle dialogs to avoid duplicates
        self.active_puzzle_app = None
        self.last_explanation = ""

        # Keep track of session-unlocked apps: maps app_name -> "pending" or "running"
        self.currently_unlocked = {}
        self.unlock_expirations = {}

        # Build GUI
        self.setup_styles()
        self.create_widgets()

        # Start process monitoring thread
        self.monitor_active = True
        self.monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        self.monitor_thread.start()

        # Periodically check message queue for process alerts
        self.root.after(100, self.check_queue)

    def setup_styles(self):
        import sv_ttk
        sv_ttk.set_theme("dark")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = self.get_default_config()
        else:
            self.config = self.get_default_config()
            self.save_config()
    def load_tips(self):
        tips_file = "tips.json"
        if getattr(sys, 'frozen', False):
            bundled_tips = os.path.join(sys._MEIPASS, tips_file)
            if os.path.exists(bundled_tips):
                tips_file = bundled_tips
                
        if os.path.exists(tips_file):
            try:
                with open(tips_file, "r", encoding="utf-8") as f:
                    self.math_tips = json.load(f)
                if isinstance(self.math_tips, list) and len(self.math_tips) > 0:
                    return
            except Exception as e:
                print(f"Error loading tips: {e}")
        
        # Fallback default tips list
        self.math_tips = [
            {"title": "Quick Division by 5", "desc": "Multiply the number by 2 and move the decimal point one place to the left!\nExample: 135 / 5  =>  135 * 2 = 270  =>  27.0"},
            {"title": "Multiplying by 11", "desc": "Add the two digits together and put the sum in the middle!\nExample: 35 * 11  =>  3 + 5 = 8  =>  385"},
            {"title": "Squaring Numbers Ending in 5", "desc": "Multiply the first digit by (first digit + 1) and append 25.\nExample: 75²  =>  7 * 8 = 56  =>  5625"},
            {"title": "Quick Division by 4", "desc": "To divide any number by 4 quickly, just halve the number twice!\nExample: 148 / 4  =>  148 / 2 = 74  =>  74 / 2 = 37"},
            {"title": "Quick Multiplication by 9", "desc": "Multiply the number by 10 and subtract the original number.\nExample: 43 * 9  =>  430 - 43 = 387"}
        ]

    def play_sound(self, sound_type):
        try:
            import winsound
            if sound_type == "success":
                # Two rising notes
                winsound.Beep(523, 100) # C5
                winsound.Beep(659, 150) # E5
            elif sound_type == "error":
                # Low warning buzz
                winsound.Beep(150, 250)
            elif sound_type == "victory":
                # Chiptune fanfare
                winsound.Beep(523, 100) # C5
                winsound.Beep(659, 100) # E5
                winsound.Beep(784, 100) # G5
                winsound.Beep(1046, 250) # C6
        except Exception:
            pass

    def trigger_sound(self, sound_type):
        threading.Thread(target=self.play_sound, args=(sound_type,), daemon=True).start()

    def write_log(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        try:
            with open("activity.log", "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"Log error: {e}")

    def show_log_window(self):
        log_win = tk.Toplevel(self.root)
        log_win.title("Activity Logs")
        log_win.geometry("480x400")
        log_win.configure(bg=COLOR_BG)
        log_win.resizable(False, False)
        
        # Header
        lbl_title = ttk.Label(log_win, text="📋 System Activity Logs")
        lbl_title.pack(pady=10)
        
        # Log textbox frame
        log_frame = ttk.Frame(log_win, padding=10)
        log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Read log content
        log_content = ""
        if os.path.exists("activity.log"):
            try:
                with open("activity.log", "r", encoding="utf-8") as f:
                    # Show last 200 lines
                    lines = f.readlines()
                    log_content = "".join(lines[-200:])
            except Exception as e:
                log_content = f"Error reading logs: {e}"
        else:
            log_content = "No activity logs recorded yet."
            
        text_box = tk.Text(
            log_frame,
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            selectbackground=COLOR_ACCENT,
            selectforeground=COLOR_BG,
            font=("Fixedsys", 9, "bold"),
            wrap="word",
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLOR_BORDER
        )
        text_box.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=text_box.yview)
        scrollbar.pack(side="right", fill="y")
        text_box.config(yscrollcommand=scrollbar.set)
        
        # Write and lock text box
        text_box.insert(tk.END, log_content)
        text_box.config(state="disabled")
        # Auto scroll to bottom
        text_box.see(tk.END)

    def get_default_config(self):
        return {
            "blocked_apps": ["notepad.exe"],
            "difficulty": "medium",
            "problem_types": ["addition", "subtraction", "multiplication", "division", "factoring", "geometry", "formulas"],
            "required_questions": 5,
            "last_completed_challenge": "",
            "current_streak": 0,
            "challenge_history": []
        }

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def create_widgets(self):
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_label = ttk.Label(header_frame, text="Productivity App Locker")
        title_label.pack(side="left")
        
        version_label = ttk.Label(header_frame, text="v2.2.0")
        version_label.pack(side="left", padx=(5, 0), anchor="s")
        
        self.status_label = ttk.Label(header_frame, text="● Monitoring Active")
        self.status_label.pack(side="right", padx=(10, 0))
        
        btn_logs = ttk.Button(header_frame, text="📋 Logs", command=self.show_log_window, width=8)
        btn_logs.pack(side="right")

        # Separator line
        sep = ttk.Separator(self.root, orient="horizontal")
        sep.pack(fill="x", padx=20, pady=5)

        # Blocked apps list panel (Card)
        list_frame = ttk.Frame(self.root, padding=15)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        lbl_list = ttk.Label(list_frame, text="Blocked Applications List")
        lbl_list.pack(anchor="w", pady=(0, 10))

        # Listbox for apps
        self.apps_listbox = tk.Listbox(
            list_frame, 
            bg=COLOR_BG, 
            fg=COLOR_TEXT, 
            selectbackground=COLOR_ACCENT, 
            selectforeground=COLOR_BG,
            highlightcolor=COLOR_BORDER,
            highlightbackground=COLOR_BORDER,
            borderwidth=1,
            relief="flat",
            font=("Fixedsys", 10, "bold"),
            height=6
        )
        self.apps_listbox.pack(fill="both", expand=True, side="left")

        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.apps_listbox.yview)
        scrollbar.pack(fill="y", side="right")
        self.apps_listbox.config(yscrollcommand=scrollbar.set)

        self.refresh_listbox()

        # Add/Remove app tools
        tool_frame = ttk.Frame(self.root, padding=(20, 5))
        tool_frame.pack(fill="x")

        self.add_entry = ttk.Entry(tool_frame, font=("Fixedsys", 10, "bold"))
        self.add_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=3)
        self.add_entry.insert(0, "e.g., chrome.exe")
        self.add_entry.bind("<FocusIn>", self.clear_placeholder)
        self.add_entry.bind("<FocusOut>", self.add_placeholder)
        self.add_entry.bind("<Return>", lambda e: self.add_app())

        btn_browse = ttk.Button(tool_frame, text="Browse...", command=self.browse_app)
        btn_browse.pack(side="left", padx=5)

        btn_add = ttk.Button(tool_frame, text="Add App", command=self.add_app)
        btn_add.pack(side="left", padx=5)

        btn_remove = ttk.Button(tool_frame, text="Remove", command=self.remove_app)
        btn_remove.pack(side="left")

        # Settings panel
        settings_frame = ttk.Frame(self.root, padding=12)
        settings_frame.pack(fill="x", padx=20, pady=8)

        lbl_settings = ttk.Label(settings_frame, text="Locker Settings")
        lbl_settings.pack(anchor="w", pady=(0, 10))

        # Grid layout for options
        options_grid = ttk.Frame(settings_frame)
        options_grid.pack(fill="x")
        options_grid.configure(style="Surface.TFrame")

        # Difficulty setting
        ttk.Label(options_grid, text="Math Difficulty:", background=COLOR_SURFACE).grid(row=0, column=0, sticky="w", pady=5)
        self.difficulty_var = tk.StringVar(value=self.config.get("difficulty", "medium").capitalize())
        difficulty_combo = ttk.Combobox(options_grid, textvariable=self.difficulty_var, values=["Easy", "Medium", "Hard"], state="readonly", width=15)
        difficulty_combo.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        difficulty_combo.bind("<<ComboboxSelected>>", self.save_settings_from_gui)

        # Questions to Unlock setting
        ttk.Label(options_grid, text="Questions to Unlock:", background=COLOR_SURFACE).grid(row=1, column=0, sticky="w", pady=5)
        self.questions_var = tk.IntVar(value=self.config.get("required_questions", 10))
        questions_spin = ttk.Spinbox(
            options_grid, 
            from_=1, 
            to=100, 
            textvariable=self.questions_var, 
            width=14,
            command=self.save_settings_from_gui
        )
        questions_spin.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        questions_spin.bind("<FocusOut>", self.save_settings_from_gui)
        questions_spin.bind("<KeyRelease>", self.save_settings_from_gui)

        # Startup Run setting
        ttk.Label(options_grid, text="Startup Run:", background=COLOR_SURFACE).grid(row=2, column=0, sticky="w", pady=5)
        self.startup_var = tk.BooleanVar(value=self.check_startup_status())
        self.startup_chk = tk.Checkbutton(
            options_grid,
            text="Launch on Windows Startup",
            variable=self.startup_var,
            onvalue=True,
            offvalue=False,
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            selectcolor=COLOR_BG,
            activebackground=COLOR_SURFACE,
            activeforeground=COLOR_TEXT,
            font=("Fixedsys", 9, "bold"),
            command=self.toggle_startup
        )
        self.startup_chk.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        # Problem Types checkboxes
        ttk.Label(options_grid, text="Problem Types:", background=COLOR_SURFACE).grid(row=3, column=0, sticky="nw", pady=5)
        
        types_frame = ttk.Frame(options_grid)
        types_frame.grid(row=3, column=1, columnspan=2, sticky="w", padx=10, pady=5)
        
        self.type_vars = {}
        active_types = self.config.get("problem_types", ["addition", "subtraction", "multiplication", "division", "factoring", "geometry", "formulas"])
        
        options = [
            ("Addition", "addition"),
            ("Subtraction", "subtraction"),
            ("Multiplication", "multiplication"),
            ("Division", "division"),
            ("Factoring", "factoring"),
            ("Geometry", "geometry"),
            ("Formulas", "formulas")
        ]
        
        for i, (label, name) in enumerate(options):
            var = tk.BooleanVar(value=(name in active_types))
            self.type_vars[name] = var
            chk = tk.Checkbutton(
                types_frame, 
                text=label, 
                variable=var, 
                onvalue=True, 
                offvalue=False,
                bg=COLOR_SURFACE,
                fg=COLOR_TEXT,
                selectcolor=COLOR_BG,
                activebackground=COLOR_SURFACE,
                activeforeground=COLOR_TEXT,
                font=("Fixedsys", 9),
                command=self.save_settings_from_gui
            )
            chk.grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 10), pady=2)

        # Dashboard Panel (Card)
        dashboard_frame = ttk.Frame(self.root, padding=15)
        dashboard_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        lbl_dash = ttk.Label(dashboard_frame, text="Daily Practice Dashboard")
        lbl_dash.pack(anchor="w", pady=(0, 5))
        
        dash_header = ttk.Frame(dashboard_frame)
        dash_header.pack(fill="x", pady=2)
        
        # Streak Count
        streak = self.config.get("current_streak", 0)
        self.lbl_streak = ttk.Label(
            dash_header, 
            text=f"Current Streak: {streak} Days 🔥", 
            font=("Fixedsys", 10, "bold"), 
            foreground=COLOR_ACCENT,
            background=COLOR_SURFACE
        )
        self.lbl_streak.pack(side="left")
        
        # Total Challenges completed
        total_completed = len(self.config.get("challenge_history", []))
        self.lbl_total = ttk.Label(
            dash_header,
            text=f"Total Practiced: {total_completed} Days",
            font=("Fixedsys", 9),
            foreground=COLOR_TEXT,
            background=COLOR_SURFACE
        )
        self.lbl_total.pack(side="right")
        
        # 30-Day Grid Canvas
        self.canvas_grid = tk.Canvas(
            dashboard_frame, 
            height=45, 
            bg=COLOR_SURFACE, 
            highlightthickness=0
        )
        self.canvas_grid.pack(fill="x", pady=(5, 0))
        
        # Draw initial grid
        self.draw_streak_grid()

        # Tips Panel (Card)
        tips_frame = ttk.Frame(self.root, padding=12)
        tips_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        tips_header = ttk.Frame(tips_frame)
        tips_header.pack(fill="x")
        
        lbl_tips_title = ttk.Label(tips_header, text="💡 Math Tip & Tutorial")
        lbl_tips_title.pack(side="left")
        
        btn_next_tip = ttk.Button(tips_header, text="Next Tip →", command=self.show_next_tip)
        btn_next_tip.pack(side="right")
        
        self.lbl_tip_title = ttk.Label(tips_frame, text="", font=("Fixedsys", 9, "bold"), foreground=COLOR_ACCENT, background=COLOR_SURFACE)
        self.lbl_tip_title.pack(anchor="w", pady=(5, 2))
        
        self.lbl_tip_desc = ttk.Label(tips_frame, text="", font=("Fixedsys", 9), foreground=COLOR_TEXT, justify="left", background=COLOR_SURFACE, wraplength=440)
        self.lbl_tip_desc.pack(anchor="w", pady=(0, 2))
        
        # Initial tip selection
        if self.math_tips:
            self.current_tip_index = random.randint(0, len(self.math_tips) - 1)
        else:
            self.current_tip_index = 0
            
        self.update_tip_display()

        # Status footer
        footer_label = ttk.Label(self.root, text="To lock/block an application, write its executable name (e.g. 'chrome.exe').\nSolving the math problem unlocks it until you close the application.")
        footer_label.pack(fill="x", padx=20, pady=(0, 10))

    def draw_streak_grid(self):
        self.canvas_grid.delete("all")
        
        import datetime
        today = datetime.date.today()
        history = set(self.config.get("challenge_history", []))
        
        box_size = 11
        spacing = 3
        start_x = 10
        start_y = 5
        
        for i in range(30):
            day_delta = datetime.timedelta(days=(29 - i))
            check_date = (today - day_delta).strftime("%Y-%m-%d")
            
            x1 = start_x + i * (box_size + spacing)
            y1 = start_y
            x2 = x1 + box_size
            y2 = y1 + box_size
            
            if check_date in history:
                color = COLOR_SUCCESS
            else:
                color = COLOR_BORDER
                
            self.canvas_grid.create_rectangle(
                x1, y1, x2, y2, 
                fill=color, 
                outline=COLOR_SURFACE, 
                width=1
            )
            
        self.canvas_grid.create_text(
            start_x, start_y + box_size + 12, 
            text="30 days ago", 
            fill=COLOR_TEXT_MUTED, 
            anchor="w", 
            font=("Fixedsys", 8, "bold")
        )
        self.canvas_grid.create_text(
            start_x + 29 * (box_size + spacing) + box_size, start_y + box_size + 12, 
            text="Today", 
            fill=COLOR_TEXT_MUTED, 
            anchor="e", 
            font=("Fixedsys", 8, "bold")
        )

    def trigger_confetti_animation(self):
        if not hasattr(self, 'canvas_grid'):
            return
        self.confetti_active = True
        self.confetti_particles = []
        colors = ["#ff007f", "#00ffff", "#39ff14", "#ffff00", "#ffaa00", "#ff00ff"]
        for _ in range(60):
            self.confetti_particles.append({
                "x": random.randint(10, 480),
                "y": random.randint(-50, 0),
                "w": random.randint(4, 8),
                "h": random.randint(4, 8),
                "dy": random.uniform(1.5, 4.0),
                "dx": random.uniform(-1.0, 1.0),
                "color": random.choice(colors)
            })
        self.animate_confetti(start_time=time.time())

    def animate_confetti(self, start_time):
        if not hasattr(self, 'canvas_grid'):
            return
        if not self.confetti_active:
            return
            
        if time.time() - start_time > 3.5:
            self.confetti_active = False
            self.draw_streak_grid()
            return
            
        self.canvas_grid.delete("all")
        
        import datetime
        today = datetime.date.today()
        history = set(self.config.get("challenge_history", []))
        box_size = 11
        spacing = 3
        start_x = 10
        start_y = 5
        
        for i in range(30):
            day_delta = datetime.timedelta(days=(29 - i))
            check_date = (today - day_delta).strftime("%Y-%m-%d")
            x1 = start_x + i * (box_size + spacing)
            y1 = start_y
            x2 = x1 + box_size
            y2 = y1 + box_size
            
            if check_date in history:
                fill_color = COLOR_SUCCESS
            else:
                fill_color = COLOR_BORDER
            self.canvas_grid.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline=COLOR_BG)
            
        for p in self.confetti_particles:
            p["x"] += p["dx"]
            p["y"] += p["dy"]
            if p["x"] < 0:
                p["x"] = 490
            elif p["x"] > 495:
                p["x"] = 5
            if p["y"] > 45:
                p["y"] = random.randint(-20, 0)
                p["x"] = random.randint(10, 480)
                
            x1 = p["x"]
            y1 = p["y"]
            x2 = x1 + p["w"]
            y2 = y1 + p["h"]
            self.canvas_grid.create_rectangle(x1, y1, x2, y2, fill=p["color"], outline="")
            
        self.root.after(30, lambda: self.animate_confetti(start_time))

    def clear_placeholder(self, event):
        if self.add_entry.get() == "e.g., chrome.exe":
            self.add_entry.delete(0, tk.END)

    def add_placeholder(self, event):
        if not self.add_entry.get():
            self.add_entry.insert(0, "e.g., chrome.exe")

    def refresh_listbox(self):
        self.apps_listbox.delete(0, tk.END)
        for app in sorted(self.config.get("blocked_apps", [])):
            self.apps_listbox.insert(tk.END, app)

    def browse_app(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Application to Block",
            filetypes=[("Executable Files", "*.exe")]
        )
        if file_path:
            app_name = os.path.basename(file_path).lower()
            self.add_entry.delete(0, tk.END)
            self.add_entry.insert(0, app_name)
            self.add_app()

    def add_app(self):
        app_name = self.add_entry.get().strip().lower()
        if not app_name or app_name == "e.g., chrome.exe":
            return
        
        if not app_name.endswith(".exe"):
            app_name += ".exe"

        if app_name == "app.py" or app_name == "python.exe" or app_name == "py.exe":
            messagebox.showwarning("Warning", "You cannot lock Python/App itself!")
            return

        blocked_list = self.config.setdefault("blocked_apps", [])
        if app_name not in blocked_list:
            blocked_list.append(app_name)
            self.write_log(f"App blocklist updated: added '{app_name}'")
            self.save_config()
            self.refresh_listbox()
            self.add_entry.delete(0, tk.END)
            self.add_placeholder(None)

    def remove_app(self):
        selected_indices = self.apps_listbox.curselection()
        if not selected_indices:
            return
        
        app_name = self.apps_listbox.get(selected_indices[0])
        blocked_list = self.config.get("blocked_apps", [])
        if app_name in blocked_list:
            blocked_list.remove(app_name)
            self.write_log(f"App blocklist updated: removed '{app_name}'")
            self.save_config()
            self.refresh_listbox()

    def check_startup_status(self):
        try:
            startup_folder = os.path.join(os.getenv('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            shortcut_path = os.path.join(startup_folder, 'ProductivityLocker.lnk')
            return os.path.exists(shortcut_path)
        except Exception:
            return False

    def toggle_startup(self):
        try:
            startup_folder = os.path.join(os.getenv('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            shortcut_path = os.path.normpath(os.path.join(startup_folder, 'ProductivityLocker.lnk')).replace('"', '`"')
            
            if self.startup_var.get():
                if getattr(sys, 'frozen', False):
                    target_path = sys.executable
                    working_dir = os.path.dirname(target_path)
                else:
                    target_path = sys.executable
                    script_path = os.path.abspath(__file__)
                    working_dir = os.path.dirname(script_path)
                    
                target_path = os.path.normpath(target_path).replace('"', '`"')
                working_dir = os.path.normpath(working_dir).replace('"', '`"')
                
                import subprocess
                if getattr(sys, 'frozen', False):
                    cmd = f'$s = (New-Object -ComObject WScript.Shell).CreateShortcut("{shortcut_path}"); $s.TargetPath = "{target_path}"; $s.WorkingDirectory = "{working_dir}"; $s.Save()'
                else:
                    script_path = os.path.normpath(script_path).replace('"', '`"')
                    cmd = f'$s = (New-Object -ComObject WScript.Shell).CreateShortcut("{shortcut_path}"); $s.TargetPath = "{target_path}"; $s.Arguments = "`"{script_path}`""; $s.WorkingDirectory = "{working_dir}"; $s.Save()'
                
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(['powershell', '-Command', cmd], capture_output=True, creationflags=creationflags)
                self.write_log("Startup enabled: Shortcut created in Windows Startup folder")
            else:
                shortcut_path_plain = os.path.join(startup_folder, 'ProductivityLocker.lnk')
                if os.path.exists(shortcut_path_plain):
                    os.remove(shortcut_path_plain)
                    self.write_log("Startup disabled: Shortcut removed from Windows Startup folder")
        except Exception as e:
            self.write_log(f"Error toggling startup: {e}")
            messagebox.showerror("Error", f"Could not toggle startup shortcut:\n{e}")

    def save_settings_from_gui(self, event=None):
        self.config["difficulty"] = self.difficulty_var.get().lower()
        
        # Save number of questions
        try:
            req_q = int(self.questions_var.get())
            if req_q < 1:
                req_q = 1
            elif req_q > 100:
                req_q = 100
        except (ValueError, tk.TclError):
            req_q = 10
        
        self.questions_var.set(req_q)
        self.config["required_questions"] = req_q

        # Collect checked problem types
        checked = [name for name, var in self.type_vars.items() if var.get()]
        
        if not checked:
            messagebox.showwarning("Warning", "At least one problem type must be selected! Defaulting to Addition.")
            self.type_vars["addition"].set(True)
            checked = ["addition"]
            
        self.config["problem_types"] = checked
        self.save_config()

    def monitor_processes(self):
        import datetime
        import time
        while self.monitor_active:
            try:
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                challenge_completed_today = (self.config.get("last_completed_challenge") == today_str)

                # Check for expired apps
                now = time.time()
                for app in list(self.currently_unlocked.keys()):
                    expires_at = self.unlock_expirations.get(app)
                    if expires_at and now >= expires_at:
                        self.kill_app_processes(app)
                        if app in self.currently_unlocked:
                            del self.currently_unlocked[app]
                        if app in self.unlock_expirations:
                            del self.unlock_expirations[app]

                blocked_apps = set(self.config.get("blocked_apps", []))
                running_blocked_apps = set()
                
                # Group active processes by name
                app_pids = {}
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        pname = proc.info['name']
                        if not pname:
                            continue
                        pname_lower = pname.lower()
                        if pname_lower in blocked_apps:
                            app_pids.setdefault(pname_lower, []).append(proc.info['pid'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                for app_name, pids in app_pids.items():
                    if challenge_completed_today:
                        running_blocked_apps.add(app_name)
                        self.currently_unlocked[app_name] = "running"
                    else:
                        if app_name not in self.currently_unlocked:
                            if self.active_puzzle_app is None:
                                self.message_queue.put((app_name, pids))
                        else:
                            running_blocked_apps.add(app_name)
                            if self.currently_unlocked[app_name] == "pending":
                                self.currently_unlocked[app_name] = "running"
                            
                for app in list(self.currently_unlocked.keys()):
                    state = self.currently_unlocked[app]
                    if state == "running" and app not in running_blocked_apps:
                        del self.currently_unlocked[app]
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(1.5)

    def check_queue(self):
        try:
            while True:
                msg = self.message_queue.get_nowait()
                app_name, pids = msg
                if self.active_puzzle_app is None and app_name not in self.currently_unlocked:
                    self.active_puzzle_app = app_name
                    self.show_puzzle_dialog(app_name, pids)
                self.message_queue.task_done()
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def generate_geometry_problem(self, difficulty):
        if difficulty == "easy":
            sub_type = random.choice(["rect_area", "rect_perim", "tri_area", "square_area", "square_perim", "tri_perim"])
            if sub_type == "rect_area":
                w = random.randint(3, 12)
                h = random.randint(3, 12)
                ans = w * h
                self.current_shape_data = {"type": "rectangle", "w": w, "h": h}
                self.last_explanation = f"Step-by-step explanation:\n1. Area of a rectangle = width * height.\n2. Area = {w} * {h} = {ans}."
                return f"Geometry: Find the area of a\nrectangle with width {w} and height {h}.", ans, False
            elif sub_type == "rect_perim":
                w = random.randint(3, 15)
                h = random.randint(3, 15)
                ans = 2 * (w + h)
                self.current_shape_data = {"type": "rectangle", "w": w, "h": h}
                self.last_explanation = f"Step-by-step explanation:\n1. Perimeter of a rectangle = 2 * (width + height).\n2. Perimeter = 2 * ({w} + {h}) = 2 * {w + h} = {ans}."
                return f"Geometry: Find the perimeter of a\nrectangle with width {w} and height {h}.", ans, False
            elif sub_type == "tri_area":
                b = random.randint(2, 10) * 2
                h = random.randint(3, 12)
                ans = (b * h) // 2
                self.current_shape_data = {"type": "triangle_area", "b": b, "h": h}
                self.last_explanation = f"Step-by-step explanation:\n1. Area of a triangle = (base * height) / 2.\n2. Area = ({b} * {h}) / 2 = {b * h} / 2 = {ans}."
                return f"Geometry: Find the area of a\ntriangle with base {b} and height {h}.", ans, False
            elif sub_type == "square_area":
                s = random.randint(3, 12)
                ans = s * s
                self.current_shape_data = {"type": "square", "s": s}
                self.last_explanation = f"Step-by-step explanation:\n1. Area of a square = side².\n2. Area = {s} * {s} = {ans}."
                return f"Geometry: Find the area of a square\nwith side length {s}.", ans, False
            elif sub_type == "square_perim":
                s = random.randint(3, 15)
                ans = 4 * s
                self.current_shape_data = {"type": "square", "s": s}
                self.last_explanation = f"Step-by-step explanation:\n1. Perimeter of a square = 4 * side.\n2. Perimeter = 4 * {s} = {ans}."
                return f"Geometry: Find the perimeter of a square\nwith side length {s}.", ans, False
            else: # tri_perim
                is_equilateral = random.choice([True, False])
                if is_equilateral:
                    s = random.randint(4, 20)
                    ans = 3 * s
                    self.current_shape_data = {"type": "triangle_perim", "is_eq": True, "s": s}
                    self.last_explanation = f"Step-by-step explanation:\n1. Perimeter of an equilateral triangle = 3 * side.\n2. Perimeter = 3 * {s} = {ans}."
                    return f"Geometry: Find the perimeter of an equilateral\ntriangle with side length {s}.", ans, False
                else:
                    a = random.randint(4, 15)
                    b = random.randint(3, 12)
                    ans = 2 * a + b
                    self.current_shape_data = {"type": "triangle_perim", "is_eq": False, "a": a, "b": b}
                    self.last_explanation = f"Step-by-step explanation:\n1. Perimeter of an isosceles triangle = 2 * leg + base.\n2. Perimeter = 2 * {a} + {b} = {2 * a} + {b} = {ans}."
                    return f"Geometry: Find the perimeter of an isosceles\ntriangle with legs {a} and base {b}.", ans, False
        elif difficulty == "hard":
            sub_type = random.choice(["missing_leg", "shaded_area", "prism_volume", "cylinder_volume"])
            if sub_type == "missing_leg":
                triples = [(5, 12, 13), (8, 15, 17), (7, 24, 25), (9, 40, 41), (12, 35, 37), (20, 21, 29), (15, 20, 25)]
                a, b, c = random.choice(triples)
                self.current_shape_data = {"type": "missing_leg", "b": b, "c": c}
                self.last_explanation = f"Step-by-step explanation:\n1. By Pythagorean theorem: leg1² + leg2² = hypotenuse².\n2. leg1² + {b}² = {c}² => leg1² + {b**2} = {c**2}.\n3. leg1² = {c**2} - {b**2} = {a**2}.\n4. leg1 = √{a**2} = {a}."
                return f"Geometry: Find the missing leg of a right\ntriangle with hypotenuse {c} and one leg {b}.", a, False
            elif sub_type == "shaded_area":
                s = 14
                r = 7
                ans = 42
                self.current_shape_data = {"type": "shaded_area"}
                self.last_explanation = f"Step-by-step explanation:\n1. Area of square = side² = 14 * 14 = 196.\n2. Area of inscribed circle = pi * radius² ≈ (22/7) * 7 * 7 = 154.\n3. Shaded Area = Square Area - Circle Area = 196 - 154 = 42."
                return f"Geometry: Find the shaded area of a square of\nside 14 with an inscribed circle (radius 7)\nremoved (use pi ≈ 22/7).", ans, False
            elif sub_type == "prism_volume":
                l = random.randint(5, 12)
                w = random.randint(4, 9)
                h = random.randint(4, 8)
                ans = l * w * h
                self.current_shape_data = {"type": "prism", "l": l, "w": w, "h": h}
                self.last_explanation = f"Step-by-step explanation:\n1. Volume of a rectangular prism = length * width * height.\n2. Volume = {l} * {w} * {h} = {ans}."
                return f"Geometry: Find the volume of a rectangular\nprism with length {l}, width {w}, and height {h}.", ans, False
            else: # cylinder_volume
                r = 7
                h = random.randint(3, 10)
                ans = 154 * h
                self.current_shape_data = {"type": "cylinder", "h": h}
                self.last_explanation = f"Step-by-step explanation:\n1. Volume of a cylinder = pi * r² * height.\n2. Base area = pi * 7² ≈ (22/7) * 49 = 154.\n3. Volume = 154 * {h} = {ans}."
                return f"Geometry: Find the volume of a cylinder with\nradius 7 and height {h} (use pi ≈ 22/7).", ans, False
        else: # medium
            sub_type = random.choice(["pythagorean", "circle_area", "circle_circum", "trapezoid"])
            if sub_type == "pythagorean":
                triples = [(3, 4, 5), (5, 12, 13), (6, 8, 10), (8, 15, 17), (9, 12, 15), (12, 16, 20)]
                a, b, c = random.choice(triples)
                if random.choice([True, False]):
                    a, b = b, a
                self.current_shape_data = {"type": "pythagorean", "a": a, "b": b}
                self.last_explanation = f"Step-by-step explanation:\n1. By Pythagorean theorem: hypotenuse² = leg1² + leg2².\n2. hypotenuse² = {a}² + {b}² = {a**2} + {b**2} = {c**2}.\n3. hypotenuse = √{c**2} = {c}."
                return f"Geometry: Find the hypotenuse of a right\ntriangle with legs {a} and {b}.", c, False
            elif sub_type == "circle_area":
                r = random.choice([7, 14])
                ans = (22 * r * r) // 7
                self.current_shape_data = {"type": "circle", "r": r}
                self.last_explanation = f"Step-by-step explanation:\n1. Area of a circle = pi * r².\n2. Area ≈ (22/7) * {r} * {r} = 22 * {r} * {r // 7} = {ans}."
                return f"Geometry: Find the area of a circle\nwith radius {r} (use pi ≈ 22/7).", ans, False
            elif sub_type == "circle_circum":
                r = random.choice([7, 14, 21])
                ans = (2 * 22 * r) // 7
                self.current_shape_data = {"type": "circle", "r": r}
                self.last_explanation = f"Step-by-step explanation:\n1. Circumference of a circle = 2 * pi * r.\n2. Circumference ≈ 2 * (22/7) * {r} = 2 * 22 * {r // 7} = {ans}."
                return f"Geometry: Find the circumference of\na circle with radius {r} (use pi ≈ 22/7).", ans, False
            else: # trapezoid
                a = random.randint(3, 15)
                if a % 2 == 0:
                    b = random.randint(2, 8) * 2
                else:
                    b = random.randint(1, 7) * 2 + 1
                h = random.randint(2, 10)
                ans = ((a + b) * h) // 2
                self.current_shape_data = {"type": "trapezoid", "a": a, "b": b, "h": h}
                self.last_explanation = f"Step-by-step explanation:\n1. Area of a trapezoid = ((base1 + base2) * height) / 2.\n2. Area = (({a} + {b}) * {h}) / 2 = ({a + b} * {h}) / 2 = {ans}."
                return f"Geometry: Find the area of a trapezoid\nwith bases {a} and {b}, and height {h}.", ans, False

    def draw_geometry_shape(self, canvas):
        if not self.current_shape_data:
            return
            
        canvas.delete("all")
        shape_type = self.current_shape_data.get("type")
        cx, cy = 100, 60
        
        if shape_type == "rectangle":
            rect_w = 100
            rect_h = 60
            x1 = cx - rect_w // 2
            y1 = cy - rect_h // 2
            x2 = cx + rect_w // 2
            y2 = cy + rect_h // 2
            canvas.create_rectangle(x1, y1, x2, y2, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            w_val = self.current_shape_data.get("w")
            h_val = self.current_shape_data.get("h")
            canvas.create_text(cx, y2 + 10, text=f"{w_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_text(x2 + 12, cy, text=f"{h_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            
        elif shape_type == "square":
            s_val = self.current_shape_data.get("s")
            side = 70
            x1 = cx - side // 2
            y1 = cy - side // 2
            x2 = cx + side // 2
            y2 = cy + side // 2
            canvas.create_rectangle(x1, y1, x2, y2, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_text(cx, y2 + 10, text=f"{s_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_text(x2 + 12, cy, text=f"{s_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            
        elif shape_type == "triangle_area":
            b_val = self.current_shape_data.get("b")
            h_val = self.current_shape_data.get("h")
            x1 = cx - 50
            y1 = cy + 30
            x2 = cx + 50
            y2 = cy + 30
            x3 = cx - 10
            y3 = cy - 30
            canvas.create_polygon(x1, y1, x2, y2, x3, y3, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_line(x3, y3, x3, y2, dash=(3, 3), fill=COLOR_ACCENT, width=1.5)
            canvas.create_text(cx, y2 + 10, text=f"base={b_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_text(x3 - 25, (y3 + y2) // 2, text=f"h={h_val}", fill=COLOR_ACCENT, font=("Fixedsys", 9, "bold"))
            
        elif shape_type == "triangle_perim":
            x1 = cx - 50
            y1 = cy + 30
            x2 = cx + 50
            y2 = cy + 30
            x3 = cx
            y3 = cy - 30
            canvas.create_polygon(x1, y1, x2, y2, x3, y3, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            is_eq = self.current_shape_data.get("is_eq")
            if is_eq:
                s_val = self.current_shape_data.get("s")
                canvas.create_text(cx, y2 + 10, text=f"{s_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
                canvas.create_text(cx - 35, cy, text=f"{s_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
                canvas.create_text(cx + 35, cy, text=f"{s_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            else:
                a_val = self.current_shape_data.get("a")
                b_val = self.current_shape_data.get("b")
                canvas.create_text(cx, y2 + 10, text=f"{b_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
                canvas.create_text(cx - 35, cy, text=f"{a_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
                canvas.create_text(cx + 35, cy, text=f"{a_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
                
        elif shape_type == "circle":
            r_val = self.current_shape_data.get("r")
            rad = 40
            canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_line(cx, cy, cx + rad, cy, fill=COLOR_ACCENT, width=2)
            canvas.create_text(cx + rad // 2, cy - 10, text=f"r={r_val}", fill=COLOR_ACCENT, font=("Fixedsys", 9, "bold"))
            
        elif shape_type == "trapezoid":
            a_val = self.current_shape_data.get("a")
            b_val = self.current_shape_data.get("b")
            h_val = self.current_shape_data.get("h")
            x1 = cx - 30
            y1 = cy - 25
            x2 = cx + 30
            y2 = cy - 25
            x3 = cx + 60
            y3 = cy + 25
            x4 = cx - 60
            y4 = cy + 25
            canvas.create_polygon(x1, y1, x2, y2, x3, y3, x4, y4, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_line(x1, y1, x1, y4, dash=(3, 3), fill=COLOR_ACCENT, width=1.5)
            canvas.create_text(cx, y1 - 10, text=f"a={a_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_text(cx, y4 + 10, text=f"b={b_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_text(x1 - 15, cy, text=f"h={h_val}", fill=COLOR_ACCENT, font=("Fixedsys", 9, "bold"))
            
        elif shape_type == "pythagorean":
            a_val = self.current_shape_data.get("a")
            b_val = self.current_shape_data.get("b")
            x1 = cx - 40
            y1 = cy + 25
            x2 = cx + 40
            y2 = cy + 25
            x3 = cx - 40
            y3 = cy - 25
            canvas.create_polygon(x1, y1, x2, y2, x3, y3, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_text(cx, y2 + 10, text=f"{b_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_text(x1 - 15, cy, text=f"{a_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_text(cx + 10, cy - 10, text="?", fill=COLOR_ACCENT, font=("Fixedsys", 10, "bold"))
            
        elif shape_type == "missing_leg":
            b_val = self.current_shape_data.get("b")
            c_val = self.current_shape_data.get("c")
            x1 = cx - 40
            y1 = cy + 25
            x2 = cx + 40
            y2 = cy + 25
            x3 = cx - 40
            y3 = cy - 25
            canvas.create_polygon(x1, y1, x2, y2, x3, y3, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_text(cx, y2 + 10, text=f"{b_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_text(x1 - 15, cy, text="?", fill=COLOR_ACCENT, font=("Fixedsys", 10, "bold"))
            canvas.create_text(cx + 12, cy - 10, text=f"{c_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            
        elif shape_type == "shaded_area":
            side = 70
            x1 = cx - side // 2
            y1 = cy - side // 2
            x2 = cx + side // 2
            y2 = cy + side // 2
            canvas.create_rectangle(x1, y1, x2, y2, outline=COLOR_TEXT, fill=COLOR_DANGER, width=2)
            canvas.create_oval(x1, y1, x2, y2, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_text(cx, y2 + 10, text="side=14", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))
            canvas.create_line(cx, cy, cx + side // 2, cy, fill=COLOR_ACCENT, width=1.5)
            canvas.create_text(cx + 15, cy - 10, text="r=7", fill=COLOR_ACCENT, font=("Fixedsys", 8, "bold"))
            
        elif shape_type == "prism":
            l_val = self.current_shape_data.get("l")
            w_val = self.current_shape_data.get("w")
            h_val = self.current_shape_data.get("h")
            bx1, by1 = cx - 35, cy - 15
            bx2, by2 = cx + 15, cy - 15
            bx3, by3 = cx + 15, cy + 25
            bx4, by4 = cx - 35, cy + 25
            fx1, fy1 = bx1 + 20, by1 - 15
            fx2, fy2 = bx2 + 20, by2 - 15
            fx3, fy3 = bx3 + 20, by3 - 15
            fx4, fy4 = bx4 + 20, by4 - 15
            canvas.create_polygon(bx1, by1, bx2, by2, bx3, by3, bx4, by4, outline=COLOR_TEXT_MUTED, fill="", width=1)
            canvas.create_polygon(fx1, fy1, fx2, fy2, fx3, fy3, fx4, fy4, outline=COLOR_TEXT, fill="", width=2)
            canvas.create_line(bx1, by1, fx1, fy1, fill=COLOR_TEXT, width=1.5)
            canvas.create_line(bx2, by2, fx2, fy2, fill=COLOR_TEXT, width=1.5)
            canvas.create_line(bx3, by3, fx3, fy3, fill=COLOR_TEXT, width=1.5)
            canvas.create_line(bx4, by4, fx4, fy4, fill=COLOR_TEXT, width=1.5)
            canvas.create_text((fx3 + fx4) // 2, fy3 + 10, text=f"l={l_val}", fill=COLOR_TEXT, font=("Fixedsys", 8, "bold"))
            canvas.create_text(fx3 + 15, (fy2 + fy3) // 2, text=f"h={h_val}", fill=COLOR_TEXT, font=("Fixedsys", 8, "bold"))
            canvas.create_text(fx2 + 10, (fy2 + by2) // 2, text=f"w={w_val}", fill=COLOR_ACCENT, font=("Fixedsys", 8, "bold"))
            
        elif shape_type == "cylinder":
            h_val = self.current_shape_data.get("h")
            canvas.create_oval(cx - 30, cy - 35, cx + 30, cy - 20, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_oval(cx - 30, cy + 20, cx + 30, cy + 35, outline=COLOR_TEXT, fill=COLOR_BG, width=2)
            canvas.create_line(cx - 30, cy - 27, cx - 30, cy + 27, fill=COLOR_TEXT, width=2)
            canvas.create_line(cx + 30, cy - 27, cx + 30, cy + 27, fill=COLOR_TEXT, width=2)
            canvas.create_line(cx, cy - 27, cx + 30, cy - 27, fill=COLOR_ACCENT, width=1.5)
            canvas.create_text(cx + 15, cy - 38, text="r=7", fill=COLOR_ACCENT, font=("Fixedsys", 8, "bold"))
            canvas.create_text(cx + 45, cy, text=f"h={h_val}", fill=COLOR_TEXT, font=("Fixedsys", 9, "bold"))

    def generate_formula_problem(self, difficulty):
        if difficulty == "easy":
            x = random.randint(1, 15)
            a = random.randint(2, 8)
            b = random.randint(-15, 15)
            while b == 0:
                b = random.randint(-15, 15)
            c = a * x + b
            if b > 0:
                eq = f"{a}x + {b} = {c}"
                self.last_explanation = f"Step-by-step explanation:\n1. {a}x + {b} = {c}\n2. Subtract {b}: {a}x = {c - b}\n3. Divide by {a}: x = {x}."
            else:
                eq = f"{a}x - {abs(b)} = {c}"
                self.last_explanation = f"Step-by-step explanation:\n1. {a}x - {abs(b)} = {c}\n2. Add {abs(b)}: {a}x = {c + abs(b)}\n3. Divide by {a}: x = {x}."
            return f"Formulas: Solve for x:\n{eq}", x, False
        elif difficulty == "hard":
            sub_type = random.choice(["system", "exp", "log"])
            if sub_type == "system":
                x = random.randint(3, 10)
                y = random.randint(2, 10)
                a = random.randint(2, 5)
                b = random.randint(2, 5)
                c1 = a * x + y
                c2 = b * x - y
                self.last_explanation = (
                    f"Step-by-step explanation:\n"
                    f"1. We have a system of linear equations:\n"
                    f"   [1] {a}x + y = {c1}\n"
                    f"   [2] {b}x - y = {c2}\n"
                    f"2. Add equation [1] and [2] to eliminate y:\n"
                    f"   ({a}x + {b}x) + (y - y) = {c1} + {c2}\n"
                    f"   {a + b}x = {c1 + c2}\n"
                    f"3. Divide by {a + b}:\n"
                    f"   x = {x}."
                )
                return f"Formulas: Solve for x:\n{a}x + y = {c1}\n{b}x - y = {c2}", x, False
            elif sub_type == "exp":
                base = random.choice([2, 3, 5])
                if base == 2:
                    p = random.randint(5, 8)
                elif base == 3:
                    p = random.randint(4, 6)
                else:
                    p = random.randint(3, 4)
                d = random.randint(1, 5)
                val = base ** p
                ans = p + d
                self.last_explanation = (
                    f"Step-by-step explanation:\n"
                    f"1. {base}^(x - {d}) = {val}\n"
                    f"2. Express {val} as base {base}: {base}^{p}\n"
                    f"3. Since base is same: x - {d} = {p}\n"
                    f"4. Solve for x: x = {p} + {d} = {ans}."
                )
                return f"Formulas: Solve for x:\n{base}^(x - {d}) = {val}", ans, False
            else: # log
                base = random.choice([2, 3, 5])
                if base == 2:
                    p = random.randint(4, 7)
                elif base == 3:
                    p = random.randint(3, 5)
                else:
                    p = random.randint(2, 3)
                d = random.randint(1, 20)
                val = base ** p
                ans = val + d
                self.last_explanation = (
                    f"Step-by-step explanation:\n"
                    f"1. log_{base}(x - {d}) = {p}\n"
                    f"2. Convert to exponential: x - {d} = {base}^{p}\n"
                    f"3. Calculate power: x - {d} = {val}\n"
                    f"4. Solve for x: x = {val} + {d} = {ans}."
                )
                return f"Formulas: Solve for x:\nlog_{base}(x - {d}) = {p}", ans, False
        else: # medium
            sub_type = random.choice(["exp", "log"])
            if sub_type == "exp":
                base = random.choice([2, 3, 5])
                if base == 2:
                    ans = random.randint(2, 6)
                elif base == 3:
                    ans = random.randint(2, 4)
                else:
                    ans = random.randint(2, 3)
                val = base ** ans
                self.last_explanation = f"Step-by-step explanation:\n1. {base}^x = {val}\n2. Since {base}^{ans} = {val}, we have x = {ans}."
                return f"Formulas: Solve for x:\n{base}^x = {val}", ans, False
            else: # log
                base = random.choice([2, 3, 4, 10])
                if base == 2:
                    power = random.randint(2, 6)
                elif base == 3:
                    power = random.randint(2, 4)
                elif base == 4:
                    power = random.randint(2, 3)
                else:
                    power = random.randint(1, 3)
                ans = base ** power
                self.last_explanation = f"Step-by-step explanation:\n1. log_{base}(x) = {power}\n2. Convert to exponential form: x = {base}^{power}\n3. x = {ans}."
                return f"Formulas: Solve for x:\nlog_{base}(x) = {power}", ans, False

    def generate_factoring_problem(self, difficulty):
        if difficulty == "easy":
            a = random.randint(1, 5)
            b = random.randint(1, 5)
            while b == a:
                b = random.randint(1, 5)
        elif difficulty == "hard":
            candidates = [x for x in range(-25, 26) if x not in (0, 1, -1)]
            a = random.choice(candidates)
            b = random.choice(candidates)
            while b == a:
                b = random.choice(candidates)
        else: # medium
            a = random.choice([x for x in range(-6, 9) if x != 0])
            b = random.choice([x for x in range(-6, 9) if x != 0])
            while b == a:
                b = random.choice([x for x in range(-6, 9) if x != 0])

        # (x - a)(x - b) = x^2 - (a+b)x + ab = 0
        s = -(a + b)
        p = a * b

        eq = "x²"
        if s != 0:
            if s > 0:
                eq += f" + {s}x"
            else:
                eq += f" - {abs(s)}x"
        if p != 0:
            if p > 0:
                eq += f" + {p}"
            else:
                eq += f" - {abs(p)}"
        eq += " = 0"

        f1 = -a
        f2 = -b
        self.last_explanation = (
            f"Step-by-step explanation:\n"
            f"1. We need to factor: {eq}\n"
            f"2. Find two numbers that multiply to {p} and add up to {s}.\n"
            f"3. Those numbers are {f1} and {f2}.\n"
            f"4. Factored form: (x {f1:+})(x {f2:+}) = 0\n"
            f"5. Enter the factors in the brackets: {f1} and {f2}."
        )

        return f"Solve (Factor):\n{eq}", sorted([a, b]), True

    def generate_division_explanation(self, a, b):
        ans = a // b
        digits = str(a)
        steps = [f"Step-by-step Long Division for {a} ÷ {b}:"]
        
        current_val = 0
        quotient_str = ""
        
        for i, digit in enumerate(digits):
            d_val = int(digit)
            prev_val = current_val
            current_val = current_val * 10 + d_val
            
            step_desc = f"  - Bring down '{digit}'"
            if prev_val > 0:
                step_desc += f" to get {current_val}"
            else:
                step_desc += f" (current value is {current_val})"
                
            q = current_val // b
            rem = current_val % b
            
            step_desc += f". {current_val} ÷ {b} = {q} rem {rem}."
            if q > 0 or quotient_str:  # avoid leading zeros
                quotient_str += str(q)
                step_desc += f" (Digit: {q})"
                
            steps.append(step_desc)
            if q > 0:
                steps.append(f"    Subtract: {current_val} - {b * q} = {rem}.")
                
            current_val = rem
            
        steps.append(f"  Final Answer: {ans}.")
        return "\n".join(steps)

    def generate_arithmetic_problem(self, difficulty, op):
        if difficulty == "easy":
            if op == "+":
                a = random.randint(1, 20)
                b = random.randint(1, 20)
                ans = a + b
            elif op == "-":
                a = random.randint(5, 30)
                b = random.randint(1, a)
                ans = a - b
            elif op == "*":
                a = random.randint(1, 10)
                b = random.randint(1, 10)
                ans = a * b
            elif op == "/":
                b = random.randint(2, 10)
                c = random.randint(1, 10)
                a = b * c
                ans = c
        elif difficulty == "hard":
            if op == "+":
                a = random.randint(1000, 9999)
                b = random.randint(1000, 9999)
                ans = a + b
            elif op == "-":
                a = random.randint(2000, 9999)
                b = random.randint(1000, a)
                ans = a - b
            elif op == "*":
                a = random.randint(12, 99)
                b = random.randint(11, 99)
                ans = a * b
            elif op == "/":
                b = random.randint(12, 50)
                c = random.randint(15, 99)
                a = b * c
                ans = c
        else: # medium
            if op == "+":
                a = random.randint(10, 99)
                b = random.randint(10, 99)
                ans = a + b
            elif op == "-":
                a = random.randint(20, 99)
                b = random.randint(10, a)
                ans = a - b
            elif op == "*":
                a = random.randint(3, 12)
                b = random.randint(3, 12)
                ans = a * b
            elif op == "/":
                b = random.randint(3, 15)
                c = random.randint(3, 12)
                a = b * c
                ans = c

        if op == "+":
            self.last_explanation = f"Step-by-step explanation:\n1. Start with {a}.\n2. Add {b}.\n3. {a} + {b} = {ans}."
            return f"{a} + {b}", ans, False
        elif op == "-":
            self.last_explanation = f"Step-by-step explanation:\n1. Start with {a}.\n2. Subtract {b}.\n3. {a} - {b} = {ans}."
            return f"{a} - {b}", ans, False
        elif op == "*":
            self.last_explanation = f"Step-by-step explanation:\n1. Multiply {a} by {b}.\n2. {a} * {b} = {ans}."
            return f"{a} * {b}", ans, False
        else: # op == "/"
            explanation = self.generate_division_explanation(a, b)
            self.last_explanation = f"Step-by-step explanation:\n{explanation}"
            return f"{a} / {b}", ans, False

    def generate_math_problem(self, difficulty):
        self.current_shape_data = None
        active_types = self.config.get("problem_types", ["addition", "subtraction", "multiplication", "division", "factoring", "geometry", "formulas"])
        if not active_types:
            active_types = ["addition", "subtraction", "multiplication", "division", "factoring", "geometry", "formulas"]
            
        chosen = random.choice(active_types)
        if chosen == "factoring":
            return self.generate_factoring_problem(difficulty)
        elif chosen == "geometry":
            return self.generate_geometry_problem(difficulty)
        elif chosen == "formulas":
            return self.generate_formula_problem(difficulty)
            
        op_map = {
            "addition": "+",
            "subtraction": "-",
            "multiplication": "*",
            "division": "/"
        }
        op = op_map.get(chosen, "+")
        return self.generate_arithmetic_problem(difficulty, op)

    def find_main_hwnd(self, pids):
        import ctypes
        from ctypes import wintypes
        
        pids_set = set(pids)
        candidates = []
        
        def enum_windows_callback(hwnd, lparam):
            if ctypes.windll.user32.IsWindowVisible(hwnd):
                window_pid = wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                if window_pid.value in pids_set:
                    rect = wintypes.RECT()
                    if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        is_minimized = (rect.left < -10000 or rect.top < -10000 or w <= 0 or h <= 0)
                        area = w * h
                        candidates.append((hwnd, rect, area, is_minimized))
            return True
            
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        
        if not candidates:
            return None
            
        # Select first non-minimized candidate with largest area
        active_candidates = [c for c in candidates if not c[3]]
        if active_candidates:
            active_candidates.sort(key=lambda x: x[2], reverse=True)
            return active_candidates[0][0]
        else:
            candidates.sort(key=lambda x: x[2], reverse=True)
            return candidates[0][0]

    def get_window_rect_for_pids(self, pids):
        import ctypes
        from ctypes import wintypes
        
        hwnd_found = self.find_main_hwnd(pids)
        if hwnd_found:
            rect = wintypes.RECT()
            if ctypes.windll.user32.GetWindowRect(hwnd_found, ctypes.byref(rect)):
                return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
        return None


    def kill_app_processes(self, app_name):
        for p in psutil.process_iter(['pid', 'name']):
            try:
                pname = p.info['name']
                if pname and pname.lower() == app_name:
                    p.kill()
            except Exception:
                pass

    def trigger_emergency_unlock(self, app_name, dialog, pids):
        import ctypes
        from ctypes import wintypes
        
        class CREDUI_INFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hwndParent", wintypes.HWND),
                ("pszMessageText", wintypes.LPWSTR),
                ("pszCaptionText", wintypes.LPWSTR),
                ("hbmBanner", wintypes.HBITMAP),
            ]
            
        try:
            credui = ctypes.WinDLL('credui.dll', use_last_error=True)
            hwnd = dialog.winfo_id()
            
            ui_info = CREDUI_INFO()
            ui_info.cbSize = ctypes.sizeof(CREDUI_INFO)
            ui_info.hwndParent = hwnd
            ui_info.pszMessageText = f"Please authenticate to authorize emergency unlock for '{app_name}'."
            ui_info.pszCaptionText = "Emergency Unlock"
            ui_info.hbmBanner = None
            
            auth_package = wintypes.ULONG(0)
            out_auth_buffer = ctypes.c_void_p()
            out_auth_size = wintypes.ULONG(0)
            save = wintypes.BOOL(False)
            
            dwFlags = 0x200
            
            result = credui.CredUIPromptForWindowsCredentialsW(
                ctypes.byref(ui_info),
                0,
                ctypes.byref(auth_package),
                None,
                0,
                ctypes.byref(out_auth_buffer),
                ctypes.byref(out_auth_size),
                ctypes.byref(save),
                dwFlags
            )
            
            if result == 0:  # ERROR_SUCCESS
                self.currently_unlocked[app_name] = "pending"
                dialog.withdraw()
                self.root.attributes("-topmost", True)
                messagebox.showinfo("Success", f"'{app_name}' is unblocked via Windows Hello/PIN!", parent=self.root)
                self.root.attributes("-topmost", False)
                self.active_puzzle_app = None
                dialog.destroy()
            else:
                messagebox.showwarning("Emergency Unlock", "Authentication failed or cancelled.", parent=dialog)
                
            if out_auth_buffer:
                ole32 = ctypes.WinDLL('ole32.dll')
                ole32.CoTaskMemFree(out_auth_buffer)
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch Windows PIN validation: {e}", parent=dialog)

    def show_puzzle_dialog(self, app_name, pids):
        import datetime
        self.write_log(f"Intercepted and locked app: '{app_name}'")
        difficulty = self.config.get("difficulty", "medium")
        
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        challenge_completed_today = (self.config.get("last_completed_challenge") == today_str)

        is_daily_challenge = False
        required_questions = max(1, self.config.get("required_questions", 5))

        solved_count = 0
        wrong_count = 0
        gamble_active = False
        gamble_offered = False
        processing_submit = False
        question, answer, is_factoring = self.generate_math_problem(difficulty)

        dialog = tk.Toplevel(self.root)
        dialog.title("Application Locked")
        dialog.configure(bg=COLOR_BG)
        dialog.resizable(False, False)
        
        # Make the dialog fullscreen and unmovable
        dialog.attributes("-fullscreen", True)
        # Start in a withdrawn (hidden) state so it only shows up when the target window gets focus
        dialog.withdraw()
        
        # Prevent any resize or snapping from escaping fullscreen
        def force_fullscreen(event=None):
            if dialog.winfo_exists() and dialog.state() != "withdrawn" and not dialog.attributes("-fullscreen"):
                dialog.attributes("-fullscreen", True)
        dialog.bind("<Configure>", force_fullscreen)
            
        dialog.wm_attributes("-topmost", True)
        dialog.transient(self.root)
        dialog.grab_set()

        # Handle user closing the window manually
        def on_close():
            self.active_puzzle_app = None
            self.kill_app_processes(app_name)
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)

        # Style UI elements
        container = ttk.Frame(dialog, padding=20)
        container.pack(expand=True)  # Centers content frame within the overlay

        hdr_frame = ttk.Frame(container)
        hdr_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(hdr_frame, text="v2.2.0").pack(side="left")
        ttk.Button(hdr_frame, text="📋 Logs", command=self.show_log_window, width=8).pack(side="right")

        if is_daily_challenge:
            lbl_lock = ttk.Label(container, text="🔥 Daily Math Challenge", foreground=COLOR_ACCENT)
            lbl_lock.pack(pady=(0, 10))
            lbl_desc = ttk.Label(container, text=f"Solve {required_questions} questions to unlock all blocked apps for today!", justify="center")
            lbl_desc.pack(pady=(0, 15))
        else:
            lbl_lock = ttk.Label(container, text="🔒 Access Blocked", foreground=COLOR_DANGER)
            lbl_lock.pack(pady=(0, 10))
            lbl_desc = ttk.Label(container, text=f"'{app_name}' has been blocked to keep you focused.\nSolve this math question to unlock it:", justify="center")
            lbl_desc.pack(pady=(0, 15))

        # Progress bar and label
        lbl_progress = ttk.Label(container, text=f"Progress: 0 / {required_questions} solved", font=("Fixedsys", 10, "bold"), foreground=COLOR_TEXT_MUTED)
        lbl_progress.pack(pady=(0, 5))

        progress_bar = ttk.Progressbar(container, orient="horizontal", length=300, mode="determinate")
        progress_bar["maximum"] = required_questions
        progress_bar["value"] = 0
        progress_bar.pack(pady=(0, 20))

        # Shape canvas frame placeholder
        shape_frame = ttk.Frame(container)
        shape_frame.pack(pady=(0, 10))
        
        canvas_shape = None
        
        def refresh_geometry_canvas():
            nonlocal canvas_shape
            if canvas_shape:
                canvas_shape.destroy()
                canvas_shape = None
            if self.current_shape_data:
                canvas_shape = tk.Canvas(
                    shape_frame,
                    width=200,
                    height=120,
                    bg=COLOR_SURFACE,
                    highlightthickness=1,
                    highlightbackground=COLOR_BORDER
                )
                canvas_shape.pack()
                self.draw_geometry_shape(canvas_shape)

        refresh_geometry_canvas()

        # Problem display box
        lbl_prob = ttk.Label(container, text=question, font=("Fixedsys", 22, "bold"), foreground=COLOR_ACCENT)
        lbl_prob.pack(pady=(0, 10))

        # Container for inputs
        input_container = ttk.Frame(container)
        input_container.pack(pady=(0, 10))

        entry_ans = None
        entry_ans1 = None
        entry_ans2 = None

        def build_input_fields(fac_mode):
            nonlocal entry_ans, entry_ans1, entry_ans2
            for child in input_container.winfo_children():
                child.destroy()
                
            if fac_mode:
                frame = ttk.Frame(input_container)
                frame.pack()
                
                lbl1 = ttk.Label(frame, text="( x ", font=("Fixedsys", 14))
                lbl1.pack(side="left")
                
                entry_ans1 = ttk.Entry(frame, font=("Fixedsys", 14), justify="center", width=6)
                entry_ans1.pack(side="left", padx=2)
                
                lbl2 = ttk.Label(frame, text=" ) ( x ", font=("Fixedsys", 14))
                lbl2.pack(side="left")
                
                entry_ans2 = ttk.Entry(frame, font=("Fixedsys", 14), justify="center", width=6)
                entry_ans2.pack(side="left", padx=2)
                
                lbl3 = ttk.Label(frame, text=" ) = 0", font=("Fixedsys", 14))
                lbl3.pack(side="left")
                
                entry_ans1.focus_set()
                entry_ans1.bind("<Return>", lambda e: submit())
                entry_ans2.bind("<Return>", lambda e: submit())
            else:
                entry_ans = ttk.Entry(input_container, font=("Fixedsys", 12), justify="center", width=15)
                entry_ans.pack(ipady=4)
                entry_ans.focus_set()
                entry_ans.bind("<Return>", lambda e: submit())

        lbl_error = ttk.Label(container, text="", foreground=COLOR_DANGER, font=("Fixedsys", 9, "bold"))
        lbl_error.pack()

        lbl_explanation = ttk.Label(
            container, 
            text="", 
            font=("Fixedsys", 11), 
            foreground=COLOR_TEXT, 
            justify="left",
            wraplength=400
        )

        def go_to_next_question():
            nonlocal question, answer, is_factoring, gamble_offered
            gamble_offered = False
            btn_next.pack_forget()
            btn_gamble.pack_forget()
            lbl_explanation.pack_forget()
            lbl_explanation.config(text="")
            lbl_error.config(text="")
            
            question, answer, is_factoring = self.generate_math_problem(difficulty)
            lbl_prob.config(text=question)
            
            refresh_geometry_canvas()
            
            build_input_fields(is_factoring)
            
            btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 5))
            btn_submit.pack(side="right", fill="x", expand=True, padx=(5, 0))
            if btn_emergency:
                btn_emergency.pack(fill="x", pady=(10, 0))
            if not is_daily_challenge and not challenge_completed_today:
                if btn_start_challenge:
                    btn_start_challenge.pack(fill="x", pady=(10, 0))

        def start_gamble():
            nonlocal question, answer, is_factoring, gamble_active, gamble_offered
            gamble_active = True
            gamble_offered = True
            
            btn_next.pack_forget()
            btn_gamble.pack_forget()
            lbl_explanation.pack_forget()
            lbl_explanation.config(text="")
            
            # Generate a hard problem
            question, answer, is_factoring = self.generate_math_problem("hard")
            lbl_prob.config(text=question)
            lbl_error.config(text="🎰 GAMBLE MODE: Solve this HARD question to UNLOCK IMMEDIATELY, or fail and add +2 penalty!", foreground=COLOR_DANGER)
            
            refresh_geometry_canvas()
            
            build_input_fields(is_factoring)
            
            btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 5))
            btn_submit.pack(side="right", fill="x", expand=True, padx=(5, 0))
            if btn_emergency:
                btn_emergency.pack(fill="x", pady=(10, 0))

        btn_next = ttk.Button(container, text="Proceed to Next Question", command=go_to_next_question)
        btn_gamble = ttk.Button(container, text="🎮 Gamble Double or Nothing!", command=start_gamble)

        def submit():
            if not dialog.winfo_exists():
                return
            nonlocal question, answer, is_factoring, solved_count, wrong_count, gamble_active, gamble_offered, processing_submit
            if processing_submit:
                return
            processing_submit = True
            try:
                try:
                    if is_factoring:
                        val1 = entry_ans1.get().strip()
                        val2 = entry_ans2.get().strip()
                        if not val1 or not val2:
                            lbl_error.config(text="Please fill in both boxes.")
                            return
                        a_val = int(val1)
                        b_val = int(val2)
                        
                        expected_factors = sorted([-x for x in answer])
                        user_factors = sorted([a_val, b_val])
                        is_correct = (user_factors == expected_factors)
                        correct_str = f"{expected_factors[0]} and {expected_factors[1]}"
                    else:
                        user_ans = int(entry_ans.get().strip())
                        is_correct = (user_ans == answer)
                        correct_str = str(answer)

                    if gamble_active:
                        if is_correct:
                            self.trigger_sound("victory")
                            wrong_count = 0
                            gamble_active = False
                            self.write_log(f"Gamble won! Unlocked '{app_name}' immediately.")
                            self.currently_unlocked[app_name] = "pending"
                            self.unlock_expirations[app_name] = None
                            dialog.withdraw()
                            self.root.attributes("-topmost", True)
                            messagebox.showinfo("Gamble Won!", "🎰 Success! You won the gamble and unlocked the application!", parent=self.root)
                            self.root.attributes("-topmost", False)
                            self.active_puzzle_app = None
                            dialog.destroy()
                        else:
                            self.trigger_sound("error")
                            wrong_count += 2
                            gamble_active = False
                            self.write_log(f"Gamble lost! Penalty increased to {wrong_count} wrong answers.")
                            messagebox.showwarning("Gamble Lost!", "💥 Oh no! You lost the gamble and your penalty increased by +2 wrong answers!", parent=dialog)
                            
                            btn_next.pack_forget()
                            btn_gamble.pack_forget()
                            lbl_explanation.pack_forget()
                            lbl_explanation.config(text="")
                            lbl_error.config(text="")
                            question, answer, is_factoring = self.generate_math_problem(difficulty)
                            lbl_prob.config(text=question)
                            
                            refresh_geometry_canvas()
                            
                            build_input_fields(is_factoring)
                            
                            btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 5))
                            btn_submit.pack(side="right", fill="x", expand=True, padx=(5, 0))
                            if btn_emergency:
                                btn_emergency.pack(fill="x", pady=(10, 0))
                            if not is_daily_challenge and not challenge_completed_today:
                                if btn_start_challenge:
                                    btn_start_challenge.pack(fill="x", pady=(10, 0))
                        return

                    if is_correct:
                        solved_count += 1
                        lbl_progress.config(text=f"Progress: {solved_count} / {required_questions} solved")
                        progress_bar["value"] = solved_count
                        self.write_log(f"Correct answer submitted for '{app_name}'. Progress: {solved_count}/{required_questions}")
                        
                        if solved_count >= required_questions:
                            if is_daily_challenge:
                                self.trigger_sound("victory")
                                self.config["last_completed_challenge"] = today_str
                                
                                yesterday = datetime.date.today() - datetime.timedelta(days=1)
                                yesterday_str = yesterday.strftime("%Y-%m-%d")
                                
                                history = self.config.setdefault("challenge_history", [])
                                current_streak = self.config.get("current_streak", 0)
                                
                                if yesterday_str in history:
                                    current_streak += 1
                                elif today_str in history:
                                    pass
                                else:
                                    current_streak = 1
                                    
                                self.config["current_streak"] = current_streak
                                if today_str not in history:
                                    history.append(today_str)
                                    
                                try:
                                    self.lbl_streak.config(text=f"Current Streak: {current_streak} Days 🔥")
                                    self.lbl_total.config(text=f"Total Practiced: {len(history)} Days")
                                    self.trigger_confetti_animation()
                                except Exception:
                                    pass
                                    
                                self.write_log(f"Daily challenge completed! Streak: {current_streak} days.")
                                self.save_config()
                                self.currently_unlocked[app_name] = "pending"
                                dialog.withdraw()
                                self.root.attributes("-topmost", True)
                                messagebox.showinfo("Daily Challenge Complete!", f"Congratulations! You completed your daily math challenge.\nAll blocked apps are unlocked for the rest of the day!\nYour current streak is now {current_streak} days 🔥", parent=self.root)
                                self.root.attributes("-topmost", False)
                                self.active_puzzle_app = None
                                dialog.destroy()
                            else:
                                self.trigger_sound("success")
                                import time
                                self.currently_unlocked[app_name] = "pending"
                                dialog.withdraw()
                                self.root.attributes("-topmost", True)
                                if wrong_count > 0:
                                    duration_minutes = max(5, 35 - 5 * wrong_count)
                                    self.write_log(f"App unblocked: '{app_name}' (Wrong count: {wrong_count}, access limited to {duration_minutes}m)")
                                    self.unlock_expirations[app_name] = time.time() + duration_minutes * 60
                                    messagebox.showinfo("Success", f"'{app_name}' is unblocked! Since you got {wrong_count} question(s) wrong, your access is limited to {duration_minutes} minutes.", parent=self.root)
                                else:
                                    self.write_log(f"App unblocked: '{app_name}' (unlimited access)")
                                    self.unlock_expirations[app_name] = None
                                    messagebox.showinfo("Success", f"'{app_name}' is unblocked! It will remain unlocked until you close it.", parent=self.root)
                                self.root.attributes("-topmost", False)
                                self.active_puzzle_app = None
                                dialog.destroy()
                        else:
                            self.trigger_sound("success")
                            lbl_error.config(text="Correct! Next question...", foreground=COLOR_SUCCESS)
                            question, answer, is_factoring = self.generate_math_problem(difficulty)
                            lbl_prob.config(text=question)
                            
                            refresh_geometry_canvas()
                            
                            build_input_fields(is_factoring)
                    else:
                        self.trigger_sound("error")
                        lbl_error.config(text="Incorrect answer!", foreground=COLOR_DANGER)
                        wrong_count += 1
                        self.write_log(f"Incorrect answer submitted for '{app_name}'. Wrong count: {wrong_count}")
                        
                        explanation_text = f"Correct Answer: {correct_str}\n\n{self.last_explanation}"
                        lbl_explanation.config(text=explanation_text)
                        lbl_explanation.pack(pady=15)
                        
                        if is_factoring:
                            entry_ans1.config(state="disabled")
                            entry_ans2.config(state="disabled")
                        else:
                            entry_ans.config(state="disabled")
                            
                        btn_submit.pack_forget()
                        btn_cancel.pack_forget()
                        if btn_emergency:
                            btn_emergency.pack_forget()
                        if btn_start_challenge:
                            btn_start_challenge.pack_forget()
                            
                        btn_next.pack(fill="x", pady=5)
                        
                        if not gamble_offered:
                            btn_gamble.pack(fill="x", pady=5)
                except ValueError:
                    lbl_error.config(text="Please enter valid integer(s).")
                    if is_factoring:
                        entry_ans1.delete(0, tk.END)
                        entry_ans2.delete(0, tk.END)
                    else:
                        entry_ans.delete(0, tk.END)
            finally:
                processing_submit = False

        def cancel():
            self.active_puzzle_app = None
            self.kill_app_processes(app_name)
            dialog.destroy()

        build_input_fields(is_factoring)

        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", pady=(10, 0))

        btn_cancel = ttk.Button(btn_frame, text="Keep Blocked", command=cancel)
        btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_submit = ttk.Button(btn_frame, text="Unlock", command=submit)
        btn_submit.pack(side="right", fill="x", expand=True, padx=(5, 0))

        btn_emergency = ttk.Button(container, text="🔒 Emergency PIN Unlock", command=lambda: self.trigger_emergency_unlock(app_name, dialog, pids))
        btn_emergency.pack(fill="x", pady=(10, 0))

        def start_daily_challenge():
            nonlocal is_daily_challenge, required_questions, solved_count
            is_daily_challenge = True
            required_questions = 30
            solved_count = 0
            
            lbl_lock.config(text="🔥 Daily Math Challenge", foreground=COLOR_ACCENT)
            lbl_desc.config(text="Solve 30 questions to unlock all blocked apps for today!", justify="center")
            lbl_progress.config(text="Progress: 0 / 30 solved")
            
            progress_bar["maximum"] = 30
            progress_bar["value"] = 0
            
            if btn_start_challenge:
                btn_start_challenge.pack_forget()

        btn_start_challenge = None
        if not challenge_completed_today:
            btn_start_challenge = ttk.Button(container, text="🔥 Start Daily Challenge (30 Questions)", command=start_daily_challenge)
            btn_start_challenge.pack(fill="x", pady=(10, 0))

        # Add random math tip/tutorial at the bottom of the lock screen container
        if self.math_tips:
            active_tip_index = random.randint(0, len(self.math_tips) - 1)
            
            # Card frame for the tip
            tip_card = ttk.Frame(container, padding=12)
            tip_card.pack(fill="x", pady=(25, 0))
            
            tip_header = ttk.Frame(tip_card)
            tip_header.pack(fill="x")
            
            lbl_tip_hdr = ttk.Label(
                tip_header,
                text="",
                font=("Fixedsys", 9, "bold"),
                foreground=COLOR_ACCENT,
                background=COLOR_SURFACE
            )
            lbl_tip_hdr.pack(side="left")
            
            def next_lock_tip():
                nonlocal active_tip_index
                active_tip_index = (active_tip_index + 1) % len(self.math_tips)
                t = self.math_tips[active_tip_index]
                lbl_tip_hdr.config(text=f"💡 Study Tip: {t.get('title')}")
                lbl_tip_body.config(text=t.get('desc'))
                
            btn_next_lock_tip = ttk.Button(tip_header, text="Next Tip →", command=next_lock_tip)
            btn_next_lock_tip.pack(side="right")
            
            lbl_tip_body = ttk.Label(
                tip_card,
                text="",
                font=("Fixedsys", 9),
                foreground=COLOR_TEXT,
                justify="left",
                wraplength=380,
                background=COLOR_SURFACE
            )
            lbl_tip_body.pack(anchor="w", pady=(4, 0))
            
            # Initial setup
            next_lock_tip()

        # Dynamic loop to follow target window's coordinates and adjust topmost behavior
        def follow_target_window():
            nonlocal processing_submit
            if not dialog.winfo_exists():
                return
            if processing_submit:
                dialog.after(100, follow_target_window)
                return
                
            import ctypes
            from ctypes import wintypes
            
            pids_set = set(pids)
            hwnd_found = self.find_main_hwnd(pids)
            
            if hwnd_found:
                rect = wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(hwnd_found, ctypes.byref(rect)):
                    left, top, width, height = rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
                    
                    is_minimized = (left < -10000 or top < -10000)
                    
                    # Dynamically check foreground window focus
                    fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
                    fg_pid = wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(fg_pid))
                    
                    is_target_focused = (fg_pid.value in pids_set)
                    my_pid = os.getpid()
                    dialog_hwnd = dialog.winfo_id()
                    is_dialog_focused = (fg_hwnd == dialog_hwnd or fg_pid.value == my_pid)
                    
                    if is_minimized or (not is_target_focused and not is_dialog_focused):
                        # Hide the lock screen if target is minimized or we lost focus to another app
                        if dialog.state() != "withdrawn":
                            dialog.withdraw()
                    else:
                        # Target is visible and either target or dialog is focused
                        if dialog.state() == "withdrawn":
                            dialog.deiconify()
                            
                        # Keep it fullscreen and topmost
                        if not dialog.attributes("-fullscreen"):
                            dialog.attributes("-fullscreen", True)
                        dialog.wm_attributes("-topmost", True)
                        dialog.lift()
                        
                        # If target app got focus, force the focus back to the dialog
                        if is_target_focused:
                            dialog.focus_force()
            else:
                # Target app closed by user
                self.active_puzzle_app = None
                dialog.destroy()
                return
                
            dialog.after(50, follow_target_window)

        # Start follow loop
        follow_target_window()

    def update_tip_display(self):
        if not self.math_tips:
            return
        tip = self.math_tips[self.current_tip_index]
        self.lbl_tip_title.config(text=tip.get("title", ""))
        self.lbl_tip_desc.config(text=tip.get("desc", ""))
        
    def show_next_tip(self):
        if not self.math_tips:
            return
        self.current_tip_index = (self.current_tip_index + 1) % len(self.math_tips)
        self.update_tip_display()


if __name__ == "__main__":
    # If running as a bundled executable, use the executable's directory
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    root = tk.Tk()
    app = ProductivityLockerApp(root)
    
    try:
        root.mainloop()
    finally:
        # Signal monitor thread to stop
        app.monitor_active = False
