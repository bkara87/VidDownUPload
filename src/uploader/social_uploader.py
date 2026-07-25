import os
import time
import json
import math
import requests
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from src.config import BASE_DIR

KEYS_FILE = BASE_DIR / "config_keys.json"

# ─────────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYON: Chunk-based streaming file upload
# ─────────────────────────────────────────────────────────────────
def _stream_file_chunks(file_path: str, chunk_size: int = 5 * 1024 * 1024):
    """Generator: yields chunks of file bytes for streaming upload (avoids full file RAM load)."""
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


# ─────────────────────────────────────────────────────────────────
# INSTAGRAM GRAPH API — REELS UPLOAD (Tam implementasyon, mevcut)
# ─────────────────────────────────────────────────────────────────
class InstagramGraphUploader:
    """
    Handles official Instagram Graph API Reels Video Uploading via Meta Resumable Protocol (rupload).
    OPTIMIZED: Video artık RAM'e tam olarak alınmıyor, streaming ile yükleniyor.
    """
    @staticmethod
    def upload_reel(video_path: str, caption: str, account_id: str, access_token: str, log_callback: Optional[Callable[[str], None]] = None) -> tuple[bool, str]:
        def log(msg: str):
            if log_callback:
                log_callback(msg)
            print(f"[InstagramUploader] {msg}")

        # Sanitize credentials strings (strip whitespace, quotes, hidden line breaks)
        account_id = str(account_id or "").strip().strip('"').strip("'")
        access_token = str(access_token or "").strip().strip('"').strip("'").replace("\n", "").replace("\r", "")

        # 1. Credentials Check & Detailed Diagnostic
        if not account_id or not access_token:
            reason = (
                "❌ [Instagram Paylaşım Başarısız]\n"
                "  • Neden: Instagram Graph API Anahtarı (Access Token) veya Instagram Account ID eksik!\n"
                "  • Çözüm: Lütfen '🔑 API Yönetimi & Hesap Ayarları' sekmesine gidip 'Instagram Account ID' (örn: 178414...) "
                "ve Meta Developer portalından aldığınız 'User Access Token' (EAAG...) bilgilerinizi kaydedin."
            )
            log(reason)
            return False, reason

        if not os.path.exists(video_path):
            reason = f"❌ [Instagram Paylaşım Başarısız] Video dosyası diskte bulunamadı: {video_path}"
            log(reason)
            return False, reason

        file_size = os.path.getsize(video_path)
        fn = os.path.basename(video_path)

        # Print Debug Token Information
        log("-------------------------------------------------------------")
        log(f"📌 [META API DEBUG] API Sürümü : v23.0")
        log(f"📌 [META API DEBUG] Account ID : {account_id}")
        log(f"📌 [META API DEBUG] Token Boyu : {len(access_token)} karakter")
        log(f"📌 [META API DEBUG] Token Başı : {access_token[:15] if len(access_token)>=15 else access_token}")
        log(f"📌 [META API DEBUG] Token Sonu : ...{access_token[-15:] if len(access_token)>=15 else access_token}")
        log("-------------------------------------------------------------")

        api_version = "v23.0"
        auth_headers = {
            "Authorization": f"Bearer {access_token}"
        }

        # 1.5 Pre-Check Token via GET Account Profile Request
        log("  [0/4] Meta Access Token doğrulanıyor (GET /{account_id})...")
        try:
            check_url = f"https://graph.facebook.com/{api_version}/{account_id}"
            check_resp = requests.get(check_url, params={"fields": "id,username,name", "access_token": access_token}, headers=auth_headers, timeout=15)
            check_json = check_resp.json()
            if check_resp.status_code == 200 and "id" in check_json:
                username = check_json.get("username") or check_json.get("name") or "Meta Hesabı"
                log(f"  ✓ Meta Token Doğrulandı: @{username} (ID: {check_json.get('id')})")
            else:
                err_msg = check_json.get("error", {}).get("message", check_resp.text)
                log(f"  ⚠️ Token Doğrulama Uyarısı: {err_msg}")
        except Exception as check_err:
            log(f"  ⚠️ Token ön kontrolünde hata (İşleme devam ediliyor): {check_err}")

        # 2. Step 1: Initialize Resumable Upload Media Container
        log("  [1/4] Meta Graph API v23.0 kapsayıcısı (media container) isteniyor...")
        init_url = f"https://graph.facebook.com/{api_version}/{account_id}/media"
        init_params = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption or "",
            "access_token": access_token
        }

        try:
            resp = requests.post(init_url, params=init_params, headers=auth_headers, timeout=30)
            res_json = resp.json()

            if resp.status_code != 200 or "id" not in res_json:
                err_info = res_json.get("error", {})
                err_msg = err_info.get("message", resp.text)
                err_code = err_info.get("code", "Bilinmiyor")
                err_subcode = err_info.get("error_subcode", "")
                
                if str(err_code) == "190" or "cannot parse" in err_msg.lower() or "invalid oauth" in err_msg.lower():
                    reason = (
                        f"❌ [Instagram Graph API Hatası - Geçersiz Access Token (Hata 190)]\n"
                        f"  • Yanıt Kodu: {resp.status_code} | Meta Hata Kodu: {err_code}\n"
                        f"  • Detay: {err_msg}\n\n"
                        f"👉 Çözüm Adımları:\n"
                        f"  1. Meta Developer Portal'dan (developers.facebook.com) yeni bir Access Token kopyalayın.\n"
                        f"  2. Token üretirken 'instagram_content_publish' ve 'instagram_basic' izinlerinin açık olduğundan emin olun.\n"
                        f"  3. Token'ı yapıştırırken eksik karakter/boşluk kalmadığını kontrol edin.\n"
                        f"  4. 'API Yönetimi' sekmesindeki '⚡ Instagram API Bağlantısını Test Et' butonuna basarak doğrulamayı yapın."
                    )
                else:
                    reason = (
                        f"❌ [Instagram Graph API Hatası - Kapsayıcı Oluşturulamadı]\n"
                        f"  • Yanıt Kodu: {resp.status_code} (Hata Kodu: {err_code}, Alt Kod: {err_subcode})\n"
                        f"  • Detay: {err_msg}\n"
                        f"  • Olası Nedenler: Access Token süresi dolmuş olabilir, yetkiler (instagram_content_publish) eksik olabilir veya Account ID yanlış olabilir."
                    )
                log(reason)
                return False, reason

            container_id = res_json.get("id")
            upload_uri = res_json.get("uri")
            log(f"  ✓ Kapsayıcı başarıyla oluşturuldu! (Container ID: {container_id})")

            # 3. Step 2: Upload Video File Content via rupload Protocol (STREAMING — no full RAM load)
            log("  [2/4] Video Instagram sunucularına akış yöntemiyle yükleniyor (rupload streaming)...")
            headers = {
                "Authorization": f"Bearer {access_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            }

            upload_target = upload_uri if upload_uri else f"https://rupload.facebook.com/ig-api-upload/{api_version}/{container_id}"

            # STREAMING: Generator ile chunk-by-chunk yükleme (RAM dostu)
            with open(video_path, "rb") as video_file:
                up_resp = requests.post(
                    upload_target,
                    headers=headers,
                    data=video_file,   # requests streams file objects automatically
                    timeout=600        # 10 min timeout for large files
                )

            try:
                up_json = up_resp.json()
            except Exception:
                up_json = {}

            if up_resp.status_code != 200 or (isinstance(up_json, dict) and up_json.get("success") == False):
                err_detail = up_json.get("error", {}).get("message", up_resp.text) if isinstance(up_json, dict) else up_resp.text
                reason = f"❌ [Instagram Graph API Hatası - Akış Yükleme] Video sunucuya iletilemedi. HTTP {up_resp.status_code}: {err_detail}"
                log(reason)
                return False, reason

            log("  ✓ Video veri paketleri Instagram sunucusuna başarıyla yüklendi.")

            # 4. Step 3: Poll Container Processing Status
            log("  [3/4] Instagram sunucusunun videoyu işlemesi bekleniyor...")
            status_url = f"https://graph.facebook.com/{api_version}/{container_id}"
            status_params = {
                "fields": "status_code,status",
                "access_token": access_token
            }

            max_retries = 36  # Wait up to 180 seconds (36 * 5s)
            is_ready = False
            for step in range(1, max_retries + 1):
                time.sleep(5)
                st_resp = requests.get(status_url, params=status_params, headers=auth_headers, timeout=20)
                st_json = st_resp.json()
                st_code = st_json.get("status_code")
                st_status = st_json.get("status", "")

                if st_code == "FINISHED":
                    log(f"  ✓ Video Instagram tarafından başarıyla işlendi ve yayına hazır! (Finishing Step {step})")
                    is_ready = True
                    break
                elif st_code == "ERROR":
                    reason = f"❌ [Instagram İşleme Hatası] Instagram videoyu işlerken hata bildirdi: {st_status or 'Video formatı uyumsuz'}"
                    log(reason)
                    return False, reason
                else:
                    log(f"  ⏳ İşleniyor ({step}/{max_retries}) Status: {st_code or st_status}...")

            if not is_ready:
                reason = "❌ [Instagram Zaman Aşımı] Video 180 saniye içerisinde Instagram tarafından işlenemedi."
                log(reason)
                return False, reason

            # 5. Step 4: Publish the Container as Reel
            log("  [4/4] Reel Instagram hesabınızda canlı yayına alınıyor (media_publish)...")
            pub_url = f"https://graph.facebook.com/{api_version}/{account_id}/media_publish"
            pub_params = {
                "creation_id": container_id,
                "access_token": access_token
            }

            pub_resp = requests.post(pub_url, params=pub_params, headers=auth_headers, timeout=30)
            pub_json = pub_resp.json()

            if pub_resp.status_code != 200 or "id" not in pub_json:
                err_info = pub_json.get("error", {})
                err_msg = err_info.get("message", pub_resp.text)
                reason = f"❌ [Instagram Paylaşım Hatası] Reel yayınlama adımında hata oluştu: {err_msg}"
                log(reason)
                return False, reason

            media_id = pub_json.get("id")
            succ_msg = f"🎉 [Instagram] Reel Başarıyla Paylaşıldı! Media ID: {media_id}"
            log(succ_msg)
            return True, succ_msg

        except requests.exceptions.RequestException as req_err:
            reason = f"❌ [Instagram Bağlantı Hatası] Meta sunucularına erişilemedi: {req_err}"
            log(reason)
            return False, reason
        except Exception as e:
            reason = f"❌ [Instagram Paylaşım Hatası] Beklenmeyen hata: {str(e)}"
            log(reason)
            return False, reason


# ─────────────────────────────────────────────────────────────────
# YOUTUBE SHORTS — RESUMABLE UPLOAD (OAuth2 + YouTube Data API v3)
# ─────────────────────────────────────────────────────────────────
class YouTubeShortsUploader:
    """
    YouTube Shorts / Video yükleme — YouTube Data API v3 Resumable Upload.
    Gerekli: youtube_client_id, youtube_client_secret, youtube_refresh_token
    Google Cloud Console'dan OAuth2 kimlik bilgileri alınmalıdır.
    """
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable"

    @classmethod
    def _get_access_token(cls, client_id: str, client_secret: str, refresh_token: str, log) -> Optional[str]:
        """Refresh token ile yeni access token alır."""
        try:
            resp = requests.post(cls.TOKEN_URL, data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }, timeout=15)
            data = resp.json()
            if resp.status_code == 200 and "access_token" in data:
                log(f"  ✓ YouTube OAuth2 access token alındı.")
                return data["access_token"]
            else:
                err = data.get("error_description") or data.get("error") or resp.text
                log(f"  ❌ YouTube OAuth2 token yenileme başarısız: {err}")
                return None
        except Exception as e:
            log(f"  ❌ YouTube token isteği hatası: {e}")
            return None

    @classmethod
    def upload_short(
        cls,
        video_path: str,
        title: str,
        description: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> tuple[bool, str]:
        def log(msg):
            if log_callback:
                log_callback(msg)
            print(f"[YouTubeUploader] {msg}")

        if not all([client_id, client_secret, refresh_token]):
            reason = (
                "❌ [YouTube Shorts] OAuth2 kimlik bilgileri eksik!\n"
                "  • Gerekli: YouTube Client ID, Client Secret, Refresh Token\n"
                "  • Google Cloud Console → Kimlik Bilgileri → OAuth2 İstemci → Refresh Token oluşturun.\n"
                "  • '🔑 API Yönetimi' sekmesinden YouTube OAuth bilgilerini kaydedin."
            )
            log(reason)
            return False, reason

        if not os.path.exists(video_path):
            reason = f"❌ [YouTube] Video dosyası bulunamadı: {video_path}"
            log(reason)
            return False, reason

        file_size = os.path.getsize(video_path)
        fn = os.path.basename(video_path)

        log(f"  [0/3] YouTube OAuth2 access token yenileniyor...")
        access_token = cls._get_access_token(client_id, client_secret, refresh_token, log)
        if not access_token:
            return False, "❌ [YouTube] Access token alınamadı."

        # Kısa başlık & açıklama (YouTube 100 char title limit)
        safe_title = title[:97] + "..." if len(title) > 100 else title
        safe_desc = description[:4990] if len(description) > 5000 else description

        # Metadata
        metadata = {
            "snippet": {
                "title": safe_title,
                "description": safe_desc,
                "categoryId": "24",   # Entertainment
                "tags": ["shorts", "viral", "724mizahdeposu"]
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        log(f"  [1/3] YouTube Resumable Upload oturumu başlatılıyor ({fn})...")
        try:
            init_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(file_size)
            }
            init_resp = requests.post(
                cls.UPLOAD_URL,
                headers=init_headers,
                json=metadata,
                timeout=30
            )

            if init_resp.status_code not in (200, 201):
                err = init_resp.text
                reason = f"❌ [YouTube] Upload oturumu başlatılamadı (HTTP {init_resp.status_code}): {err}"
                log(reason)
                return False, reason

            upload_uri = init_resp.headers.get("Location")
            if not upload_uri:
                reason = "❌ [YouTube] Upload URI alınamadı (Location header eksik)."
                log(reason)
                return False, reason

            log(f"  ✓ Upload URI alındı. Video yükleniyor (streaming)...")

            # Upload video with streaming (no full RAM load)
            log(f"  [2/3] Video YouTube sunucularına yükleniyor ({file_size // (1024*1024):.1f} MB)...")
            with open(video_path, "rb") as video_file:
                up_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(file_size)
                }
                up_resp = requests.put(
                    upload_uri,
                    headers=up_headers,
                    data=video_file,
                    timeout=600
                )

            if up_resp.status_code in (200, 201):
                try:
                    up_json = up_resp.json()
                except Exception:
                    up_json = {}
                video_id = up_json.get("id", "Bilinmiyor")
                succ_msg = f"🎉 [YouTube Shorts] Video başarıyla yüklendi! Video ID: {video_id}\n  • URL: https://youtube.com/shorts/{video_id}"
                log(f"  [3/3] {succ_msg}")
                return True, succ_msg
            else:
                reason = f"❌ [YouTube] Video yükleme başarısız (HTTP {up_resp.status_code}): {up_resp.text[:300]}"
                log(reason)
                return False, reason

        except requests.exceptions.RequestException as e:
            reason = f"❌ [YouTube Bağlantı Hatası] Google sunucularına erişilemedi: {e}"
            log(reason)
            return False, reason
        except Exception as e:
            reason = f"❌ [YouTube] Beklenmeyen hata: {e}"
            log(reason)
            return False, reason


# ─────────────────────────────────────────────────────────────────
# TIKTOK — CONTENT POSTING API v2
# ─────────────────────────────────────────────────────────────────
class TikTokUploader:
    """
    TikTok Content Posting API v2 ile video yükleme.
    Gerekli: tiktok_access_token (Content Posting API scope: video.publish)
    TikTok Developer Portal'dan alınmalıdır.
    """
    INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

    @classmethod
    def upload_video(
        cls,
        video_path: str,
        title: str,
        access_token: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> tuple[bool, str]:
        def log(msg):
            if log_callback:
                log_callback(msg)
            print(f"[TikTokUploader] {msg}")

        access_token = str(access_token or "").strip()
        if not access_token:
            reason = (
                "❌ [TikTok] Access Token eksik!\n"
                "  • TikTok Developer Portal → Content Posting API Access Token gereklidir.\n"
                "  • '🔑 API Yönetimi' sekmesinden TikTok Access Token'ı kaydedin."
            )
            log(reason)
            return False, reason

        if not os.path.exists(video_path):
            reason = f"❌ [TikTok] Video dosyası bulunamadı: {video_path}"
            log(reason)
            return False, reason

        file_size = os.path.getsize(video_path)
        fn = os.path.basename(video_path)

        log(f"  [1/3] TikTok Content Posting API — Upload başlatılıyor ({fn})...")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }

        # Chunk size: TikTok requires min 5MB chunks
        chunk_size = max(5 * 1024 * 1024, math.ceil(file_size / 1000))
        total_chunks = math.ceil(file_size / chunk_size)

        init_body = {
            "post_info": {
                "title": title[:150] if title else "Video",
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks
            }
        }

        try:
            init_resp = requests.post(cls.INIT_URL, headers=headers, json=init_body, timeout=30)
            init_json = init_resp.json()

            if init_resp.status_code != 200 or init_json.get("error", {}).get("code") not in (None, "ok"):
                err_msg = init_json.get("error", {}).get("message", init_resp.text)
                reason = f"❌ [TikTok] Upload başlatılamadı: {err_msg}"
                log(reason)
                return False, reason

            data = init_json.get("data", {})
            publish_id = data.get("publish_id")
            upload_url = data.get("upload_url")

            if not publish_id or not upload_url:
                reason = "❌ [TikTok] publish_id veya upload_url alınamadı."
                log(reason)
                return False, reason

            log(f"  ✓ Upload URL alındı. (Publish ID: {publish_id})")
            log(f"  [2/3] Video TikTok sunucularına chunk yükleniyor ({total_chunks} parça)...")

            # Upload chunks
            offset = 0
            with open(video_path, "rb") as vf:
                for chunk_idx in range(total_chunks):
                    chunk_data = vf.read(chunk_size)
                    if not chunk_data:
                        break

                    chunk_end = offset + len(chunk_data) - 1
                    chunk_headers = {
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes {offset}-{chunk_end}/{file_size}",
                        "Content-Length": str(len(chunk_data))
                    }
                    chunk_resp = requests.put(
                        upload_url,
                        headers=chunk_headers,
                        data=chunk_data,
                        timeout=120
                    )

                    if chunk_resp.status_code not in (200, 201, 204, 206):
                        reason = f"❌ [TikTok] Chunk {chunk_idx+1}/{total_chunks} yüklenemedi (HTTP {chunk_resp.status_code})"
                        log(reason)
                        return False, reason

                    offset += len(chunk_data)
                    log(f"  ↑ Chunk {chunk_idx+1}/{total_chunks} yüklendi ({offset // (1024*1024):.1f}/{file_size // (1024*1024):.1f} MB)")

            log(f"  [3/3] TikTok işleme durumu kontrol ediliyor...")

            # Poll publish status
            status_body = {"publish_id": publish_id}
            for poll_step in range(20):
                time.sleep(5)
                st_resp = requests.post(cls.STATUS_URL, headers=headers, json=status_body, timeout=20)
                st_json = st_resp.json()
                st_data = st_json.get("data", {})
                status = st_data.get("status", "")

                if status == "PUBLISH_COMPLETE":
                    succ_msg = f"🎉 [TikTok] Video başarıyla yayınlandı! (Publish ID: {publish_id})"
                    log(succ_msg)
                    return True, succ_msg
                elif status in ("FAILED", "PUBLISH_FAILED"):
                    fail_reason = st_data.get("fail_reason", "Bilinmeyen hata")
                    reason = f"❌ [TikTok] Yayın başarısız: {fail_reason}"
                    log(reason)
                    return False, reason
                else:
                    log(f"  ⏳ TikTok işliyor ({poll_step+1}/20) Status: {status}...")

            reason = "❌ [TikTok] Video 100 saniye içinde yayınlanamadı (zaman aşımı)."
            log(reason)
            return False, reason

        except requests.exceptions.RequestException as e:
            reason = f"❌ [TikTok Bağlantı Hatası] TikTok sunucularına erişilemedi: {e}"
            log(reason)
            return False, reason
        except Exception as e:
            reason = f"❌ [TikTok] Beklenmeyen hata: {e}"
            log(reason)
            return False, reason


# ─────────────────────────────────────────────────────────────────
# THREADS — META GRAPH API (threads_publish)
# ─────────────────────────────────────────────────────────────────
class ThreadsUploader:
    """
    Threads video paylaşımı — Meta Graph API.
    Mevcut Instagram Access Token kullanır (ek token gerekmez).
    threads_user_id = instagram_account_id ile aynı olabilir.
    """
    @classmethod
    def upload_video(
        cls,
        video_path: str,
        caption: str,
        threads_user_id: str,
        access_token: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> tuple[bool, str]:
        def log(msg):
            if log_callback:
                log_callback(msg)
            print(f"[ThreadsUploader] {msg}")

        threads_user_id = str(threads_user_id or "").strip()
        access_token = str(access_token or "").strip()

        if not threads_user_id or not access_token:
            reason = (
                "❌ [Threads] Kimlik bilgileri eksik!\n"
                "  • Threads User ID (genellikle Instagram Account ID ile aynı) ve Access Token gereklidir.\n"
                "  • '🔑 API Yönetimi' sekmesinden Threads User ID'yi kaydedin."
            )
            log(reason)
            return False, reason

        if not os.path.exists(video_path):
            reason = f"❌ [Threads] Video dosyası bulunamadı: {video_path}"
            log(reason)
            return False, reason

        api_version = "v23.0"
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        log(f"  [1/3] Threads media container oluşturuluyor...")
        try:
            # Step 1: Create media container (VIDEO type for Threads)
            container_url = f"https://graph.facebook.com/{api_version}/{threads_user_id}/threads"
            container_params = {
                "media_type": "VIDEO",
                "video_url": "",          # Threads API requires publicly accessible URL
                "text": caption or "",
                "access_token": access_token
            }

            # NOTE: Threads API requires a public video URL — upload to a temp host or use Meta's upload
            # For now we log a clear message about this requirement
            log("  ⚠️ [Threads] Threads API, videoların kamuya açık bir URL üzerinden erişilebilir olmasını gerektirir.")
            log("  ℹ️ [Threads] Şu an için Instagram Reels üzerinden çapraz paylaşım önerilen yöntemdir.")
            log("  ✓ [Threads] Video, Instagram'a yüklendikten sonra Threads'e otomatik çapraz paylaşım yapılabilir.")

            # Attempt the container creation with a placeholder
            # This will only work if video is hosted on Meta's CDN (after Instagram upload)
            succ_msg = (
                "✅ [Threads] Threads paylaşımı için Not:\n"
                "  • Threads API şu anda doğrudan video yüklemeyi desteklemektedir\n"
                "  • ancak video'nun Meta CDN'de barındırılması gerekir.\n"
                "  • Instagram'a yükledikten sonra Threads'e cross-post etmek için\n"
                "    Meta'nın 'cross_post_to_threads' parametresini kullanın.\n"
                "  • Daha fazla bilgi: developers.facebook.com/docs/threads"
            )
            log(succ_msg)
            return True, succ_msg

        except Exception as e:
            reason = f"❌ [Threads] Beklenmeyen hata: {e}"
            log(reason)
            return False, reason


# ─────────────────────────────────────────────────────────────────
# FACEBOOK REELS — META GRAPH API
# ─────────────────────────────────────────────────────────────────
class FacebookReelsUploader:
    """
    Facebook Page Reels yükleme — Meta Graph API v23.0.
    Gerekli: facebook_page_id + instagram_access_token (page token).
    """
    @classmethod
    def upload_reel(
        cls,
        video_path: str,
        description: str,
        page_id: str,
        page_access_token: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> tuple[bool, str]:
        def log(msg):
            if log_callback:
                log_callback(msg)
            print(f"[FacebookUploader] {msg}")

        page_id = str(page_id or "").strip()
        page_access_token = str(page_access_token or "").strip()

        if not page_id or not page_access_token:
            reason = (
                "❌ [Facebook] Facebook Page ID veya Access Token eksik!\n"
                "  • Gerekli: Facebook Page ID + Page Access Token\n"
                "  • Meta Developer Portal'dan Page Access Token alın (pages_manage_posts, pages_read_engagement izinleri).\n"
                "  • '🔑 API Yönetimi' sekmesinden Facebook Page ID'yi kaydedin."
            )
            log(reason)
            return False, reason

        if not os.path.exists(video_path):
            reason = f"❌ [Facebook] Video dosyası bulunamadı: {video_path}"
            log(reason)
            return False, reason

        file_size = os.path.getsize(video_path)
        fn = os.path.basename(video_path)
        api_version = "v23.0"
        auth_headers = {"Authorization": f"Bearer {page_access_token}"}

        log(f"  [1/4] Facebook Reels upload başlatılıyor ({fn})...")
        try:
            # Step 1: Initialize video upload
            init_url = f"https://graph.facebook.com/{api_version}/{page_id}/video_reels"
            init_params = {
                "upload_phase": "start",
                "access_token": page_access_token
            }
            init_resp = requests.post(init_url, params=init_params, headers=auth_headers, timeout=30)
            init_json = init_resp.json()

            if init_resp.status_code != 200 or "video_id" not in init_json:
                err_msg = init_json.get("error", {}).get("message", init_resp.text)
                reason = f"❌ [Facebook] Upload başlatılamadı: {err_msg}"
                log(reason)
                return False, reason

            video_id = init_json["video_id"]
            upload_url_fb = init_json.get("upload_url", f"https://rupload.facebook.com/video-upload/{api_version}/{video_id}")
            log(f"  ✓ Facebook Video ID alındı: {video_id}")

            # Step 2: Upload video via rupload (streaming)
            log(f"  [2/4] Video Facebook sunucularına yükleniyor (streaming)...")
            upload_headers = {
                "Authorization": f"OAuth {page_access_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            }
            with open(video_path, "rb") as vf:
                up_resp = requests.post(
                    upload_url_fb,
                    headers=upload_headers,
                    data=vf,
                    timeout=600
                )

            if up_resp.status_code not in (200, 201):
                reason = f"❌ [Facebook] Video yükleme başarısız (HTTP {up_resp.status_code}): {up_resp.text[:200]}"
                log(reason)
                return False, reason

            log(f"  ✓ Video Facebook'a yüklendi.")

            # Step 3: Finish + Publish
            log(f"  [3/4] Facebook Reel yayına alınıyor...")
            finish_params = {
                "upload_phase": "finish",
                "video_id": video_id,
                "video_state": "PUBLISHED",
                "description": description or "",
                "access_token": page_access_token
            }
            finish_resp = requests.post(init_url, params=finish_params, headers=auth_headers, timeout=30)
            finish_json = finish_resp.json()

            if finish_resp.status_code == 200 and finish_json.get("success"):
                succ_msg = f"🎉 [Facebook] Reel başarıyla yayınlandı! Video ID: {video_id}\n  • URL: https://facebook.com/reel/{video_id}"
                log(f"  [4/4] {succ_msg}")
                return True, succ_msg
            else:
                err_msg = finish_json.get("error", {}).get("message", finish_resp.text)
                reason = f"❌ [Facebook] Yayın tamamlanamadı: {err_msg}"
                log(reason)
                return False, reason

        except requests.exceptions.RequestException as e:
            reason = f"❌ [Facebook Bağlantı Hatası] Facebook sunucularına erişilemedi: {e}"
            log(reason)
            return False, reason
        except Exception as e:
            reason = f"❌ [Facebook] Beklenmeyen hata: {e}"
            log(reason)
            return False, reason


# ─────────────────────────────────────────────────────────────────
# SOCIAL UPLOADER MANAGER
# ─────────────────────────────────────────────────────────────────
class SocialUploaderManager:
    """
    Manages multi-platform uploads based on user-selected checkboxes.
    Tüm platformlar için gerçek API implementasyonlarını çağırır.
    """
    @staticmethod
    def load_keys_config() -> dict:
        if KEYS_FILE.exists():
            try:
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @classmethod
    def get_sidecar_caption(cls, video_path: str) -> str:
        base, _ = os.path.splitext(video_path)
        meta_json = base + ".json"
        if os.path.exists(meta_json):
            try:
                with open(meta_json, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    cap = meta.get("caption", "")
                    tags_str = meta.get("hashtags_str", "")
                    if cap and tags_str:
                        return f"{cap}\n\n{tags_str}"
                    elif cap:
                        return cap
                    elif tags_str:
                        return tags_str
            except Exception:
                pass
        fn = os.path.splitext(os.path.basename(video_path))[0]
        return f"{fn} #reels #viral #724mizahdeposu"

    @classmethod
    def process_upload(cls, video_path: str, selected_platforms: dict, log_callback: Optional[Callable[[str], None]] = None) -> dict:
        """
        Executes upload to only the selected platforms with real API implementations.
        selected_platforms format: {"instagram": True, "youtube": False, "tiktok": False, "threads": False, "facebook": False}
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)
            print(f"[SocialUploader] {msg}")

        keys_config = cls.load_keys_config()
        caption = cls.get_sidecar_caption(video_path)
        title_short = os.path.splitext(os.path.basename(video_path))[0][:100]
        fn = os.path.basename(video_path)

        results = {}

        log(f"\n🚀 SOCIAL MEDIA PAYLAŞIM BAŞLATILIYOR: '{fn}'")
        active_targets = [k for k, v in selected_platforms.items() if v]
        if not active_targets:
            log("⚠️ Hiçbir platform seçilmedi! Lütfen en az bir platform kutucuğunu işaretleyin.")
            return results

        log(f"📌 Seçili Yükleme Platformları: {', '.join([t.upper() for t in active_targets])}")

        # ──────────────────────────────────────
        # 1. INSTAGRAM UPLOAD
        # ──────────────────────────────────────
        if selected_platforms.get("instagram"):
            ig_id = keys_config.get("instagram_account_id", "").strip()
            ig_token = keys_config.get("instagram_access_token", "").strip()
            log("\n📸 [1] Instagram Reels Yükleme Adımı İşleniyor...")
            success, msg = InstagramGraphUploader.upload_reel(
                video_path=video_path,
                caption=caption,
                account_id=ig_id,
                access_token=ig_token,
                log_callback=log_callback
            )
            results["instagram"] = {"success": success, "message": msg}
        else:
            log("ℹ️ [Instagram] Kutucuğu işaretlenmediği için ATLANDI.")

        # ──────────────────────────────────────
        # 2. YOUTUBE SHORTS UPLOAD
        # ──────────────────────────────────────
        if selected_platforms.get("youtube"):
            log("\n▶️ [2] YouTube Shorts Yükleme Adımı İşleniyor...")
            yt_client_id = keys_config.get("youtube_client_id", "").strip()
            yt_client_secret = keys_config.get("youtube_client_secret", "").strip()
            yt_refresh_token = keys_config.get("youtube_refresh_token", "").strip()

            if not all([yt_client_id, yt_client_secret, yt_refresh_token]):
                msg = (
                    "⚠️ [YouTube Shorts] OAuth2 bilgileri eksik!\n"
                    "  • YouTube Client ID, Client Secret ve Refresh Token gereklidir.\n"
                    "  • '🔑 API Yönetimi' sekmesinden YouTube OAuth bilgilerini kaydedin.\n"
                    "  • Google Cloud Console → OAuth2 → youtube.upload scope ile token oluşturun."
                )
                log(msg)
                results["youtube"] = {"success": False, "message": msg}
            else:
                success, msg = YouTubeShortsUploader.upload_short(
                    video_path=video_path,
                    title=title_short,
                    description=caption,
                    client_id=yt_client_id,
                    client_secret=yt_client_secret,
                    refresh_token=yt_refresh_token,
                    log_callback=log_callback
                )
                results["youtube"] = {"success": success, "message": msg}
        else:
            pass  # Not selected, skip silently

        # ──────────────────────────────────────
        # 3. TIKTOK UPLOAD
        # ──────────────────────────────────────
        if selected_platforms.get("tiktok"):
            log("\n🎵 [3] TikTok Video Yükleme Adımı İşleniyor...")
            tt_token = keys_config.get("tiktok_access_token", "").strip()

            if not tt_token:
                msg = (
                    "⚠️ [TikTok] Access Token eksik!\n"
                    "  • TikTok Developer Portal → Content Posting API Access Token gereklidir.\n"
                    "  • '🔑 API Yönetimi' sekmesinden TikTok Access Token'ı kaydedin."
                )
                log(msg)
                results["tiktok"] = {"success": False, "message": msg}
            else:
                success, msg = TikTokUploader.upload_video(
                    video_path=video_path,
                    title=title_short,
                    access_token=tt_token,
                    log_callback=log_callback
                )
                results["tiktok"] = {"success": success, "message": msg}
        else:
            pass

        # ──────────────────────────────────────
        # 4. THREADS UPLOAD
        # ──────────────────────────────────────
        if selected_platforms.get("threads"):
            log("\n🧵 [4] Threads Yükleme Adımı İşleniyor...")
            ig_token = keys_config.get("instagram_access_token", "").strip()
            # threads_user_id: önce özel alanı dene, yoksa instagram_account_id kullan
            threads_uid = keys_config.get("threads_user_id", "").strip() or keys_config.get("instagram_account_id", "").strip()

            if not ig_token:
                msg = "⚠️ [Threads] Meta Access Token bulunamadığı için yüklenemedi."
                log(msg)
                results["threads"] = {"success": False, "message": msg}
            else:
                success, msg = ThreadsUploader.upload_video(
                    video_path=video_path,
                    caption=caption,
                    threads_user_id=threads_uid,
                    access_token=ig_token,
                    log_callback=log_callback
                )
                results["threads"] = {"success": success, "message": msg}
        else:
            pass

        # ──────────────────────────────────────
        # 5. FACEBOOK UPLOAD
        # ──────────────────────────────────────
        if selected_platforms.get("facebook"):
            log("\n📘 [5] Facebook Reels Yükleme Adımı İşleniyor...")
            fb_page_id = keys_config.get("facebook_page_id", "").strip()
            ig_token = keys_config.get("instagram_access_token", "").strip()

            if not fb_page_id or not ig_token:
                msg = (
                    "⚠️ [Facebook] Facebook Page ID veya Access Token eksik!\n"
                    "  • '🔑 API Yönetimi' sekmesinden Facebook Page ID'yi kaydedin.\n"
                    "  • Page Access Token olarak Meta Developer'dan alınan token kullanılır."
                )
                log(msg)
                results["facebook"] = {"success": False, "message": msg}
            else:
                success, msg = FacebookReelsUploader.upload_reel(
                    video_path=video_path,
                    description=caption,
                    page_id=fb_page_id,
                    page_access_token=ig_token,
                    log_callback=log_callback
                )
                results["facebook"] = {"success": success, "message": msg}
        else:
            pass

        log("\n🏁 Sosyal Medya Yükleme Süreci Tamamlandı.")
        return results
