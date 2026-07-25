import os
import re
import json
import time
import yt_dlp
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from src.config import BASE_DIR
from src.downloader.instagram_auth import InstagramAuthManager

class VideoDownloader:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self.auth_manager = InstagramAuthManager(BASE_DIR / "config_keys.json")

    def _save_metadata(self, video_path: str, info: Dict[str, Any], url: str):
        """Saves video caption, hashtags, and uploader info as sidecar JSON with 7/24 Mizah tags"""
        if not video_path or not os.path.exists(video_path):
            return
        try:
            base, _ = os.path.splitext(video_path)
            meta_path = base + ".json"

            raw_description = info.get('description') or info.get('title') or ""
            uploader = info.get('uploader') or info.get('uploader_id') or ''

            # Extract & clean hashtags: Remove third-party channel tags for ANY channel and inject #724mizahdeposu #724mizah
            cleaned_caption, hashtags, hashtags_str = self.process_and_clean_hashtags(raw_description, uploader, url)

            meta = {
                'title': info.get('title', 'Video'),
                'uploader': uploader or 'Unspecified',
                'caption': cleaned_caption,
                'hashtags': hashtags,
                'hashtags_str': hashtags_str,
                'url': url,
                'video_file': os.path.basename(video_path),
                'downloaded_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving metadata JSON: {e}")

    @staticmethod
    def process_and_clean_hashtags(description: str, uploader: str = None, url: str = None) -> tuple:
        """
        Dynamically extracts and cleans ANY third-party channel hashtags, handles, and usernames
        from the video caption/hashtags, and replaces them with 7/24 Mizah Deposu channel hashtags (#724mizahdeposu #724mizah).
        Works dynamically for ANY channel (Instagram, YouTube, TikTok).
        """
        if not description:
            description = ""

        # Extract all hashtags
        all_tags = re.findall(r'#[\w\d_]+', description, re.UNICODE)
        our_tags = ["#724mizahdeposu", "#724mizah"]
        
        # Build dynamic list of channel name keywords to wipe
        uploader_keywords = []

        if uploader:
            u_clean = re.sub(r'[^\w]', '', uploader.lower())
            if len(u_clean) >= 3:
                uploader_keywords.append(u_clean)
                no_num = re.sub(r'\d+$', '', u_clean)
                if len(no_num) >= 3 and no_num not in uploader_keywords:
                    uploader_keywords.append(no_num)

        if url:
            url_match = re.search(r'(?:instagram\.com|tiktok\.com/@|youtube\.com/@)([A-Za-z0-9._]+)', url)
            if url_match:
                handle = re.sub(r'[^\w]', '', url_match.group(1).lower())
                if len(handle) >= 3 and handle not in ['reels', 'reel', 'p', 'shorts', 'watch']:
                    if handle not in uploader_keywords:
                        uploader_keywords.append(handle)
                    handle_no_num = re.sub(r'\d+$', '', handle)
                    if len(handle_no_num) >= 3 and handle_no_num not in uploader_keywords:
                        uploader_keywords.append(handle_no_num)

        # Filter out hashtags matching ANY channel keyword
        cleaned_tags = []
        for tag in all_tags:
            tag_lower = tag.lower()
            is_channel_tag = False
            for kw in uploader_keywords:
                if kw in tag_lower:
                    is_channel_tag = True
                    break
            if not is_channel_tag:
                if tag_lower not in [t.lower() for t in cleaned_tags]:
                    cleaned_tags.append(tag)

        # Inject our channel tags at the beginning if missing
        for ot in reversed(our_tags):
            if not any(ot.lower() == t.lower() for t in cleaned_tags):
                cleaned_tags.insert(0, ot)

        # Clean description text: replace old channel tags and @handles with #724mizahdeposu
        cleaned_description = description
        for kw in uploader_keywords:
            cleaned_description = re.sub(rf'#{kw}\w*', '#724mizahdeposu', cleaned_description, flags=re.IGNORECASE)
            cleaned_description = re.sub(rf'@{kw}\w*', '@724mizahdeposu', cleaned_description, flags=re.IGNORECASE)

        if not any(ot.lower() in cleaned_description.lower() for ot in our_tags):
            cleaned_description = f"{cleaned_description.strip()}\n\n#724mizahdeposu #724mizah"

        return cleaned_description, cleaned_tags, ' '.join(cleaned_tags)

    def _get_history(self) -> dict:
        history_file = Path(self.download_dir) / "download_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_history(self, video_id: str, video_path: str, url: str, title: str):
        history_file = Path(self.download_dir) / "download_history.json"
        data = self._get_history()
        data[video_id] = {
            'file': os.path.basename(video_path),
            'full_path': video_path,
            'url': url,
            'title': title,
            'downloaded_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving download history: {e}")

    def is_already_downloaded(self, url: str) -> Optional[str]:
        """
        Checks if video URL/ID is already downloaded in download_dir or history.
        Returns existing file path if present, or None.
        """
        # Extract ID candidate (e.g. shortcode from Instagram or YouTube ID)
        video_id = None
        ig_match = re.search(r'/(?:reel|p|reels)/([A-Za-z0-9_-]+)', url)
        yt_match = re.search(r'(?:v=|\/)([A-Za-z0-9_-]{11})', url)

        if ig_match:
            video_id = ig_match.group(1)
        elif yt_match:
            video_id = yt_match.group(1)

        # 1. Check download history JSON
        history = self._get_history()
        if video_id and video_id in history:
            existing_path = history[video_id].get('full_path')
            if existing_path and os.path.exists(existing_path):
                return existing_path
            rel_file = history[video_id].get('file')
            if rel_file:
                candidate = os.path.join(self.download_dir, rel_file)
                if os.path.exists(candidate):
                    return candidate

        # 2. Check for filename matching *_ID.mp4 in downloads directory
        if video_id:
            for file in os.listdir(self.download_dir):
                if file.endswith('.mp4') and video_id in file:
                    return os.path.join(self.download_dir, file)

        return None

    def download_video(self, url: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[str]:
        """
        Downloads video with duplicate checking, account login or hesapsiz fallback.
        Returns local path of MP4 file.
        """
        # Duplicate check: skip if already downloaded
        existing = self.is_already_downloaded(url)
        if existing and os.path.exists(existing):
            print(f"Video already downloaded, skipping: {existing}")
            if progress_callback:
                progress_callback({'status': 'finished', 'filename': existing, '_percent_str': 'Zaten İndirildi (Atlandı)'})
            return existing

        last_finished_filename = None

        def _yt_dlp_hook(d):
            nonlocal last_finished_filename
            if d.get('status') == 'finished':
                fn = d.get('filename')
                if fn and not fn.endswith('.fdash') and not '.fdash-' in fn:
                    last_finished_filename = fn
            if progress_callback:
                progress_callback(d)

        ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(title).50s_%(id)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'progress_hooks': [_yt_dlp_hook],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
        }

        # Inject Instagram account credentials or session cookies if downloading Instagram URL
        if 'instagram.com' in url.lower():
            auth_opts = self.auth_manager.get_ytdlp_auth_opts()
            ydl_opts.update(auth_opts)

        info = None
        # 1. Try with user configured options / credentials
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception as e:
            print(f"Download attempt 1 failed: {e}")

        # 2. Browser cookies fallback for Instagram / Age-restricted videos if 1 failed
        if not info or not last_finished_filename:
            for browser in ['chrome', 'edge', 'firefox', 'brave']:
                try:
                    opts = ydl_opts.copy()
                    opts['cookiesfrombrowser'] = (browser,)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if info:
                            break
                except Exception:
                    continue

        # Resolve final MP4 path
        final_mp4_path = None
        if info:
            try:
                prep = ydl.prepare_filename(info)
                base, _ = os.path.splitext(prep)
                mp4_candidate = base + ".mp4"
                if os.path.exists(mp4_candidate):
                    final_mp4_path = mp4_candidate
                elif os.path.exists(prep):
                    final_mp4_path = prep
            except Exception:
                pass

        if not final_mp4_path and last_finished_filename:
            base, _ = os.path.splitext(last_finished_filename)
            mp4_candidate = base + ".mp4"
            if os.path.exists(mp4_candidate):
                final_mp4_path = mp4_candidate
            elif os.path.exists(last_finished_filename):
                final_mp4_path = last_finished_filename

        # If we got a file, save sidecar metadata + history and return final MP4 path
        if final_mp4_path and os.path.exists(final_mp4_path):
            v_id = info.get('id') if info else os.path.basename(final_mp4_path)
            v_title = info.get('title') if info else os.path.basename(final_mp4_path)
            if info:
                self._save_metadata(final_mp4_path, info, url)
            self._save_history(v_id, final_mp4_path, url, v_title)
            return final_mp4_path

        return None

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

