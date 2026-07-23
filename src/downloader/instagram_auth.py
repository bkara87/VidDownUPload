import os
import json
import requests
from pathlib import Path

class InstagramAuthManager:
    """
    Manages Instagram Login authentication, credentials storage, and session cookies for yt-dlp.
    """
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load_auth_info(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("instagram_auth", {})
            except Exception:
                pass
        return {}

    def save_auth_info(self, username="", password="", sessionid="", use_hesapsiz=False):
        data = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        data["instagram_auth"] = {
            "username": username.strip(),
            "password": password.strip(),
            "sessionid": sessionid.strip(),
            "use_hesapsiz": use_hesapsiz
        }

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # If sessionid provided, write Netscape cookies.txt file for yt-dlp
            if sessionid.strip():
                cookie_file = self.config_path.parent / "instagram_cookies.txt"
                with open(cookie_file, "w", encoding="utf-8") as f_c:
                    f_c.write("# Netscape HTTP Cookie File\n")
                    f_c.write(f".instagram.com\tTRUE\t/\tTRUE\t2147483647\tsessionid\t{sessionid.strip()}\n")

            return True
        except Exception as e:
            print(f"Error saving Instagram auth: {e}")
            return False

    def get_ytdlp_auth_opts(self) -> dict:
        info = self.load_auth_info()
        if info.get("use_hesapsiz"):
            return {}

        opts = {}
        username = info.get("username")
        password = info.get("password")
        sessionid = info.get("sessionid")

        cookie_file = self.config_path.parent / "instagram_cookies.txt"
        if cookie_file.exists() and sessionid:
            opts["cookiefile"] = str(cookie_file)
        elif username and password:
            opts["username"] = username
            opts["password"] = password

        return opts
