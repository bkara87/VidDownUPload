import os
import sys
import time
import shutil
import zipfile
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
VERSION = "1.1.0"
SETUP_NAME = f"VidDownUPload_Setup_v{VERSION}"

def kill_running_apps():
    for proc in ["VidDownUPload.exe", f"VidDownUPload_Setup_v{VERSION}.exe", "uninstall.exe"]:
        try:
            subprocess.run(['taskkill', '/F', '/IM', proc],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           creationflags=0x08000000)
        except Exception:
            pass

def safe_remove(path):
    kill_running_apps()
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
        except Exception:
            try:
                bak_path = str(path) + f".old_{int(time.time())}"
                os.rename(path, bak_path)
            except Exception:
                pass

def build_installer():
    kill_running_apps()
    python_exe = sys.executable
    safe_remove(BASE_DIR / "dist")
    safe_remove(BASE_DIR / "build")

    print("==========================================")
    print(f"1. Derleniyor: Main Application (VidDownUPload.exe) — v{VERSION}")
    print("==========================================")
    subprocess.run([python_exe, "build_exe.py"], check=True)

    print("\n==========================================")
    print("2. Derleniyor: Uninstaller (uninstall.exe)")
    print("==========================================")
    uninstaller_cmd = [
        python_exe, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--icon=assets/icon.ico",
        "--name", "uninstall",
        "src/installer/uninstaller_gui.py"
    ]
    subprocess.run(uninstaller_cmd, check=True)

    # Copy uninstall.exe into dist/VidDownUPload/
    uninstaller_bin = BASE_DIR / "dist" / "uninstall.exe"
    target_dist = BASE_DIR / "dist" / "VidDownUPload"
    if uninstaller_bin.exists() and target_dist.exists():
        shutil.copy(uninstaller_bin, target_dist / "uninstall.exe")
        print("[OK] uninstall.exe copied into dist/VidDownUPload/")

    print("\n==========================================")
    print(f"3. Paketlenecek dosyalar zipleşiyor (app_payload.zip) — v{VERSION}")
    print("==========================================")
    payload_zip = BASE_DIR / "app_payload.zip"
    with zipfile.ZipFile(payload_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(target_dist):
            for file in files:
                abs_file = Path(root) / file
                rel_path = abs_file.relative_to(target_dist)
                zipf.write(abs_file, rel_path)
    print(f"[OK] Payload zip created: {payload_zip}")

    print("\n==========================================")
    print(f"4. Derleniyor: Setup Installer ({SETUP_NAME}.exe)")
    print("==========================================")
    installer_cmd = [
        python_exe, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--icon=assets/icon.ico",
        "--name", SETUP_NAME,
        "--add-data", f"{payload_zip};.",
        "src/installer/installer_gui.py"
    ]
    subprocess.run(installer_cmd, check=True)

    # Cleanup zip
    if payload_zip.exists():
        payload_zip.unlink()

    setup_exe = BASE_DIR / "dist" / f"{SETUP_NAME}.exe"
    print("\n==========================================")
    print(f"[OK] TEBRİKLER! v{VERSION} Kurulum Paketi Hazır:")
    print(f"-> Setup Installer: {setup_exe}")
    print(f"-> Portable Folder: {target_dist}")
    print("==========================================")

if __name__ == "__main__":
    build_installer()
