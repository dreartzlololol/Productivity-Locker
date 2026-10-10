import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "packages": ["os", "json", "time", "random", "threading", "queue", "tkinter", "psutil", "webview"],
    "include_files": ["tips.json", "index.html"],
    "excludes": [],
}

# base="Win32GUI" should be used only for Windows GUI app
base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="ProductivityLocker",
    version="2.3.0",
    description="Productivity App Locker",
    options={"build_exe": build_exe_options},
    executables=[Executable("web_app.py", base=base, target_name="ProductivityLocker.exe")],
)
