import os
import re
import requests
from io import BytesIO
from PIL import Image
import yt_dlp

from src.config import BASE_DIR
from src.downloader.instagram_auth import InstagramAuthManager

class VideoInfoFetcher:
    """
    Fetches video metadata (thumbnail, title, duration, uploader) and public/authenticated profile video lists.
    """
    auth_manager = InstagramAuthManager(BASE_DIR / "config_keys.json")

    @classmethod
    def fetch_video_info(cls, url: str) -> dict:
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        if 'instagram.com' in url.lower():
            ydl_opts.update(cls.auth_manager.get_ytdlp_auth_opts())

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                # Platform detection
                extractor = info.get('extractor_key', '').lower()
                platform = 'YouTube'
                if 'instagram' in extractor or 'instagram.com' in url.lower():
                    platform = 'Instagram'
                elif 'tiktok' in extractor:
                    platform = 'TikTok'

                duration = info.get('duration', 0)
                dur_str = f"{int(duration // 60):02d}:{int(duration % 60):02d}" if duration else "Canlı / Bilinmiyor"

                description = info.get('description') or info.get('title') or ""
                hashtags = re.findall(r'#\w+', description)

                return {
                    'title': info.get('title', 'Video'),
                    'uploader': info.get('uploader') or info.get('uploader_id') or 'Bilinmeyen Kanal',
                    'thumbnail_url': info.get('thumbnail'),
                    'duration_str': dur_str,
                    'platform': platform,
                    'view_count': info.get('view_count', 0),
                    'url': url,
                    'caption': description,
                    'hashtags': hashtags
                }
        except Exception as e:
            print(f"Error fetching video info: {e}")
            return None

    @classmethod
    def fetch_profile_videos(cls, profile_url: str, limit: int = 25) -> list:
        """
        Extracts video list from a profile/channel URL or single reel URL.
        """
        url_clean = profile_url.strip()

        # 1. Single reel URL passed to profile scan
        if '/reel/' in url_clean.lower() or '/p/' in url_clean.lower():
            single_info = cls.fetch_video_info(url_clean)
            if single_info:
                return [{
                    'title': single_info.get('title', 'Reel Video'),
                    'id': single_info.get('url'),
                    'url': url_clean,
                    'uploader': single_info.get('uploader', 'Profil'),
                    'duration': None,
                    'thumbnail_url': single_info.get('thumbnail_url')
                }]

        # 2. Extract Instagram username if instagram profile URL
        ig_username = None
        if 'instagram.com' in url_clean.lower():
            match = re.search(r'instagram\.com/([^/?#]+)', url_clean)
            if match:
                u = match.group(1).strip()
                if u.lower() not in ['reel', 'p', 'reels', 'stories', 'explore']:
                    ig_username = u

        # 3. Direct Feed API Scraper for Instagram (Instant Hesapsiz Profile Reels Query with Pagination)
        if ig_username:
            try:
                headers = {
                    'User-Agent': 'Instagram 275.0.0.27.98 Android (33/13; 420dpi; 1080x2400; Xiaomi; M2007J20CG; surya; qcom; en_US; 456206120)',
                    'X-IG-App-ID': '936619743392459',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
                auth_info = cls.auth_manager.load_auth_info()
                sid = auth_info.get("sessionid")
                cookies = {'sessionid': sid} if sid else None

                results = []
                next_max_id = None

                while len(results) < limit:
                    api_url = f'https://www.instagram.com/api/v1/feed/user/{ig_username}/username/'
                    if next_max_id:
                        api_url += f'?max_id={next_max_id}'

                    res = requests.get(api_url, headers=headers, cookies=cookies, timeout=10)
                    if res.status_code != 200:
                        break

                    data = res.json()
                    items = data.get('items', [])
                    if not items:
                        break

                    for it in items:
                        code = it.get('code')
                        if not code:
                            continue
                        caption_obj = it.get('caption')
                        caption_text = caption_obj.get('text', '') if caption_obj else ''
                        title = (caption_text[:60] + '...') if caption_text else f"Instagram Reel {code}"
                        
                        image_versions = it.get('image_versions2', {}).get('candidates', [])
                        thumb_url = image_versions[0].get('url') if image_versions else None

                        results.append({
                            'title': title,
                            'id': code,
                            'url': f"https://www.instagram.com/reel/{code}/",
                            'uploader': ig_username,
                            'duration': None,
                            'thumbnail_url': thumb_url
                        })
                        if len(results) >= limit:
                            break

                    next_max_id = data.get('next_max_id')
                    more_available = data.get('more_available', False)
                    if not more_available or not next_max_id:
                        break

                if results:
                    print(f"Direct Feed API successfully extracted TOTAL {len(results)} reels for {ig_username}")
                    return results
            except Exception as e:
                print(f"Direct Feed API note: {e}")

        # 4. Try Instaloader for Instagram profile fetching
        if ig_username:
            try:
                import instaloader
                L = instaloader.Instaloader(quiet=True)
                auth_info = cls.auth_manager.load_auth_info()
                sid = auth_info.get("sessionid")
                if sid:
                    L.context._session.cookies.set("sessionid", sid, domain=".instagram.com")

                profile = instaloader.Profile.from_username(L.context, ig_username)
                results = []
                for p in profile.get_posts():
                    if p.is_video:
                        results.append({
                            'title': (p.caption[:60] + '...') if p.caption else f"Instagram Reel {p.shortcode}",
                            'id': p.shortcode,
                            'url': f"https://www.instagram.com/reel/{p.shortcode}/",
                            'uploader': profile.username,
                            'duration': None,
                            'thumbnail_url': p.url
                        })
                        if len(results) >= limit:
                            break
                if results:
                    return results
            except Exception as e:
                print(f"Instaloader profile fetch note: {e}")

        # 4. Standard yt-dlp profile playlist extraction
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'playlistend': limit,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True
        }
        if 'instagram.com' in url_clean.lower():
            ydl_opts.update(cls.auth_manager.get_ytdlp_auth_opts())

        target_urls = [url_clean]
        if ig_username:
            target_urls.append(f"https://www.instagram.com/{ig_username}/reels/")

        for t_url in target_urls:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(t_url, download=False)
                    if not info:
                        continue

                    entries = info.get('entries', [])
                    results = []

                    if entries:
                        for entry in entries:
                            if not entry:
                                continue
                            v_url = entry.get('url') or entry.get('webpage_url')
                            if not v_url and entry.get('id'):
                                if 'instagram' in t_url.lower():
                                    v_url = f"https://www.instagram.com/reel/{entry.get('id')}/"
                                else:
                                    v_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                            
                            if v_url:
                                results.append({
                                    'title': entry.get('title') or entry.get('description') or 'Video',
                                    'id': entry.get('id'),
                                    'url': v_url,
                                    'uploader': entry.get('uploader') or info.get('title', 'Profil'),
                                    'duration': entry.get('duration'),
                                    'thumbnail_url': entry.get('thumbnail')
                                })
                        if results:
                            return results
            except Exception as e:
                print(f"Error fetching profile videos from {t_url}: {e}")

        # 5. Browser cookies fallback for profile scan
        for browser in ['chrome', 'edge', 'firefox']:
            try:
                opts = ydl_opts.copy()
                opts['cookiesfrombrowser'] = (browser,)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url_clean, download=False)
                    if info and info.get('entries'):
                        results = []
                        for entry in info.get('entries'):
                            if entry:
                                v_url = entry.get('url') or entry.get('webpage_url') or url_clean
                                results.append({
                                    'title': entry.get('title', 'Video'),
                                    'id': entry.get('id'),
                                    'url': v_url,
                                    'uploader': entry.get('uploader', 'Profil'),
                                    'duration': entry.get('duration')
                                })
                        if results:
                            return results
            except Exception:
                continue

        return []

    _thumb_cache = {}

    @classmethod
    def load_thumbnail_image(cls, img_url: str, size=(90, 160)):
        if not img_url:
            return None
        if img_url in cls._thumb_cache:
            return cls._thumb_cache[img_url]
        try:
            res = requests.get(img_url, timeout=2)
            if res.status_code == 200:
                img = Image.open(BytesIO(res.content)).convert("RGB")
                img.thumbnail(size, Image.Resampling.NEAREST)
                cls._thumb_cache[img_url] = img
                return img
        except Exception:
            pass
        return None

