import os
import sys
import io
from pathlib import Path

# Force UTF-8 stdio encoding to prevent charmap UnicodeEncodeError with emojis on Windows
if sys.stdout is not None:
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

if sys.stderr is not None:
    try:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

APP_NAME = "VidDownUPload"
APP_VERSION = "2.1.0"

import shutil

# Root folder of source or executable
BASE_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent

# Persistent User Data Directory (AppData/Local/VidDownUPload)
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME

DOWNLOADS_DIR = USER_DATA_DIR / "downloads"
PROCESSED_DIR = USER_DATA_DIR / "processed"
LOGS_DIR = USER_DATA_DIR / "logs"
THUMB_CACHE_DIR = USER_DATA_DIR / "thumb_cache"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Auto-sync legacy config_keys.json or downloads if present in BASE_DIR
try:
    if BASE_DIR != USER_DATA_DIR:
        legacy_keys = BASE_DIR / "config_keys.json"
        target_keys = USER_DATA_DIR / "config_keys.json"
        if legacy_keys.exists() and not target_keys.exists():
            shutil.copy(legacy_keys, target_keys)
        legacy_dl = BASE_DIR / "downloads"
        if legacy_dl.exists() and legacy_dl != DOWNLOADS_DIR:
            for item in legacy_dl.iterdir():
                t_file = DOWNLOADS_DIR / item.name
                if not t_file.exists():
                    try:
                        shutil.copy(item, t_file)
                    except Exception:
                        pass
except Exception as e:
    print(f"Data sync note: {e}")

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
