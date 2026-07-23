import os
import yt_dlp
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from src.config import BASE_DIR
from src.downloader.instagram_auth import InstagramAuthManager

class VideoDownloader:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self.auth_manager = InstagramAuthManager(BASE_DIR / "config_keys.json")

    def download_video(self, url: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[str]:
        """
        Downloads video from Instagram, YouTube, TikTok, etc. with account login or hesapsiz fallback.
        Returns the local path of the downloaded file.
        """
        downloaded_file_path = None

        def _yt_dlp_hook(d):
            nonlocal downloaded_file_path
            if d.get('status') == 'finished':
                downloaded_file_path = d.get('filename')
            if progress_callback:
                progress_callback(d)

        ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(title).50s_%(id)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'progress_hooks': [_yt_dlp_hook],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }

        # Inject Instagram account credentials or session cookies if downloading Instagram URL
        if 'instagram.com' in url.lower():
            auth_opts = self.auth_manager.get_ytdlp_auth_opts()
            ydl_opts.update(auth_opts)

        # 1. Try with user configured options / credentials
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not downloaded_file_path and info:
                    downloaded_file_path = ydl.prepare_filename(info)
                if downloaded_file_path and os.path.exists(downloaded_file_path):
                    return downloaded_file_path
        except Exception:
            pass

        # 2. Try browser cookies fallback for Instagram / Age-restricted videos
        for browser in ['chrome', 'edge', 'firefox', 'brave']:
            try:
                opts = ydl_opts.copy()
                opts['cookiesfrombrowser'] = (browser,)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if not downloaded_file_path and info:
                        downloaded_file_path = ydl.prepare_filename(info)
                    if downloaded_file_path and os.path.exists(downloaded_file_path):
                        return downloaded_file_path
            except Exception:
                continue

        return downloaded_file_path

    def fetch_info(self, url: str) -> Dict[str, Any]:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        if 'instagram.com' in url.lower():
            ydl_opts.update(self.auth_manager.get_ytdlp_auth_opts())
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
