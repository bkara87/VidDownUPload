import os
import json
import time
import base64
import threading
import subprocess
import webview
from pathlib import Path
from typing import Dict, Any, Optional, List

import hashlib
from src.config import APP_NAME, APP_VERSION, DOWNLOADS_DIR, PROCESSED_DIR, BASE_DIR, USER_DATA_DIR, THUMB_CACHE_DIR, FFMPEG_BINARY
from src.downloader.downloader import VideoDownloader
from src.updater.github_updater import GitHubUpdater

KEYS_FILE = USER_DATA_DIR / "config_keys.json"


class ApiBridge:
    """
    Full Python–JavaScript bridge for VidDownUPload v2.0 PyWebView app.
    All public methods are callable from JavaScript via window.pywebview.api.*
    """

    def __init__(self):
        self.downloader = VideoDownloader(str(DOWNLOADS_DIR))
        self.updater = GitHubUpdater()
        self._window = None
        self._current_download_path: Optional[str] = None
        self._current_studio_path: Optional[str] = None
        self._thumb_mem_cache: Dict[str, str] = {}

    def set_window(self, window):
        self._window = window

    # ──────────────────────────────────────────────────────────────
    # LOGGING
    # ──────────────────────────────────────────────────────────────

    def log(self, message: str, log_type: str = "info"):
        """Send log message to frontend JS console."""
        if self._window:
            safe_msg = json.dumps(message)
            try:
                self._window.evaluate_js(f"window.appendLog({safe_msg}, '{log_type}');")
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────
    # APP INFO
    # ──────────────────────────────────────────────────────────────

    def get_app_info(self) -> Dict[str, Any]:
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "downloads_dir": str(DOWNLOADS_DIR),
            "processed_dir": str(PROCESSED_DIR),
            "base_dir": str(BASE_DIR)
        }

    # ──────────────────────────────────────────────────────────────
    # VIDEO LISTINGS
    # ──────────────────────────────────────────────────────────────

    def get_downloaded_videos(self) -> List[Dict[str, Any]]:
        """Returns list of downloaded videos with their metadata."""
        return self._list_videos(DOWNLOADS_DIR)

    def get_processed_videos(self) -> List[Dict[str, Any]]:
        """Returns list of processed (watermarked) videos."""
        return self._list_videos(PROCESSED_DIR)

    def _get_thumb_cache_key(self, video_path: str, st_mtime: float = 0, st_size: int = 0) -> str:
        raw_key = f"{video_path}_{st_mtime}_{st_size}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    def _list_videos(self, directory: Path) -> List[Dict[str, Any]]:
        result = []
        try:
            dirs_to_scan = [directory]
            # Check fallback directory in project BASE_DIR if different
            folder_name = directory.name
            fallback_dir = BASE_DIR / folder_name
            if fallback_dir.exists() and fallback_dir.resolve() != directory.resolve():
                dirs_to_scan.append(fallback_dir)

            seen_filenames = set()
            items = []
            for target_d in dirs_to_scan:
                if not target_d.exists():
                    continue
                with os.scandir(str(target_d)) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in ('.mp4', '.mov', '.avi', '.mkv', '.webm'):
                                if entry.name not in seen_filenames:
                                    seen_filenames.add(entry.name)
                                    st = entry.stat(follow_symlinks=False)
                                    items.append((entry, st))
            
            # En son değiştirilenleri en üstte göster
            items.sort(key=lambda x: x[1].st_mtime, reverse=True)

            for entry, st in items:
                video_path = entry.path
                meta = self._load_sidecar(video_path)
                size_mb = round(st.st_size / (1024 * 1024), 1)

                # Disk önbelleğinde resim var mı kontrol et
                cache_key = self._get_thumb_cache_key(video_path, st.st_mtime, st.st_size)
                thumb_base64 = ""
                if cache_key in self._thumb_mem_cache:
                    thumb_base64 = self._thumb_mem_cache[cache_key]
                else:
                    disk_file = THUMB_CACHE_DIR / f"{cache_key}.jpg"
                    if disk_file.exists():
                        try:
                            with open(disk_file, "rb") as tf:
                                data = base64.b64encode(tf.read()).decode("utf-8")
                                thumb_base64 = f"data:image/jpeg;base64,{data}"
                                self._thumb_mem_cache[cache_key] = thumb_base64
                        except Exception:
                            pass

                result.append({
                    "path": video_path,
                    "filename": entry.name,
                    "stem": os.path.splitext(entry.name)[0],
                    "size_mb": size_mb,
                    "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
                    "title": meta.get("title", entry.name) if meta else os.path.splitext(entry.name)[0],
                    "uploader": meta.get("uploader", "") if meta else "",
                    "caption": meta.get("caption", "") if meta else "",
                    "hashtags": meta.get("hashtags", []) if meta else [],
                    "hashtags_str": meta.get("hashtags_str", "") if meta else "",
                    "url": meta.get("url", "") if meta else "",
                    "has_meta": meta is not None,
                    "thumbnail": thumb_base64
                })
        except Exception as e:
            print(f"Error listing videos: {e}")
        return result

    def _load_sidecar(self, video_path: str) -> Optional[Dict]:
        base, _ = os.path.splitext(video_path)
        meta_path = base + ".json"
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def get_sidecar_meta(self, video_path: str) -> Dict[str, Any]:
        """Returns sidecar metadata for a video (caption, hashtags, etc)."""
        meta = self._load_sidecar(video_path)
        if meta:
            return meta
        fn = os.path.splitext(os.path.basename(video_path))[0]
        return {
            "title": fn,
            "uploader": "",
            "caption": fn,
            "hashtags": ["#reels", "#viral", "#724mizahdeposu"],
            "hashtags_str": "#reels #viral #724mizahdeposu",
            "url": ""
        }

    # ──────────────────────────────────────────────────────────────
    # VIDEO THUMBNAIL (base64 for web display)
    # ──────────────────────────────────────────────────────────────

    def get_video_thumbnail(self, video_path: str) -> str:
        """
        Extract a thumbnail from the video using ffmpeg and return as base64 data URL.
        Uses high-speed memory and disk caching.
        """
        if not video_path or not os.path.exists(video_path):
            return ""
        try:
            st = os.stat(video_path)
            cache_key = self._get_thumb_cache_key(video_path, st.st_mtime, st.st_size)

            # 1. Hafıza önbelleği
            if cache_key in self._thumb_mem_cache:
                return self._thumb_mem_cache[cache_key]

            # 2. Disk önbelleği
            disk_file = THUMB_CACHE_DIR / f"{cache_key}.jpg"
            if disk_file.exists():
                try:
                    with open(disk_file, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                        res = f"data:image/jpeg;base64,{data}"
                        self._thumb_mem_cache[cache_key] = res
                        return res
                except Exception:
                    pass

            # 3. FFmpeg ile hızlı kare çıkarma
            ffmpeg_bin = FFMPEG_BINARY
            cmd = [
                ffmpeg_bin,
                "-ss", "00:00:01",
                "-i", video_path,
                "-vframes", "1",
                "-vf", "scale=240:-2",
                "-q:v", "4",
                "-y",
                str(disk_file)
            ]
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )

            if disk_file.exists():
                with open(disk_file, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                res = f"data:image/jpeg;base64,{data}"
                self._thumb_mem_cache[cache_key] = res
                return res
        except Exception as e:
            print(f"Thumbnail extraction error: {e}")
        return ""

    def _get_ffmpeg_path(self) -> str:
        """Returns the path to ffmpeg binary (embedded or system)."""
        embedded = BASE_DIR / "ffmpeg.exe"
        if embedded.exists():
            return str(embedded)
        return "ffmpeg"

    # ──────────────────────────────────────────────────────────────
    # FILE OPERATIONS
    # ──────────────────────────────────────────────────────────────

    def delete_video(self, video_path: str) -> Dict[str, Any]:
        """Delete a video and its sidecar JSON if present."""
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            base, _ = os.path.splitext(video_path)
            json_path = base + ".json"
            if os.path.exists(json_path):
                os.remove(json_path)
            self.log(f"🗑️ Silindi: {os.path.basename(video_path)}", "info")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_folder(self, folder_type: str) -> Dict[str, Any]:
        """Opens folder in Windows Explorer."""
        folder_map = {
            "downloads": str(DOWNLOADS_DIR),
            "processed": str(PROCESSED_DIR),
            "base": str(BASE_DIR)
        }
        path = folder_map.get(folder_type, str(DOWNLOADS_DIR))
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            os.startfile(path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_file_location(self, file_path: str) -> Dict[str, Any]:
        """Opens Windows Explorer with the specific video file selected."""
        try:
            if not file_path:
                return self.open_folder("downloads")
            
            norm_path = os.path.normpath(file_path)
            if os.path.exists(norm_path):
                subprocess.run(f'explorer /select,"{norm_path}"', shell=True)
                return {"success": True}
            else:
                folder = os.path.dirname(norm_path)
                if os.path.exists(folder):
                    os.startfile(folder)
                    return {"success": True}
                return self.open_folder("downloads")
        except Exception as e:
            return {"success": False, "error": str(e)}

    def select_logo_file(self) -> str:
        """Opens native Windows file dialog for logo PNG selection."""
        if self._window:
            file_types = ('Image Files (*.png;*.jpg;*.jpeg)', 'All files (*.*)')
            result = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
            if result and len(result) > 0:
                return result[0]
        return ""

    def get_asset_logo_list(self) -> List[Dict[str, str]]:
        """Returns list of available logo assets from assets/ directory."""
        logos = []
        asset_dir = BASE_DIR / "assets"
        if asset_dir.exists():
            for f in asset_dir.iterdir():
                if f.suffix.lower() in ('.png', '.jpg', '.jpeg') and 'logo' in f.name.lower():
                    logos.append({
                        "name": f.name,
                        "path": str(f)
                    })
        return logos

    # ──────────────────────────────────────────────────────────────
    # DOWNLOAD
    # ──────────────────────────────────────────────────────────────

    def start_download(self, url: str) -> Dict[str, Any]:
        """Start async video download."""
        if not url or not url.strip():
            return {"success": False, "message": "URL boş"}
        threading.Thread(target=self._download_task, args=(url.strip(),), daemon=True).start()
        return {"success": True, "message": "İndirme başlatıldı"}

    def _download_task(self, url: str):
        self.log(f"📥 İndirme başlatılıyor: {url}", "info")
        try:
            def _progress(d):
                status = d.get("status")
                pct = d.get("_percent_str", "")
                speed = d.get("_speed_str", "")
                if status == "downloading" and pct:
                    self.log(f"⬇️ İndiriliyor: {pct} {speed}", "info")

            file_path = self.downloader.download_video(url, progress_callback=_progress)
            if file_path and os.path.exists(file_path):
                self._current_download_path = file_path
                self._current_studio_path = file_path
                fn = os.path.basename(file_path)
                self.log(f"✅ İndirme Tamamlandı: {fn}", "success")
                if self._window:
                    self._window.evaluate_js(
                        f"window.onDownloadComplete({json.dumps(file_path)});"
                    )
            else:
                self.log("❌ İndirme başarısız veya dosya alınamadı.", "error")
        except Exception as e:
            self.log(f"❌ İndirme Hatası: {str(e)}", "error")

    def scan_profile(self, url: str) -> Dict[str, Any]:
        """Scan profile/channel for videos (async, result sent via JS callback)."""
        threading.Thread(target=self._scan_profile_task, args=(url,), daemon=True).start()
        return {"success": True, "message": "Profil taraması başlatıldı"}

    def _scan_profile_task(self, url: str):
        self.log(f"🔍 Profil taranıyor: {url}", "info")
        try:
            from src.downloader.info_fetcher import VideoInfoFetcher
            items = VideoInfoFetcher.fetch_profile_videos(url, limit=300)
            self.log(f"✅ {len(items)} video bulundu.", "success")
            if self._window:
                self._window.evaluate_js(
                    f"window.onProfileScanComplete({json.dumps(items)});"
                )
        except Exception as e:
            self.log(f"❌ Profil tarama hatası: {e}", "error")

    def fetch_video_info(self, url: str) -> Dict[str, Any]:
        """Synchronous video info fetch for URL preview card."""
        try:
            from src.downloader.info_fetcher import VideoInfoFetcher
            info = VideoInfoFetcher.fetch_video_info(url)
            return info or {}
        except Exception:
            return {}

    # ──────────────────────────────────────────────────────────────
    # STUDIO — VIDEO PROCESSING
    # ──────────────────────────────────────────────────────────────

    def set_studio_video(self, video_path: str) -> Dict[str, Any]:
        """Set the video currently being edited in studio."""
        if video_path and os.path.exists(video_path):
            self._current_studio_path = video_path
            return {"success": True, "path": video_path}
        return {"success": False, "error": "Dosya bulunamadı"}

    def start_process(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Start async video processing with watermark/blur/logo options."""
        source_path = options.get("source_path") or self._current_studio_path
        if not source_path or not os.path.exists(source_path):
            return {"success": False, "message": "İşlenecek video bulunamadı"}

        threading.Thread(target=self._process_task, args=(source_path, options), daemon=True).start()
        return {"success": True, "message": "Video işleme başlatıldı"}

    def _process_task(self, source_path: str, options: Dict[str, Any]):
        self.log(f"🎨 Video işleniyor: {os.path.basename(source_path)}", "info")
        try:
            from src.processor.ffmpeg_utils import VideoProcessor
            processor = VideoProcessor()

            out_name = f"processed_{os.path.basename(source_path)}"
            out_path = str(PROCESSED_DIR / out_name)

            logo_path = options.get("logo_path") if options.get("logo_enabled") else None
            if logo_path:
                if not os.path.exists(logo_path):
                    clean_name = os.path.basename(logo_path)
                    candidates = [
                        BASE_DIR / logo_path,
                        USER_DATA_DIR / logo_path,
                        BASE_DIR / "assets" / clean_name,
                        USER_DATA_DIR / "assets" / clean_name,
                        BASE_DIR / "web" / "assets" / clean_name,
                    ]
                    found = False
                    for cand in candidates:
                        if cand.exists():
                            logo_path = str(cand)
                            found = True
                            break
                    if not found:
                        print(f"DEBUG [_process_task]: Logo file not found: {options.get('logo_path')}")
                        logo_path = None

            text_wm = options.get("text_watermark") or None
            badge_preset = options.get("badge_preset") or None
            logo_scale = float(options.get("logo_scale", 0.22))
            quality_label = options.get("quality_label") or None

            # Multi-Blur positions (relative coords B1-B5)
            blur_boxes = None
            if options.get("blur_boxes") and isinstance(options.get("blur_boxes"), list):
                blur_boxes = []
                for b in options.get("blur_boxes"):
                    if isinstance(b, (list, tuple)) and len(b) == 4:
                        blur_boxes.append((float(b[0]), float(b[1]), float(b[2]), float(b[3])))
            elif options.get("blur_enabled"):
                blur_boxes = [(
                    float(options.get("blur_x", 0.65)),
                    float(options.get("blur_y", 0.88)),
                    float(options.get("blur_w", 0.35)),
                    float(options.get("blur_h", 0.12))
                )]

            # Logo position (relative coords)
            logo_rel_pos = None
            if options.get("logo_enabled") and logo_path:
                logo_rel_pos = (
                    float(options.get("logo_x", 0.78)),
                    float(options.get("logo_y", 0.88))
                )

            # Frame template options
            frame_png_path = options.get("frame_png_path") if options.get("frame_enabled") else None
            frame_config = options.get("frame_config") if options.get("frame_enabled") else None
            frame_adjustments = options.get("frame_adjustments") if options.get("frame_enabled") else None

            success = processor.process_video(
                input_path=source_path,
                output_path=out_path,
                watermark_logo_path=logo_path,
                logo_scale=logo_scale,
                text_watermark=text_wm,
                badge_preset=badge_preset,
                logo_rel_pos=logo_rel_pos,
                blur_boxes=blur_boxes,
                quality_label=quality_label,
                frame_png_path=frame_png_path,
                frame_config=frame_config,
                frame_adjustments=frame_adjustments
            )

            if success:
                self.log(f"🎉 İşlem Tamamlandı! → {out_name}", "success")
                if self._window:
                    self._window.evaluate_js(
                        f"window.onProcessComplete({json.dumps(out_path)});"
                    )
            else:
                self.log("❌ Video işleme sırasında FFmpeg hatası oluştu.", "error")

        except Exception as e:
            self.log(f"❌ İşleme Hatası: {str(e)}", "error")

    # ──────────────────────────────────────────────────────────────
    # SOCIAL MEDIA UPLOAD
    # ──────────────────────────────────────────────────────────────

    def upload_video(self, video_path: str, platforms: Dict[str, bool], custom_caption: str = "") -> Dict[str, Any]:
        """Start async social media upload for selected platforms."""
        if not video_path or not os.path.exists(video_path):
            return {"success": False, "message": "Video dosyası bulunamadı"}

        threading.Thread(
            target=self._upload_task,
            args=(video_path, platforms, custom_caption),
            daemon=True
        ).start()
        return {"success": True, "message": "Yükleme başlatıldı"}

    def _upload_task(self, video_path: str, platforms: Dict[str, bool], custom_caption: str):
        fn = os.path.basename(video_path)
        self.log(f"🚀 Sosyal Medya Paylaşımı Başlatılıyor: {fn}", "info")
        active = [k for k, v in platforms.items() if v]
        self.log(f"🎯 Hedef Platformlar: {', '.join(active)}", "info")

        try:
            from src.uploader.social_uploader import SocialUploaderManager

            # If user provided custom caption, save it to override sidecar
            if custom_caption and custom_caption.strip():
                self._override_sidecar_caption(video_path, custom_caption.strip())

            results = SocialUploaderManager.process_upload(
                video_path=video_path,
                selected_platforms=platforms,
                log_callback=self.log
            )

            if self._window:
                self._window.evaluate_js(
                    f"window.onUploadComplete({json.dumps(results)});"
                )
        except Exception as e:
            self.log(f"❌ Yükleme Hatası: {e}", "error")

    def _override_sidecar_caption(self, video_path: str, caption: str):
        """Temporarily overrides the sidecar caption with user's custom text."""
        base, _ = os.path.splitext(video_path)
        meta_path = base + ".json"
        meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                pass
        meta["caption"] = caption
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Loads and returns cleaned metadata for video (title, description, tags, channel name)."""
        try:
            from src.processor.metadata_cleaner import MetadataCleaner
            return MetadataCleaner.get_metadata_for_video(video_path)
        except Exception as e:
            return {"error": str(e)}

    # ──────────────────────────────────────────────────────────────
    # FRAME TEMPLATE STUDIO
    # ──────────────────────────────────────────────────────────────

    def get_frame_templates(self) -> List[Dict[str, Any]]:
        """Returns list of imported PNG frame templates with base64 previews."""
        try:
            from src.processor.frame_manager import FrameManager
            return FrameManager.list_templates()
        except Exception as e:
            print(f"DEBUG [get_frame_templates]: Error: {e}")
            return []

    def import_frame_template(self, name: str, category: str, png_base64: str, config_json_str: str) -> Dict[str, Any]:
        """Imports a new PNG frame template."""
        try:
            from src.processor.frame_manager import FrameManager
            import json as _json

            if "," in png_base64:
                png_base64 = png_base64.split(",", 1)[1]

            png_bytes = base64.b64decode(png_base64)
            config_data = _json.loads(config_config_json_str if 'config_config_json_str' in locals() else config_json_str)

            res = FrameManager.save_template(name=name, category=category, png_bytes=png_bytes, config_data=config_data)
            if res.get("success"):
                self.log(f"✅ Çerçeve şablonu kaydedildi: '{res['name']}'", "success")
            return res
        except Exception as e:
            self.log(f"❌ Çerçeve kaydetme hatası: {e}", "error")
            return {"success": False, "error": str(e)}

    def delete_frame_template(self, name: str) -> Dict[str, Any]:
        """Deletes a frame template."""
        try:
            from src.processor.frame_manager import FrameManager
            res = FrameManager.delete_template(name)
            if res.get("success"):
                self.log(f"🗑️ Çerçeve şablonu silindi: '{name}'", "info")
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ──────────────────────────────────────────────────────────────
    # API KEYS MANAGEMENT
    # ──────────────────────────────────────────────────────────────

    def get_api_keys(self) -> Dict[str, Any]:
        """Load and return all saved API keys from USER_DATA_DIR and BASE_DIR."""
        target_files = [USER_DATA_DIR / "config_keys.json", BASE_DIR / "config_keys.json"]
        data = {}
        for kf in target_files:
            if kf.exists():
                try:
                    with open(kf, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                        if file_data and isinstance(file_data, dict):
                            for key, val in file_data.items():
                                if val or key not in data:
                                    data[key] = val
                except Exception as e:
                    print(f"DEBUG [get_api_keys]: Error reading {kf}: {e}")

        if data:
            safe = dict(data)
            # Mask password
            if "instagram_auth" in safe and isinstance(safe["instagram_auth"], dict):
                auth = dict(safe["instagram_auth"])
                if auth.get("password"):
                    auth["password"] = "●" * min(len(auth["password"]), 8)
                safe["instagram_auth"] = auth
            return safe
        return {}

    def save_api_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save API keys to config_keys.json in both USER_DATA_DIR and BASE_DIR. Preserves existing values if masked."""
        try:
            existing = self.get_api_keys()

            def is_masked(val: str) -> bool:
                return bool(val and ('*' in val or '●' in val))

            # Preserve existing password if masked
            if "instagram_auth" in data and isinstance(data["instagram_auth"], dict):
                new_pass = data["instagram_auth"].get("password", "")
                if is_masked(new_pass):
                    existing_auth = existing.get("instagram_auth", {})
                    data["instagram_auth"]["password"] = existing_auth.get("password", "")

            # Preserve access token / secrets if masked
            for k in ["instagram_access_token", "youtube_client_secret", "tiktok_access_token", "tiktok_client_secret", "tiktok_refresh_token"]:
                if k in data and is_masked(data[k]):
                    data[k] = existing.get(k, "")

            existing.update(data)

            # Save to persistent AppData (USER_DATA_DIR)
            user_keys_file = USER_DATA_DIR / "config_keys.json"
            user_keys_file.parent.mkdir(parents=True, exist_ok=True)
            with open(user_keys_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            # Sync to BASE_DIR if writable and different
            try:
                base_keys_file = BASE_DIR / "config_keys.json"
                if base_keys_file != user_keys_file:
                    with open(base_keys_file, "w", encoding="utf-8") as f:
                        json.dump(existing, f, ensure_ascii=False, indent=2)
            except Exception as sync_err:
                print(f"DEBUG [save_api_keys]: Sync to BASE_DIR note: {sync_err}")

            self.log("✅ API anahtarları başarıyla kaydedildi.", "success")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


    def start_tiktok_auth_wizard(self, client_key: str = "", client_secret: str = "", scope: str = "video.publish", scope_fmt: str = "comma") -> Dict[str, Any]:
        """
        TikTok OAuth 2.0 PKCE Login Wizard.
        Triggers system browser, receives callback, exchanges tokens & fetches user profile automatically.
        """
        import threading
        def _worker():
            try:
                from src.uploader.tiktokapi import TikTokOAuthPKCE, _decrypt_secret
                keys = self.get_api_keys()

                ck = client_key.strip()
                if not ck or "*" in ck or "\u25cf" in ck:
                    ck = keys.get("tiktok_client_key", "").strip()

                raw_cs = client_secret.strip()
                if not raw_cs or "*" in raw_cs or "\u25cf" in raw_cs:
                    raw_cs = keys.get("tiktok_client_secret", "").strip()

                cs = _decrypt_secret(raw_cs)

                if not ck or not cs:
                    self.log("❌ Lütfen önce TikTok Client Key ve Client Secret girin.", "error")
                    return

                chosen_scope = scope.strip() if scope else "video.publish"
                self.log(f"🔐 TikTok OAuth 2.0 PKCE Giriş Sihirbazı başlatılıyor (Scope: {chosen_scope}, Format: {scope_fmt})...", "info")
                res = TikTokOAuthPKCE.run_auth_wizard(ck, cs, scope=chosen_scope, scope_fmt=scope_fmt)

                if isinstance(res, str):
                    res = {"success": False, "error": res}
                elif not isinstance(res, dict):
                    res = {"success": False, "error": str(res)}

                if res.get("success"):
                    uname = res.get("username") or res.get("display_name") or ""
                    open_id = res.get("open_id", "")
                    self.log("🎉 TikTok hesabınız başarıyla bağlandı.", "success")
                    if self._window:
                        try:
                            self._window.evaluate_js(
                                "if(typeof refreshApiKeysUI==='function') refreshApiKeysUI(); "
                                "var st = document.getElementById('ttAuthStatus'); if(st) st.style.display='none'; "
                                "var btn = document.getElementById('btnTtAuth'); if(btn) btn.disabled=false;"
                            )
                        except Exception:
                            pass
                else:
                    self.log(f"❌ TikTok Girişi Başarısız: {res.get('error')}", "error")
                    if self._window:
                        try:
                            self._window.evaluate_js(
                                "var st = document.getElementById('ttAuthStatus'); if(st) st.style.display='none'; "
                                "var btn = document.getElementById('btnTtAuth'); if(btn) btn.disabled=false;"
                            )
                        except Exception:
                            pass
            except Exception as e:
                self.log(f"❌ TikTok OAuth İstisnası: {str(e)}", "error")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return {"success": True, "message": "Giriş işlemi başlatıldı..."}

    def save_manual_tiktok_token(self, access_token: str, open_id: str = "") -> Dict[str, Any]:
        """Saves manually pasted TikTok Access Token & Open ID directly into config_keys.json."""
        acc_tok = (access_token or "").strip()
        open_id_val = (open_id or "").strip()

        if not acc_tok:
            return {"success": False, "error": "Access Token boş olamaz."}

        try:
            from src.uploader.tiktokapi import TikTokOAuthPKCE, KEYS_FILE
            existing = {}
            if KEYS_FILE.exists():
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing["tiktok_access_token"] = acc_tok
            existing["tiktok_open_id"] = open_id_val
            existing["tiktok_expires_at"] = int(time.time()) + (30 * 86400) # 30 days default fallback

            # Auto fetch user info
            user_info = TikTokOAuthPKCE.fetch_user_info(acc_tok)
            if user_info.get("success"):
                existing["tiktok_username"] = user_info.get("username", "")
                existing["tiktok_display_name"] = user_info.get("display_name", "")
                existing["tiktok_avatar_url"] = user_info.get("avatar_url", "")
                if not open_id_val and user_info.get("open_id"):
                    existing["tiktok_open_id"] = user_info["open_id"]

            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            self.log(f"🎉 Manuel TikTok Access Token Başarıyla Kaydedildi! (Hesap: @{existing.get('tiktok_username', 'Bilinmiyor')})", "success")
            
            if self._window:
                try:
                    self._window.evaluate_js("if(typeof refreshApiKeysUI==='function') refreshApiKeysUI();")
                except Exception:
                    pass

            return {"success": True, "message": "TikTok Token kaydedildi."}
        except Exception as e:
            self.log(f"❌ Manuel Token Kaydetme Hatası: {str(e)}", "error")
            return {"success": False, "error": str(e)}

    def test_tiktok_connection(self) -> Dict[str, Any]:
        """Tests saved TikTok token and returns user profile & diagnostic details."""
        try:
            from src.uploader.tiktokapi import TikTokOAuthPKCE, KEYS_FILE
            keys = self.get_api_keys()
            tok, refreshed = TikTokOAuthPKCE.ensure_valid_token(keys)

            if not tok:
                return {
                    "success": False,
                    "message": "❌ TikTok Access Token bulunamadı. Lütfen 'TikTok ile Giriş Yap' butonuna tıklayarak hesabınızı bağlayın."
                }

            user_res = TikTokOAuthPKCE.fetch_user_info(tok)
            if user_res.get("success"):
                uname = user_res.get("username") or user_res.get("display_name") or "Kullanıcı"
                open_id = user_res.get("open_id") or keys.get("tiktok_open_id", "")
                
                # Save refreshed username into config
                try:
                    if KEYS_FILE.exists():
                        with open(KEYS_FILE, "r", encoding="utf-8") as f:
                            kd = json.load(f)
                        kd["tiktok_username"] = user_res.get("username", "")
                        kd["tiktok_display_name"] = user_res.get("display_name", "")
                        kd["tiktok_avatar_url"] = user_res.get("avatar_url", "")
                        with open(KEYS_FILE, "w", encoding="utf-8") as f:
                            json.dump(kd, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

                return {
                    "success": True,
                    "message": f"✅ TikTok API Bağlantısı Başarılı! Bağlı Hesap: @{uname}",
                    "username": user_res.get("username"),
                    "display_name": user_res.get("display_name"),
                    "avatar_url": user_res.get("avatar_url"),
                    "open_id": open_id
                }
            else:
                return {
                    "success": False,
                    "message": f"⚠️ TikTok API Doğrulama Uyarısı: {user_res.get('error')}"
                }
        except Exception as e:
            return {"success": False, "message": f"❌ TikTok Test Hatası: {str(e)}"}

    def reset_tiktok_connection(self) -> Dict[str, Any]:
        """Clears stored TikTok token, open_id and user profile info."""
        try:
            user_keys_file = USER_DATA_DIR / "config_keys.json"
            if user_keys_file.exists():
                with open(user_keys_file, "r", encoding="utf-8") as f:
                    kd = json.load(f)

                for field in [
                    "tiktok_access_token", "tiktok_refresh_token", "tiktok_open_id",
                    "tiktok_expires_at", "tiktok_refresh_expires_at",
                    "tiktok_username", "tiktok_display_name", "tiktok_avatar_url"
                ]:
                    kd.pop(field, None)

                with open(user_keys_file, "w", encoding="utf-8") as f:
                    json.dump(kd, f, ensure_ascii=False, indent=2)

            self.log("🗑️ TikTok hesabı ve bağlantı oturumu başarıyla sıfırlandı.", "info")
            return {"success": True, "message": "TikTok bağlantısı sıfırlandı."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_instagram_api(self) -> Dict[str, Any]:
        """Robustly test Instagram / Meta Access Token validity across multiple Graph endpoints."""
        try:
            keys = {}
            if KEYS_FILE.exists():
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    keys = json.load(f)

            account_id = keys.get("instagram_account_id", "").strip()
            access_token = keys.get("instagram_access_token", "").strip()

            if not access_token:
                return {"success": False, "message": "❌ Access Token bulunamadı. Lütfen Token girip kaydedin."}

            import requests

            # 1. Test Graph API /me endpoint (works for Page Token, User Token, App Token)
            me_url = "https://graph.facebook.com/v20.0/me"
            resp = requests.get(me_url, params={"fields": "id,name", "access_token": access_token}, timeout=12)

            if resp.status_code == 200:
                rj = resp.json()
                uname = rj.get("name") or rj.get("id") or "Meta Hesabı"

                # If account_id is also supplied, test specific account query
                if account_id:
                    acc_url = f"https://graph.facebook.com/v20.0/{account_id}"
                    acc_resp = requests.get(acc_url, params={"fields": "id,username,name", "access_token": access_token}, timeout=12)
                    if acc_resp.status_code == 200:
                        acc_rj = acc_resp.json()
                        ig_name = acc_rj.get("username") or acc_rj.get("name") or uname
                        return {"success": True, "message": f"✅ Token Geçerli: @{ig_name} (ID: {account_id})"}

                return {"success": True, "message": f"✅ Meta Token Geçerli: {uname} (ID: {rj.get('id')})"}

            # 2. Test direct Instagram Graph Account ID endpoint if specified
            if account_id:
                acc_url = f"https://graph.facebook.com/v20.0/{account_id}"
                acc_resp = requests.get(acc_url, params={"fields": "id,username,name", "access_token": access_token}, timeout=12)
                if acc_resp.status_code == 200:
                    acc_rj = acc_resp.json()
                    ig_name = acc_rj.get("username") or acc_rj.get("name") or "Instagram Hesabı"
                    return {"success": True, "message": f"✅ Token Geçerli: @{ig_name} (ID: {account_id})"}

            # 3. Test Instagram Basic Display API (/me)
            ig_me_url = "https://graph.instagram.com/me"
            ig_resp = requests.get(ig_me_url, params={"fields": "id,username", "access_token": access_token}, timeout=12)
            if ig_resp.status_code == 200:
                ig_rj = ig_resp.json()
                return {"success": True, "message": f"✅ Instagram Token Geçerli: @{ig_rj.get('username')} (ID: {ig_rj.get('id')})"}

            # Extract detailed error message from response
            err_msg = "Meta API erişimi reddetti"
            try:
                err_data = resp.json().get("error", {})
                err_msg = err_data.get("message") or err_data.get("error_user_msg") or resp.text
            except Exception:
                err_msg = resp.text[:150]

            return {"success": False, "message": f"❌ Test Başarısız: {err_msg}"}

        except Exception as e:
            return {"success": False, "message": f"❌ Bağlantı Hatası: {str(e)}"}

    # ──────────────────────────────────────────────────────────────
    # UPDATES
    # ──────────────────────────────────────────────────────────────

    def check_for_updates(self) -> Dict[str, Any]:
        """Check for updates asynchronously."""
        threading.Thread(target=self._update_task, daemon=True).start()
        return {"success": True}

    def _update_task(self):
        self.log("🔄 GitHub üzerinden güncelleme denetimi yapılıyor...", "info")
        try:
            has_update, new_ver, dl_url = self.updater.check_for_updates()
            if has_update and dl_url:
                self.log(f"🚀 Yeni sürüm mevcut: v{new_ver}", "warning")
                if self._window:
                    self._window.evaluate_js(
                        f"window.showUpdatePrompt('{new_ver}', {json.dumps(dl_url)});"
                    )
            else:
                self.log(f"✅ Uygulamanız en güncel sürümde (v{APP_VERSION}).", "success")
        except Exception as e:
            self.log(f"⚠️ Güncelleme kontrolü başarısız: {e}", "warning")

    def apply_update(self, dl_url: str) -> Dict[str, Any]:
        """Download and install update asynchronously."""
        self.log("📥 Güncelleme paketi indiriliyor...", "info")
        threading.Thread(
            target=lambda: self.updater.download_and_install_update(
                dl_url,
                progress_callback=lambda p: self.log(f"Güncelleme: %{int(p*100)}", "info")
            ),
            daemon=True
        ).start()
        return {"success": True}
