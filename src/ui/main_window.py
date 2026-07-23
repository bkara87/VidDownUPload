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
from src.ui.api_keys_tab import ApiKeysTab
from src.ui.equalizer_widget import AnimatedEqualizerWidget
from src.ui.styles import (
    COLOR_BG_DARK, COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_WARNING, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_TEXT_ACCENT, COLOR_INPUT_BG, COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_TAB_BG
)

# Enforce Windows AppUserModelID BEFORE any Tk root window initializes
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BURAKKARABULUT87.VidDownUPload.App.1.0.2")
except Exception:
    pass

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} Studio v{APP_VERSION} - Live Video Preview & Public Profile Browser")
        self.geometry("1140x880")
        self.minsize(1020, 740)
        self.configure(fg_color=COLOR_BG_DARK)

        self.downloader = VideoDownloader(str(DOWNLOADS_DIR))
        self.processor = VideoProcessor()
        self.updater = GitHubUpdater()
        self.downloaded_video_path = None
        self._app_icon_photo = None
        self._thumb_photo = None

        self._force_window_icon()
        self._build_ui()

    def _force_window_icon(self):
        icon_ico = BASE_DIR / "assets" / "icon.ico"
        icon_png = BASE_DIR / "assets" / "icon.png"

        try:
            import customtkinter as ctk_lib
            import shutil
            ctk_icon = Path(ctk_lib.__file__).parent / "assets" / "icons" / "CustomTkinter_icon_Windows.ico"
            if icon_ico.exists() and ctk_icon.exists():
                shutil.copy2(icon_ico, ctk_icon)
        except Exception:
            pass

        try:
            if icon_ico.exists():
                self.iconbitmap(default=str(icon_ico))
                self.wm_iconbitmap(str(icon_ico))
        except Exception:
            pass

        try:
            if icon_png.exists():
                img = Image.open(icon_png).resize((64, 64), Image.Resampling.LANCZOS)
                self._app_icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._app_icon_photo)
        except Exception:
            pass

        def apply_win32():
            try:
                import ctypes
                user32 = ctypes.windll.user32
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010

                hwnd = self.winfo_id()
                parent_hwnd = user32.GetParent(hwnd)
                target_hwnd = parent_hwnd if parent_hwnd else hwnd

                hicon_big = user32.LoadImageW(0, str(icon_ico), IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                hicon_small = user32.LoadImageW(0, str(icon_ico), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

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

    def _build_ui(self):
        # 1. TOP HEADER BAR
        header = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=16, border_width=1, border_color=COLOR_CARD_BORDER)
        header.pack(fill="x", padx=20, pady=(15, 10))

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", padx=18, pady=12)

        icon_png_path = BASE_DIR / "assets" / "icon.png"
        if icon_png_path.exists():
            try:
                pil_icon = Image.open(icon_png_path)
                header_logo = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(48, 48))
                lbl_logo = ctk.CTkLabel(header_left, image=header_logo, text="")
                lbl_logo.pack(side="left", padx=(0, 14))
            except Exception:
                pass

        title_box = ctk.CTkFrame(header_left, fg_color="transparent")
        title_box.pack(side="left")

        title_sub_frame = ctk.CTkFrame(title_box, fg_color="transparent")
        title_sub_frame.pack(anchor="w")

        lbl_title = ctk.CTkLabel(
            title_sub_frame,
            text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        lbl_title.pack(side="left", padx=(0, 10))

        lbl_badge = ctk.CTkLabel(
            title_sub_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FFFFFF",
            fg_color=COLOR_PRIMARY,
            corner_radius=8,
            width=55,
            height=22
        )
        lbl_badge.pack(side="left")

        lbl_subtitle = ctk.CTkLabel(
            title_box,
            text="Instagram • YouTube • TikTok Hesapsız Video Tarayıcı, Live Studio & Auto Publisher",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        lbl_subtitle.pack(anchor="w", pady=(2, 0))

        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.pack(side="right", padx=18, pady=12)

        self.btn_update = ctk.CTkButton(
            header_right,
            text="🔄 Sürüm Kontrol Et",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(weight="bold"),
            corner_radius=10,
            height=38,
            command=self._check_for_updates_async
        )
        self.btn_update.pack(side="right")

        # 2. TABBED NAVIGATION VIEW
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLOR_CARD_BG,
            segmented_button_fg_color=COLOR_TAB_BG,
            segmented_button_selected_color=COLOR_PRIMARY,
            segmented_button_selected_hover_color=COLOR_PRIMARY_HOVER,
            segmented_button_unselected_color=COLOR_TAB_BG,
            segmented_button_unselected_hover_color="#1E293B",
            corner_radius=16,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.tab_download = self.tabview.add("📥 Video İndirici & Profil Tarayıcı")
        self.tab_studio = self.tabview.add("🎨 Canlı Önizleme & Filigran Stüdyosu")
        self.tab_api = self.tabview.add("🚀 Otomatik Paylaşım & API Yönetimi")
        self.tab_settings = self.tabview.add("⚙️ Ayarlar & Sistem")

        self._build_download_tab()
        self._build_studio_tab()
        self._build_api_tab()
        self._build_settings_tab()

        # 3. BOTTOM LIVE LOG TERMINAL BAR WITH EQUALIZER ANIMATION
        log_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        log_frame.pack(fill="x", padx=20, pady=(0, 15))

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(8, 4))

        lbl_log = ctk.CTkLabel(log_header, text="📋 Canlı İşlem Günlüğü & Ses/Video Dalga Formu", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_log.pack(side="left")

        btn_clear_log = ctk.CTkButton(log_header, text="Temizle", width=65, height=22, font=ctk.CTkFont(size=11), fg_color="#334155", hover_color="#475569", command=self._clear_log)
        btn_clear_log.pack(side="right")

        # Dynamic Moving Equalizer Waveform Widget
        self.equalizer = AnimatedEqualizerWidget(log_frame, num_bars=24, height=18)
        self.equalizer.pack(fill="x", padx=14, pady=(0, 4))

        self.txt_log = ctk.CTkTextbox(
            log_frame,
            height=75,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#070B12",
            text_color="#A7F3D0",
            corner_radius=8,
            border_width=1,
            border_color="#1E293B"
        )
        self.txt_log.pack(fill="x", padx=14, pady=(0, 10))
        self.log(f"[{APP_NAME} v{APP_VERSION}] Sistem hazır. Bir video veya sayfa/profil bağlantısı girin.")

    def _build_download_tab(self):
        tab = self.tab_download

        lbl_title = ctk.CTkLabel(tab, text="📥 Video İndirme & Hesapsız Profil Tarayıcı", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_title.pack(anchor="w", padx=20, pady=(15, 2))

        lbl_desc = ctk.CTkLabel(tab, text="Video bağlantısı veya Instagram/YouTube/TikTok sayfa/profil linki yapıştırın (Giriş yapmanız gerekmez).", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED)
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 12))

        # URL Input Row with Paste & Scan Profile Buttons
        url_frame = ctk.CTkFrame(tab, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.entry_url = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://www.youtube.com/@sayfa veya video bağlantısı...",
            height=46,
            corner_radius=10,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_CARD_BORDER,
            font=ctk.CTkFont(size=13)
        )
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_url.bind("<KeyRelease>", lambda _: self._auto_fetch_info_delay())

        btn_paste = ctk.CTkButton(
            url_frame,
            text="📋 Yapıştır",
            width=90,
            height=46,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(weight="bold"),
            command=self._paste_clipboard
        )
        btn_paste.pack(side="right", padx=(0, 6))

        btn_scan = ctk.CTkButton(
            url_frame,
            text="🔍 Hesapsız Profili Tara",
            width=150,
            height=46,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(weight="bold"),
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
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            corner_radius=12,
            command=self._start_download_thread
        )
        self.btn_download.pack(fill="x", padx=20, pady=(0, 8))

        self.progress_download = ctk.CTkProgressBar(tab, mode="indeterminate", height=8, corner_radius=4)
        self.progress_download.pack(fill="x", padx=20, pady=(0, 10))
        self.progress_download.set(0)

        # PROFILE VIDEOS SCROLLABLE CONTAINER
        self.frame_profile_results = ctk.CTkFrame(tab, fg_color="transparent")
        self.frame_profile_results.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.frame_profile_results.pack_forget()

        lbl_res_header = ctk.CTkLabel(self.frame_profile_results, text="📋 Hesapsız Bulunan Sayfa Videoları (Tıklayıp İndirin):", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_res_header.pack(anchor="w", pady=(0, 4))

        self.scroll_profile = ctk.CTkScrollableFrame(self.frame_profile_results, fg_color="#0B101D", corner_radius=12, height=160)
        self.scroll_profile.pack(fill="both", expand=True)

    def _build_studio_tab(self):
        tab = self.tab_studio

        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        left_controls = ctk.CTkFrame(container, fg_color="transparent")
        left_controls.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_preview = ctk.CTkFrame(container, fg_color="transparent")
        right_preview.pack(side="right", fill="both", expand=False)

        ctk.CTkLabel(right_preview, text="🎬 Canlı Video & Filigran Önizleme", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", pady=(0, 6))
        self.video_preview = VideoPreviewWidget(right_preview, width=440, height=360)
        self.video_preview.pack(fill="both", expand=True)

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

        card_mask = ctk.CTkFrame(left_controls, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_mask.pack(fill="x", pady=4)

        self.chk_mask = ctk.CTkCheckBox(card_mask, text="Eski Filigranı Kapat (Blur Box)", font=ctk.CTkFont(size=12, weight="bold"), border_color=COLOR_PRIMARY, command=self._trigger_live_preview)
        self.chk_mask.pack(anchor="w", padx=14, pady=(8, 4))
        self.chk_mask.select()

        mask_options = ctk.CTkFrame(card_mask, fg_color="transparent")
        mask_options.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(mask_options, text="Maskeleme Konumu:", text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=11)).pack(side="left")
        self.combo_mask_pos = ctk.CTkComboBox(
            mask_options,
            values=["Sağ Alt (Instagram/TikTok)", "Sol Üst", "Sağ Üst", "Sol Alt"],
            dropdown_fg_color=COLOR_CARD_BG,
            corner_radius=8,
            width=180,
            command=lambda _: self._trigger_live_preview()
        )
        self.combo_mask_pos.pack(side="left", padx=8)

        card_logo = ctk.CTkFrame(left_controls, fg_color="#0B101D", corner_radius=12, border_width=1, border_color="#1E293B")
        card_logo.pack(fill="x", pady=4)

        self.chk_logo = ctk.CTkCheckBox(card_logo, text="Kendi Logonuzu / Görseli Ekle", font=ctk.CTkFont(size=12, weight="bold"), border_color=COLOR_PRIMARY, command=self._trigger_live_preview)
        self.chk_logo.pack(anchor="w", padx=14, pady=(8, 4))
        self.chk_logo.select()

        logo_file_frame = ctk.CTkFrame(card_logo, fg_color="transparent")
        logo_file_frame.pack(fill="x", padx=14, pady=2)

        self.entry_logo_path = ctk.CTkEntry(logo_file_frame, placeholder_text="Logo PNG Dosyası (.png)", height=34, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_logo_path.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_select_logo = ctk.CTkButton(logo_file_frame, text="📁 Görsel Seç", width=90, height=34, corner_radius=8, fg_color="#334155", hover_color="#475569", command=self._browse_logo)
        self.btn_select_logo.pack(side="right")

        logo_options = ctk.CTkFrame(card_logo, fg_color="transparent")
        logo_options.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(logo_options, text="Logo Konumu:", text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=11)).pack(side="left")
        self.combo_logo_pos = ctk.CTkComboBox(
            logo_options,
            values=["Sağ Alt", "Sol Üst", "Sağ Üst", "Sol Alt", "Orta"],
            dropdown_fg_color=COLOR_CARD_BG,
            corner_radius=8,
            width=140,
            command=lambda _: self._trigger_live_preview()
        )
        self.combo_logo_pos.pack(side="left", padx=8)

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

    def _build_api_tab(self):
        self.tab_api_keys = ApiKeysTab(self.tab_api, log_callback=self.log)
        self.tab_api_keys.pack(fill="both", expand=True)

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
        ctk.CTkLabel(card_upd, text=f"Mevcut Yüklü Sürüm: v{APP_VERSION}\nDepo: BURAKKARABULUT87/VidDownUPload", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED, justify="left").pack(anchor="w", padx=16, pady=(0, 12))

    def _auto_fetch_info_delay(self):
        url = self.entry_url.get().strip()
        if len(url) > 15 and ("http://" in url or "https://" in url):
            threading.Thread(target=self._fetch_info_task, args=(url,), daemon=True).start()

    def _fetch_info_task(self, url):
        info = VideoInfoFetcher.fetch_video_info(url)
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
        items = VideoInfoFetcher.fetch_profile_videos(url, limit=8)
        self.after(100, lambda: self._render_profile_results(items))

    def _render_profile_results(self, items):
        self.progress_download.stop()
        self.equalizer.stop_animation()
        for widget in self.scroll_profile.winfo_children():
            widget.destroy()

        if not items:
            self.log("❌ Profil videoları bulunamadı veya bağlantı gizli.")
            messagebox.showinfo("Bilgi", "Hesapsız açık video bulunamadı.")
            return

        self.log(f"✅ {len(items)} adet açık video bulundu (Giriş yapmadan).")
        self.frame_profile_results.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for item in items:
            row = ctk.CTkFrame(self.scroll_profile, fg_color="#151C2C", corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)

            lbl_name = ctk.CTkLabel(row, text=item.get('title', 'Video')[:55], font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
            lbl_name.pack(side="left", padx=10, pady=8, fill="x", expand=True)

            btn_dl = ctk.CTkButton(
                row,
                text="⚡ İndir",
                width=75,
                height=28,
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda u=item.get('url'): self._select_profile_url_and_download(u)
            )
            btn_dl.pack(side="right", padx=6)

    def _select_profile_url_and_download(self, url):
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, url)
        self._start_download_thread()

    def _trigger_live_preview(self):
        if hasattr(self, 'video_preview'):
            self.video_preview.update_preview(
                mask_enabled=self.chk_mask.get(),
                mask_pos=self.combo_mask_pos.get(),
                logo_enabled=self.chk_logo.get(),
                logo_path=self.entry_logo_path.get().strip(),
                logo_pos=self.combo_logo_pos.get(),
                text_wm=self.entry_text_wm.get().strip()
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
            self.combo_mask_pos.set("Sağ Alt (Instagram/TikTok)")
            self.chk_logo.select()
            self.combo_logo_pos.set("Sağ Alt")
            self.log("✅ Instagram Reels şablonu uygulandı.")
        elif preset_name == "tiktok":
            self.chk_mask.select()
            self.combo_mask_pos.set("Sağ Alt (Instagram/TikTok)")
            self.chk_logo.select()
            self.combo_logo_pos.set("Sağ Üst")
            self.log("✅ TikTok şablonu uygulandı.")
        elif preset_name == "shorts":
            self.chk_mask.select()
            self.combo_mask_pos.set("Sol Üst")
            self.chk_logo.select()
            self.combo_logo_pos.set("Sol Üst")
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

        blur_box = None
        if self.chk_mask.get():
            blur_box = (10, 10, 150, 60)

        logo_path = self.entry_logo_path.get().strip() if self.chk_logo.get() else None
        pos_str = self.combo_logo_pos.get().lower().replace(" ", "_")
        pos_key_map = {"sağ_alt": "bottom_right", "sol_üst": "top_left", "sağ_üst": "top_right", "sol_alt": "bottom_left", "orta": "center"}
        logo_pos = pos_key_map.get(pos_str, "bottom_right")
        text_wm = self.entry_text_wm.get().strip() or None

        success = self.processor.process_video(
            input_path=self.downloaded_video_path,
            output_path=out_path,
            blur_box=blur_box,
            watermark_logo_path=logo_path,
            logo_position=logo_pos,
            text_watermark=text_wm
        )

        if success:
            self.log(f"🎉 İşlem Tamamlandı! Kaydedilen Dosya:\n{out_path}")
            messagebox.showinfo("Tamamlandı", f"Video başarıyla işlendi ve kaydedildi:\n{out_path}")
        else:
            self.log("❌ Video işleme sırasında FFmpeg hatası oluştu.")

        self.progress_process.stop()
        self.progress_process.set(0)
        self.equalizer.stop_animation()
        self.btn_process.configure(state="normal", text="✨ Videoyu İşle ve Yüksek Kalitede Kaydet")

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
