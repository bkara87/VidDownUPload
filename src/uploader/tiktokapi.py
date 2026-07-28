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
from typing import Dict, Any, Optional

from src.config import BASE_DIR, USER_DATA_DIR

KEYS_FILE = USER_DATA_DIR / "config_keys.json"


class ReuseThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def _open_url_in_browser(url: str) -> bool:
    """
    Robust cross-platform URL launcher specifically designed for PyInstaller frozen Windows EXEs.
    Preserves all query parameters (& symbols) without truncation.
    """
    print(f"DEBUG [_open_url_in_browser]: Launching URL = {url}")
    
    # Method 1: Windows ShellExecute os.startfile (Direct Win32 API call — 100% safe for & in URLs)
    if hasattr(os, 'startfile'):
        try:
            os.startfile(url)
            print("DEBUG [_open_url_in_browser]: Method 1 (os.startfile) executed successfully.")
            return True
        except Exception as e1:
            print(f"DEBUG [_open_url_in_browser]: Method 1 (os.startfile) failed: {e1}")

    # Method 2: Python standard webbrowser module
    try:
        if webbrowser.open(url):
            print("DEBUG [_open_url_in_browser]: Method 2 (webbrowser.open) executed successfully.")
            return True
    except Exception as e2:
        print(f"DEBUG [_open_url_in_browser]: Method 2 (webbrowser.open) failed: {e2}")

    # Method 3: Windows CMD Start (URL enclosed in quotes to prevent & truncation)
    if os.name == 'nt':
        try:
            cmd_str = f'start "" "{url}"'
            subprocess.Popen(cmd_str, shell=True)
            print("DEBUG [_open_url_in_browser]: Method 3 (cmd /c start) executed successfully.")
            return True
        except Exception as e3:
            print(f"DEBUG [_open_url_in_browser]: Method 3 failed: {e3}")

    return False


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
        print(f"DEBUG [_encrypt_secret]: DPAPI Encryption Exception: {e}\n{traceback.format_exc()}")
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
            print(f"DEBUG [_decrypt_secret]: DPAPI Decryption Exception: {e}\n{traceback.format_exc()}")
    elif enc_str.startswith("B64:"):
        try:
            return base64.b64decode(enc_str[4:]).decode('utf-8')
        except Exception as e:
            print(f"DEBUG [_decrypt_secret]: B64 Decryption Exception: {e}\n{traceback.format_exc()}")
    return enc_str


class TikTokOAuthPKCE:
    """
    Dedicated TikTok OAuth 2.0 Authorization Code + PKCE Manager.
    Features Windows ShellExecute/cmd start fallback, ReuseThreadingHTTPServer, and full debug logging.
    """
    PORT = 8989
    REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback/"

    @staticmethod
    def generate_pkce_pair() -> tuple[str, str]:
        """Generates (code_verifier, code_challenge) for PKCE SHA256 flow."""
        verifier = secrets.token_urlsafe(64)[:128]
        sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').replace('=', '')
        return verifier, challenge

    @classmethod
    def get_auth_url(cls, client_key: str, code_challenge: str, state: str, scope: str = "user.info.basic,video.publish") -> str:
        """Constructs TikTok OAuth 2.0 Authorization URL."""
        raw_scope = str(scope or "user.info.basic,video.publish").strip()
        # Clean invalid/deprecated scopes like video.upload
        scope_list = [s.strip() for s in raw_scope.split(",") if s.strip() and s.strip() != "video.upload"]
        if not scope_list:
            scope_list = ["user.info.basic", "video.publish"]
        clean_scope = ",".join(scope_list)
        encoded_scopes = quote(clean_scope, safe=",")
        encoded_redirect = quote(cls.REDIRECT_URI)
        url = (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={client_key}"
            f"&scope={encoded_scopes}"
            f"&response_type=code"
            f"&redirect_uri={encoded_redirect}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
            f"&state={state}"
        )
        print(f"DEBUG [get_auth_url]: Constructed Auth URL = {url}")
        return url

    @classmethod
    def exchange_code_for_token(
        cls,
        client_key: str,
        client_secret: str,
        code: str,
        code_verifier: str
    ) -> Dict[str, Any]:
        """Exchanges authorization_code for TikTok Access Token, Open ID, and Refresh Token with FULL VERBOSE LOGGING."""
        token_url = "https://open.tiktokapis.com/v2/oauth/token/"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": cls.REDIRECT_URI,
            "code_verifier": code_verifier
        }

        print("=" * 80)
        print("DEBUG [exchange_code_for_token]: PRE-REQUEST PARAMETERS")
        print(f"  • Token URL: {token_url}")
        print(f"  • Authorization Code: {code}")
        print(f"  • Client Key: {client_key}")
        print(f"  • Client Secret (len={len(client_secret)}): {client_secret[:4]}***")
        print(f"  • Redirect URI: {cls.REDIRECT_URI}")
        print(f"  • Code Verifier: {code_verifier}")
        print("=" * 80)

        try:
            resp = requests.post(token_url, headers=headers, data=data, timeout=30)
            
            print("=" * 80)
            print("DEBUG [exchange_code_for_token]: POST-REQUEST RESPONSE")
            print(f"  • HTTP Status Code: {resp.status_code}")
            print(f"  • Response Headers: {dict(resp.headers)}")
            print(f"  • Response Raw Body: {resp.text}")
            print("=" * 80)

            res_json = resp.json()
            print(f"DEBUG [exchange_code_for_token]: Parsed res_json = {res_json}")

            data_field = res_json.get("data", {})
            print(f"DEBUG [exchange_code_for_token]: res_json['data'] = {data_field}")

            access_token = data_field.get("access_token", "")
            open_id = data_field.get("open_id", "")
            refresh_token = data_field.get("refresh_token", "")

            print(f"DEBUG [exchange_code_for_token]: Extracted access_token = {access_token}")
            print(f"DEBUG [exchange_code_for_token]: Extracted open_id = {open_id}")
            print(f"DEBUG [exchange_code_for_token]: Extracted refresh_token = {refresh_token}")

            if resp.status_code == 200 and access_token:
                now = int(time.time())
                exp_in = data_field.get("expires_in", 86400)
                ref_exp_in = data_field.get("refresh_expires_in", 31536000)
                result = {
                    "success": True,
                    "access_token": access_token,
                    "open_id": open_id,
                    "refresh_token": refresh_token,
                    "expires_in": exp_in,
                    "refresh_expires_in": ref_exp_in,
                    "expires_at": now + exp_in,
                    "refresh_expires_at": now + ref_exp_in,
                    "scope": data_field.get("scope", "")
                }
                print(f"DEBUG [exchange_code_for_token]: Returning SUCCESS result = {result}")
                return result
            else:
                err_msg = res_json.get("error", {}).get("message") or resp.text
                err_res = {"success": False, "error": f"Token değişimi başarısız (Status {resp.status_code}): {err_msg}"}
                print(f"DEBUG [exchange_code_for_token]: Returning ERROR result = {err_res}")
                return err_res
        except Exception as e:
            err_msg = f"Token isteği sırasında istisna oluştu: {e}\n{traceback.format_exc()}"
            print(f"DEBUG [exchange_code_for_token]: EXCEPTION: {err_msg}")
            return {"success": False, "error": str(e)}

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
        print(f"DEBUG [refresh_access_token]: Sending refresh request with refresh_token={refresh_token}")
        try:
            resp = requests.post(token_url, headers=headers, data=data, timeout=30)
            print(f"DEBUG [refresh_access_token]: Status={resp.status_code}, Body={resp.text}")
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
                    "refresh_expires_at": now + ref_exp_in
                }
            else:
                err_msg = res_json.get("error", {}).get("message") or resp.text
                return {"success": False, "error": f"Refresh token yenileme başarısız: {err_msg}"}
        except Exception as e:
            print(f"DEBUG [refresh_access_token]: Exception: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    @classmethod
    def ensure_valid_token(cls, keys_dict: Dict[str, Any]) -> tuple[str, bool]:
        """Checks if current access_token is expired and refreshes if needed."""
        current_token = keys_dict.get("tiktok_access_token", "").strip()
        refresh_token = keys_dict.get("tiktok_refresh_token", "").strip()
        client_key = keys_dict.get("tiktok_client_key", "").strip()
        raw_secret = keys_dict.get("tiktok_client_secret", "").strip()
        client_secret = _decrypt_secret(raw_secret)
        expires_at = keys_dict.get("tiktok_expires_at", 0)

        now = int(time.time())

        if (now >= expires_at - 300 or not current_token) and refresh_token and client_key and client_secret:
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
                except Exception as e:
                    print(f"DEBUG [ensure_valid_token]: Failed saving keys: {e}\n{traceback.format_exc()}")
                return new_token, True

        return current_token, False

    @classmethod
    def run_auth_wizard(cls, client_key: str, client_secret: str, open_popup_fn=None) -> Dict[str, Any]:
        """Executes complete PKCE OAuth Flow using pywebview In-App Popup Window or OS Browser fallback."""
        client_secret = _decrypt_secret(client_secret)

        print("=" * 80)
        print(f"DEBUG [run_auth_wizard]: STARTING WIZARD for client_key={client_key}")
        print("=" * 80)

        if not client_key or not client_secret:
            return {"success": False, "error": "TikTok Client Key ve Client Secret gereklidir."}

        verifier, challenge = cls.generate_pkce_pair()
        state = secrets.token_hex(16)

        print(f"DEBUG [run_auth_wizard]: Generated PKCE verifier={verifier[:10]}... challenge={challenge}")
        print(f"DEBUG [run_auth_wizard]: Generated state={state}")

        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.state = None
        OAuthCallbackHandler.error = None

        server = None
        for try_port in [8989, 8990, 8991, 8992]:
            try:
                cls.PORT = try_port
                cls.REDIRECT_URI = f"http://127.0.0.1:{try_port}/callback/"
                server = ReuseThreadingHTTPServer(("127.0.0.1", try_port), OAuthCallbackHandler)
                server.timeout = 1.0
                print(f"DEBUG [run_auth_wizard]: ReuseThreadingHTTPServer bound to http://127.0.0.1:{try_port}")
                break
            except Exception as port_err:
                print(f"DEBUG [run_auth_wizard]: Port {try_port} busy/unavailable: {port_err}")

        if not server:
            return {"success": False, "error": "Yerel dinleyici başlatılamadı (Portlar meşgul)."}

        auth_url = cls.get_auth_url(client_key, challenge, state)

        print("=" * 80)
        print("TikTok OAuth URL:")
        print(auth_url)
        print("=" * 80)

        # Launch In-App Popup Window or fallback to OS browser
        popup = None
        if open_popup_fn:
            try:
                popup = open_popup_fn(auth_url)
                print(f"DEBUG [run_auth_wizard]: In-App Popup Window created: {popup}")
            except Exception as pop_err:
                print(f"DEBUG [run_auth_wizard]: In-App Popup creation failed: {pop_err}\n{traceback.format_exc()}")

        if not popup:
            _open_url_in_browser(auth_url)

        print("DEBUG [run_auth_wizard]: Waiting for OAuth redirect callback (timeout 120s)...")
        start_time = time.time()
        while time.time() - start_time < 120:
            server.handle_request()
            if OAuthCallbackHandler.auth_code or OAuthCallbackHandler.error:
                print(f"DEBUG [run_auth_wizard]: Callback received! auth_code={OAuthCallbackHandler.auth_code}, error={OAuthCallbackHandler.error}")
                break

        server.server_close()

        # Destroy in-app popup window if created
        if popup:
            try:
                popup.destroy()
                print("DEBUG [run_auth_wizard]: Closed In-App Popup Window.")
            except Exception as destroy_err:
                print(f"DEBUG [run_auth_wizard]: Popup destroy error: {destroy_err}")

        if OAuthCallbackHandler.error:
            return {"success": False, "error": f"Giriş reddedildi: {OAuthCallbackHandler.error}"}

        if not OAuthCallbackHandler.auth_code:
            return {"success": False, "error": "Zaman aşımı: TikTok giriş yapılması beklenirken 120 saniye doldu."}

        print(f"DEBUG [run_auth_wizard]: Validating state... Received={OAuthCallbackHandler.state}, Expected={state}")
        if OAuthCallbackHandler.state != state:
            return {"success": False, "error": "Güvenlik İhlali (CSRF): TikTok state parametresi doğrulanamadı!"}

        print("DEBUG [run_auth_wizard]: Calling exchange_code_for_token...")
        res = cls.exchange_code_for_token(
            client_key=client_key,
            client_secret=client_secret,
            code=OAuthCallbackHandler.auth_code,
            code_verifier=verifier
        )

        print(f"DEBUG [run_auth_wizard]: exchange_code_for_token result = {res}")

        if res.get("success"):
            print("=" * 80)
            print("DEBUG [run_auth_wizard]: PREPARING TO WRITE TO config_keys.json")
            print(f"  • Target File Path: {KEYS_FILE}")
            print(f"  • tiktok_access_token: {res.get('access_token')}")
            print(f"  • tiktok_open_id: {res.get('open_id')}")
            print(f"  • tiktok_refresh_token: {res.get('refresh_token')}")
            print("=" * 80)

            try:
                existing = {}
                if KEYS_FILE.exists():
                    with open(KEYS_FILE, "r", encoding="utf-8") as f:
                        existing = json.load(f)

                existing["tiktok_access_token"] = res["access_token"]
                existing["tiktok_open_id"] = res["open_id"]
                existing["tiktok_expires_at"] = res.get("expires_at", int(time.time()) + 86400)

                if res.get("refresh_token"):
                    existing["tiktok_refresh_token"] = res["refresh_token"]
                if res.get("refresh_expires_at"):
                    existing["tiktok_refresh_expires_at"] = res.get("refresh_expires_at", int(time.time()) + 31536000)

                existing["tiktok_client_key"] = client_key
                existing["tiktok_client_secret"] = _encrypt_secret(client_secret)

                with open(KEYS_FILE, "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)

                print("DEBUG [run_auth_wizard]: Successfully wrote to config_keys.json!")

                # VERIFICATION READ-BACK
                with open(KEYS_FILE, "r", encoding="utf-8") as rf:
                    verify_data = json.load(rf)

                print("=" * 80)
                print("DEBUG [run_auth_wizard]: READ-BACK VERIFICATION FROM DISK:")
                print(f"  • tiktok_access_token in file: {verify_data.get('tiktok_access_token')}")
                print(f"  • tiktok_open_id in file: {verify_data.get('tiktok_open_id')}")
                print(f"  • tiktok_refresh_token in file: {verify_data.get('tiktok_refresh_token')}")
                print("=" * 80)

            except Exception as write_err:
                print(f"DEBUG [run_auth_wizard]: FAILED TO WRITE/READ config_keys.json: {write_err}\n{traceback.format_exc()}")

        return res


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        print(f"DEBUG [OAuthCallbackHandler]: GET received path={self.path}, qs={qs}")
        if "code" in qs:
            OAuthCallbackHandler.auth_code = qs["code"][0]
            if "state" in qs:
                OAuthCallbackHandler.state = qs["state"][0]
            msg = """
            <html>
            <body style="font-family:'Segoe UI',sans-serif; text-align:center; padding:60px 20px; background:linear-gradient(135deg,#0B0F19,#1a1f2e); color:#fff; min-height:100vh; margin:0;">
              <div style="max-width:480px; margin:0 auto;">
                <div style="font-size:64px; margin-bottom:20px;">✅</div>
                <h2 style="color:#10B981; margin-bottom:12px; font-size:24px;">TikTok Girişi Başarılı!</h2>
                <p style="font-size:16px; color:#E2E8F0; margin-bottom:8px;">Yetkilendirme kodu alındı ve token otomatik olarak işleniyor.</p>
                <p style="color:#94A3B8; font-size:14px;">Bu pencere <span id="cd">3</span> saniye içinde kapanacak...</p>
                <p style="color:#64748B; font-size:13px; margin-top:24px;">VidDownUPload uygulamasına dönebilirsiniz.</p>
              </div>
              <script>
                var s=3;
                var i=setInterval(function(){s--;document.getElementById('cd').textContent=s;if(s<=0){clearInterval(i);window.close();}},1000);
              </script>
            </body>
            </html>
            """
        else:
            OAuthCallbackHandler.error = qs.get("error_description", ["Yetkilendirme reddedildi"])[0]
            msg = f"""
            <html>
            <body style="font-family:'Segoe UI',sans-serif; text-align:center; padding:60px 20px; background:linear-gradient(135deg,#0B0F19,#1a1f2e); color:#fff; min-height:100vh; margin:0;">
              <div style="max-width:480px; margin:0 auto;">
                <div style="font-size:64px; margin-bottom:20px;">❌</div>
                <h2 style="color:#EF4444; margin-bottom:12px;">Giriş İptal Edildi</h2>
                <p style="color:#E2E8F0; font-size:15px;">{OAuthCallbackHandler.error}</p>
                <p style="color:#94A3B8; font-size:14px; margin-top:16px;">Uygulamaya dönüp tekrar deneyin.</p>
              </div>
            </body>
            </html>
            """

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(msg.encode("utf-8"))

    def log_message(self, format, *args):
        pass
