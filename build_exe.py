"""
VidDownUPload v2.0 — PyInstaller Build Script
Builds the PyWebView-based embedded browser EXE.
"""
import os
import sys
import subprocess
from pathlib import Path

import shutil
import time

BASE = Path(__file__).parent

def kill_running_apps():
    for proc in ["VidDownUPload.exe", "uninstall.exe"]:
        try:
            subprocess.run(['taskkill', '/F', '/IM', proc],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           creationflags=0x08000000)
        except Exception:
            pass

def safe_remove_dir(path):
    kill_running_apps()
    if path.exists():
        def remove_readonly(func, path, exc_info):
            os.chmod(path, 0o777)
            func(path)
        try:
            shutil.rmtree(path, onerror=remove_readonly)
        except Exception:
            try:
                bak = str(path) + f".old_{int(time.time())}"
                os.rename(path, bak)
                shutil.rmtree(bak, ignore_errors=True)
            except Exception:
                pass

def build():
    print("=" * 60)
    print("VidDownUPload v2.0 — PyInstaller EXE Build")
    print("Architecture: PyWebView + Edge WebView2 (Chromeless)")
    print("=" * 60)

    # Clean existing dist/VidDownUPload and build/VidDownUPload
    safe_remove_dir(BASE / "dist" / "VidDownUPload")
    safe_remove_dir(BASE / "build" / "VidDownUPload")

    # Gather extra binaries (ffmpeg if present)
    binaries = []
    ffmpeg_path = BASE / "ffmpeg.exe"
    if ffmpeg_path.exists():
        binaries += [f"--add-binary", f"{ffmpeg_path};."]
        print(f"[+] FFmpeg binary found and included: {ffmpeg_path}")
    else:
        print("[!] ffmpeg.exe not found in project root. FFmpeg must be on system PATH.")

    # Icon
    icon_path = BASE / "assets" / "icon.ico"
    icon_arg = []
    if icon_path.exists():
        icon_arg = ["--icon", str(icon_path)]
        print(f"[+] Icon: {icon_path}")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--workpath", str(BASE / "build" / "work_app"),
        "VidDownUPload.spec"
    ]

    print("\n[*] Running PyInstaller for main app...")
    subprocess.run(cmd, check=True)

    print("\n" + "=" * 60)
    print("[SUCCESS] Build complete!")
    print(f"Output: {BASE / 'dist' / 'VidDownUPload' / 'VidDownUPload.exe'}")
    print("=" * 60)


if __name__ == "__main__":
    build()
