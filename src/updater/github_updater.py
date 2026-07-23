import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple

from src.config import APP_VERSION, GITHUB_OWNER, GITHUB_REPO, GITHUB_RELEASE_URL

class GitHubUpdater:
    def __init__(self, owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO):
        self.owner = owner
        self.repo = repo
        self.latest_version_info: Optional[Dict] = None

    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Checks GitHub Releases for a newer version.
        Returns: (has_update, new_version, download_url)
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                remote_tag = data.get("tag_name", "").lstrip("v")
                
                # Check version numbers
                if remote_tag and self._is_newer_version(remote_tag, APP_VERSION):
                    # Look for .exe asset in release assets
                    assets = data.get("assets", [])
                    exe_url = None
                    for asset in assets:
                        if asset.get("name", "").endswith(".exe"):
                            exe_url = asset.get("browser_download_url")
                            break
                    
                    return True, remote_tag, exe_url
        except Exception as e:
            print(f"Update check failed: {e}")

        return False, None, None

    def download_and_install_update(self, download_url: str, progress_callback=None) -> bool:
        """
        Downloads update exe and runs update_bootstrap script to replace current running exe.
        """
        try:
            base_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent.parent
            temp_dir = base_dir / "temp_update"
            temp_dir.mkdir(exist_ok=True)
            new_exe_path = temp_dir / "VidDownUPload_new.exe"

            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(new_exe_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded / total_size)

            # Launch bootstrap updater script to swap executable
            current_exe = sys.executable if getattr(sys, 'frozen', False) else str(base_dir / "VidDownUPload.exe")
            bootstrap_script = base_dir / "updater_bootstrap.py"

            cmd = [sys.executable, str(bootstrap_script), "--current", current_exe, "--new", str(new_exe_path), "--pid", str(os.getpid())]
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)

            # Exit current application so file lock is released
            sys.exit(0)
            return True

        except Exception as e:
            print(f"Error applying update: {e}")
            return False

    @staticmethod
    def _is_newer_version(remote: str, current: str) -> bool:
        """Helper to compare semantic versioning x.y.z"""
        def parse(v):
            return [int(x) for x in v.split(".") if x.isdigit()]
        return parse(remote) > parse(current)
