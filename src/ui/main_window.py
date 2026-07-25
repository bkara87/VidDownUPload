import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from src.config import APP_NAME, APP_VERSION, DOWNLOADS_DIR, PROCESSED_DIR, BASE_DIR
from src.downloader.downloader import VideoDownloader
from src.downloader.info_fetcher import VideoInfoFetcher
from src.processor.ffmpeg_utils import VideoProcessor
from src.updater.github_updater import GitHubUpdater
from src.ui.video_preview import VideoPreviewWidget
from src.ui.video_grid_widget import VideoGridWidget
from src.ui.preset_badges import PRESET_BADGES, get_badge_icon_pil
from src.ui.api_keys_tab import ApiKeysTab
from src.ui.asset_marketplace_widget import AssetMarketplaceWidget
from src.ui.equalizer_widget import AnimatedEqualizerWidget
from src.ui.styles import (
    COLOR_BG_DARK, COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_WARNING, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_TEXT_ACCENT, COLOR_INPUT_BG, COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_TAB_BG
)

# Enforce Windows AppUserModelID BEFORE any Tk root window initializes
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("bkara87.VidDownUPload.App")
except Exception:
    pass

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} Studio v{APP_VERSION} - Live Video Preview & Public Profile Browser")
        self.geometry("1400x900")
        self.minsize(1020, 740)
        try:
            self.state('zoomed')
        except Exception:
            pass
        self.configure(fg_color="#05080F")

        self.downloader = VideoDownloader(str(DOWNLOADS_DIR))
        self.processor = VideoProcessor()
        self.updater = GitHubUpdater()
        self.downloaded_video_path = None
        self.selected_badge_preset = None
        self._app_icon_photo = None
        self._thumb_photo = None

        # Debounce: URL bilgi çekme için after() ID'si
        self._fetch_info_after_id = None
        # URL önbelleği: aynı URL için tekrar yt-dlp çalışmasını önler
        self._url_info_cache = {}

        self._force_window_icon()
        self._build_ui()

    def _force_window_icon(self):
        icon_ico = BASE_DIR / "assets" / "icon.ico"
        icon_png = BASE_DIR / "assets" / "icon.png"

        try:
            import customtkinter as ctk_lib
            win_id = self.winfo_id()
            import ctypes
            user32 = ctypes.windll.user32
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1

            if icon_ico.exists():
                hicon_small = user32.LoadImageW(0, str(icon_ico), 1, 16, 16, 0x00000010)
                hicon_big = user32.LoadImageW(0, str(icon_ico), 1, 32, 32, 0x00000010)
            else:
                hicon_small = hicon_big = 0

            def apply_win32():
                try:
                    hwnd = user32.GetAncestor(win_id, 3)
                    target_hwnd = hwnd if hwnd else win_id

                    if hicon_big:
                        user32.SendMessageW(target_hwnd, WM_SETICON, ICON_BIG, hicon_big)
                        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                    if hicon_small:
                        user32.SendMessageW(target_hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                except Exception:
                    pass

            apply_win32()
            self.after(50, apply_win32)
            self.after(200, apply_win32)
        except Exception:
            pass

    def _build_ui(self):
        # ══════════════════════════════════════════════════════════════
        # ULTRA PREMIUM HEADER BAR
        # ══════════════════════════════════════════════════════════════
        header = ctk.CTkFrame(
            self,
            fg_color="#0A0F1E",
            corner_radius=16,
            border_width=1,
            border_color="#1A2540",
            height=52
        )
        header.pack(fill="x", padx=16, pady=(10, 6))
        header.pack_propagate(False)

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", padx=16, pady=8, fill="y")

        # App Icon
        icon_png_path = BASE_DIR / "assets" / "icon.png"
        if icon_png_path.exists():
            try:
                pil_icon = Image.open(icon_png_path)
                header_logo = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(32, 32))
                lbl_logo = ctk.CTkLabel(header_left, image=header_logo, text="")
                lbl_logo.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        # App Name — Large, Bold, Premium
        lbl_title = ctk.CTkLabel(
            header_left,
            text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#F1F5F9"
        )
        lbl_title.pack(side="left", padx=(0, 8))

        # Version Badge
        lbl_badge = ctk.CTkLabel(
            header_left,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color="#FFFFFF",
            fg_color="#7C3AED",
            corner_radius=6,
            width=44,
            height=18
        )
        lbl_badge.pack(side="left", padx=(0, 12))

        # Subtitle
        lbl_sub = ctk.CTkLabel(
            header_left,
            text="Instagram  •  YouTube  •  TikTok  •  Facebook  •  Threads",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#475569"
        )
        lbl_sub.pack(side="left")

        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.pack(side="right", padx=16, pady=8)

        # Live status indicator dot
        lbl_live = ctk.CTkLabel(
            header_right,
            text="⬤ LIVE",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#10B981",
            fg_color="#052E16",
            corner_radius=6,
            padx=8, pady=2
        )
        lbl_live.pack(side="right", padx=(8, 0))

        self.btn_update = ctk.CTkButton(
            header_right,
            text="🔄 Güncelle",
            fg_color="#1A2540",
            hover_color="#243050",
            border_width=1,
            border_color="#2D3E60",
            text_color="#94A3B8",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            corner_radius=10,
            height=30,
            width=110,
            command=self._check_for_updates_async
        )
        self.btn_update.pack(side="right")

        # ══════════════════════════════════════════════════════════════
        # PREMIUM TABVIEW
        # ══════════════════════════════════════════════════════════════
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#0A0F1E",
            segmented_button_fg_color="#060A14",
            segmented_button_selected_color="#7C3AED",
            segmented_button_selected_hover_color="#6D28D9",
            segmented_button_unselected_color="#060A14",
            segmented_button_unselected_hover_color="#0D1528",
            text_color="#94A3B8",
            text_color_disabled="#334155",
            corner_radius=20,
            border_width=1,
            border_color="#1A2540"
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.tab_download = self.tabview.add("  📥 İndirici  ")
        self.tab_studio = self.tabview.add("  🎨 Stüdyo  ")
        self.tab_queue = self.tabview.add("  🚀 Paylaşım  ")
        self.tab_api = self.tabview.add("  🔑 API  ")
        self.tab_settings = self.tabview.add("  ⚙️ Ayarlar  ")

        self._build_download_tab()
        self._build_studio_tab()
        self._build_queue_tab()
        self._build_api_tab()
        self._build_settings_tab()

        # ══════════════════════════════════════════════════════════════
        # ULTRA PREMIUM LIVE LOG TERMINAL
        # ══════════════════════════════════════════════════════════════
        log_frame = ctk.CTkFrame(
            self,
            fg_color="#080C18",
            corner_radius=16,
            border_width=1,
            border_color="#1A2540"
        )
        log_frame.pack(fill="x", padx=16, pady=(0, 12))

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(8, 2))

        # Terminal title with live dot
        log_title_frame = ctk.CTkFrame(log_header, fg_color="transparent")
        log_title_frame.pack(side="left")

        ctk.CTkLabel(
            log_title_frame,
            text="⬤",
            font=ctk.CTkFont(size=8),
            text_color="#10B981"
        ).pack(side="left", padx=(0, 6))

        lbl_log = ctk.CTkLabel(
            log_title_frame,
            text="CANLI İŞlem Günlüğü",
            font=ctk.CTkFont(family="Cascadia Code", size=11, weight="bold"),
            text_color="#4ADE80"
        )
        lbl_log.pack(side="left")

        btn_controls = ctk.CTkFrame(log_header, fg_color="transparent")
        btn_controls.pack(side="right")

        btn_clear_log = ctk.CTkButton(
            btn_controls,
            text="Temizle",
            width=65, height=22,
            font=ctk.CTkFont(size=10),
            fg_color="#1A2540", hover_color="#243050",
            corner_radius=6,
            command=self._clear_log
        )
        btn_clear_log.pack(side="right", padx=(4, 0))

        self.btn_toggle_log = ctk.CTkButton(
            btn_controls,
            text="▼ Günlüğü Gizle",
            width=100, height=22,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#1A2540", hover_color="#243050",
            corner_radius=6,
            command=self._toggle_log_drawer
        )
        self.btn_toggle_log.pack(side="right")

        # Dynamic Spectrum Equalizer (premium 32 bars)
        self.equalizer = AnimatedEqualizerWidget(log_frame, num_bars=32, height=22)
        self.equalizer.pack(fill="x", padx=14, pady=(4, 2))

        self.txt_log = ctk.CTkTextbox(
            log_frame,
            height=65,
            font=ctk.CTkFont(family="Cascadia Code", size=10),
            fg_color="#030609",
            text_color="#4ADE80",
            corner_radius=8,
            border_width=1,
            border_color="#0D1528",
            scrollbar_button_color="#1A2540",
            scrollbar_button_hover_color="#243050"
        )
        self.txt_log.pack(fill="x", padx=14, pady=(2, 10))
        self.log(f"[{APP_NAME} v{APP_VERSION}] ✅ Sistem hazır. Bir video veya sayfa/profil bağlantısı girin.")

    def _toggle_log_drawer(self):
        self.is_log_collapsed = not getattr(self, 'is_log_collapsed', False)
        if self.is_log_collapsed:
            self.txt_log.pack_forget()
            self.btn_toggle_log.configure(text="▲ Günlüğü Göster")
        else:
            self.txt_log.pack(fill="x", padx=14, pady=(0, 10))
            self.btn_toggle_log.configure(text="▼ Günlüğü Gizle")

    def _build_download_tab(self):
        # Wrap tab in a vertical scrollable container so mouse wheel can scroll down to lower sections
        self.download_tab_scroll = ctk.CTkScrollableFrame(self.tab_download, fg_color="transparent")
        self.download_tab_scroll.pack(fill="both", expand=True, padx=4, pady=4)
        tab = self.download_tab_scroll

        lbl_title = ctk.CTkLabel(tab, text="📥 Video İndirme & Hesapsız Profil Tarayıcı", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_title.pack(anchor="w", padx=20, pady=(15, 2))

        lbl_desc = ctk.CTkLabel(tab, text="Video bağlantısı veya Instagram/YouTube/TikTok sayfa/profil linki yapıştırın (Giriş yapmanız gerekmez).", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED)
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 12))

        # URL Input Row with Scan Button (Paste button removed, button renamed to 🔍 Tara)
        url_frame = ctk.CTkFrame(tab, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.entry_url = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://www.instagram.com/sayfa/reels/ veya video bağlantısı...",
            height=44,
            corner_radius=10,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_CARD_BORDER,
            font=ctk.CTkFont(size=13)
        )
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_url.bind("<KeyRelease>", lambda _: self._auto_fetch_info_delay())

        btn_scan = ctk.CTkButton(
            url_frame,
            text="🔍 Tara",
            width=110,
            height=44,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._scan_profile_async
        )
        btn_scan.pack(side="right")

        # LIVE VIDEO INFO CARD (Appears when valid video link is entered)
        self.card_info = ctk.CTkFrame(tab, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        self.card_info.pack(fill="x", padx=20, pady=(0, 10))
        self.card_info.pack_forget()  # Hidden by default

        self.lbl_thumb = ctk.CTkLabel(self.card_info, text="", width=140, height=80, fg_color="#070B12", corner_radius=8)
        self.lbl_thumb.pack(side="left", padx=12, pady=10)

        info_meta = ctk.CTkFrame(self.card_info, fg_color="transparent")
        info_meta.pack(side="left", fill="both", expand=True, padx=8, pady=10)

        self.lbl_video_title = ctk.CTkLabel(info_meta, text="Video Başlığı", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_MAIN, anchor="w")
        self.lbl_video_title.pack(anchor="w")

        self.lbl_video_uploader = ctk.CTkLabel(info_meta, text="Kanal / Sayfa", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED, anchor="w")
        self.lbl_video_uploader.pack(anchor="w", pady=(2, 0))

        self.lbl_video_duration = ctk.CTkLabel(info_meta, text="Süre: --:-- | Platform: --", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_ACCENT, anchor="w")
        self.lbl_video_duration.pack(anchor="w", pady=(4, 0))

        # Main Download Button & Progress
        self.btn_download = ctk.CTkButton(
            tab,
            text="⚡ Videoyu Yüksek Kalitede İndir",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            corner_radius=10,
            command=self._start_download_thread
        )
        self.btn_download.pack(fill="x", padx=20, pady=(0, 6))

        self.progress_download = ctk.CTkProgressBar(tab, mode="indeterminate", height=6, corner_radius=3)
        self.progress_download.pack(fill="x", padx=20, pady=(0, 8))
        self.progress_download.set(0)

        # PROFILE VIDEOS SCROLLABLE CONTAINER
        self.frame_profile_results = ctk.CTkFrame(tab, fg_color="transparent")
        self.frame_profile_results.pack(fill="x", padx=20, pady=(0, 10))
        self.frame_profile_results.pack_forget()

        # Downloaded Videos 9:16 Grid Gallery (Bottom Half)
        self.grid_gallery_dl = VideoGridWidget(tab, target_dir=DOWNLOADS_DIR, on_select_video=self._on_grid_select_video)
        self.grid_gallery_dl.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def _build_studio_tab(self):
        tab = self.tab_studio

        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        left_controls = ctk.CTkFrame(container, fg_color="transparent")
        left_controls.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_preview = ctk.CTkFrame(container, fg_color="transparent")
        right_preview.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right_preview, text="🎬 9:16 Canlı Video & Filigran Önizleme", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", pady=(0, 4))
        
        # 9:16 Vertical Video Preview Container
        preview_box = ctk.CTkFrame(right_preview, fg_color="transparent")
        preview_box.pack(fill="x", pady=(0, 10))

        self.video_preview = VideoPreviewWidget(
            preview_box,
            width=270,
            height=480,
            on_pos_changed=self._on_overlay_pos_changed
        )
        self.video_preview.pack(anchor="center")

        # Studio Downloaded Videos Grid Gallery below player
        self.grid_gallery_studio = VideoGridWidget(right_preview, target_dir=DOWNLOADS_DIR, on_select_video=self._on_grid_select_video)
        self.grid_gallery_studio.pack(fill="both", expand=True, pady=(6, 0))

        lbl_title = ctk.CTkLabel(left_controls, text="🎨 Canlı Önizlemeli Filigran & Logo Stüdyosu", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_title.pack(anchor="w", pady=(0, 8))

        presets_frame = ctk.CTkFrame(left_controls, fg_color="transparent")
        presets_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(presets_frame, text="Hızlı Şablonlar:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 8))
        btn_p1 = ctk.CTkButton(presets_frame, text="📸 Reels", width=80, height=28, font=ctk.CTkFont(size=11), fg_color="#1E293B", hover_color="#334155", command=lambda: self._apply_preset("reels"))
        btn_p1.pack(side="left", padx=2)
        btn_p2 = ctk.CTkButton(presets_frame, text="🎵 TikTok", width=80, height=28, font=ctk.CTkFont(size=11), fg_color="#1E293B", hover_color="#334155", command=lambda: self._apply_preset("tiktok"))
        btn_p2.pack(side="left", padx=2)
        btn_p3 = ctk.CTkButton(presets_frame, text="▶️ Shorts", width=80, height=28, font=ctk.CTkFont(size=11), fg_color="#1E293B", hover_color="#334155", command=lambda: self._apply_preset("shorts"))
        btn_p3.pack(side="left", padx=2)

        # CANVA / TIKTOK STYLE VISUAL BADGES STICKER PICKER CARD
        card_badges = ctk.CTkFrame(left_controls, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_badges.pack(fill="x", pady=4)

        ctk.CTkLabel(card_badges, text="🏷️ Görsel Trend Rozet / Etiket Paketi (Şeffaf Canva/TikTok Stili):", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=14, pady=(8, 4))
        
        badge_buttons_scroll = ctk.CTkScrollableFrame(card_badges, fg_color="transparent", height=90, orientation="horizontal")
        badge_buttons_scroll.pack(fill="x", padx=10, pady=(0, 8))

        btn_no_badge = ctk.CTkButton(
            badge_buttons_scroll,
            text="❌ Yok",
            width=70,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self._select_badge_preset("none")
        )
        btn_no_badge.pack(side="left", padx=4)

        self._badge_ctk_imgs = []  # Keep references
        for b_info in PRESET_BADGES:
            b_id = b_info["id"]
            pil_icon = get_badge_icon_pil(b_id, size=(110, 32))
            ctk_icon = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(110, 32))
            self._badge_ctk_imgs.append(ctk_icon)

            btn = ctk.CTkButton(
                badge_buttons_scroll,
                image=ctk_icon,
                text="",
                width=110,
                height=32,
                fg_color="transparent",
                hover_color="#1E293B",
                command=lambda b=b_id: self._select_badge_preset(b)
            )
            btn.pack(side="left", padx=4)

        # 🎨 TREND ASSET MARKETPLACE WIDGET (Entegrasyon: Görsel Trend Rozet Paketi ALTINDA)
        self.marketplace_widget = AssetMarketplaceWidget(
            left_controls,
            on_apply_asset=self._on_apply_marketplace_asset,
            log_callback=self.log
        )
        self.marketplace_widget.pack(fill="x", pady=6)

        # 7/24 MİZAH DEPOSU LOGO SELECTION CARD
        card_logo = ctk.CTkFrame(left_controls, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_logo.pack(fill="x", pady=4)

        self.chk_logo = ctk.CTkCheckBox(card_logo, text="🎭 '7/24 Mizah Deposu' / Özel Logo Ekle", font=ctk.CTkFont(size=12, weight="bold"), border_color=COLOR_PRIMARY, command=self._trigger_live_preview)
        self.chk_logo.pack(anchor="w", padx=14, pady=(8, 4))
        self.chk_logo.select()

        # Preset logo buttons row
        preset_logo_row = ctk.CTkFrame(card_logo, fg_color="transparent")
        preset_logo_row.pack(fill="x", padx=14, pady=2)

        ctk.CTkLabel(preset_logo_row, text="Kanal Logosu:", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))

        btn_l_trans = ctk.CTkButton(preset_logo_row, text="✨ Şeffaf", width=75, height=26, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#334155", hover_color="#475569", command=lambda: self._select_logo_preset("logo_724mizah_transparent.png"))
        btn_l_trans.pack(side="left", padx=2)

        btn_l_dark = ctk.CTkButton(preset_logo_row, text="⬛ Siyah", width=75, height=26, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#1E293B", hover_color="#334155", command=lambda: self._select_logo_preset("logo_724mizah_dark.png"))
        btn_l_dark.pack(side="left", padx=2)

        btn_l_light = ctk.CTkButton(preset_logo_row, text="⬜ Beyaz", width=75, height=26, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#475569", hover_color="#64748B", command=lambda: self._select_logo_preset("logo_724mizah_light.png"))
        btn_l_light.pack(side="left", padx=2)

        logo_file_frame = ctk.CTkFrame(card_logo, fg_color="transparent")
        logo_file_frame.pack(fill="x", padx=14, pady=4)

        default_logo = str(BASE_DIR / "assets" / "logo_724mizah_transparent.png")
        self.entry_logo_path = ctk.CTkEntry(logo_file_frame, placeholder_text="Logo PNG Dosyası (.png)", height=32, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_logo_path.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry_logo_path.insert(0, default_logo)

        self.btn_select_logo = ctk.CTkButton(logo_file_frame, text="📁 Görsel Seç", width=85, height=32, corner_radius=8, fg_color="#334155", hover_color="#475569", command=self._browse_logo)
        self.btn_select_logo.pack(side="right")

        # Logo Scale Slider Row
        logo_scale_row = ctk.CTkFrame(card_logo, fg_color="transparent")
        logo_scale_row.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(logo_scale_row, text="Logo Boyutu / Ölçek:", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.slider_logo_scale = ctk.CTkSlider(logo_scale_row, from_=0.08, to=0.45, number_of_steps=37, width=160, command=lambda _: self._trigger_live_preview())
        self.slider_logo_scale.set(0.22)
        self.slider_logo_scale.pack(side="left", padx=8)

        # BLUR BOX MASK CARD
        card_mask = ctk.CTkFrame(left_controls, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_mask.pack(fill="x", pady=4)

        self.chk_mask = ctk.CTkCheckBox(card_mask, text="Eski Filigranı Kapat (Blur Box Mask)", font=ctk.CTkFont(size=12, weight="bold"), border_color=COLOR_PRIMARY, command=self._trigger_live_preview)
        self.chk_mask.pack(anchor="w", padx=14, pady=(8, 4))
        self.chk_mask.select()

        blur_slider_row = ctk.CTkFrame(card_mask, fg_color="transparent")
        blur_slider_row.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(blur_slider_row, text="Blur Genişliği:", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.slider_blur_w = ctk.CTkSlider(blur_slider_row, from_=0.10, to=0.60, number_of_steps=50, width=100, command=lambda _: self._trigger_live_preview())
        self.slider_blur_w.set(0.35)
        self.slider_blur_w.pack(side="left", padx=4)

        ctk.CTkLabel(blur_slider_row, text="Yüksekliği:", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(6, 0))
        self.slider_blur_h = ctk.CTkSlider(blur_slider_row, from_=0.05, to=0.35, number_of_steps=30, width=100, command=lambda _: self._trigger_live_preview())
        self.slider_blur_h.set(0.12)
        self.slider_blur_h.pack(side="left", padx=4)

        self.entry_text_wm = ctk.CTkEntry(left_controls, placeholder_text="İsteğe Bağlı Yazı Filigranı (ör: @SayfaAdiniz)", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_text_wm.pack(fill="x", pady=4)
        self.entry_text_wm.bind("<KeyRelease>", lambda _: self._trigger_live_preview())

        self.btn_process = ctk.CTkButton(
            left_controls,
            text="✨ Videoyu İşle ve Yüksek Kalitede Kaydet",
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            corner_radius=10,
            command=self._start_process_thread
        )
        self.btn_process.pack(fill="x", pady=(8, 4))

        self.progress_process = ctk.CTkProgressBar(left_controls, mode="indeterminate", height=6, corner_radius=3)
        self.progress_process.pack(fill="x", pady=(2, 4))
        self.progress_process.set(0)

    def _build_queue_tab(self):
        tab = self.tab_queue

        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(10, 5))

        lbl_title = ctk.CTkLabel(
            header_frame,
            text="🚀 Sosyal Medya Otomatik Paylaşım & İndirilen Videolar Kuyruğu",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        lbl_title.pack(side="left")

        # -------------------------------------------------------------
        # PLATFORM SELECTION CHECKBOX BAR (Yan yana yükleme platform seçimi)
        # -------------------------------------------------------------
        card_platforms = ctk.CTkFrame(tab, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_platforms.pack(fill="x", padx=10, pady=(5, 8))

        plat_header = ctk.CTkFrame(card_platforms, fg_color="transparent")
        plat_header.pack(fill="x", padx=14, pady=(8, 4))

        lbl_plat = ctk.CTkLabel(
            plat_header,
            text="🎯 Otomatik Yüklenecek Platformları Seçin:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        lbl_plat.pack(side="left")

        lbl_plat_hint = ctk.CTkLabel(
            plat_header,
            text="• Sadece seçili işaretli platformlara otomatik paylaşım yapılır.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        lbl_plat_hint.pack(side="right")

        plat_row = ctk.CTkFrame(card_platforms, fg_color="transparent")
        plat_row.pack(fill="x", padx=14, pady=(0, 10))

        self.chk_platform_ig = ctk.CTkCheckBox(
            plat_row, text="📸 Instagram", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#E1306C", fg_color="#E1306C", hover_color="#C13584"
        )
        self.chk_platform_ig.pack(side="left", padx=(0, 15))
        self.chk_platform_ig.select()  # Default Instagram selected

        self.chk_platform_yt = ctk.CTkCheckBox(
            plat_row, text="▶️ YouTube", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FF0000", fg_color="#FF0000", hover_color="#CC0000"
        )
        self.chk_platform_yt.pack(side="left", padx=(0, 15))

        self.chk_platform_tt = ctk.CTkCheckBox(
            plat_row, text="🎵 TikTok", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00F2FE", fg_color="#00F2FE", hover_color="#00C4D8"
        )
        self.chk_platform_tt.pack(side="left", padx=(0, 15))

        self.chk_platform_th = ctk.CTkCheckBox(
            plat_row, text="🧵 Threads", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#E2E8F0", fg_color="#475569", hover_color="#334155"
        )
        self.chk_platform_th.pack(side="left", padx=(0, 15))

        self.chk_platform_fb = ctk.CTkCheckBox(
            plat_row, text="📘 Facebook", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1877F2", fg_color="#1877F2", hover_color="#166FE5"
        )
        self.chk_platform_fb.pack(side="left")

        # Full height video grid widget dedicated purely to processed/ videos
        self.grid_gallery_processed = VideoGridWidget(
            tab,
            target_dir=PROCESSED_DIR,
            on_select_video=self._on_grid_select_video,
            on_upload_video=self._on_upload_video_single
        )
        self.grid_gallery_processed.pack(fill="both", expand=True, padx=10, pady=(5, 10))


    def _build_api_tab(self):
        tab = self.tab_api
        self.tab_api_keys = ApiKeysTab(tab, log_callback=self.log)
        self.tab_api_keys.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_settings_tab(self):
        tab = self.tab_settings

        lbl_title = ctk.CTkLabel(tab, text="⚙️ Sistem Ayarları & Otomatik Güncelleme", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_title.pack(anchor="w", padx=20, pady=(15, 5))

        card_folders = ctk.CTkFrame(tab, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_folders.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(card_folders, text="📂 Çıktı Klasörleri Hızlı Erişim", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=16, pady=(12, 6))

        folder_btns = ctk.CTkFrame(card_folders, fg_color="transparent")
        folder_btns.pack(fill="x", padx=16, pady=(0, 14))

        btn_open_proc = ctk.CTkButton(folder_btns, text="📁 İşlenen Videolar (processed/)", fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, font=ctk.CTkFont(weight="bold"), height=36, corner_radius=8, command=lambda: self._open_folder(PROCESSED_DIR))
        btn_open_proc.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_open_dl = ctk.CTkButton(folder_btns, text="📁 İndirilen Videolar (downloads/)", fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(weight="bold"), height=36, corner_radius=8, command=lambda: self._open_folder(DOWNLOADS_DIR))
        btn_open_dl.pack(side="right", fill="x", expand=True, padx=(6, 0))

        card_upd = ctk.CTkFrame(tab, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_upd.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(card_upd, text="🔄 GitHub Otomatik Güncelleme Bilgisi", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=16, pady=(12, 6))
        ctk.CTkLabel(card_upd, text=f"Mevcut Yüklü Sürüm: v{APP_VERSION}\nDepo: bkara87/VidDownUPload", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED, justify="left").pack(anchor="w", padx=16, pady=(0, 12))

        # ───────────────────────────────────
        # VIDEO KALİTE SEÇİM KARTI
        # ───────────────────────────────────
        card_quality = ctk.CTkFrame(tab, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_quality.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(card_quality, text="🎥 İşleme Video Kalitesi", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=16, pady=(12, 4))

        quality_desc = (
            "• 🚀 Hızlı (Düşük CPU): ultrafast preset, CRF 23, 128k ses — en hızlı, biraz daha düşük kalite\n"
            "• ✨ Yüksek Kalite (Varsayılan): slow preset, CRF 18, 192k ses — Instagram/TikTok optimal\n"
            "• 🏆 Maksimum Kalite: veryslow preset, CRF 16, 256k ses — en yüksek kalite, çok yavaş"
        )
        ctk.CTkLabel(card_quality, text=quality_desc, font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED, justify="left").pack(anchor="w", padx=16, pady=(0, 8))

        quality_row = ctk.CTkFrame(card_quality, fg_color="transparent")
        quality_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(quality_row, text="Video Kalitesi:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 12))

        from src.processor.ffmpeg_utils import QUALITY_PRESETS, DEFAULT_QUALITY
        self.opt_quality = ctk.CTkOptionMenu(
            quality_row,
            values=list(QUALITY_PRESETS.keys()),
            font=ctk.CTkFont(size=12, weight="bold"),
            width=220,
            height=36,
            fg_color="#1E293B",
            button_color="#334155",
            button_hover_color="#475569",
            command=self._on_quality_change
        )
        self.opt_quality.set(DEFAULT_QUALITY)
        self.opt_quality.pack(side="left")

    def _on_quality_change(self, quality_label: str):
        """Kalite seçimi değiştiğinde processor'u günceller."""
        self.processor.set_quality(quality_label)
        self.log(f"🎥 Video kalitesi değiştirildi: {quality_label}")

    def _auto_fetch_info_delay(self):
        """Debounced URL info fetch — waits 800ms after last keystroke before firing."""
        # Cancel any pending fetch
        if self._fetch_info_after_id is not None:
            try:
                self.after_cancel(self._fetch_info_after_id)
            except Exception:
                pass
            self._fetch_info_after_id = None

        url = self.entry_url.get().strip()
        if len(url) > 15 and ("http://" in url or "https://" in url):
            # Schedule fetch after 800ms of inactivity
            self._fetch_info_after_id = self.after(
                800,
                lambda u=url: threading.Thread(target=self._fetch_info_task, args=(u,), daemon=True).start()
            )

    def _fetch_info_task(self, url):
        # URL önbelleği: aynı URL için yt-dlp'yi tekrar çalıştırma
        if url in self._url_info_cache:
            cached = self._url_info_cache[url]
            if cached:
                self.after(0, lambda: self._show_video_info_card(cached))
            return

        info = VideoInfoFetcher.fetch_video_info(url)
        # Önbelleğe kaydet (hata da olsa — None da kaydedilir, tekrar denemez)
        self._url_info_cache[url] = info
        if info:
            self.after(100, lambda: self._show_video_info_card(info))

    def _show_video_info_card(self, info):
        self.lbl_video_title.configure(text=info.get('title', 'Video')[:50])
        self.lbl_video_uploader.configure(text=f"Kanal / Yükleyen: {info.get('uploader', '-')}")
        self.lbl_video_duration.configure(text=f"Süre: {info.get('duration_str', '-')} | Platform: {info.get('platform', '-')}")

        thumb_url = info.get('thumbnail_url')
        if thumb_url:
            img = VideoInfoFetcher.load_thumbnail_image(thumb_url, size=(140, 78))
            if img:
                self._thumb_photo = ctk.CTkImage(light_image=img, dark_image=img, size=(140, 78))
                self.lbl_thumb.configure(image=self._thumb_photo, text="")

        self.card_info.pack(fill="x", padx=20, pady=(0, 10))

    def _scan_profile_async(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen bir profil veya kanal URL'si girin!")
            return
        self.log(f"Profil videoları hesapsız taranıyor: {url}")
        self.progress_download.start()
        self.equalizer.start_animation()
        threading.Thread(target=self._scan_profile_task, args=(url,), daemon=True).start()

    def _scan_profile_task(self, url):
        items = VideoInfoFetcher.fetch_profile_videos(url, limit=300)
        self.after(100, lambda: self._render_profile_results(items))

    def _render_profile_results(self, items):
        self.progress_download.stop()
        self.equalizer.stop_animation()
        
        # Clear profile scroll frame
        for widget in self.frame_profile_results.winfo_children():
            widget.destroy()

        if not items:
            self.log("❌ Profil videoları bulunamadı veya bağlantı gizli.")
            messagebox.showinfo("Bilgi", "Hesapsız açık video veya reels bulunamadı.")
            return

        self.log(f"✅ Toplam {len(items)} adet açık Reels/video bulundu.")
        self.frame_profile_results.pack(fill="x", padx=10, pady=(0, 10))

        # Top Bar for Batch Downloading
        top_bar = ctk.CTkFrame(self.frame_profile_results, fg_color="#0F172A", corner_radius=10)
        top_bar.pack(fill="x", pady=(0, 6))

        lbl_res_header = ctk.CTkLabel(top_bar, text=f"🎉 Profilde Bulunan Reels/Videolar ({len(items)} Adet):", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_res_header.pack(side="left", padx=10, pady=6)

        btn_batch_dl = ctk.CTkButton(
            top_bar,
            text="⚡ TÜM REELS'LERİ İNDİR (TOPLU)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            height=30,
            command=lambda: self._batch_download_profile_reels(items)
        )
        btn_batch_dl.pack(side="right", padx=8, pady=4)

        self.scroll_profile = ctk.CTkScrollableFrame(self.frame_profile_results, fg_color="#0B101D", corner_radius=12, height=270, orientation="horizontal")
        self.scroll_profile.pack(fill="x", expand=True)

        # Non-blocking async batch widget creation (20 cards per tick)
        self._render_profile_cards_chunked(items, index=0, chunk_size=20)

    def _render_profile_cards_chunked(self, items, index, chunk_size=20):
        end = min(index + chunk_size, len(items))
        for i in range(index, end):
            card = self._create_found_reel_card(self.scroll_profile, items[i])
            card.pack(side="left", padx=5, pady=6)

        if end < len(items):
            self.after(15, lambda: self._render_profile_cards_chunked(items, end, chunk_size))

    def _create_found_reel_card(self, parent, item):
        v_url = item.get('url', '')
        already_dl = self.downloader.is_already_downloaded(v_url)

        card = ctk.CTkFrame(
            parent,
            fg_color="#0D1322",
            corner_radius=10,
            border_width=1,
            border_color="#1E293B",
            width=135
        )

        lbl_thumb = ctk.CTkLabel(card, text="🎬 9:16 Reel", width=120, height=213, fg_color="#1E293B", corner_radius=8)
        lbl_thumb.pack(padx=6, pady=(6, 4))

        # Asynchronously load thumbnail image in background without blocking UI
        thumb_url = item.get('thumbnail_url')
        if thumb_url:
            def load_bg():
                pil_img = VideoInfoFetcher.load_thumbnail_image(thumb_url, size=(120, 213))
                if pil_img and card.winfo_exists():
                    try:
                        ctk_thumb = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(120, 213))
                        self.after(0, lambda: lbl_thumb.configure(image=ctk_thumb, text=""))
                    except Exception:
                        pass
            threading.Thread(target=load_bg, daemon=True).start()

        title_display = item.get('title', 'Reel Video')
        if len(title_display) > 22:
            title_display = title_display[:20] + "..."

        lbl_title = ctk.CTkLabel(
            card,
            text=title_display,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLOR_SUCCESS if already_dl else COLOR_TEXT_MAIN,
            wraplength=125,
            justify="left"
        )
        lbl_title.pack(anchor="w", padx=6, pady=(1, 4))

        btn_dl = ctk.CTkButton(
            card,
            text="✅ İndirildi" if already_dl else "⚡ İndir",
            height=24,
            fg_color="#1E293B" if already_dl else COLOR_PRIMARY,
            hover_color="#334155" if already_dl else COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=lambda u=v_url: self._select_profile_url_and_download(u)
        )
        btn_dl.pack(fill="x", padx=6, pady=(0, 6))

        return card

    def _batch_download_profile_reels(self, items):
        if not items:
            return
        total = len(items)
        self.log(f"⚡ Toplu indirme başlatılıyor: Toplam {total} adet reel kuyruğa alındı...")
        self.btn_download.configure(state="disabled", text=f"⏳ Toplu İndiriliyor (0/{total})...")
        self.progress_download.start()
        self.equalizer.start_animation()

        def task():
            success_count = 0
            skip_count = 0
            for idx, item in enumerate(items, 1):
                url = item.get('url')
                if not url:
                    continue

                title = item.get('title', 'Reel Video')[:35]
                if self.downloader.is_already_downloaded(url):
                    skip_count += 1
                    self.log(f"[{idx}/{total}] ⏩ Zaten var, atlanıyor: {title}")
                    continue

                self.log(f"[{idx}/{total}] 📥 İndiriliyor: {title}...")
                try:
                    # download_video() returns a file path string (or None), not a dict
                    res = self.downloader.download_video(url)
                    if res and os.path.exists(res):
                        success_count += 1
                        fn = os.path.basename(res)
                        self.log(f"[{idx}/{total}] ✓ Başarıyla indirildi: {fn}")
                        self.after(50, self.grid_gallery_dl.refresh_grid)
                    else:
                        self.log(f"[{idx}/{total}] ⚠️ İndirme başarısız veya dosya bulunamadı.")
                except Exception as e:
                    self.log(f"[{idx}/{total}] ❌ İndirme hatası: {e}")

            self.after(100, lambda: self._on_batch_complete(success_count, skip_count, total))

        threading.Thread(target=task, daemon=True).start()

    def _on_batch_complete(self, success_count, skip_count, total):
        self.progress_download.stop()
        self.progress_download.set(0)
        self.equalizer.stop_animation()
        self.btn_download.configure(state="normal", text="⚡ Videoyu Yüksek Kalitede İndir")
        self.grid_gallery_dl.refresh_grid()
        if hasattr(self, 'grid_gallery_studio'):
            self.grid_gallery_studio.refresh_grid()
        self.log(f"🎉 TOPLU İNDİRME TAMAMLANDI! Toplam: {total} | Yeni İndirilen: {success_count} | Zaten Var Olan: {skip_count}")
        messagebox.showinfo("Toplu İndirme Tamamlandı", f"🎉 Toplam {total} adet video işlendi!\n\n✅ Yeni İndirilen: {success_count}\n⏩ Zaten Var Olan: {skip_count}")

    def _select_profile_url_and_download(self, url):
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, url)
        self._start_download_thread()

    def _select_logo_preset(self, filename: str):
        logo_path = str(BASE_DIR / "assets" / filename)
        self.entry_logo_path.delete(0, "end")
        self.entry_logo_path.insert(0, logo_path)
        self._trigger_live_preview()
        self.log(f"🎭 Kanal Logosu seçildi: {filename}")

    def _select_badge_preset(self, badge_id: str):
        self.selected_badge_preset = badge_id
        self._trigger_live_preview()
        self.log(f"🏷️ Trend Görsel Rozet Seçildi: {badge_id}")

    def _on_apply_marketplace_asset(self, asset_path: str):
        if asset_path and os.path.exists(asset_path):
            self.entry_logo_path.delete(0, "end")
            self.entry_logo_path.insert(0, asset_path)
            self.chk_logo.select()
            self._trigger_live_preview()
            self.log(f"🎨 Trend Asset canlı stüdyoya eklendi: {os.path.basename(asset_path)}")

    def _on_overlay_pos_changed(self, lx, ly, bx, by):
        pass

    def _on_grid_select_video(self, video_path: str):
        if video_path and os.path.exists(video_path):
            self.downloaded_video_path = video_path
            self.video_preview.load_video(video_path)
            self._trigger_live_preview()
            self.tabview.set("🎨 Canlı Önizleme & Filigran Stüdyosu")
            self.log(f"🎬 Video stüdyo canlı oyuncusuna yüklendi: {os.path.basename(video_path)}")

    def _trigger_live_preview(self):
        if hasattr(self, 'video_preview'):
            logo_scale = self.slider_logo_scale.get() if hasattr(self, 'slider_logo_scale') else 0.22
            blur_w = self.slider_blur_w.get() if hasattr(self, 'slider_blur_w') else 0.35
            blur_h = self.slider_blur_h.get() if hasattr(self, 'slider_blur_h') else 0.12

            self.video_preview.update_settings(
                mask_enabled=self.chk_mask.get(),
                logo_enabled=self.chk_logo.get(),
                logo_path=self.entry_logo_path.get().strip(),
                text_wm=self.entry_text_wm.get().strip() if hasattr(self, 'entry_text_wm') else None,
                badge_preset=self.selected_badge_preset,
                logo_scale=logo_scale,
                blur_w=blur_w,
                blur_h=blur_h
            )

    def log(self, text: str):
        self.txt_log.insert("end", f"{text}\n")
        self.txt_log.see("end")

    def _clear_log(self):
        self.txt_log.delete("1.0", "end")

    def _paste_clipboard(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.entry_url.delete(0, "end")
                self.entry_url.insert(0, clipboard_text.strip())
                self._auto_fetch_info_delay()
        except Exception:
            pass

    def _open_folder(self, path):
        try:
            os.startfile(str(path))
        except Exception as e:
            messagebox.showerror("Hata", f"Klasör açılamadı:\n{e}")

    def _apply_preset(self, preset_name):
        if preset_name == "reels":
            self.chk_mask.select()
            self.chk_logo.select()
            self._select_logo_preset("logo_724mizah_transparent.png")
            self.selected_badge_preset = "trending"
            self.log("✅ Instagram Reels şablonu uygulandı.")
        elif preset_name == "tiktok":
            self.chk_mask.select()
            self.chk_logo.select()
            self._select_logo_preset("logo_724mizah_dark.png")
            self.selected_badge_preset = "viral"
            self.log("✅ TikTok şablonu uygulandı.")
        elif preset_name == "shorts":
            self.chk_mask.select()
            self.chk_logo.select()
            self._select_logo_preset("logo_724mizah_light.png")
            self.selected_badge_preset = "daily_shorts"
            self.log("✅ YouTube Shorts şablonu uygulandı.")
        self.tabview.set("🎨 Canlı Önizleme & Filigran Stüdyosu")
        self._trigger_live_preview()

    def _browse_logo(self):
        filename = filedialog.askopenfilename(title="Logo PNG Dosyası Seç", filetypes=[("Görsel Dosyaları", "*.png *.jpg *.jpeg")])
        if filename:
            self.entry_logo_path.delete(0, "end")
            self.entry_logo_path.insert(0, filename)
            self._trigger_live_preview()

    def _start_download_thread(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir video URL'si girin!")
            return
        self.btn_download.configure(state="disabled", text="⏳ İndiriliyor...")
        self.progress_download.start()
        self.equalizer.start_animation()
        threading.Thread(target=self._download_task, args=(url,), daemon=True).start()

    def _download_task(self, url: str):
        self.log(f"İndirme başlatılıyor: {url}")
        try:
            path = self.downloader.download_video(url, progress_callback=lambda d: self.log(f"Durum: {d.get('status')} - {d.get('_percent_str', '')}"))
            if path:
                self.downloaded_video_path = path
                self.log(f"✅ İndirme Tamamlandı! Dosya: {os.path.basename(path)}")
                messagebox.showinfo("Başarılı", f"Video başarıyla indirildi:\n{os.path.basename(path)}")
                self.after(100, lambda: self._load_downloaded_preview(path))
            else:
                self.log("❌ İndirme başarısız veya dosya yolu alınamadı.")
        except Exception as e:
            self.log(f"❌ Hata: {e}")
        finally:
            self.progress_download.stop()
            self.progress_download.set(0)
            self.equalizer.stop_animation()
            self.btn_download.configure(state="normal", text="⚡ Videoyu Yüksek Kalitede İndir")

    def _load_downloaded_preview(self, video_path):
        self.grid_gallery_dl.refresh_grid()
        if hasattr(self, 'grid_gallery_studio'):
            self.grid_gallery_studio.refresh_grid()
        self.video_preview.load_video(video_path)
        self._trigger_live_preview()
        self.tabview.set("🎨 Canlı Önizleme & Filigran Stüdyosu")

    def _start_process_thread(self):
        if not self.downloaded_video_path or not os.path.exists(self.downloaded_video_path):
            messagebox.showwarning("Uyarı", "Lütfen önce bir video indirin veya dosya yolunu doğrulayın!")
            return
        self.btn_process.configure(state="disabled", text="⏳ İşleniyor...")
        self.progress_process.start()
        self.equalizer.start_animation()
        threading.Thread(target=self._process_task, daemon=True).start()

    def _process_task(self):
        out_name = f"processed_{os.path.basename(self.downloaded_video_path)}"
        out_path = str(PROCESSED_DIR / out_name)
        self.log(f"Video işleme başlatılıyor -> {out_name}")

        logo_path = self.entry_logo_path.get().strip() if self.chk_logo.get() else None
        text_wm = self.entry_text_wm.get().strip() or None

        logo_rel_pos = (self.video_preview.logo_rel_x, self.video_preview.logo_rel_y)
        blur_rel_pos = (self.video_preview.blur_rel_x, self.video_preview.blur_rel_y, self.video_preview.blur_rel_w, self.video_preview.blur_rel_h)

        success = self.processor.process_video(
            input_path=self.downloaded_video_path,
            output_path=out_path,
            watermark_logo_path=logo_path,
            logo_scale=self.video_preview.logo_scale,
            text_watermark=text_wm,
            badge_preset=self.selected_badge_preset,
            logo_rel_pos=logo_rel_pos if self.chk_logo.get() else None,
            blur_rel_pos=blur_rel_pos if self.chk_mask.get() else None,
            quality_label=getattr(self, 'opt_quality', None) and self.opt_quality.get() or None
        )

        if success:
            self.log(f"🎉 Video Başarıyla İşlendi ve Kaydedildi:\n{out_path}")
            if hasattr(self, 'grid_gallery_dl'):
                self.grid_gallery_dl.refresh_grid()
            if hasattr(self, 'grid_gallery_studio'):
                self.grid_gallery_studio.refresh_grid()
            if hasattr(self, 'grid_gallery_processed'):
                self.grid_gallery_processed.refresh_grid()

            self.after(200, lambda: self.tabview.set("🚀 Sosyal Medya Paylaşım Kuyruğu"))
            messagebox.showinfo("İşlem Tamamlandı", f"🎉 Video başarıyla işlendi ve Paylaşım Kuyruğuna kaydedildi!\n\nOtomatik Yükleme sekmesine yönlendirildiniz:\n{os.path.basename(out_path)}")
        else:
            self.log("❌ Video işleme sırasında FFmpeg hatası oluştu.")

        self.progress_process.stop()
        self.progress_process.set(0)
        self.equalizer.stop_animation()
        self.btn_process.configure(state="normal", text="✨ Videoyu İşle ve Yüksek Kalitede Kaydet")

    def _on_upload_video_single(self, video_path: str):
        fn = os.path.basename(video_path)

        # Retrieve selected checkbox states
        selected_platforms = {
            "instagram": bool(getattr(self, 'chk_platform_ig', None) and self.chk_platform_ig.get()),
            "youtube": bool(getattr(self, 'chk_platform_yt', None) and self.chk_platform_yt.get()),
            "tiktok": bool(getattr(self, 'chk_platform_tt', None) and self.chk_platform_tt.get()),
            "threads": bool(getattr(self, 'chk_platform_th', None) and self.chk_platform_th.get()),
            "facebook": bool(getattr(self, 'chk_platform_fb', None) and self.chk_platform_fb.get())
        }

        active_names = [k.capitalize() for k, v in selected_platforms.items() if v]
        if not active_names:
            messagebox.showwarning("Platform Seçilmedi", "Lütfen en az bir sosyal medya platformu kutucuğunu işaretleyin (örn. 📸 Instagram)!")
            return

        self.log(f"🚀 SOSYAL MEDYA OTOMATİK PAYLAŞIM BAŞLATILDI: {fn}")
        self.log(f"🎯 Hedef Platformlar: {', '.join(active_names)}")
        self.equalizer.start_animation()

        def upload_bg():
            try:
                from src.uploader.social_uploader import SocialUploaderManager
                results = SocialUploaderManager.process_upload(
                    video_path=video_path,
                    selected_platforms=selected_platforms,
                    log_callback=self.log
                )

                ig_res = results.get("instagram")
                if ig_res:
                    if ig_res.get("success"):
                        self.after(0, lambda: messagebox.showinfo("Başarılı", f"🎉 Video Instagram Reel olarak başarıyla paylaşıldı!\n\nDosya: {fn}"))
                    else:
                        err_msg = ig_res.get("message", "Bilinmeyen hata")
                        self.after(0, lambda: messagebox.showerror("Instagram Paylaşım Hatası", f"{err_msg}"))
                else:
                    self.after(0, lambda: messagebox.showinfo("İşlem Tamamlandı", f"🎉 Seçili platformlar için işlem tamamlandı:\n\n{', '.join(active_names)}"))
            except Exception as e:
                self.log(f"❌ Paylaşım sırasında hata: {e}")
                self.after(0, lambda: messagebox.showerror("Hata", f"Yükleme sırasında hata oluştu:\n{e}"))
            finally:
                self.equalizer.stop_animation()

        threading.Thread(target=upload_bg, daemon=True).start()


    def _check_for_updates_async(self):
        self.btn_update.configure(state="disabled", text="Denetleniyor...")
        threading.Thread(target=self._update_task, daemon=True).start()

    def _update_task(self):
        self.log("GitHub üzerinden güncelleme denetimi yapılıyor...")
        has_update, new_ver, dl_url = self.updater.check_for_updates()
        if has_update and dl_url:
            self.log(f"🚀 Yeni sürüm bulundu: v{new_ver}")
            ans = messagebox.askyesno("Güncelleme Mevcut", f"Yeni bir güncelleme mevcut (v{new_ver}). Şimdi indirip otomatik yüklemek ister misiniz?")
            if ans:
                self.log("Güncelleme paketi indiriliyor ve kurulum başlatılıyor...")
                def on_progress(p):
                    self.log(f"Güncelleme İndiriliyor: %{int(p*100)}")
                
                success = self.updater.download_and_install_update(dl_url, progress_callback=on_progress)
                if success:
                    self.log("✅ Güncelleme indirildi, kurulum başlatılıyor...")
                    self.after(200, self.destroy)
        else:
            self.log(f"✅ Uygulamanız en güncel sürümde (v{APP_VERSION}).")
            messagebox.showinfo("Güncel", f"Uygulamanız güncel (v{APP_VERSION})!")

        self.btn_update.configure(state="normal", text="🔄 Sürüm Kontrol Et")

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
