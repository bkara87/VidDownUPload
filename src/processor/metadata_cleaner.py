import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List

from src.config import USER_DATA_DIR

KEYS_FILE = USER_DATA_DIR / "config_keys.json"


class MetadataCleaner:
    """
    Automatic Video Metadata Extractor & Channel Name Cleaner.
    Replaces third-party channel handles/names with the user's configured channel name.
    """

    @staticmethod
    def get_user_channel_name() -> str:
        """Reads configured channel handle/name from config_keys.json."""
        try:
            if KEYS_FILE.exists():
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    keys = json.load(f)
                    ig_user = keys.get("instagram_auth", {}).get("username", "").strip()
                    if ig_user:
                        return ig_user.replace("@", "")
        except Exception:
            pass
        return "724mizahdeposu"

    @classmethod
    def get_metadata_for_video(cls, video_path: str) -> Dict[str, Any]:
        """
        Loads sidecar .json metadata for a given video path.
        If missing, generates dynamic clean metadata based on filename and user's channel.
        """
        if not video_path:
            return cls._default_meta("", "")

        base, _ = os.path.splitext(video_path)
        meta_path = base + ".json"

        meta_data = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
            except Exception as e:
                print(f"[MetadataCleaner] Failed reading {meta_path}: {e}")

        raw_title = meta_data.get("title") or os.path.basename(base).replace("processed_", "").replace("Video by ", "")
        raw_desc = meta_data.get("caption") or meta_data.get("description") or raw_title
        uploader = meta_data.get("uploader") or ""
        url = meta_data.get("url") or ""

        user_channel = cls.get_user_channel_name()
        cleaned_title, cleaned_desc, tags = cls.clean_text_and_tags(raw_title, raw_desc, uploader, url, user_channel)

        return {
            "file_name": os.path.basename(video_path),
            "video_path": video_path,
            "title": cleaned_title,
            "description": cleaned_desc,
            "tags": tags,
            "tags_str": " ".join(tags),
            "original_uploader": uploader,
            "user_channel": user_channel
        }

    @classmethod
    def clean_text_and_tags(
        cls,
        title: str,
        description: str,
        uploader: str = "",
        url: str = "",
        user_channel: str = "724mizahdeposu"
    ) -> Tuple[str, str, List[str]]:
        """
        Cleans original title & description by stripping third-party channel mentions
        and replacing them with user's own channel name.
        """
        user_handle = f"@{user_channel}"
        user_hashtag = f"#{user_channel}"

        # Extract third-party uploader keywords
        keywords = []
        if uploader:
            clean_u = re.sub(r"[^\w]", "", uploader.lower())
            if len(clean_u) >= 3 and clean_u not in ["video", "reels", "shorts"]:
                keywords.append(clean_u)
                no_digits = re.sub(r"\d+$", "", clean_u)
                if len(no_digits) >= 3 and no_digits not in keywords:
                    keywords.append(no_digits)

        if url:
            url_match = re.search(r"(?:instagram\.com|tiktok\.com/@|youtube\.com/@)([A-Za-z0-9._]+)", url)
            if url_match:
                h = re.sub(r"[^\w]", "", url_match.group(1).lower())
                if len(h) >= 3 and h not in ["reels", "reel", "p", "shorts", "watch"] and h not in keywords:
                    keywords.append(h)

        found_tags = re.findall(r"#[\w\d_]+", description, re.UNICODE)

        # Replace keywords in description
        cleaned_desc = description or title or ""
        for kw in keywords:
            cleaned_desc = re.sub(rf"@{kw}\w*", user_handle, cleaned_desc, flags=re.IGNORECASE)
            cleaned_desc = re.sub(rf"#{kw}\w*", user_hashtag, cleaned_desc, flags=re.IGNORECASE)
            cleaned_desc = re.sub(rf"\b{kw}\b", user_channel, cleaned_desc, flags=re.IGNORECASE)

        # Replace keywords in title
        cleaned_title = title or ""
        for kw in keywords:
            cleaned_title = re.sub(rf"Video by {kw}\w*", f"Video - {user_channel}", cleaned_title, flags=re.IGNORECASE)
            cleaned_title = re.sub(rf"@{kw}\w*", user_handle, cleaned_title, flags=re.IGNORECASE)
            cleaned_title = re.sub(rf"#{kw}\w*", user_hashtag, cleaned_title, flags=re.IGNORECASE)

        # Clean tags list
        final_tags = [user_hashtag]
        for t in found_tags:
            t_lower = t.lower()
            is_old_kw = any(kw in t_lower for kw in keywords)
            if not is_old_kw and t_lower not in [ft.lower() for ft in final_tags]:
                final_tags.append(t)

        if user_hashtag.lower() not in [t.lower() for t in final_tags]:
            final_tags.insert(0, user_hashtag)

        return cleaned_title.strip(), cleaned_desc.strip(), final_tags

    @classmethod
    def _default_meta(cls, video_path: str, title: str) -> Dict[str, Any]:
        ch = cls.get_user_channel_name()
        h_tag = f"#{ch}"
        return {
            "file_name": os.path.basename(video_path) if video_path else "",
            "video_path": video_path or "",
            "title": title or f"Video | {ch}",
            "description": f"{title}\n\n{h_tag}",
            "tags": [h_tag],
            "tags_str": h_tag,
            "original_uploader": "",
            "user_channel": ch
        }
