import os
import json
import time
import base64
import threading
import subprocess
import webview
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.config import APP_NAME, APP_VERSION, DOWNLOADS_DIR, PROCESSED_DIR, BASE_DIR, FFMPEG_BINARY
from src.downloader.downloader import VideoDownloader
from src.updater.github_updater import GitHubUpdater

KEYS_FILE = BASE_DIR / "config_keys.json"


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

    def _list_videos(self, directory: Path) -> List[Dict[str, Any]]:
        result = []
        try:
            for f in sorted(directory.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.suffix.lower() not in ('.mp4', '.mov', '.avi', '.mkv', '.webm'):
                    continue
                meta = self._load_sidecar(str(f))
                size_mb = round(f.stat().st_size / (1024 * 1024), 1)
                result.append({
                    "path": str(f),
                    "filename": f.name,
                    "stem": f.stem,
                    "size_mb": size_mb,
                    "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime)),
                    "title": meta.get("title", f.stem) if meta else f.stem,
                    "uploader": meta.get("uploader", "") if meta else "",
                    "caption": meta.get("caption", "") if meta else "",
                    "hashtags": meta.get("hashtags", []) if meta else [],
                    "hashtags_str": meta.get("hashtags_str", "") if meta else "",
                    "url": meta.get("url", "") if meta else "",
                    "has_meta": meta is not None
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
        Returns empty string if extraction fails.
        """
        if not video_path or not os.path.exists(video_path):
            return ""
        try:
            import tempfile
            thumb_path = tempfile.mktemp(suffix=".jpg")

            # Use ffmpeg to extract frame at 1 second
            ffmpeg_bin = FFMPEG_BINARY
            cmd = [
                ffmpeg_bin,
                "-ss", "00:00:01",
                "-i", video_path,
                "-vframes", "1",
                "-vf", "scale=240:-2",
                "-q:v", "3",
                "-y",
                thumb_path
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=15,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )

            if os.path.exists(thumb_path):
                with open(thumb_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                try:
                    os.remove(thumb_path)
                except Exception:
                    pass
                return f"data:image/jpeg;base64,{data}"
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
            os.startfile(path)
            return {"success": True}
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
            text_wm = options.get("text_watermark") or None
            badge_preset = options.get("badge_preset") or None
            logo_scale = float(options.get("logo_scale", 0.22))
            quality_label = options.get("quality_label") or None

            # Blur position (relative coords)
            blur_rel_pos = None
            if options.get("blur_enabled"):
                blur_rel_pos = (
                    float(options.get("blur_x", 0.65)),
                    float(options.get("blur_y", 0.88)),
                    float(options.get("blur_w", 0.35)),
                    float(options.get("blur_h", 0.12))
                )

            # Logo position (relative coords)
            logo_rel_pos = None
            if options.get("logo_enabled") and logo_path:
                logo_rel_pos = (
                    float(options.get("logo_x", 0.78)),
                    float(options.get("logo_y", 0.88))
                )

            success = processor.process_video(
                input_path=source_path,
                output_path=out_path,
                watermark_logo_path=logo_path,
                logo_scale=logo_scale,
                text_watermark=text_wm,
                badge_preset=badge_preset,
                logo_rel_pos=logo_rel_pos,
                blur_rel_pos=blur_rel_pos,
                quality_label=quality_label
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

    # ──────────────────────────────────────────────────────────────
    # API KEYS MANAGEMENT
    # ──────────────────────────────────────────────────────────────

    def get_api_keys(self) -> Dict[str, Any]:
        """Load and return all saved API keys."""
        if KEYS_FILE.exists():
            try:
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Don't expose passwords to JS in plain text — mask them
                    safe = dict(data)
                    if "instagram_auth" in safe and isinstance(safe["instagram_auth"], dict):
                        auth = dict(safe["instagram_auth"])
                        if auth.get("password"):
                            auth["password"] = "●" * min(len(auth["password"]), 8)
                        safe["instagram_auth"] = auth
                    return safe
            except Exception as e:
                return {"error": str(e)}
        return {}

    def save_api_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save API keys to config_keys.json. Preserves existing password if masked."""
        try:
            # Load existing to preserve actual password
            existing = {}
            if KEYS_FILE.exists():
                try:
                    with open(KEYS_FILE, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    pass

            # If password is masked (●●●●), keep the existing password
            if "instagram_auth" in data:
                new_pass = data["instagram_auth"].get("password", "")
                if new_pass and all(c == "●" for c in new_pass):
                    existing_auth = existing.get("instagram_auth", {})
                    data["instagram_auth"]["password"] = existing_auth.get("password", "")

            # Merge new data over existing
            existing.update(data)

            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            self.log("✅ API anahtarları kaydedildi.", "success")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_instagram_api(self) -> Dict[str, Any]:
        """Test Instagram API token validity."""
        try:
            keys = {}
            if KEYS_FILE.exists():
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    keys = json.load(f)

            account_id = keys.get("instagram_account_id", "").strip()
            access_token = keys.get("instagram_access_token", "").strip()

            if not account_id or not access_token:
                return {"success": False, "message": "Account ID veya Access Token eksik"}

            import requests
            check_url = f"https://graph.facebook.com/v23.0/{account_id}"
            resp = requests.get(
                check_url,
                params={"fields": "id,username,name", "access_token": access_token},
                timeout=15
            )
            rj = resp.json()
            if resp.status_code == 200 and "id" in rj:
                username = rj.get("username") or rj.get("name") or "Meta Hesabı"
                return {"success": True, "message": f"✅ Token geçerli: @{username} (ID: {rj.get('id')})"}
            else:
                err = rj.get("error", {}).get("message", resp.text)
                return {"success": False, "message": f"❌ Token Hatası: {err}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

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
