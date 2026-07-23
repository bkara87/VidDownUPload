import os
import subprocess
import sys
from pathlib import Path

def build():
    print("Building VidDownUPload.exe using PyInstaller...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--icon=assets/icon.ico",
        "--name", "VidDownUPload",
        "--add-data", "src;src",
        "--add-data", "assets;assets",
        "main.py"
    ]
    
    subprocess.run(cmd, check=True)
    print("\n[OK] Build finished successfully! Output binary located in dist/VidDownUPload/VidDownUPload.exe")

if __name__ == "__main__":
    build()
