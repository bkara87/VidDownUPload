import os
import requests
from io import BytesIO
from PIL import Image
import yt_dlp

class VideoInfoFetcher:
    """
    Fetches video metadata (thumbnail, title, duration, uploader) and public profile video lists without account login.
    """
    @staticmethod
    def fetch_video_info(url: str) -> dict:
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                # Platform detection
                extractor = info.get('extractor_key', '').lower()
                platform = 'YouTube'
                if 'instagram' in extractor:
                    platform = 'Instagram'
                elif 'tiktok' in extractor:
                    platform = 'TikTok'

                duration = info.get('duration', 0)
                dur_str = f"{int(duration // 60):02d}:{int(duration % 60):02d}" if duration else "Canlı / Bilinmiyor"

                return {
                    'title': info.get('title', 'Video'),
                    'uploader': info.get('uploader') or info.get('uploader_id') or 'Bilinmeyen Kanal',
                    'thumbnail_url': info.get('thumbnail'),
                    'duration_str': dur_str,
                    'platform': platform,
                    'view_count': info.get('view_count', 0),
                    'url': url
                }
        except Exception as e:
            print(f"Error fetching video info: {e}")
            return None

    @staticmethod
    def fetch_profile_videos(profile_url: str, limit: int = 10) -> list:
        """
        Extracts public video list from a profile/channel URL without requiring an account login.
        """
        ydl_opts = {
            'extract_flat': True,
            'skip_download': True,
            'playlistend': limit,
            'quiet': True,
            'no_warnings': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(profile_url, download=False)
                entries = info.get('entries', [])
                results = []
                for entry in entries:
                    if not entry:
                        continue
                    v_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                    results.append({
                        'title': entry.get('title', 'Video'),
                        'id': entry.get('id'),
                        'url': v_url,
                        'uploader': entry.get('uploader') or info.get('title', 'Profil'),
                        'duration': entry.get('duration')
                    })
                return results
        except Exception as e:
            print(f"Error fetching profile videos: {e}")
            return []

    @staticmethod
    def load_thumbnail_image(img_url: str, size=(160, 90)):
        if not img_url:
            return None
        try:
            res = requests.get(img_url, timeout=5)
            if res.status_code == 200:
                img = Image.open(BytesIO(res.content)).convert("RGB")
                img = img.resize(size, Image.Resampling.LANCZOS)
                return img
        except Exception as e:
            print(f"Thumbnail load error: {e}")
        return None
