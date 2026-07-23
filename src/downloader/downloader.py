import os
import yt_dlp
from typing import Callable, Optional, Dict, Any

class VideoDownloader:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir

    def download_video(self, url: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[str]:
        """
        Downloads video from Instagram, YouTube, TikTok, etc. using yt-dlp.
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
            'ignoreerrors': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not downloaded_file_path and info:
                # Fallback if filename wasn't set in hook
                downloaded_file_path = ydl.prepare_filename(info)

        return downloaded_file_path

    def fetch_info(self, url: str) -> Dict[str, Any]:
        """
        Fetches video metadata without downloading.
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
