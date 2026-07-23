import os
import sys
from pathlib import Path

APP_NAME = "VidDownUPload"
APP_VERSION = "1.0.3"

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
GITHUB_OWNER = "BURAKKARABULUT87"  # User can configure in UI or config
GITHUB_REPO = "VidDownUPload"
GITHUB_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/version.json"
GITHUB_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# FFmpeg settings
FFMPEG_BINARY = "ffmpeg"  # Will default to embedded ffmpeg.exe if packaged or system ffmpeg
