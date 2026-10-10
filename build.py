import sys
import subprocess
import os
import shutil

def main():
    print("=== Productivity App Locker Build Script ===")
    
    # Check if pyinstaller is installed
    try:
        import PyInstaller
        print(f"PyInstaller is already installed (version {PyInstaller.__version__})")
    except ImportError:
        print("PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installed successfully.")

    # Get the project root directory (where this script is)
    project_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(project_dir, "web_app.py")
    index_path = os.path.join(project_dir, "index.html")
    tips_path = os.path.join(project_dir, "tips.json")
    
    if not os.path.exists(app_path):
        print(f"Error: Could not find '{app_path}'")
        sys.exit(1)

    print("\nRunning PyInstaller to compile app.py...")
    # Formulate PyInstaller command
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "ProductivityLocker",
        "--clean",
    ]
    
    # Add tips.json as a bundled data file if it exists
    if os.path.exists(tips_path):
        # On Windows, the separator for --add-data is ';'
        pyinstaller_args.extend(["--add-data", f"{tips_path};."])
        
    if os.path.exists(index_path):
        pyinstaller_args.extend(["--add-data", f"{index_path};."])
        
    pyinstaller_args.append(app_path)
    
    print(f"Executing: {' '.join(pyinstaller_args)}")
    result = subprocess.run(pyinstaller_args, cwd=project_dir)
    
    if result.returncode != 0:
        print("PyInstaller failed. Please check the output above.")
        sys.exit(result.returncode)
        
    print("\nCompilation successful!")
    
    # Move the executable from dist/ to the project root
    dist_dir = os.path.join(project_dir, "dist")
    exe_name = "ProductivityLocker.exe"
    compiled_exe = os.path.join(dist_dir, exe_name)
    destination_exe = os.path.join(project_dir, exe_name)
    
    if os.path.exists(compiled_exe):
        print(f"Moving '{exe_name}' to the project root directory...")
        if os.path.exists(destination_exe):
            os.remove(destination_exe)
        shutil.move(compiled_exe, destination_exe)
        print(f"Done! You can now run the app from: {destination_exe}")
    else:
        print(f"Error: Could not find the compiled executable at '{compiled_exe}'")

if __name__ == "__main__":
    main()
