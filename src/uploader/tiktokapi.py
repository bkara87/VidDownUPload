import os
import json
import time
import base64
import hashlib
import secrets
import threading
import traceback
import subprocess
import requests
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
from typing import Dict, Any, Optional, Tuple

from src.config import BASE_DIR, USER_DATA_DIR

KEYS_FILE = USER_DATA_DIR / "config_keys.json"


def _mask_secret(val: str, show_first: int = 2, show_last: int = 4) -> str:
    """Masks sensitive tokens/secrets for safe logging (e.g. ab**************1234)."""
    if not val:
        return "<EMPTY>"
    val_str = str(val).strip()
    if len(val_str) <= show_first + show_last:
        return "*" * len(val_str)
    return val_str[:show_first] + "*" * (len(val_str) - show_first - show_last) + val_str[-show_last:]


def _open_url_in_browser(url: str) -> Optional[Any]:
    """
    Launches URL in an isolated Chrome/Edge App Window (--app=URL) for 100% Google OAuth compatibility,
    bypassing WebView2 restrictions while preserving a native app window look.
    Returns subprocess.Popen instance for automatic process cleanup.
    """
    print(f"DEBUG [_open_url_in_browser]: Launching URL = {url}")

    if os.name == 'nt':
        candidate_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]

        for exe_path in candidate_paths:
            if os.path.exists(exe_path):
                try:
                    cmd = [exe_path, f"--app={url}", "--window-size=580,740"]
                    proc = subprocess.Popen(cmd)
                    print(f"DEBUG [_open_url_in_browser]: App Window launched via {os.path.basename(exe_path)} (PID={proc.pid})")
                    return proc
                except Exception as app_err:
                    print(f"DEBUG [_open_url_in_browser]: App Window launch error via {exe_path}: {app_err}")

        if hasattr(os, 'startfile'):
            try:
                os.startfile(url)
                print("DEBUG [_open_url_in_browser]: Fallback os.startfile executed successfully.")
                return None
            except Exception as e1:
                print(f"DEBUG [_open_url_in_browser]: Fallback os.startfile failed: {e1}")

    try:
        if webbrowser.open(url):
            print("DEBUG [_open_url_in_browser]: Method webbrowser.open executed successfully.")
            return None
    except Exception as e2:
        print(f"DEBUG [_open_url_in_browser]: Method webbrowser.open failed: {e2}")

    return None


def _encrypt_secret(secret_str: str) -> str:
    """Encrypts sensitive client secret using Windows DPAPI (CryptProtectData)."""
    if not secret_str:
        return ""
    try:
        import ctypes
        import ctypes.wintypes
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        in_bytes = secret_str.encode('utf-8')
        in_blob = DATA_BLOB(len(in_bytes), (ctypes.c_byte * len(in_bytes))(*in_bytes))
        out_blob = DATA_BLOB()

        if ctypes.windll.crypt32.CryptProtectData(ctypes.byref(in_blob), "TikTokSecret", None, None, None, 0, ctypes.byref(out_blob)):
            enc_bytes = bytes((ctypes.c_byte * out_blob.cbData).from_address(ctypes.addressof(out_blob.pbData.contents)))
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
            return "DPAPI:" + base64.b64encode(enc_bytes).decode('utf-8')
    except Exception as e:
        print(f"DEBUG [_encrypt_secret]: DPAPI Encryption Exception: {e}")
    return "B64:" + base64.b64encode(secret_str.encode('utf-8')).decode('utf-8')


def _decrypt_secret(enc_str: str) -> str:
    """Decrypts client secret using Windows DPAPI (CryptUnprotectData)."""
    if not enc_str:
        return ""
    if enc_str.startswith("DPAPI:"):
        try:
            import ctypes
            import ctypes.wintypes
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

            raw_data = base64.b64decode(enc_str[6:])
            in_blob = DATA_BLOB(len(raw_data), (ctypes.c_byte * len(raw_data))(*raw_data))
            out_blob = DATA_BLOB()
            if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
                dec_bytes = bytes((ctypes.c_byte * out_blob.cbData).from_address(ctypes.addressof(out_blob.pbData.contents)))
                ctypes.windll.kernel32.LocalFree(out_blob.pbData)
                return dec_bytes.decode('utf-8')
        except Exception as e:
            print(f"DEBUG [_decrypt_secret]: DPAPI Decryption Exception: {e}")
    elif enc_str.startswith("B64:"):
        try:
            return base64.b64decode(enc_str[4:]).decode('utf-8')
        except Exception as e:
            print(f"DEBUG [_decrypt_secret]: B64 Decryption Exception: {e}")
    return enc_str


class ReuseThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        print(f"DEBUG [OAuthCallbackHandler]: GET path={parsed.path}, query_keys={list(qs.keys())}")

        # Ignore favicon.ico or secondary resource requests
        if parsed.path.endswith("favicon.ico"):
            self.send_response(204)
            self.end_headers()
            return

        if "code" in qs:
            code_val = qs["code"][0]
            OAuthCallbackHandler.auth_code = code_val
            if "state" in qs:
                OAuthCallbackHandler.state = qs["state"][0]
            msg = """
            <html>
            <body style="font-family:'Segoe UI',sans-serif; text-align:center; padding:60px 20px; background:linear-gradient(135deg,#0B0F19,#1a1f2e); color:#fff; min-height:100vh; margin:0;">
              <div style="max-width:480px; margin:0 auto; padding:30px; background:rgba(255,255,255,0.05); border-radius:16px; backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.1);">
                <div style="font-size:64px; margin-bottom:20px;">🎵</div>
                <h2 style="color:#10B981; margin-bottom:12px; font-size:24px;">TikTok hesabınız başarıyla bağlandı.</h2>
                <p style="font-size:14px; color:#E2E8F0; margin-bottom:8px;">Yetkilendirme tamamlandı. Hesabınız uygulamaya bağlanıyor...</p>
                <p style="color:#94A3B8; font-size:12px;">Bu pencere 2 saniye içinde otomatik kapanacaktır.</p>
              </div>
              <script>
                setTimeout(function(){ window.close(); }, 2000);
              </script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode("utf-8"))
        elif "error" in qs or "error_description" in qs:
            OAuthCallbackHandler.error = qs.get("error_description", qs.get("error", ["Yetkilendirme reddedildi veya iptal edildi"]))[0]
            msg = f"""
            <html>
            <body style="font-family:'Segoe UI',sans-serif; text-align:center; padding:60px 20px; background:linear-gradient(135deg,#0B0F19,#1a1f2e); color:#fff; min-height:100vh; margin:0;">
              <div style="max-width:480px; margin:0 auto; padding:30px; background:rgba(255,255,255,0.05); border-radius:16px;">
                <div style="font-size:64px; margin-bottom:20px;">❌</div>
                <h2 style="color:#EF4444; margin-bottom:12px;">Giriş Tamamlanamadı</h2>
                <p style="color:#E2E8F0; font-size:15px;">{OAuthCallbackHandler.error}</p>
                <p style="color:#94A3B8; font-size:14px; margin-top:16px;">Lütfen uygulamaya dönüp tekrar deneyin.</p>
              </div>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode("utf-8"))
        else:
            # Neutral response for unrelated path queries
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


class TikTokOAuthPKCE:
    """
    Dedicated 2026 TikTok OAuth 2.0 PKCE & User Info Manager.
    Handles PKCE flow, State validation, Token Exchange, Auto-Refresh & User Profile Fetching.
    """
    PORT = 8989
    REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback/"

    @staticmethod
    def generate_pkce_pair() -> Tuple[str, str]:
        """Generates (code_verifier, code_challenge) for PKCE SHA256 flow."""
        verifier = secrets.token_urlsafe(64)[:128]
        sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').replace('=', '')
        return verifier, challenge

    @classmethod
    def get_auth_url(
        cls,
        client_key: str,
        code_challenge: str,
        state: str,
        scope: str = "user.info.basic,video.publish",
        scope_fmt: str = "comma"
    ) -> str:
        """
        Constructs official TikTok OAuth 2.0 Authorization URL (v2 API Spec).
        
        Official TikTok v2 Docs Structure:
        GET https://www.tiktok.com/v2/auth/authorize/
            ?client_key=CLIENT_KEY
            &scope=SCOPE_LIST
            &response_type=code
            &redirect_uri=ENCODED_REDIRECT_URI
            &state=STATE
            &code_challenge=CODE_CHALLENGE
            &code_challenge_method=S256
        """
        raw_scope = str(scope or "user.info.basic,video.publish").strip()
        
        # Split by comma or space
        if "," in raw_scope:
            parts = [s.strip() for s in raw_scope.split(",") if s.strip()]
        else:
            parts = [s.strip() for s in raw_scope.split() if s.strip()]
            
        if not parts:
            parts = ["user.info.basic", "video.publish"]

        # Format scope string based on chosen separator
        if scope_fmt == "encoded_comma":
            scope_str = "%2C".join(parts)
        elif scope_fmt == "space":
            scope_str = "%20".join(parts)
        else:
            # Default official TikTok v2 docs standard: comma-separated
            scope_str = ",".join(parts)

        # TikTok v2 official docs require fully URL-encoded redirect_uri
        encoded_redirect = quote(cls.REDIRECT_URI, safe="")

        url = (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={quote(client_key.strip(), safe='')}"
            f"&scope={scope_str}"
            f"&response_type=code"
            f"&redirect_uri={encoded_redirect}"
            f"&state={state}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
        )

        print("=" * 80)
        print("DEBUG [TikTokOAuthPKCE]: TIKTOK OAUTH v2 AUTHORIZATION URL GENERATED")
        print(f"  • Client Key: {client_key[:4]}***")
        print(f"  • Raw Scope Input: {raw_scope}")
        print(f"  • Scope Parts: {parts}")
        print(f"  • Formatted Scope ({scope_fmt}): {scope_str}")
        print(f"  • Raw Redirect URI: {cls.REDIRECT_URI}")
        print(f"  • Encoded Redirect URI: {encoded_redirect}")
        print(f"  • Full Authorization URL:\n    {url}")
        print("=" * 80)

        return url

    @classmethod
    def exchange_code_for_token(
        cls,
        client_key: str,
        client_secret: str,
        code: str,
        code_verifier: str
    ) -> Dict[str, Any]:
        """Exchanges authorization_code for TikTok Access Token, Open ID, and Refresh Token."""
        client_secret_plain = _decrypt_secret(client_secret)
        token_url = "https://open.tiktokapis.com/v2/oauth/token/"
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"}

        redirect_uri = cls.REDIRECT_URI.strip()

        # Official TikTok v2 OAuth PKCE token payload
        data = {
            "client_key": client_key.strip(),
            "client_secret": client_secret_plain.strip(),
            "code": code.strip(),
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier.strip()
        }

        print("=" * 70)
        print("DEBUG [TikTokOAuthPKCE]: Exchanging code for token")
        print(f"  • Client Key: {client_key}")
        print(f"  • Client Secret: {_mask_secret(client_secret_plain)}")
        print(f"  • Auth Code: {_mask_secret(code)}")
        print(f"  • Redirect URI: {redirect_uri}")
        print("=" * 70)

        try:
            resp = requests.post(token_url, headers=headers, data=data, timeout=30)
            print(f"DEBUG [TikTokOAuthPKCE]: HTTP {resp.status_code} Response: {resp.text}")

            try:
                res_json = resp.json()
            except Exception:
                res_json = {}

            # Handle invalid_grant: Retry if redirect_uri trailing slash mismatch occurs
            if resp.status_code != 200 and "invalid_grant" in resp.text.lower():
                print("DEBUG [TikTokOAuthPKCE]: invalid_grant detected. Retrying with fallback redirect_uri without trailing slash...")
                alt_redirect = redirect_uri.rstrip('/')
                data_alt = dict(data)
                data_alt["redirect_uri"] = alt_redirect
                resp_alt = requests.post(token_url, headers=headers, data=data_alt, timeout=30)
                print(f"DEBUG [TikTokOAuthPKCE]: Fallback HTTP {resp_alt.status_code} Response: {resp_alt.text}")
                if resp_alt.status_code == 200:
                    resp = resp_alt
                    try:
                        res_json = resp.json()
                    except Exception:
                        pass

            data_field = res_json.get("data")
            if not isinstance(data_field, dict):
                data_field = {}

            access_token = data_field.get("access_token") or res_json.get("access_token", "")
            open_id = data_field.get("open_id") or res_json.get("open_id", "")
            refresh_token = data_field.get("refresh_token") or res_json.get("refresh_token", "")
            exp_in = data_field.get("expires_in") or res_json.get("expires_in", 86400)
            ref_exp_in = data_field.get("refresh_expires_in") or res_json.get("refresh_expires_in", 31536000)
            scope_val = data_field.get("scope") or res_json.get("scope", "")

            if resp.status_code == 200 and access_token:
                print(f"DEBUG [TikTokOAuthPKCE]: Token success! Parsed access_token={_mask_secret(access_token)}, open_id={open_id}")
                now = int(time.time())
                return {
                    "success": True,
                    "access_token": access_token,
                    "open_id": open_id,
                    "refresh_token": refresh_token,
                    "expires_in": exp_in,
                    "refresh_expires_in": ref_exp_in,
                    "expires_at": now + exp_in,
                    "refresh_expires_at": now + ref_exp_in,
                    "scope": scope_val
                }

            err_code = "unknown"
            err_msg = resp.text
            if isinstance(res_json.get("error"), dict):
                err_code = res_json["error"].get("code", "unknown")
                err_msg = res_json["error"].get("message") or resp.text
            elif isinstance(res_json.get("error"), str):
                err_msg = res_json.get("error_description") or res_json["error"]
                err_code = res_json.get("error", "unknown")
                log_id = res_json.get("log_id", "")
                if log_id:
                    err_msg = f"{err_msg} (log_id: {log_id})"

            friendly_err = cls.get_friendly_error(err_code, err_msg)
            print(f"DEBUG [TikTokOAuthPKCE]: Token exchange failed: {friendly_err}")
            return {"success": False, "error": friendly_err}
        except Exception as e:
            print(f"DEBUG [TikTokOAuthPKCE]: Exception: {e}")
            return {"success": False, "error": f"Bağlantı hatası: {str(e)}"}

    @classmethod
    def refresh_access_token(
        cls,
        client_key: str,
        client_secret: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """Renews an expired TikTok access token using refresh_token."""
        token_url = "https://open.tiktokapis.com/v2/oauth/token/"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        print(f"DEBUG [TikTokOAuthPKCE]: Refreshing token with refresh_token={_mask_secret(refresh_token)}")
        try:
            resp = requests.post(token_url, headers=headers, data=data, timeout=30)
            res_json = resp.json()
            if resp.status_code == 200 and "access_token" in res_json.get("data", {}):
                d = res_json["data"]
                now = int(time.time())
                exp_in = d.get("expires_in", 86400)
                ref_exp_in = d.get("refresh_expires_in", 31536000)
                return {
                    "success": True,
                    "access_token": d.get("access_token", ""),
                    "open_id": d.get("open_id", ""),
                    "refresh_token": d.get("refresh_token", refresh_token),
                    "expires_in": exp_in,
                    "refresh_expires_in": ref_exp_in,
                    "expires_at": now + exp_in,
                    "refresh_expires_at": now + ref_exp_in,
                    "scope": d.get("scope", "")
                }
            else:
                err_msg = res_json.get("error", {}).get("message") or resp.text
                return {"success": False, "error": f"Token yenileme başarısız: {err_msg}"}
        except Exception as e:
            return {"success": False, "error": f"Refresh isteği hatası: {str(e)}"}

    @classmethod
    def ensure_valid_token(cls, keys_dict: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Auto-checks token expiration (5 min threshold).
        Refreshes token silently if expired.
        """
        current_token = keys_dict.get("tiktok_access_token", "").strip()
        refresh_token = keys_dict.get("tiktok_refresh_token", "").strip()
        client_key = keys_dict.get("tiktok_client_key", "").strip()
        raw_secret = keys_dict.get("tiktok_client_secret", "").strip()
        client_secret = _decrypt_secret(raw_secret)
        expires_at = keys_dict.get("tiktok_expires_at", 0)

        now = int(time.time())

        # If expired or expiring in less than 300 seconds (5 mins)
        if (now >= expires_at - 300 or not current_token) and refresh_token and client_key and client_secret:
            print("DEBUG [TikTokOAuthPKCE]: Access Token süresi dolmak üzere. Otomatik yenileniyor...")
            res = cls.refresh_access_token(client_key, client_secret, refresh_token)
            if res.get("success") and res.get("access_token"):
                new_token = res["access_token"]
                try:
                    existing = {}
                    if KEYS_FILE.exists():
                        with open(KEYS_FILE, "r", encoding="utf-8") as f:
                            existing = json.load(f)

                    existing["tiktok_access_token"] = new_token
                    existing["tiktok_expires_at"] = res.get("expires_at", now + 86400)
                    if res.get("refresh_token"):
                        existing["tiktok_refresh_token"] = res["refresh_token"]
                    if res.get("refresh_expires_at"):
                        existing["tiktok_refresh_expires_at"] = res["refresh_expires_at"]

                    with open(KEYS_FILE, "w", encoding="utf-8") as f:
                        json.dump(existing, f, ensure_ascii=False, indent=2)
                    print("DEBUG [TikTokOAuthPKCE]: Yeni token config_keys.json içine kaydedildi!")
                except Exception as e:
                    print(f"DEBUG [TikTokOAuthPKCE]: Token kaydetme hatası: {e}")
                return new_token, True

        return current_token, False

    @classmethod
    def fetch_user_info(cls, access_token: str) -> Dict[str, Any]:
        """
        Fetches user profile (username, display_name, avatar_url, open_id) via TikTok Open API v2.
        Endpoint: https://open.tiktokapis.com/v2/user/info/
        """
        if not access_token:
            return {"success": False, "error": "Access token bulunamadı."}

        url = "https://open.tiktokapis.com/v2/user/info/"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"fields": "open_id,union_id,avatar_url,display_name,username"}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            res_json = resp.json()
            if resp.status_code == 200 and "data" in res_json and "user" in res_json["data"]:
                u = res_json["data"]["user"]
                return {
                    "success": True,
                    "open_id": u.get("open_id", ""),
                    "union_id": u.get("union_id", ""),
                    "username": u.get("username", ""),
                    "display_name": u.get("display_name", ""),
                    "avatar_url": u.get("avatar_url", "")
                }
            else:
                err_msg = res_json.get("error", {}).get("message") or resp.text
                return {"success": False, "error": f"Kullanıcı bilgisi alınamadı: {err_msg}"}
        except Exception as e:
            return {"success": False, "error": f"User Info isteği başarısız: {str(e)}"}

    @classmethod
    def get_friendly_error(cls, err_code: str, raw_msg: str) -> str:
        """Returns clear user-friendly Turkish error explanations with action steps."""
        raw_msg_lower = str(raw_msg).lower()
        if "scope" in raw_msg_lower or "invalid_scope" in raw_msg_lower:
            return (
                "❌ [Geçersiz Scope İzni]\n"
                "• TikTok Developer Portal'da uygulamanız için ilgili yetki (Content Posting / Login Kit) ekli değil.\n"
                "• Çözüm: TikTok Dev Portal -> Uygulamanız -> Products alanından Content Posting API veya Login Kit ekleyin."
            )
        elif "invalid_client" in raw_msg_lower or "client_key" in raw_msg_lower:
            return (
                "❌ [Geçersiz Client Key / Secret]\n"
                "• Girdiğiniz Client Key veya Client Secret TikTok tarafından doğrulanamadı.\n"
                "• Çözüm: TikTok Dev Portal'dan Client Key ve Client Secret bilgilerinizi kontrol edip tekrar yapıştırın."
            )
        elif "redirect_uri" in raw_msg_lower:
            return (
                "❌ [Geçersiz Redirect URI]\n"
                "• TikTok Portalında Redirect URI eşleşmiyor.\n"
                "• Çözüm: TikTok Dev Portal -> Redirect URI kısmına 'http://127.0.0.1:8989/callback/' ekleyin."
            )
        elif "access_denied" in raw_msg_lower or "denied" in raw_msg_lower:
            return "❌ Giriş TikTok sayfasında reddedildi veya iptal edildi."
        return f"❌ TikTok API Hatası ({err_code}): {raw_msg}"

    @classmethod
    def run_auth_wizard(cls, client_key: str, client_secret: str, scope: str = "video.publish", scope_fmt: str = "comma") -> Dict[str, Any]:
        """
        Executes complete PKCE OAuth 2.0 Flow.
        Launches OS browser, starts local callback listener, exchanges code, fetches profile & saves keys.
        """
        client_secret = _decrypt_secret(client_secret)
        if not client_key or not client_secret:
            return {"success": False, "error": "TikTok Client Key ve Client Secret gereklidir."}

        target_scope = scope.strip() if scope else "video.publish"

        verifier, challenge = cls.generate_pkce_pair()
        state = secrets.token_hex(16)

        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.state = None
        OAuthCallbackHandler.error = None

        server = None
        chosen_port = None
        for try_port in [8989, 8990, 8991]:
            try:
                cls.PORT = try_port
                cls.REDIRECT_URI = f"http://127.0.0.1:{try_port}/callback/"
                server = ReuseThreadingHTTPServer(("127.0.0.1", try_port), OAuthCallbackHandler)
                server.timeout = 1.0
                chosen_port = try_port
                print(f"DEBUG [run_auth_wizard]: Local server running on http://127.0.0.1:{try_port}")
                break
            except Exception as pe:
                print(f"DEBUG [run_auth_wizard]: Port {try_port} busy: {pe}")

        if not server:
            return {"success": False, "error": "Yerel callback dinleyici başlatılamadı (Portlar meşgul)."}

        auth_url = cls.get_auth_url(client_key, challenge, state, scope=target_scope, scope_fmt=scope_fmt)
        browser_proc = _open_url_in_browser(auth_url)

        # Wait for callback up to 180 seconds
        start_time = time.time()
        while time.time() - start_time < 180:
            server.handle_request()
            if OAuthCallbackHandler.auth_code or OAuthCallbackHandler.error:
                break

        server.server_close()

        print("=" * 80)
        print(f"DEBUG [run_auth_wizard]: RECEIVED AUTH CODE FROM TIKTOK:")
        print(f"  FULL CODE: {OAuthCallbackHandler.auth_code}")
        print("=" * 80)

        # Forcefully terminate Chrome/Edge App Window process tree on Windows
        if browser_proc:
            try:
                time.sleep(0.5)
                if os.name == 'nt' and hasattr(browser_proc, 'pid') and browser_proc.pid:
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(browser_proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=0x08000000
                    )
                browser_proc.kill()
                print(f"DEBUG [run_auth_wizard]: Successfully force-closed login window PID={browser_proc.pid}")
            except Exception as close_err:
                print(f"DEBUG [run_auth_wizard]: App Window close note: {close_err}")

        if OAuthCallbackHandler.error:
            return {"success": False, "error": f"Giriş iptal edildi: {OAuthCallbackHandler.error}"}

        if not OAuthCallbackHandler.auth_code:
            return {"success": False, "error": "Zaman aşımı: TikTok girişi 180 saniyede tamamlanamadı."}

        if OAuthCallbackHandler.state != state:
            return {"success": False, "error": "Güvenlik İhlali (CSRF): State doğrulanamadı!"}

        # Token exchange
        res = cls.exchange_code_for_token(
            client_key=client_key,
            client_secret=client_secret,
            code=OAuthCallbackHandler.auth_code,
            code_verifier=verifier
        )

        if res.get("success"):
            acc_tok = res["access_token"]
            open_id = res["open_id"]

            # Automatically fetch TikTok User Profile (Username, Display Name, Avatar)
            user_info = cls.fetch_user_info(acc_tok)
            if user_info.get("success"):
                res["username"] = user_info.get("username", "")
                res["display_name"] = user_info.get("display_name", "")
                res["avatar_url"] = user_info.get("avatar_url", "")
                if not open_id and user_info.get("open_id"):
                    open_id = user_info["open_id"]
                    res["open_id"] = open_id

            # Save into config_keys.json
            try:
                existing = {}
                if KEYS_FILE.exists():
                    with open(KEYS_FILE, "r", encoding="utf-8") as f:
                        existing = json.load(f)

                existing["tiktok_access_token"] = acc_tok
                existing["tiktok_open_id"] = open_id
                existing["tiktok_expires_at"] = res.get("expires_at", int(time.time()) + 86400)
                existing["tiktok_scope"] = target_scope

                if res.get("refresh_token"):
                    existing["tiktok_refresh_token"] = res["refresh_token"]
                if res.get("refresh_expires_at"):
                    existing["tiktok_refresh_expires_at"] = res.get("refresh_expires_at", int(time.time()) + 31536000)

                existing["tiktok_client_key"] = client_key
                existing["tiktok_client_secret"] = _encrypt_secret(client_secret)

                if res.get("username"):
                    existing["tiktok_username"] = res["username"]
                if res.get("display_name"):
                    existing["tiktok_display_name"] = res["display_name"]
                if res.get("avatar_url"):
                    existing["tiktok_avatar_url"] = res["avatar_url"]

                with open(KEYS_FILE, "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)

                print("DEBUG [run_auth_wizard]: Successfully persisted TikTok auth keys & profile!")
            except Exception as e:
                print(f"DEBUG [run_auth_wizard]: Save keys error: {e}")

        return res
