import os
import glob
import json
import math
import threading
import subprocess
import tkinter as tk
from pathlib import Path
import customtkinter as ctk
import cv2
from PIL import Image

from src.ui.styles import (
    COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_WARNING, COLOR_GLASS_BG,
    COLOR_GLASS_BORDER, COLOR_TEXT_ACCENT, COLOR_INPUT_BG, COLOR_LOG_BG
)

class VideoGridWidget(ctk.CTkFrame):
    """
    Vertical 9:16 Aspect Ratio Video Cards Grid Gallery for Downloaded/Processed Videos with Pagination.
    """
    def __init__(self, master, target_dir: Path, on_select_video=None, on_upload_video=None, **kwargs):
        super().__init__(master, **kwargs)
        self.target_dir = Path(target_dir)
        self.on_select_video = on_select_video
        self.on_upload_video = on_upload_video

        self.per_page = 12
        self.current_page = 1
        self.total_pages = 1
        self._current_video_files = []
        self._last_cols = 0
        self._resize_job = None

        self._build_ui()
        self.refresh_grid()

    def _build_ui(self):
        self.configure(fg_color="transparent")

        # ── PREMIUM HEADER TOOLBAR ────────────────────────────────
        header = ctk.CTkFrame(
            self,
            fg_color=COLOR_GLASS_BG,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_GLASS_BORDER,
            height=48
        )
        header.pack(fill="x", padx=4, pady=(4, 8))

        # ── PREMIUM PLATFORM SELECTION BAR ────────────────────────
        if self.on_upload_video or "processed" in self.target_dir.name.lower():
            plat_card = ctk.CTkFrame(
                self,
                fg_color=COLOR_GLASS_BG,
                corner_radius=14,
                border_width=1,
                border_color=COLOR_GLASS_BORDER
            )
            plat_card.pack(fill="x", padx=4, pady=(0, 8))

            p_top = ctk.CTkFrame(plat_card, fg_color="transparent")
            p_top.pack(fill="x", padx=14, pady=(10, 4))

            ctk.CTkLabel(
                p_top,
                text="🎯 Otomatik Yüklenecek Platformlar",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=COLOR_TEXT_MAIN
            ).pack(side="left")

            ctk.CTkLabel(
                p_top,
                text="Sadece seçili platformlara yükleme yapılır",
                font=ctk.CTkFont(size=11),
                text_color=COLOR_TEXT_MUTED
            ).pack(side="right")

            p_row = ctk.CTkFrame(plat_card, fg_color="transparent")
            p_row.pack(fill="x", padx=14, pady=(0, 10))

            self.chk_platform_ig = ctk.CTkCheckBox(
                p_row, text="📸 Instagram",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#F77AB4", fg_color="#C13584", hover_color="#A8275F",
                border_color="#E1306C", checkmark_color="#FFFFFF"
            )
            self.chk_platform_ig.pack(side="left", padx=(0, 18))
            self.chk_platform_ig.select()

            self.chk_platform_yt = ctk.CTkCheckBox(
                p_row, text="▶️ YouTube",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#FF6B6B", fg_color="#CC0000", hover_color="#990000",
                border_color="#FF0000", checkmark_color="#FFFFFF"
            )
            self.chk_platform_yt.pack(side="left", padx=(0, 18))

            self.chk_platform_tt = ctk.CTkCheckBox(
                p_row, text="🎵 TikTok",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#67E8F9", fg_color="#0891B2", hover_color="#0E7490",
                border_color="#00F2FE", checkmark_color="#FFFFFF"
            )
            self.chk_platform_tt.pack(side="left", padx=(0, 18))

            self.chk_platform_th = ctk.CTkCheckBox(
                p_row, text="🧵 Threads",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#CBD5E1", fg_color="#475569", hover_color="#334155",
                border_color="#64748B", checkmark_color="#FFFFFF"
            )
            self.chk_platform_th.pack(side="left", padx=(0, 18))

            self.chk_platform_fb = ctk.CTkCheckBox(
                p_row, text="📘 Facebook",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#93C5FD", fg_color="#1D4ED8", hover_color="#1E40AF",
                border_color="#1877F2", checkmark_color="#FFFFFF"
            )
            self.chk_platform_fb.pack(side="left")


        lbl_title = ctk.CTkLabel(
            header,
            text=f"📹 {self.target_dir.name}/ Galerim",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_ACCENT
        )
        lbl_title.pack(side="left", padx=14)

        # Action Buttons on the Right
        btn_refresh = ctk.CTkButton(
            header, text="🔄",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1A2540", hover_color="#243050",
            width=36, height=32, corner_radius=10,
            command=self.refresh_grid
        )
        btn_refresh.pack(side="right", padx=6)

        btn_open_folder = ctk.CTkButton(
            header, text="📁 Klasör",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            width=80, height=32, corner_radius=10,
            command=self._open_target_folder
        )
        btn_open_folder.pack(side="right", padx=(0, 4))

        self.btn_next = ctk.CTkButton(
            header, text="▶",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1A2540", hover_color="#243050",
            width=30, height=32, corner_radius=8,
            command=self._next_page
        )
        self.btn_next.pack(side="right", padx=4)

        self.lbl_page_info = ctk.CTkLabel(
            header,
            text="1 / 1",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_SUCCESS
        )
        self.lbl_page_info.pack(side="right", padx=6)

        self.btn_prev = ctk.CTkButton(
            header, text="◀",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1A2540", hover_color="#243050",
            width=30, height=32, corner_radius=8,
            command=self._prev_page
        )
        self.btn_prev.pack(side="right", padx=4)

        self.opt_per_page = ctk.CTkOptionMenu(
            header,
            values=["12 / Sayfa", "24 / Sayfa", "48 / Sayfa", "Tamamı"],
            width=100, height=32,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#1A2540", button_color="#243050",
            button_hover_color="#2D3E60",
            command=self._on_per_page_change
        )
        self.opt_per_page.pack(side="right", padx=6)

        # ── PREMIUM SCROLL GALLERY SURFACE ────────────────────────────
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color=COLOR_LOG_BG,
            corner_radius=16,
            border_width=1,
            border_color=COLOR_GLASS_BORDER,
            height=560
        )
        self.scroll_container.pack(fill="both", expand=True, padx=4, pady=4)
        self.scroll_container.bind("<Configure>", self._on_container_configure)

    def _open_target_folder(self):
        if os.path.exists(self.target_dir):
            try:
                os.startfile(self.target_dir)
            except Exception as e:
                print(f"Error opening target folder: {e}")

    def _on_container_configure(self, event):
        w = event.width
        if w > 200:
            cols = max(1, int((w - 30) // 190))
            if cols != self._last_cols and hasattr(self, '_current_video_files') and self._current_video_files:
                if self._resize_job:
                    self.after_cancel(self._resize_job)
                self._resize_job = self.after(250, lambda: self._render_cards_layout(self._current_video_files, cols=cols))

    def _on_per_page_change(self, choice):
        if "12" in choice:
            self.per_page = 12
        elif "24" in choice:
            self.per_page = 24
        elif "48" in choice:
            self.per_page = 48
        else:
            self.per_page = 999999
        self.current_page = 1
        self._render_cards_layout(self._current_video_files)

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render_cards_layout(self._current_video_files)

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._render_cards_layout(self._current_video_files)

    def refresh_grid(self):
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir, exist_ok=True)

        video_files = sorted(
            glob.glob(os.path.join(self.target_dir, "*.mp4")),
            key=os.path.getmtime,
            reverse=True
        )
        self._current_video_files = video_files
        self.current_page = 1
        self._last_cols = 0
        self._render_cards_layout(video_files)

    def _render_cards_layout(self, video_files, cols=None):
        # Clear existing cards
        for widget in self.scroll_container.winfo_children():
            widget.destroy()

        total_files = len(video_files)
        if total_files == 0:
            self.lbl_page_info.configure(text="Sayfa 0 / 0 (0 Video)")
            self.btn_prev.configure(state="disabled")
            self.btn_next.configure(state="disabled")

            no_vid_lbl = ctk.CTkLabel(
                self.scroll_container,
                text="📭 Henüz indirilen video bulunmuyor.\n\n'Video İndirici' sekmesinden bir video veya profil reels'i indirin.",
                font=ctk.CTkFont(size=13),
                text_color=COLOR_TEXT_MUTED
            )
            no_vid_lbl.pack(padx=20, pady=40)
            return

        # Calculate pages
        self.total_pages = max(1, math.ceil(total_files / self.per_page))
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

        self.lbl_page_info.configure(text=f"Sayfa {self.current_page} / {self.total_pages}  •  {total_files} Video")
        self.btn_prev.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < self.total_pages else "disabled")

        # Slice current page files ONLY (12 per page)
        start_idx = (self.current_page - 1) * self.per_page
        end_idx = min(start_idx + self.per_page, total_files)
        page_files = video_files[start_idx:end_idx]

        if not cols or cols < 1:
            w = self.scroll_container.winfo_width() or self.winfo_width()
            if w < 200:
                w = 1400
            cols = max(1, int((w - 30) // 190))

        self._last_cols = cols

        grid_wrapper = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        grid_wrapper.pack(fill="both", expand=True, padx=4, pady=4)

        row = 0
        col = 0
        for vid_path in page_files:
            card = self._create_video_card(grid_wrapper, vid_path)
            card.grid(row=row, column=col, padx=6, pady=8, sticky="n")

            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _create_video_card(self, parent, video_path: str):
        meta = self._load_sidecar_meta(video_path)
        is_processed = "processed" in self.target_dir.name.lower()

        # ── ULTRA PREMIUM CARD FRAME ───────────────────────────
        border_color = "#2D1B69" if is_processed else "#1A2540"
        card = ctk.CTkFrame(
            parent,
            fg_color="#0A0F1E",
            corner_radius=16,
            border_width=1,
            border_color=border_color,
            width=178
        )

        # ── THUMBNAIL FRAME (16:9 ratio, cinematic border) ──
        thumb_frame = ctk.CTkFrame(
            card,
            fg_color="#080C18",
            corner_radius=12,
            border_width=1,
            border_color="#1E2D45",
            width=162, height=228
        )
        thumb_frame.pack(padx=8, pady=(8, 4))
        thumb_frame.pack_propagate(False)

        thumb_inner_color = "#2D1B69" if is_processed else "#0D1528"
        lbl_thumb = ctk.CTkLabel(
            thumb_frame,
            text="🎦",
            font=ctk.CTkFont(size=28),
            text_color="#334155",
            width=160, height=226,
            fg_color=thumb_inner_color,
            corner_radius=10
        )
        lbl_thumb.pack(fill="both", expand=True, padx=1, pady=1)

        # Processed badge overlay
        if is_processed:
            badge_lbl = ctk.CTkLabel(
                thumb_frame,
                text="✨ İşlendi",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color="#FFFFFF",
                fg_color="#7C3AED",
                corner_radius=6,
                width=60, height=18
            )
            badge_lbl.place(x=4, y=4)

        # Async thumbnail extraction
        def extract_bg():
            img = self._extract_916_thumbnail(video_path)
            if img and card.winfo_exists():
                try:
                    ctk_thumb = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 226))
                    self.after(0, lambda: lbl_thumb.configure(image=ctk_thumb, text=""))
                except Exception:
                    pass
        threading.Thread(target=extract_bg, daemon=True).start()

        # ── VIDEO TITLE ───────────────────────────────────────
        title_text = meta.get('title') or os.path.basename(video_path)
        if len(title_text) > 28:
            title_text = title_text[:25] + "..."

        lbl_title = ctk.CTkLabel(
            card,
            text=title_text,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#CBD5E1",
            wraplength=165,
            justify="left"
        )
        lbl_title.pack(anchor="w", padx=8, pady=(2, 2))

        # ── COPY BUTTONS ROW ──────────────────────────────────
        caption = meta.get('caption') or title_text
        hashtags_str = meta.get('hashtags_str') or "#reels #viral"

        btn_row_copy = ctk.CTkFrame(card, fg_color="transparent")
        btn_row_copy.pack(fill="x", padx=6, pady=(0, 4))

        btn_cp_cap = ctk.CTkButton(
            btn_row_copy,
            text="📋 Metin",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#12183A",
            hover_color="#1E2D55",
            border_width=1,
            border_color="#243050",
            height=26, width=78,
            corner_radius=8,
            command=lambda: self._copy_to_clipboard(caption)
        )
        btn_cp_cap.pack(side="left", padx=(0, 2))

        btn_cp_tags = ctk.CTkButton(
            btn_row_copy,
            text="🏷️ Etiket",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#12183A",
            hover_color="#1E2D55",
            border_width=1,
            border_color="#243050",
            height=26, width=78,
            corner_radius=8,
            command=lambda: self._copy_to_clipboard(hashtags_str)
        )
        btn_cp_tags.pack(side="right", padx=(2, 0))

        # ── ACTION BUTTONS ROW ─────────────────────────────────
        btn_row_actions = ctk.CTkFrame(card, fg_color="transparent")
        btn_row_actions.pack(fill="x", padx=6, pady=(0, 4))

        btn_edit = ctk.CTkButton(
            btn_row_actions,
            text="🎨 Stüdyo",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            height=28, corner_radius=8,
            command=lambda p=video_path: self._on_edit_click(p)
        )
        btn_edit.pack(side="left", fill="x", expand=True, padx=(0, 2))

        btn_play = ctk.CTkButton(
            btn_row_actions,
            text="▶",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            width=28, height=28, corner_radius=8,
            command=lambda p=video_path: os.startfile(p)
        )
        btn_play.pack(side="right", padx=(2, 0))

        # ── UPLOAD BUTTON (processed videos only) ───────────────
        if is_processed or self.on_upload_video:
            btn_upload_social = ctk.CTkButton(
                card,
                text="🚀 Platforma Yükle",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="#1E1065",
                hover_color="#2D1B69",
                border_width=1,
                border_color="#4C1D95",
                height=28, corner_radius=8,
                command=lambda p=video_path: self._on_upload_click(p)
            )
            btn_upload_social.pack(fill="x", padx=6, pady=(0, 8))
        else:
            # Spacer at the bottom
            ctk.CTkLabel(card, text="", height=4).pack()

        return card

    def get_selected_platforms(self) -> dict:
        if hasattr(self, 'chk_platform_ig'):
            return {
                "instagram": bool(self.chk_platform_ig.get()),
                "youtube": bool(self.chk_platform_yt.get()),
                "tiktok": bool(self.chk_platform_tt.get()),
                "threads": bool(self.chk_platform_th.get()),
                "facebook": bool(self.chk_platform_fb.get())
            }
        return {"instagram": True, "youtube": False, "tiktok": False, "threads": False, "facebook": False}

    def _on_upload_click(self, video_path: str):
        if self.on_upload_video:
            selected_plats = self.get_selected_platforms()
            try:
                self.on_upload_video(video_path, selected_plats)
            except TypeError:
                self.on_upload_video(video_path)


    def _load_sidecar_meta(self, video_path: str) -> dict:
        base, _ = os.path.splitext(video_path)
        meta_json = base + ".json"
        if os.path.exists(meta_json):
            try:
                with open(meta_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Dynamically clean third-party channel hashtags & inject #724mizahdeposu tags for existing videos
                from src.downloader.downloader import VideoDownloader
                raw_cap = data.get('caption') or data.get('title') or ""
                uploader = data.get('uploader') or ""
                url = data.get('url') or ""

                cleaned_cap, tags, tags_str = VideoDownloader.process_and_clean_hashtags(raw_cap, uploader, url)
                data['caption'] = cleaned_cap
                data['hashtags'] = tags
                data['hashtags_str'] = tags_str
                return data
            except Exception:
                pass
        return {}

    def _extract_916_thumbnail(self, video_path: str) -> Image.Image:
        try:
            base, _ = os.path.splitext(video_path)
            thumb_cache_path = base + ".thumb.jpg"

            # 1. Fast loading from disk cache
            if os.path.exists(thumb_cache_path):
                try:
                    return Image.open(thumb_cache_path)
                except Exception:
                    pass

            # 2. Extract frame with OpenCV & save cache
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 5)
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img_resized = img.resize((150, 266), Image.Resampling.BILINEAR)
                try:
                    img_resized.save(thumb_cache_path, format="JPEG", quality=85)
                except Exception:
                    pass
                return img_resized
        except Exception as e:
            print(f"Error extracting 9:16 thumbnail: {e}")
        return None

    def _copy_to_clipboard(self, text: str):
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _on_edit_click(self, video_path: str):
        if self.on_select_video:
            self.on_select_video(video_path)
