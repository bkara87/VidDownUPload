import os
import sys
import threading
import urllib.request
from io import BytesIO
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image

from src.processor.asset_marketplace import AssetMarketplaceManager
from src.ui.styles import (
    COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_INPUT_BG
)

CATEGORIES = [
    "Stickers", "Animated", "CTA", "Meme", "Emoji", 
    "Overlay", "Effects", "Titles", "Lower Third", "Sound FX", "Fonts"
]

class AssetMarketplaceWidget(ctk.CTkFrame):
    """
    🎨 Trend Asset Marketplace Component for Video Downloader & Studio
    Integrates directly below 'Görsel Trend Rozet Paketi'
    """
    def __init__(self, master, on_apply_asset=None, log_callback=None, **kwargs):
        super().__init__(master, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B", **kwargs)
        self.on_apply_asset = on_apply_asset
        self.log_callback = log_callback

        self.manager = AssetMarketplaceManager()
        self.active_category = "Stickers"
        self.favorite_only = False
        self._image_cache = {}

        self._build_ui()
        self._load_assets()

    def _build_ui(self):
        # Header title
        head_frame = ctk.CTkFrame(self, fg_color="transparent")
        head_frame.pack(fill="x", padx=14, pady=(10, 4))

        lbl_head = ctk.CTkLabel(
            head_frame,
            text="🎨 Trend Asset Marketplace",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        lbl_head.pack(side="left")

        self.btn_fav_filter = ctk.CTkButton(
            head_frame,
            text="❤️ Favorilerim",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            height=24,
            width=85,
            command=self._toggle_fav_filter
        )
        self.btn_fav_filter.pack(side="right")

        # Search Bar & Filter Row
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=14, pady=(2, 6))

        self.entry_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Trend etiket, sticker, emoji ara...",
            height=30,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            font=ctk.CTkFont(size=11)
        )
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry_search.bind("<KeyRelease>", lambda _: self._load_assets())

        # Category Scrollable Tabs Bar
        tabs_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=34, orientation="horizontal")
        tabs_scroll.pack(fill="x", padx=10, pady=(0, 6))

        self.cat_buttons = {}
        for cat in CATEGORIES:
            btn = ctk.CTkButton(
                tabs_scroll,
                text=cat,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=COLOR_PRIMARY if cat == self.active_category else "#1E293B",
                hover_color=COLOR_PRIMARY_HOVER if cat == self.active_category else "#334155",
                height=26,
                width=75,
                corner_radius=6,
                command=lambda c=cat: self._select_category(c)
            )
            btn.pack(side="left", padx=3)
            self.cat_buttons[cat] = btn

        # Scrollable Grid Container for Cards
        self.grid_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="#070B12",
            height=190,
            corner_radius=10,
            border_width=1,
            border_color="#1E293B"
        )
        self.grid_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _select_category(self, cat: str):
        self.active_category = cat
        self.favorite_only = False
        self.btn_fav_filter.configure(fg_color="#334155")
        for c, btn in self.cat_buttons.items():
            if c == cat:
                btn.configure(fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER)
            else:
                btn.configure(fg_color="#1E293B", hover_color="#334155")
        self._load_assets()

    def _toggle_fav_filter(self):
        self.favorite_only = not self.favorite_only
        if self.favorite_only:
            self.btn_fav_filter.configure(fg_color=COLOR_PRIMARY)
        else:
            self.btn_fav_filter.configure(fg_color="#334155")
        self._load_assets()

    def _load_assets(self):
        for widget in self.grid_scroll.winfo_children():
            widget.destroy()

        search_kw = self.entry_search.get().strip()
        items = self.manager.get_assets(
            category=None if self.favorite_only else self.active_category,
            search=search_kw,
            favorite_only=self.favorite_only
        )

        if not items:
            lbl_empty = ctk.CTkLabel(
                self.grid_scroll,
                text="📭 Aranan kritere uygun trend asset bulunamadı.",
                font=ctk.CTkFont(size=11),
                text_color=COLOR_TEXT_MUTED
            )
            lbl_empty.pack(padx=20, pady=30)
            return

        grid_frame = ctk.CTkFrame(self.grid_scroll, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=4, pady=4)

        cols = 3
        row = 0
        col = 0
        for item in items:
            card = self._create_asset_card(grid_frame, item)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="n")

            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _create_asset_card(self, parent, item: dict):
        asset_id = item["id"]
        is_installed = bool(item.get("file_path") and os.path.exists(item.get("file_path")))
        is_fav = bool(item.get("favorite") == 1)

        card = ctk.CTkFrame(
            parent,
            fg_color="#0D1322",
            corner_radius=10,
            border_width=1,
            border_color="#1E293B",
            width=135
        )

        # Thumbnail Label
        lbl_thumb = ctk.CTkLabel(card, text="🎨 Asset", width=120, height=70, fg_color="#1E293B", corner_radius=6)
        lbl_thumb.pack(padx=5, pady=(5, 3))

        url = item.get("preview_url")
        if url:
            def load_bg():
                try:
                    if url in self._image_cache:
                        img = self._image_cache[url]
                    else:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            raw_data = resp.read()
                        pil_img = Image.open(BytesIO(raw_data)).convert("RGBA")
                        img = pil_img.resize((64, 64), Image.Resampling.LANCZOS)
                        self._image_cache[url] = img

                    if card.winfo_exists():
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(50, 50))
                        self.after(0, lambda: lbl_thumb.configure(image=ctk_img, text=""))
                except Exception:
                    pass

            threading.Thread(target=load_bg, daemon=True).start()

        # Name
        name_text = item.get("name", "Asset")
        if len(name_text) > 18:
            name_text = name_text[:16] + "..."

        lbl_name = ctk.CTkLabel(
            card,
            text=name_text,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
            wraplength=125,
            justify="left"
        )
        lbl_name.pack(anchor="w", padx=5, pady=(1, 1))

        # Format & Source info
        fmt_str = f"{item.get('format', 'PNG')} • {item.get('source', 'OpenMoji')}"
        lbl_meta = ctk.CTkLabel(card, text=fmt_str, font=ctk.CTkFont(size=8), text_color=COLOR_TEXT_MUTED)
        lbl_meta.pack(anchor="w", padx=5, pady=(0, 3))

        # Action Buttons Row (Download / Apply & Fav)
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(0, 5))

        btn_fav = ctk.CTkButton(
            btn_row,
            text="❤️" if is_fav else "🤍",
            width=24,
            height=22,
            fg_color="#1E293B",
            hover_color="#334155",
            command=lambda: self._toggle_fav(asset_id)
        )
        btn_fav.pack(side="left", padx=(0, 2))

        if is_installed:
            btn_act = ctk.CTkButton(
                btn_row,
                text="✨ Ekle",
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=COLOR_SUCCESS,
                hover_color=COLOR_SUCCESS_HOVER,
                height=22,
                command=lambda: self._apply_asset_to_studio(item.get("file_path"))
            )
        else:
            btn_act = ctk.CTkButton(
                btn_row,
                text="📥 İndir",
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER,
                height=22,
                command=lambda: self._download_and_apply(asset_id)
            )
        btn_act.pack(side="left", fill="x", expand=True)

        return card

    def _toggle_fav(self, asset_id: str):
        self.manager.toggle_favorite(asset_id)
        self._load_assets()

    def _download_and_apply(self, asset_id: str):
        def task():
            path = self.manager.download_asset(asset_id)
            if path:
                if self.log_callback:
                    self.log_callback(f"✅ Asset indirildi ve sqlite veritabanına kaydedildi: {os.path.basename(path)}")
                self.after(0, self._load_assets)
                self.after(0, lambda: self._apply_asset_to_studio(path))
            else:
                self.after(0, lambda: messagebox.showerror("Hata", "Asset indirilemedi."))

        threading.Thread(target=task, daemon=True).start()

    def _apply_asset_to_studio(self, file_path: str):
        if file_path and os.path.exists(file_path):
            if self.on_apply_asset:
                self.on_apply_asset(file_path)
            if self.log_callback:
                self.log_callback(f"🎨 Asset stüdyoya eklendi: {os.path.basename(file_path)}")
