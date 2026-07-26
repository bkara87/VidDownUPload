import os
import sys
from pathlib import Path

APP_NAME = "VidDownUPload"
APP_VERSION = "2.0.0"

# Default directories
BASE_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
PROCESSED_DIR = BASE_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# GitHub Auto-Updater Config
GITHUB_OWNER = "bkara87"  # User can configure in UI or config
GITHUB_REPO = "VidDownUPload"
GITHUB_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/version.json"
GITHUB_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

import shutil

def get_ffmpeg_path() -> str:
    # 1. Check inside PyInstaller frozen bundle directory
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_ffmpeg = Path(sys._MEIPASS) / "ffmpeg.exe"
        if bundle_ffmpeg.exists():
            return str(bundle_ffmpeg)

    # 2. Check executable or root directory
    root_ffmpeg = BASE_DIR / "ffmpeg.exe"
    if root_ffmpeg.exists():
        return str(root_ffmpeg)

    # 3. Check imageio_ffmpeg module
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass

    # 4. System PATH (excluding WindowsApps fake alias)
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg and "WindowsApps" not in sys_ffmpeg:
        return sys_ffmpeg

    return "ffmpeg"

FFMPEG_BINARY = get_ffmpeg_path()
