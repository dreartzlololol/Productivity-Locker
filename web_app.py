import sys
import os
import json
import time
import threading
import webview
import psutil
import app as original_app

try:
    import win32ui, win32gui, win32con, win32api, win32process
    from PIL import Image
    import base64
    from io import BytesIO
except ImportError:
    pass

window = None

def get_visible_pids():
    pids = set()
    try:
        def enum_windows_callback(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                pids.add(pid)
        win32gui.EnumWindows(enum_windows_callback, None)
    except:
        pass
    return pids

def get_app_rect(app_name):
    rects = []
    try:
        def enum_windows_callback(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    p = psutil.Process(pid)
                    if p.name().lower() == app_name.lower():
                        rect = win32gui.GetWindowRect(hwnd)
                        if rect[0] > -10000 and rect[1] > -10000:
                            rects.append(rect)
                except:
                    pass
        win32gui.EnumWindows(enum_windows_callback, None)
    except:
        pass
    if rects:
        rects.sort(key=lambda r: (r[2]-r[0])*(r[3]-r[1]), reverse=True)
        return rects[0]
    return None

def get_icon_base64(exe_path):
    try:
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        use_icon = large[0] if large else small[0] if small else None
        if not use_icon: return None
        
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
        hdc2 = hdc.CreateCompatibleDC()
        hdc2.SelectObject(hbmp)
        win32gui.DrawIconEx(hdc2.GetSafeHdc(), 0, 0, use_icon, ico_x, ico_y, 0, None, win32con.DI_NORMAL)
        
        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)
        img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
        win32gui.DestroyIcon(use_icon)
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()
    except:
        return None

# Add scratch to path to import app_original if needed, but wait!
# I can just import from app.py if I restore app.py to its original state.
# Let's restore app.py from app_original.py first, then monkey patch it.

import shutil
shutil.copyfile(r"c:\Users\User\.gemini\antigravity-ide\scratch\app_original.py", r"c:\Users\User\Downloads\yak tua pragrob\app.py")

import app as original_app

class WebAPI:
    def __init__(self):
        # Initialize original app logic without starting tkinter
        self.config = self.get_default_config()
        self.load_config()
        self.currently_unlocked = {}
        self.unlock_expirations = {}
        
        self.monitor_active = True
        self.monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        self.monitor_thread.start()
        
        self.active_puzzle_app = None
        self.current_question = None
        self.current_answer = None
        self.solved_count = 0
        
        self.load_tips()

    def load_tips(self):
        self.math_tips = []
        tips_file = get_asset_path("tips.json")
        if os.path.exists(tips_file):
            try:
                with open(tips_file, "r", encoding="utf-8") as f:
                    self.math_tips = json.load(f)
            except:
                pass
        if not self.math_tips:
            self.math_tips = [{"title": "Tip", "desc": "Math is fun!"}]

    def get_default_config(self):
        return {
            "blocked_apps": [],
            "difficulty": "medium",
            "problem_types": ["addition", "subtraction", "multiplication", "division", "factoring", "geometry", "formulas"],
            "required_questions": 5,
            "unlock_duration_minutes": 120,
            "last_completed_challenge": "",
            "current_streak": 0,
            "challenge_history": []
        }

    def load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    self.config = json.load(f)
            except:
                self.config = self.get_default_config()
        else:
            self.config = self.get_default_config()
            self.save_config()

    def save_config(self):
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=2)

    def get_config(self):
        self.load_config()
        return self.config

    def get_state(self):
        return {
            "currently_unlocked": self.currently_unlocked,
            "strict_mode_until": self.config.get("strict_mode_until", 0)
        }

    def add_app(self, val):
        val = val.lower().strip()
        if not val.endswith(".exe"):
            val += ".exe"
        if val not in self.config["blocked_apps"]:
            self.config["blocked_apps"].append(val)
            self.save_config()
        return self.get_config()

    def remove_app(self, val):
        if val in self.config["blocked_apps"]:
            self.config["blocked_apps"].remove(val)
            self.save_config()
        return self.get_config()

    def update_settings(self, config_data):
        for k, v in config_data.items():
            self.config[k] = v
        self.save_config()
        return self.get_config()

    def activate_strict_mode(self, hours):
        until = time.time() + (hours * 3600)
        self.config["strict_mode_until"] = until
        self.save_config()
        return self.get_config()

    def browse_file(self):
        file_types = ('Executable Files (*.exe)', 'All files (*.*)')
        result = window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result and len(result) > 0:
            return os.path.basename(result[0]).lower()
        return None

    def get_running_apps(self):
        apps = {}
        ignore_list = ['explorer.exe', 'searchapp.exe', 'startmenuexperiencehost.exe', 'cmd.exe', 'powershell.exe', 'python.exe', 'textinputhost.exe']
        
        visible_pids = get_visible_pids()
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                exe = proc.info.get('exe')
                
                if name and name.endswith('.exe') and pid in visible_pids:
                    name_lower = name.lower()
                    if name_lower not in ignore_list and name_lower not in apps:
                        icon = get_icon_base64(exe) if exe else None
                        apps[name_lower] = {"name": name_lower, "icon": icon}
            except:
                pass
        
        # Sort by name
        sorted_apps = sorted(apps.values(), key=lambda x: x["name"])
        return sorted_apps

    def kill_app_processes(self, app_name):
        try:
            for p in psutil.process_iter(['name']):
                if p.info['name'] and p.info['name'].lower() == app_name:
                    p.kill()
        except:
            pass
            
    def suspend_app_processes(self, app_name):
        try:
            for p in psutil.process_iter(['name']):
                if p.info['name'] and p.info['name'].lower() == app_name:
                    try:
                        if p.status() != psutil.STATUS_STOPPED:
                            p.suspend()
                    except:
                        pass
        except:
            pass

    def resume_app_processes(self, app_name):
        try:
            for p in psutil.process_iter(['name']):
                if p.info['name'] and p.info['name'].lower() == app_name:
                    try:
                        count = 0
                        while p.status() == psutil.STATUS_STOPPED and count < 1000:
                            p.resume()
                            count += 1
                    except:
                        pass
        except:
            pass

    def monitor_processes(self):
        import datetime
        while self.monitor_active:
            try:
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                challenge_completed_today = (self.config.get("last_completed_challenge") == today_str)

                blocked_apps = set(self.config.get("blocked_apps", []))
                
                # Check expirations
                now = time.time()
                for app, exp in list(self.currently_unlocked.items()):
                    if now > exp:
                        del self.currently_unlocked[app]
                
                # Group active processes by name
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        pname = proc.info['name']
                        if not pname:
                            continue
                        pname_lower = pname.lower()
                        if pname_lower in blocked_apps:
                            if challenge_completed_today or pname_lower in self.currently_unlocked:
                                continue
                            
                            # Blocked app detected!
                            self.suspend_app_processes(pname_lower)
                            if self.active_puzzle_app is None:
                                self.active_puzzle_app = pname_lower
                                self.trigger_puzzle(pname_lower)
                                
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(1.5)
            
    def trigger_puzzle(self, app_name):
        strict_until = self.config.get("strict_mode_until", 0)
        if time.time() < strict_until:
            # Strict mode active: kill the suspended app so it doesn't linger as a zombie process
            self.kill_app_processes(app_name)
            
            import datetime
            unlock_time = datetime.datetime.fromtimestamp(strict_until).strftime('%I:%M %p')
            msg = f"Strict Mode is active. Unlocks disabled until {unlock_time}."
            if 'window' in globals():
                hwnd = win32gui.FindWindow(None, "Productivity App Locker")
                if hwnd:
                    win32gui.ShowWindow(hwnd, 9) # SW_RESTORE
                    win32gui.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 3) # HWND_TOPMOST
                window.evaluate_js(f"showStrictModal('{self.active_puzzle_app}', '{msg}')")
            self.active_puzzle_app = None
            return
            
        self.solved_count = 0
        self.generate_next_question()
        
    def generate_next_question(self):
        # Create a dummy app instance to borrow its math generation methods
        dummy_app = original_app.ProductivityLockerApp.__new__(original_app.ProductivityLockerApp)
        dummy_app.config = self.config
        
        diff = self.config.get("difficulty", "medium")
        types = self.config.get("problem_types", ["addition"])
        if not types:
            types = ["addition"]
            
        import random
        ptype = random.choice(types)
        
        shape_data = None
        
        # Borrow the methods
        if ptype == "addition":
            q, a, exp = original_app.ProductivityLockerApp.generate_arithmetic_problem(dummy_app, diff, "+")
        elif ptype == "subtraction":
            q, a, exp = original_app.ProductivityLockerApp.generate_arithmetic_problem(dummy_app, diff, "-")
        elif ptype == "multiplication":
            q, a, exp = original_app.ProductivityLockerApp.generate_arithmetic_problem(dummy_app, diff, "*")
        elif ptype == "division":
            q, a, exp = original_app.ProductivityLockerApp.generate_arithmetic_problem(dummy_app, diff, "/")
        elif ptype == "factoring":
            q, a, exp = original_app.ProductivityLockerApp.generate_factoring_problem(dummy_app, diff)
        elif ptype == "geometry":
            q, a, exp = original_app.ProductivityLockerApp.generate_geometry_problem(dummy_app, diff)
            shape_data = getattr(dummy_app, "current_shape_data", None)
        else:
            q, a, exp = original_app.ProductivityLockerApp.generate_formula_problem(dummy_app, diff)
            
        self.current_question = q
        self.current_answer = a
        
        req = self.config.get("required_questions", 5)
        progress = f"Progress: {self.solved_count} / {req} solved"
        
        tip = random.choice(self.math_tips) if self.math_tips else {"title": "", "desc": ""}
        
        if 'window' in globals():
            try:
                hwnd = win32gui.FindWindow(None, "Productivity App Locker")
                if hwnd:
                    win32gui.ShowWindow(hwnd, 9) # SW_RESTORE
                    win32gui.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 3) # HWND_TOPMOST
                    
                rect = get_app_rect(self.active_puzzle_app)
                if hwnd and rect:
                    w = max(600, rect[2] - rect[0])
                    h = max(500, rect[3] - rect[1])
                    win32gui.MoveWindow(hwnd, rect[0], rect[1], w, h, True)
                elif hwnd:
                    win32gui.MoveWindow(hwnd, 100, 100, 1050, 850, True)
            except:
                pass
            import json
            shape_json = json.dumps(shape_data) if shape_data else "null"
            tip_json = json.dumps(tip)
            is_factoring = isinstance(self.current_answer, (list, tuple))
            is_factoring_str = "true" if is_factoring else "false"
            window.evaluate_js(f"showPuzzle('{self.active_puzzle_app}', `{q}`, '{progress}', {shape_json}, {tip_json}, {is_factoring_str})")
            
    def submit_answer(self, ans):
        # Check answer
        try:
            if isinstance(self.current_answer, (list, tuple)):
                # Multiple answers logic (e.g. factoring)
                ans_parts = [float(x.strip()) for x in ans.split(",")]
                ans_parts.sort()
                expected_factors = sorted([-float(x) for x in self.current_answer])
                is_correct = (ans_parts == expected_factors)
            else:
                is_correct = (float(ans) == float(self.current_answer))
        except:
            is_correct = False
            
        if is_correct:
            self.solved_count += 1
            req = self.config.get("required_questions", 5)
            if self.solved_count >= req:
                duration = self.config.get("unlock_duration_minutes", 120)
                self.currently_unlocked[self.active_puzzle_app] = time.time() + (duration * 60)
                self.resume_app_processes(self.active_puzzle_app)
                self.active_puzzle_app = None
                window.evaluate_js("hidePuzzle()")
                if 'window' in globals():
                    try:
                        hwnd = win32gui.FindWindow(None, "Productivity App Locker")
                        if hwnd:
                            win32gui.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 3) # HWND_NOTOPMOST
                            win32gui.MoveWindow(hwnd, 100, 100, 1050, 850, True)
                            win32gui.ShowWindow(hwnd, 6) # SW_MINIMIZE
                    except:
                        pass
            else:
                # Next question
                window.evaluate_js("showPuzzleError('Correct! Next question...', true)")
                self.generate_next_question()
        else:
            window.evaluate_js("showPuzzleError('Incorrect answer!')")

    def emergency_unlock(self):
        if not self.active_puzzle_app:
            return False
            
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
            ui_info = CREDUI_INFO()
            ui_info.cbSize = ctypes.sizeof(CREDUI_INFO)
            ui_info.hwndParent = ctypes.windll.user32.GetForegroundWindow()
            ui_info.pszMessageText = f"Please authenticate to authorize emergency unlock for '{self.active_puzzle_app}'."
            ui_info.pszCaptionText = "Emergency Unlock"
            ui_info.hbmBanner = None
            
            auth_package = wintypes.ULONG(0)
            out_auth_buffer = ctypes.c_void_p()
            out_auth_size = wintypes.ULONG(0)
            save = wintypes.BOOL(False)
            dwFlags = 0x200
            
            result = credui.CredUIPromptForWindowsCredentialsW(
                ctypes.byref(ui_info), 0, ctypes.byref(auth_package), None, 0,
                ctypes.byref(out_auth_buffer), ctypes.byref(out_auth_size),
                ctypes.byref(save), dwFlags
            )
            
            if result == 0:  # ERROR_SUCCESS
                duration = self.config.get("unlock_duration_minutes", 120)
                self.currently_unlocked[self.active_puzzle_app] = time.time() + (duration * 60)
                self.resume_app_processes(self.active_puzzle_app)
                self.active_puzzle_app = None
                window.evaluate_js("hidePuzzle()")
                if 'window' in globals():
                    try:
                        hwnd = win32gui.FindWindow(None, "Productivity App Locker")
                        if hwnd:
                            win32gui.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 3) # HWND_NOTOPMOST
                            win32gui.MoveWindow(hwnd, 100, 100, 1050, 850, True)
                            win32gui.ShowWindow(hwnd, 6) # SW_MINIMIZE
                    except:
                        pass
                return True
            else:
                return False
        except:
            pass
        return False


def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return filename

if __name__ == '__main__':
    api = WebAPI()
    window = webview.create_window('Productivity App Locker', get_asset_path('index.html'), js_api=api, width=1050, height=850, resizable=False)
    
    def on_closing():
        if api.active_puzzle_app:
            try:
                for p in psutil.process_iter(['name']):
                    if p.info['name'] and p.info['name'].lower() == api.active_puzzle_app:
                        p.kill()
            except:
                pass
                
    window.events.closing += on_closing
    webview.start()
