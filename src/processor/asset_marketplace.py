import os
import sys
import json
import sqlite3
import urllib.request
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import BASE_DIR

MARKETPLACE_DIR = BASE_DIR / "assets" / "marketplace"
DB_FILE = BASE_DIR / "assets" / "marketplace.db"

# Sample Curated Asset Manifest from Open-License Sources (OpenMoji, SVG Repo, Mixkit, Twemoji, Lucide)
CURATED_MANIFEST: List[Dict[str, Any]] = [
    # Stickers & Memes
    {
        "id": "stk_laugh_crying",
        "name": "😂 Gülmekten Yarılma (Laugh Crying)",
        "category": "Emoji",
        "tags": "meme, emoji, laugh, funny, komik, mizah",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F602.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F602.png",
        "file_size": "12 KB",
        "is_new": True
    },
    {
        "id": "stk_rofl",
        "name": "🤣 Yerlerde Sürünme (ROFL Emoji)",
        "category": "Emoji",
        "tags": "rofl, laugh, meme, funny, mizah",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F923.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F923.png",
        "file_size": "14 KB",
        "is_new": True
    },
    {
        "id": "stk_fire",
        "name": "🔥 Alev / Trend Ateş Emoji",
        "category": "Stickers",
        "tags": "fire, trend, hot, viral, ates",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F525.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F525.png",
        "file_size": "11 KB",
        "is_new": False
    },
    {
        "id": "stk_explosion",
        "name": "💥 Bomba / Patlama (Explosion)",
        "category": "Effects",
        "tags": "explosion, boom, effect, shock, patlama",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4A5.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4A5.png",
        "file_size": "15 KB",
        "is_new": True
    },

    # CTA (Call To Action) Buttons & Badges
    {
        "id": "cta_sub_bell",
        "name": "🔔 Abone Ol & Bildirimleri Aç (Subscribe)",
        "category": "CTA",
        "tags": "subscribe, bell, youtube, cta, takip, abone",
        "format": "SVG",
        "license": "MIT (Lucide)",
        "source": "Lucide",
        "url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/bell-ring.svg",
        "preview_url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/bell-ring.svg",
        "file_size": "4 KB",
        "is_new": True
    },
    {
        "id": "cta_like_thumbs",
        "name": "👍 Beğen / Like Butonu (Hand Like)",
        "category": "CTA",
        "tags": "like, thumbsup, cta, begen, buton",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F44D.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F44D.png",
        "file_size": "9 KB",
        "is_new": False
    },
    {
        "id": "cta_follow_heart",
        "name": "❤️ Takip Et / Follow Kalp",
        "category": "CTA",
        "tags": "heart, follow, instagram, tiktok, takip",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/2764.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/2764.png",
        "file_size": "8 KB",
        "is_new": True
    },
    {
        "id": "cta_share_arrow",
        "name": "📤 Paylaş / Share Ok İkonu",
        "category": "CTA",
        "tags": "share, arrow, viral, paylas, reels",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4E4.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4E4.png",
        "file_size": "7 KB",
        "is_new": False
    },

    # Overlays & Visual Stickers
    {
        "id": "ovl_vip_badge",
        "name": "⭐ VIP Premium Rozet Paket",
        "category": "Overlay",
        "tags": "vip, premium, star, badge, rozet",
        "format": "PNG",
        "license": "CC0 Public Domain",
        "source": "SVG Repo",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/2B50.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/2B50.png",
        "file_size": "10 KB",
        "is_new": True
    },
    {
        "id": "ovl_skull",
        "name": "💀 Gülmekten Öldüm (Skull Meme)",
        "category": "Meme",
        "tags": "skull, dead, meme, funny, olu",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F480.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F480.png",
        "file_size": "13 KB",
        "is_new": False
    },
    {
        "id": "ovl_sparkles",
        "name": "✨ Işıltı & Neon Sparkle Efekt",
        "category": "Effects",
        "tags": "sparkle, neon, shine, magic, isilti",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/2728.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/2728.png",
        "file_size": "12 KB",
        "is_new": True
    },
    {
        "id": "ovl_glitch_tv",
        "name": "📺 Retro TV / Glitch Kamera",
        "category": "Effects",
        "tags": "tv, camera, glitch, vhs, retro",
        "format": "PNG",
        "license": "CC-BY-SA 4.0 (OpenMoji)",
        "source": "OpenMoji",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4FA.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4FA.png",
        "file_size": "14 KB",
        "is_new": False
    },
    {
        "id": "tit_lower_third",
        "name": "📰 Alt Başlık / Lower Third Bantsı",
        "category": "Lower Third",
        "tags": "lowerthird, title, caption, news, bant",
        "format": "PNG",
        "license": "CC0 Public Domain",
        "source": "Mixkit",
        "url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4F0.png",
        "preview_url": "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4F0.png",
        "file_size": "16 KB",
        "is_new": True
    }
]

class AssetMarketplaceManager:
    """
    Manages SQLite database, offline disk caching, downloading, and synchronization for Trend Asset Marketplace.
    """
    def __init__(self):
        MARKETPLACE_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,
                    source TEXT,
                    file_path TEXT,
                    license TEXT,
                    version TEXT,
                    favorite INTEGER DEFAULT 0,
                    installed_date TEXT,
                    preview_url TEXT,
                    format TEXT,
                    file_size TEXT,
                    is_new INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()

            # Seed initial manifest if empty
            self._seed_manifest_if_empty()
        except Exception as e:
            print(f"Marketplace DB init error: {e}")

    def _seed_manifest_if_empty(self):
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM assets")
            count = cursor.fetchone()[0]
            if count == 0:
                for item in CURATED_MANIFEST:
                    cursor.execute("""
                        INSERT OR REPLACE INTO assets 
                        (id, name, category, tags, source, file_path, license, version, favorite, installed_date, preview_url, format, file_size, is_new)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
                    """, (
                        item["id"],
                        item["name"],
                        item["category"],
                        item["tags"],
                        item["source"],
                        "",
                        item["license"],
                        "1.0.0",
                        "",
                        item["preview_url"],
                        item["format"],
                        item["file_size"],
                        1 if item.get("is_new") else 0
                    ))
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error seeding manifest: {e}")

    def get_assets(self, category: Optional[str] = None, search: str = "", favorite_only: bool = False) -> List[Dict[str, Any]]:
        results = []
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM assets WHERE 1=1"
            params = []

            if category and category != "Tümü" and category != "All":
                query += " AND category LIKE ?"
                params.append(f"%{category}%")

            if favorite_only:
                query += " AND favorite = 1"

            if search.strip():
                query += " AND (name LIKE ? OR tags LIKE ? OR category LIKE ?)"
                kw = f"%{search.strip()}%"
                params.extend([kw, kw, kw])

            query += " ORDER BY is_new DESC, id ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for r in rows:
                results.append(dict(r))
            conn.close()
        except Exception as e:
            print(f"Error fetching assets from DB: {e}")
        return results

    def toggle_favorite(self, asset_id: str) -> bool:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT favorite FROM assets WHERE id = ?", (asset_id,))
            row = cursor.fetchone()
            if row:
                new_state = 0 if row[0] == 1 else 1
                cursor.execute("UPDATE assets SET favorite = ? WHERE id = ?", (new_state, asset_id))
                conn.commit()
                conn.close()
                return bool(new_state)
            conn.close()
        except Exception as e:
            print(f"Error toggling favorite: {e}")
        return False

    def download_asset(self, asset_id: str) -> Optional[str]:
        """
        Downloads asset to local assets/marketplace/<category>/ and updates SQLite DB.
        """
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None

            asset = dict(row)
            cat_dir = MARKETPLACE_DIR / asset["category"].lower()
            cat_dir.mkdir(parents=True, exist_ok=True)

            ext = asset["format"].lower()
            dest_file = cat_dir / f"{asset_id}.{ext}"

            # Download file from preview_url if remote
            url = asset["preview_url"]
            if url and url.startswith("http"):
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp, open(dest_file, "wb") as out_f:
                    shutil.copyfileobj(resp, out_f)

            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE assets SET file_path = ?, installed_date = ? WHERE id = ?", (str(dest_file), now_str, asset_id))
            conn.commit()
            conn.close()
            return str(dest_file)
        except Exception as e:
            print(f"Error downloading asset {asset_id}: {e}")
        return None
