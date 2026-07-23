import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from src.config import APP_NAME, APP_VERSION, DOWNLOADS_DIR, PROCESSED_DIR, BASE_DIR
from src.downloader.downloader import VideoDownloader
from src.processor.ffmpeg_utils import VideoProcessor
from src.updater.github_updater import GitHubUpdater
from src.ui.styles import (
    COLOR_BG_DARK, COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_WARNING, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_TEXT_ACCENT, COLOR_INPUT_BG, COLOR_ACCENT
)

# Set Windows AppUserModelID BEFORE any Tk root window initializes
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BURAKKARABULUT87.VidDownUPload.App.1.0")
except Exception:
    pass

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} - Professional Video Downloader & Watermark Studio (v{APP_VERSION})")
        self.geometry("1020x780")
        self.minsize(920, 680)
        self.configure(fg_color=COLOR_BG_DARK)

        self.downloader = VideoDownloader(str(DOWNLOADS_DIR))
        self.processor = VideoProcessor()
        self.updater = GitHubUpdater()
        self.downloaded_video_path = None
        self._app_icon_photo = None

        # Apply Custom Icon to Window Titlebar & Windows Taskbar
        self._set_window_icon()

        self._build_ui()

    def _set_window_icon(self):
        icon_ico = BASE_DIR / "assets" / "icon.ico"
        icon_png = BASE_DIR / "assets" / "icon.png"

        def apply_icon():
            try:
                if icon_ico.exists():
                    self.iconbitmap(str(icon_ico))
            except Exception as e:
                pass

            try:
                if icon_png.exists():
                    img = Image.open(icon_png).resize((32, 32), Image.Resampling.LANCZOS)
                    self._app_icon_photo = ImageTk.PhotoImage(img)
                    self.iconphoto(True, self._app_icon_photo)
            except Exception as e:
                pass

        apply_icon()
        # Enforce after CustomTkinter initialization finishes
        self.after(200, apply_icon)
        self.after(800, apply_icon)

    def _build_ui(self):
        # Header Bar Container
        header = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        header.pack(fill="x", padx=20, pady=(15, 10))

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", padx=15, pady=12)

        # Header Logo Image
        icon_png_path = BASE_DIR / "assets" / "icon.png"
        if icon_png_path.exists():
            try:
                pil_icon = Image.open(icon_png_path)
                header_logo = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(44, 44))
                lbl_logo = ctk.CTkLabel(header_left, image=header_logo, text="")
                lbl_logo.pack(side="left", padx=(0, 12))
            except Exception:
                pass

        title_box = ctk.CTkFrame(header_left, fg_color="transparent")
        title_box.pack(side="left")

        title_sub_frame = ctk.CTkFrame(title_box, fg_color="transparent")
        title_sub_frame.pack(anchor="w")

        lbl_title = ctk.CTkLabel(
            title_sub_frame,
            text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        lbl_title.pack(side="left", padx=(0, 8))

        lbl_badge = ctk.CTkLabel(
            title_sub_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=COLOR_PRIMARY,
            corner_radius=6,
            width=50,
            height=20
        )
        lbl_badge.pack(side="left")

        lbl_subtitle = ctk.CTkLabel(
            title_box,
            text="Instagram Reels • YouTube Shorts • TikTok Video Downloader & Watermark Studio",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        lbl_subtitle.pack(anchor="w", pady=(2, 0))

        self.btn_update = ctk.CTkButton(
            header,
            text="🔄 Güncelleme Kontrol Et",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(weight="bold"),
            corner_radius=10,
            height=36,
            command=self._check_for_updates_async
        )
        self.btn_update.pack(side="right", padx=15, pady=12)

        # Main Layout Container
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=5)

        # Left Column: Downloader & Processing
        left_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 1. Video Download Card
        card_download = ctk.CTkFrame(left_frame, fg_color=COLOR_CARD_BG, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        card_download.pack(fill="x", pady=(0, 10))

        lbl_dl = ctk.CTkLabel(card_download, text="📥 1. Video Bağlantısı ve İndirme", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_dl.pack(anchor="w", padx=18, pady=(14, 6))

        self.entry_url = ctk.CTkEntry(
            card_download,
            placeholder_text="Video veya Paylaşım Bağlantısını Yapıştırın (Instagram / YouTube / TikTok)",
            height=42,
            corner_radius=10,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_CARD_BORDER,
            font=ctk.CTkFont(size=13)
        )
        self.entry_url.pack(fill="x", padx=18, pady=5)

        dl_btn_frame = ctk.CTkFrame(card_download, fg_color="transparent")
        dl_btn_frame.pack(fill="x", padx=18, pady=(8, 14))

        self.btn_download = ctk.CTkButton(
            dl_btn_frame,
            text="⚡ Videoyu İndir",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            corner_radius=10,
            command=self._start_download_thread
        )
        self.btn_download.pack(side="left", fill="x", expand=True)

        # 2. Watermark & Processing Card
        card_process = ctk.CTkFrame(left_frame, fg_color=COLOR_CARD_BG, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        card_process.pack(fill="both", expand=True, pady=5)

        lbl_proc = ctk.CTkLabel(card_process, text="🎨 2. Filigran Maskeleme & Logo Stüdyosu", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_proc.pack(anchor="w", padx=18, pady=(14, 6))

        # Checkbox: Cover old watermark
        self.chk_mask = ctk.CTkCheckBox(card_process, text="Eski Filigranı Flulaştır / Maskele (Blur Box)", font=ctk.CTkFont(size=13), border_color=COLOR_PRIMARY)
        self.chk_mask.pack(anchor="w", padx=18, pady=6)
        self.chk_mask.select()

        mask_pos_frame = ctk.CTkFrame(card_process, fg_color="transparent")
        mask_pos_frame.pack(fill="x", padx=18, pady=4)
        ctk.CTkLabel(mask_pos_frame, text="Maskeleme Alanı:", text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=12)).pack(side="left")
        self.combo_mask_pos = ctk.CTkComboBox(
            mask_pos_frame,
            values=["Sağ Alt (Instagram/TikTok)", "Sol Üst", "Sağ Üst", "Sol Alt"],
            dropdown_fg_color=COLOR_CARD_BG,
            corner_radius=8,
            width=220
        )
        self.combo_mask_pos.pack(side="left", padx=10)

        # Checkbox & controls: Add custom logo
        self.chk_logo = ctk.CTkCheckBox(card_process, text="Kendi Logo / Filigran Görselinizi Ekle", font=ctk.CTkFont(size=13), border_color=COLOR_PRIMARY)
        self.chk_logo.pack(anchor="w", padx=18, pady=(12, 6))
        self.chk_logo.select()

        logo_file_frame = ctk.CTkFrame(card_process, fg_color="transparent")
        logo_file_frame.pack(fill="x", padx=18, pady=4)

        self.entry_logo_path = ctk.CTkEntry(logo_file_frame, placeholder_text="Logo PNG Görseli Seçin (.png)", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_logo_path.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_select_logo = ctk.CTkButton(logo_file_frame, text="📁 Gözat", width=90, height=36, corner_radius=8, fg_color="#334155", hover_color="#475569", command=self._browse_logo)
        self.btn_select_logo.pack(side="right")

        logo_options_frame = ctk.CTkFrame(card_process, fg_color="transparent")
        logo_options_frame.pack(fill="x", padx=18, pady=6)

        ctk.CTkLabel(logo_options_frame, text="Logo Konumu:", text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=12)).pack(side="left")
        self.combo_logo_pos = ctk.CTkComboBox(
            logo_options_frame,
            values=["Sağ Alt", "Sol Üst", "Sağ Üst", "Sol Alt", "Orta"],
            dropdown_fg_color=COLOR_CARD_BG,
            corner_radius=8,
            width=160
        )
        self.combo_logo_pos.pack(side="left", padx=10)

        # Text Watermark Entry
        self.entry_text_wm = ctk.CTkEntry(card_process, placeholder_text="İsteğe Bağlı Metin Filigranı (ör: @SayfaAdiniz)", height=38, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_text_wm.pack(fill="x", padx=18, pady=(10, 6))

        self.btn_process = ctk.CTkButton(
            card_process,
            text="✨ Filigranı İşle ve Yüksek Kalitede Kaydet",
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            corner_radius=10,
            command=self._start_process_thread
        )
        self.btn_process.pack(fill="x", padx=18, pady=16)

        # Right Column: Publisher info & Console Log
        right_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        card_pub = ctk.CTkFrame(right_frame, fg_color=COLOR_CARD_BG, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        card_pub.pack(fill="x", pady=(0, 10))

        lbl_pub = ctk.CTkLabel(card_pub, text="🚀 3. Otomatik Paylaşım Modülü", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_pub.pack(anchor="w", padx=18, pady=(14, 6))

        pub_info = ctk.CTkLabel(
            card_pub,
            text="ℹ️ Sosyal medya paylaşım modülü pasif tutulmaktadır.\nİşlenen videolar yüksek kalitede 'processed/' klasörüne kaydedilir.",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_ACCENT,
            justify="left"
        )
        pub_info.pack(anchor="w", padx=18, pady=(0, 14))

        # Terminal / Log Box Card
        card_log = ctk.CTkFrame(right_frame, fg_color=COLOR_CARD_BG, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        card_log.pack(fill="both", expand=True, pady=5)

        lbl_log = ctk.CTkLabel(card_log, text="📋 Canlı İşlem Günlüğü / Console", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_log.pack(anchor="w", padx=18, pady=(12, 6))

        self.txt_log = ctk.CTkTextbox(
            card_log,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#090D16",
            text_color="#A7F3D0",
            corner_radius=8,
            border_width=1,
            border_color="#1E293B"
        )
        self.txt_log.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log(f"[{APP_NAME}] Sistem hazır. Lütfen bir video bağlantısı yapıştırın.")

    def log(self, text: str):
        self.txt_log.insert("end", f"{text}\n")
        self.txt_log.see("end")

    def _browse_logo(self):
        filename = filedialog.askopenfilename(title="Logo PNG Dosyası Seç", filetypes=[("Görsel Dosyaları", "*.png *.jpg *.jpeg")])
        if filename:
            self.entry_logo_path.delete(0, "end")
            self.entry_logo_path.insert(0, filename)

    def _start_download_thread(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir video URL'si girin!")
            return
        self.btn_download.configure(state="disabled", text="⏳ İndiriliyor...")
        threading.Thread(target=self._download_task, args=(url,), daemon=True).start()

    def _download_task(self, url: str):
        self.log(f"İndirme başlatılıyor: {url}")
        try:
            path = self.downloader.download_video(url, progress_callback=lambda d: self.log(f"Durum: {d.get('status')} - {d.get('_percent_str', '')}"))
            if path:
                self.downloaded_video_path = path
                self.log(f"✅ İndirme Tamamlandı! Dosya: {os.path.basename(path)}")
                messagebox.showinfo("Başarılı", f"Video başarıyla indirildi:\n{os.path.basename(path)}")
            else:
                self.log("❌ İndirme başarısız veya dosya yolu alınamadı.")
        except Exception as e:
            self.log(f"❌ Hata: {e}")
        finally:
            self.btn_download.configure(state="normal", text="⚡ Videoyu İndir")

    def _start_process_thread(self):
        if not self.downloaded_video_path or not os.path.exists(self.downloaded_video_path):
            messagebox.showwarning("Uyarı", "Lütfen önce bir video indirin veya dosya yolunu doğrulayın!")
            return
        self.btn_process.configure(state="disabled", text="⏳ İşleniyor...")
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

        self.btn_process.configure(state="normal", text="✨ Filigranı İşle ve Yüksek Kalitede Kaydet")

    def _check_for_updates_async(self):
        self.btn_update.configure(state="disabled", text="Denetleniyor...")
        threading.Thread(target=self._update_task, daemon=True).start()

    def _update_task(self):
        self.log("GitHub üzerinden güncelleme denetimi yapılıyor...")
        has_update, new_ver, dl_url = self.updater.check_for_updates()
        if has_update and dl_url:
            self.log(f"🚀 Yeni sürüm bulundu: v{new_ver}")
            ans = messagebox.askyesno("Güncelleme Mevcut", f"Yeni bir güncelleme mevcut (v{new_ver}). Şimdi indirip yüklemek ister misiniz?")
            if ans:
                self.log("Güncelleme indiriliyor...")
                self.updater.download_and_install_update(dl_url, progress_callback=lambda p: self.log(f"İndirme: %{int(p*100)}"))
        else:
            self.log("✅ Uygulamanız en güncel sürümde (v1.0.0).")
            messagebox.showinfo("Güncel", "Uygulamanız güncel!")

        self.btn_update.configure(state="normal", text="🔄 Güncelleme Kontrol Et")

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
