import os
import sys
import time
import json
import shutil
import zipfile
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent

def get_current_version():
    ver_json = BASE_DIR / "version.json"
    if ver_json.exists():
        try:
            with open(ver_json, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "2.0.0")
        except Exception:
            pass
    return "2.0.0"

VERSION = get_current_version()
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
        def remove_readonly(func, p, exc_info):
            try:
                os.chmod(p, 0o777)
                func(p)
            except Exception:
                pass
        try:
            shutil.rmtree(path, onerror=remove_readonly)
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
    print("1. Derleniyor: Uninstaller (uninstall.exe)")
    print("==========================================")
    uninstaller_cmd = [
        python_exe, "-m", "PyInstaller",
        "--noconfirm",
        "--workpath", str(BASE_DIR / "build" / "work_uninstaller"),
        "uninstall.spec"
    ]
    subprocess.run(uninstaller_cmd, check=True)

    uninstaller_bin = BASE_DIR / "dist" / "uninstall.exe"
    uninstaller_temp = BASE_DIR / "build" / "uninstall.exe"
    if uninstaller_bin.exists():
        shutil.copy(uninstaller_bin, uninstaller_temp)

    print("\n==========================================")
    print(f"2. Derleniyor: Main Application (VidDownUPload.exe) — v{VERSION}")
    print("==========================================")
    subprocess.run([python_exe, "build_exe.py"], check=True)

    target_dist = BASE_DIR / "dist" / "VidDownUPload"
    if uninstaller_temp.exists() and target_dist.exists():
        shutil.copy(uninstaller_temp, target_dist / "uninstall.exe")
        print("[OK] uninstall.exe copied into dist/VidDownUPload/")

    print("\n==========================================")
    print(f"3. Paketlenecek dosyalar zipleşiyor (app_payload.zip) — v{VERSION}")
    print("==========================================")
    payload_zip = BASE_DIR / "app_payload.zip"
    with zipfile.ZipFile(payload_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(target_dist):
            for file in files:
                abs_file = Path(root) / file
                if not abs_file.is_file():
                    continue
                try:
                    rel_path = abs_file.relative_to(target_dist)
                    zipf.write(abs_file, rel_path)
                except Exception as e:
                    print(f"[!] Warning skipping file during zip: {abs_file} -> {e}")
    print(f"[OK] Payload zip created: {payload_zip}")

    print("\n==========================================")
    print(f"4. Derleniyor: Setup Installer ({SETUP_NAME}.exe)")
    print("==========================================")
    spec_file = BASE_DIR / f"{SETUP_NAME}.spec"
    if spec_file.exists():
        installer_cmd = [
            python_exe, "-m", "PyInstaller",
            "--noconfirm",
            "--workpath", str(BASE_DIR / "build" / "work_setup"),
            str(spec_file)
        ]
    else:
        installer_cmd = [
            python_exe, "-m", "PyInstaller",
            "--noconfirm",
            "--workpath", str(BASE_DIR / "build" / "work_setup"),
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
        try:
            payload_zip.unlink()
        except Exception:
            time.sleep(1)
            try:
                payload_zip.unlink()
            except Exception as e:
                print(f"[!] Warning: Could not remove app_payload.zip: {e}")

    setup_exe = BASE_DIR / "dist" / f"{SETUP_NAME}.exe"
    print("\n==========================================")
    print(f"[OK] TEBRİKLER! v{VERSION} Kurulum Paketi Hazır:")
    print(f"-> Setup Installer: {setup_exe}")
    print(f"-> Portable Folder: {target_dist}")
    print("==========================================")

if __name__ == "__main__":
    build_installer()
