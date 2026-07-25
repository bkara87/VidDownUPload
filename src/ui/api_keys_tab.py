import os
import json
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.config import BASE_DIR
from src.downloader.instagram_auth import InstagramAuthManager
from src.ui.styles import (
    COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_WARNING, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_TEXT_ACCENT, COLOR_INPUT_BG, COLOR_ACCENT, COLOR_ACCENT_HOVER
)

KEYS_FILE = BASE_DIR / "config_keys.json"

class ApiKeysTab(ctk.CTkFrame):
    """
    Social Media Auto-Publish, Account Logins & API Keys Configuration Tab
    """
    def __init__(self, master, log_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.log_callback = log_callback

        self.auth_manager = InstagramAuthManager(KEYS_FILE)
        self.keys_data = self._load_keys()

        self._build_ui()

    def _load_keys(self):
        if KEYS_FILE.exists():
            try:
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "instagram_auth": {"username": "", "password": "", "sessionid": "", "use_hesapsiz": False},
            "instagram_account_id": "",
            "instagram_access_token": "",
            "youtube_client_id": "",
            "youtube_client_secret": "",
            "youtube_refresh_token": "",
            "youtube_api_key": "",
            "tiktok_open_id": "",
            "tiktok_access_token": "",
            "facebook_page_id": "",
            "threads_user_id": ""
        }

    def _save_keys(self):
        ig_user = self.entry_ig_user.get().strip()
        ig_pass = self.entry_ig_pass.get().strip()
        ig_sess = self.entry_ig_sess.get().strip()
        use_hesapsiz = self.chk_hesapsiz_ig.get()

        self.auth_manager.save_auth_info(username=ig_user, password=ig_pass, sessionid=ig_sess, use_hesapsiz=use_hesapsiz)

        data = {
            "instagram_auth": {
                "username": ig_user,
                "password": ig_pass,
                "sessionid": ig_sess,
                "use_hesapsiz": use_hesapsiz
            },
            "instagram_account_id": self.entry_ig_id.get().strip(),
            "instagram_access_token": self.entry_ig_token.get().strip(),
            "youtube_client_id": self.entry_yt_id.get().strip(),
            "youtube_client_secret": self.entry_yt_secret.get().strip(),
            "youtube_refresh_token": self.entry_yt_refresh.get().strip(),
            "youtube_api_key": self.entry_yt_key.get().strip(),
            "tiktok_open_id": self.entry_tt_id.get().strip(),
            "tiktok_access_token": self.entry_tt_token.get().strip(),
            "facebook_page_id": self.entry_fb_page_id.get().strip(),
            "threads_user_id": self.entry_threads_uid.get().strip()
        }

        try:
            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.keys_data = data
            self._update_status_badges()
            if self.log_callback:
                self.log_callback("✅ Tüm hesap bilgileri ve API anahtarları kaydedildi.")
            messagebox.showinfo("Başarılı", "Hesap bilgileri ve API anahtarları kaydedildi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydedilemedi:\n{e}")

    def _build_ui(self):
        lbl_title = ctk.CTkLabel(self, text="🚀 Sosyal Medya Hesap Girişi & API Yönetimi", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_title.pack(anchor="w", padx=20, pady=(15, 2))

        lbl_sub = ctk.CTkLabel(self, text="İnstagram hesap girişi yapabilir veya isteğe bağlı hesapsız mod ile API anahtarlarınızı kaydedebilirsiniz.", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", padx=20, pady=(0, 15))

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=12)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # -------------------------------------------------------------
        # STEP-BY-STEP API KEYS & ACCOUNT SETUP GUIDE CARD
        # -------------------------------------------------------------
        card_guide = ctk.CTkFrame(scroll_frame, fg_color="#111827", corner_radius=14, border_width=1, border_color="#374151")
        card_guide.pack(fill="x", pady=(0, 10))

        guide_head = ctk.CTkFrame(card_guide, fg_color="transparent")
        guide_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(guide_head, text="📖 Otomatik Paylaşım & API Anahtarları Nasıl Alınır?", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(side="left")

        guide_text = (
            "📌 1. Instagram Graph API (Reels Paylaşımı):\n"
            "   • Meta Developers Portal'ına (developers.facebook.com) gidin -> Yeni Uygulama Oluşturun.\n"
            "   • Instagram Graph API ürününü ekleyin ve Instagram İşletme Hesabınızı bağlayın.\n"
            "   • Access Token ve Instagram Account ID (178414...) değerlerini aşağıdaki kutulara yapıştırın.\n\n"
            "📌 2. YouTube Data API v3 (Shorts & Video Yükleme):\n"
            "   • Google Cloud Console'a (console.cloud.google.com) gidin -> Yeni Proje Oluşturun.\n"
            "   • 'API ve Hizmetler' -> 'YouTube Data API v3' hizmetini etkinleştirin.\n"
            "   • Kimlik Bilgileri kısmından API Anahtarı (API Key) oluşturup aşağıdaki kutuya yapıştırın.\n\n"
            "📌 3. TikTok Content Posting API (Otomatik Paylaşım):\n"
            "   • TikTok Developer Portal'a (developers.tiktok.com) gidin -> Uygulama Tanımlayın.\n"
            "   • 'Content Posting API' iznini açıp Access Token ve Open ID bilgilerinizi kaydedin."
        )

        lbl_guide_body = ctk.CTkLabel(card_guide, text=guide_text, font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED, justify="left", anchor="w")
        lbl_guide_body.pack(fill="x", padx=16, pady=(0, 10))

        btn_row_devs = ctk.CTkFrame(card_guide, fg_color="transparent")
        btn_row_devs.pack(fill="x", padx=16, pady=(0, 12))

        btn_meta_dev = ctk.CTkButton(btn_row_devs, text="🌐 Meta Developer Portal", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#3B82F6", hover_color="#2563EB", height=30, command=lambda: webbrowser.open("https://developers.facebook.com/"))
        btn_meta_dev.pack(side="left", padx=(0, 8))

        btn_google_dev = ctk.CTkButton(btn_row_devs, text="🌐 Google Cloud Console", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#EF4444", hover_color="#DC2626", height=30, command=lambda: webbrowser.open("https://console.cloud.google.com/"))
        btn_google_dev.pack(side="left", padx=(0, 8))

        btn_tt_dev = ctk.CTkButton(btn_row_devs, text="🌐 TikTok Developer Portal", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#06B6D4", hover_color="#0891B2", height=30, command=lambda: webbrowser.open("https://developers.tiktok.com/"))
        btn_tt_dev.pack(side="left")

        # -------------------------------------------------------------
        # 0. INSTAGRAM ACCOUNT LOGIN CARD (Kullanıcı Girişi / Kayıt Ol)
        # -------------------------------------------------------------
        card_ig_auth = ctk.CTkFrame(scroll_frame, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        card_ig_auth.pack(fill="x", pady=8)

        ig_auth_head = ctk.CTkFrame(card_ig_auth, fg_color="transparent")
        ig_auth_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(ig_auth_head, text="🔑 İnstagram Kullanıcı Hesabı Girişi", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E1306C").pack(side="left")
        self.badge_ig_auth = ctk.CTkLabel(ig_auth_head, text="⚪ Hesapsız Mod", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8", fg_color="#1E293B", corner_radius=6, padx=8, pady=2)
        self.badge_ig_auth.pack(side="right")

        ig_info_saved = self.keys_data.get("instagram_auth", {})

        f_ig_u = ctk.CTkFrame(card_ig_auth, fg_color="transparent")
        f_ig_u.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_ig_u, text="İnstagram Kullanıcı Adı:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_ig_user = ctk.CTkEntry(f_ig_u, placeholder_text="kullanici_adiniz", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_ig_user.insert(0, ig_info_saved.get("username", ""))
        self.entry_ig_user.pack(side="left", fill="x", expand=True)

        f_ig_p = ctk.CTkFrame(card_ig_auth, fg_color="transparent")
        f_ig_p.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_ig_p, text="İnstagram Şifresi:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_ig_pass = ctk.CTkEntry(f_ig_p, placeholder_text="••••••••", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_ig_pass.insert(0, ig_info_saved.get("password", ""))
        self.entry_ig_pass.pack(side="left", fill="x", expand=True)

        f_ig_s = ctk.CTkFrame(card_ig_auth, fg_color="transparent")
        f_ig_s.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_ig_s, text="veya sessionid (Çerez):", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_ig_sess = ctk.CTkEntry(f_ig_s, placeholder_text="İsteğe bağlı sessionid çerezi...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_ig_sess.insert(0, ig_info_saved.get("sessionid", ""))
        self.entry_ig_sess.pack(side="left", fill="x", expand=True)

        ig_opts_row = ctk.CTkFrame(card_ig_auth, fg_color="transparent")
        ig_opts_row.pack(fill="x", padx=16, pady=(6, 12))

        self.chk_hesapsiz_ig = ctk.CTkCheckBox(ig_opts_row, text="Hesapsız İndir (Giriş Yapmadan)", font=ctk.CTkFont(size=12))
        if ig_info_saved.get("use_hesapsiz"):
            self.chk_hesapsiz_ig.select()
        self.chk_hesapsiz_ig.pack(side="left")

        btn_register = ctk.CTkButton(
            ig_opts_row,
            text="🌐 İnstagram'da Yeni Hesap Aç (Kayıt Ol)",
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: webbrowser.open("https://www.instagram.com/accounts/emailsignup/")
        )
        btn_register.pack(side="right")

        # -------------------------------------------------------------
        # 1. INSTAGRAM GRAPH API CARD
        # -------------------------------------------------------------
        card_ig = ctk.CTkFrame(scroll_frame, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        card_ig.pack(fill="x", pady=8)

        ig_head = ctk.CTkFrame(card_ig, fg_color="transparent")
        ig_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(ig_head, text="📸 Instagram Graph API (Reels Auto-Publish)", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E1306C").pack(side="left")
        self.badge_ig = ctk.CTkLabel(ig_head, text="⚪ Yapılandırılmadı", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8", fg_color="#1E293B", corner_radius=6, padx=8, pady=2)
        self.badge_ig.pack(side="right")

        f_ig_id = ctk.CTkFrame(card_ig, fg_color="transparent")
        f_ig_id.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_ig_id, text="Instagram Account ID:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_ig_id = ctk.CTkEntry(f_ig_id, placeholder_text="17841400000000000", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_ig_id.insert(0, self.keys_data.get("instagram_account_id", ""))
        self.entry_ig_id.pack(side="left", fill="x", expand=True)

        f_ig_tok = ctk.CTkFrame(card_ig, fg_color="transparent")
        f_ig_tok.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_ig_tok, text="User Access Token:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_ig_token = ctk.CTkEntry(f_ig_tok, placeholder_text="EAAG...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_ig_token.insert(0, self.keys_data.get("instagram_access_token", ""))
        self.entry_ig_token.pack(side="left", fill="x", expand=True)

        f_ig_btn = ctk.CTkFrame(card_ig, fg_color="transparent")
        f_ig_btn.pack(fill="x", padx=16, pady=(4, 12))
        btn_test_ig = ctk.CTkButton(
            f_ig_btn,
            text="⚡ Instagram API Bağlantısını Test Et",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#E1306C",
            hover_color="#C13584",
            height=30,
            command=self._test_instagram_api
        )
        btn_test_ig.pack(side="right")

        # -------------------------------------------------------------
        # 2. YOUTUBE DATA API v3 CARD
        # -------------------------------------------------------------
        card_yt = ctk.CTkFrame(scroll_frame, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        card_yt.pack(fill="x", pady=8)

        yt_head = ctk.CTkFrame(card_yt, fg_color="transparent")
        yt_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(yt_head, text="▶️ YouTube Data API v3", font=ctk.CTkFont(size=15, weight="bold"), text_color="#FF0000").pack(side="left")
        self.badge_yt = ctk.CTkLabel(yt_head, text="⚪ Yapılandırılmadı", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8", fg_color="#1E293B", corner_radius=6, padx=8, pady=2)
        self.badge_yt.pack(side="right")

        f_yt_id = ctk.CTkFrame(card_yt, fg_color="transparent")
        f_yt_id.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_yt_id, text="OAuth2 Client ID:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_yt_id = ctk.CTkEntry(f_yt_id, placeholder_text="123456789-abc.apps.googleusercontent.com", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_yt_id.insert(0, self.keys_data.get("youtube_client_id", ""))
        self.entry_yt_id.pack(side="left", fill="x", expand=True)

        f_yt_secret = ctk.CTkFrame(card_yt, fg_color="transparent")
        f_yt_secret.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_yt_secret, text="OAuth2 Client Secret:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_yt_secret = ctk.CTkEntry(f_yt_secret, placeholder_text="GOCSPX-...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_yt_secret.insert(0, self.keys_data.get("youtube_client_secret", ""))
        self.entry_yt_secret.pack(side="left", fill="x", expand=True)

        f_yt_refresh = ctk.CTkFrame(card_yt, fg_color="transparent")
        f_yt_refresh.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_yt_refresh, text="Refresh Token:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_yt_refresh = ctk.CTkEntry(f_yt_refresh, placeholder_text="1//0g...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_yt_refresh.insert(0, self.keys_data.get("youtube_refresh_token", ""))
        self.entry_yt_refresh.pack(side="left", fill="x", expand=True)

        f_yt_key = ctk.CTkFrame(card_yt, fg_color="transparent")
        f_yt_key.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(f_yt_key, text="API Key (İsteğe bağlı):", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_yt_key = ctk.CTkEntry(f_yt_key, placeholder_text="AIzaSy...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_yt_key.insert(0, self.keys_data.get("youtube_api_key", ""))
        self.entry_yt_key.pack(side="left", fill="x", expand=True)

        yt_note = ctk.CTkLabel(card_yt, text="ℹ️ YouTube Shorts yüklemesi için OAuth2 Client ID + Secret + Refresh Token gereklidir (API Key yeterli değil).\n   Google Cloud Console → OAuth2 İstemci → youtube.upload scope → Token oluşturun.", font=ctk.CTkFont(size=10), text_color="#64748B", justify="left")
        yt_note.pack(anchor="w", padx=16, pady=(0, 12))

        # -------------------------------------------------------------
        # 3. TIKTOK CONTENT POSTING API CARD
        # -------------------------------------------------------------
        card_tt = ctk.CTkFrame(scroll_frame, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        card_tt.pack(fill="x", pady=8)

        tt_head = ctk.CTkFrame(card_tt, fg_color="transparent")
        tt_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(tt_head, text="🎵 TikTok Content Posting API", font=ctk.CTkFont(size=15, weight="bold"), text_color="#00F2FE").pack(side="left")
        self.badge_tt = ctk.CTkLabel(tt_head, text="⚪ Yapılandırılmadı", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8", fg_color="#1E293B", corner_radius=6, padx=8, pady=2)
        self.badge_tt.pack(side="right")

        f_tt_id = ctk.CTkFrame(card_tt, fg_color="transparent")
        f_tt_id.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_tt_id, text="TikTok Open ID:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_tt_id = ctk.CTkEntry(f_tt_id, placeholder_text="act.12345...", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_tt_id.insert(0, self.keys_data.get("tiktok_open_id", ""))
        self.entry_tt_id.pack(side="left", fill="x", expand=True)

        f_tt_tok = ctk.CTkFrame(card_tt, fg_color="transparent")
        f_tt_tok.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(f_tt_tok, text="Access Token:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_tt_token = ctk.CTkEntry(f_tt_tok, placeholder_text="act.token...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_tt_token.insert(0, self.keys_data.get("tiktok_access_token", ""))
        self.entry_tt_token.pack(side="left", fill="x", expand=True)

        # ─────────────────────────────────────────────
        # 4. FACEBOOK PAGE REELS API CARD
        # ─────────────────────────────────────────────
        card_fb = ctk.CTkFrame(scroll_frame, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        card_fb.pack(fill="x", pady=8)

        fb_head = ctk.CTkFrame(card_fb, fg_color="transparent")
        fb_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(fb_head, text="📘 Facebook Page Reels API", font=ctk.CTkFont(size=15, weight="bold"), text_color="#1877F2").pack(side="left")
        self.badge_fb = ctk.CTkLabel(fb_head, text="⚪ Yapılandırılmadı", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8", fg_color="#1E293B", corner_radius=6, padx=8, pady=2)
        self.badge_fb.pack(side="right")

        f_fb_page = ctk.CTkFrame(card_fb, fg_color="transparent")
        f_fb_page.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_fb_page, text="Facebook Page ID:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_fb_page_id = ctk.CTkEntry(f_fb_page, placeholder_text="100000000000000", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_fb_page_id.insert(0, self.keys_data.get("facebook_page_id", ""))
        self.entry_fb_page_id.pack(side="left", fill="x", expand=True)

        fb_note = ctk.CTkLabel(card_fb, text="ℹ️ Facebook Page Access Token olarak Instagram/Meta Access Token kullanılır.\n   Page ID: facebook.com/YourPage → Hakkında → Sayfa Kimliği", font=ctk.CTkFont(size=10), text_color="#64748B", justify="left")
        fb_note.pack(anchor="w", padx=16, pady=(0, 12))

        # ─────────────────────────────────────────────
        # 5. THREADS USER ID CARD
        # ─────────────────────────────────────────────
        card_threads = ctk.CTkFrame(scroll_frame, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        card_threads.pack(fill="x", pady=8)

        th_head = ctk.CTkFrame(card_threads, fg_color="transparent")
        th_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(th_head, text="🧵 Threads API (Meta)", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E2E8F0").pack(side="left")
        self.badge_th = ctk.CTkLabel(th_head, text="⚪ Yapılandırılmadı", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8", fg_color="#1E293B", corner_radius=6, padx=8, pady=2)
        self.badge_th.pack(side="right")

        f_th_uid = ctk.CTkFrame(card_threads, fg_color="transparent")
        f_th_uid.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_th_uid, text="Threads User ID:", width=160, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_threads_uid = ctk.CTkEntry(f_th_uid, placeholder_text="178414... (genellikle Instagram Account ID ile aynı)", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_threads_uid.insert(0, self.keys_data.get("threads_user_id", ""))
        self.entry_threads_uid.pack(side="left", fill="x", expand=True)

        th_note = ctk.CTkLabel(card_threads, text="ℹ️ Threads User ID genellikle Instagram Account ID ile aynıdır.\n   Meta Access Token zaten Instagram token'ı kullanılır — ek token gerekmez.", font=ctk.CTkFont(size=10), text_color="#64748B", justify="left")
        th_note.pack(anchor="w", padx=16, pady=(0, 12))

        # Bottom Action Bar
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=20, pady=(5, 10))

        self.chk_show_pass = ctk.CTkCheckBox(bottom_bar, text="Şifre & Anahtarları Göster/Gizle", command=self._toggle_show_keys)
        self.chk_show_pass.pack(side="left")

        btn_save = ctk.CTkButton(
            bottom_bar,
            text="💾 Tüm Hesap ve API Bilgilerini Kaydet",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            corner_radius=10,
            command=self._save_keys
        )
        btn_save.pack(side="right")

        self._update_status_badges()

    def _toggle_show_keys(self):
        show_char = "" if self.chk_show_pass.get() else "*"
        self.entry_ig_pass.configure(show=show_char)
        self.entry_ig_sess.configure(show=show_char)
        self.entry_ig_token.configure(show=show_char)
        self.entry_yt_secret.configure(show=show_char)
        self.entry_yt_refresh.configure(show=show_char)
        self.entry_yt_key.configure(show=show_char)
        self.entry_tt_token.configure(show=show_char)

    def _update_status_badges(self):
        ig_auth = self.keys_data.get("instagram_auth", {})
        if ig_auth.get("username") or ig_auth.get("sessionid"):
            self.badge_ig_auth.configure(text="🟢 Oturum Kaydedildi", fg_color="#064E3B", text_color="#34D399")
        else:
            self.badge_ig_auth.configure(text="⚪ Hesapsız Mod", fg_color="#1E293B", text_color="#94A3B8")

        if self.keys_data.get("instagram_access_token"):
            self.badge_ig.configure(text="🟢 Bağlandı", fg_color="#064E3B", text_color="#34D399")
        else:
            self.badge_ig.configure(text="⚪ Yapılandırılmadı", fg_color="#1E293B", text_color="#94A3B8")

        if self.keys_data.get("youtube_client_id") and self.keys_data.get("youtube_refresh_token"):
            self.badge_yt.configure(text="🟢 OAuth2 Bağlandı", fg_color="#064E3B", text_color="#34D399")
        elif self.keys_data.get("youtube_api_key"):
            self.badge_yt.configure(text="🟡 API Key (OAuth2 önerilir)", fg_color="#422006", text_color="#FCD34D")
        else:
            self.badge_yt.configure(text="⚪ Yapılandırılmadı", fg_color="#1E293B", text_color="#94A3B8")

        if self.keys_data.get("tiktok_access_token"):
            self.badge_tt.configure(text="🟢 Bağlandı", fg_color="#064E3B", text_color="#34D399")
        else:
            self.badge_tt.configure(text="⚪ Yapılandırılmadı", fg_color="#1E293B", text_color="#94A3B8")

        if hasattr(self, 'badge_fb'):
            if self.keys_data.get("facebook_page_id"):
                self.badge_fb.configure(text="🟢 Bağlandı", fg_color="#064E3B", text_color="#34D399")
            else:
                self.badge_fb.configure(text="⚪ Yapılandırılmadı", fg_color="#1E293B", text_color="#94A3B8")

        if hasattr(self, 'badge_th'):
            if self.keys_data.get("threads_user_id") or self.keys_data.get("instagram_account_id"):
                self.badge_th.configure(text="🟢 Hazır", fg_color="#064E3B", text_color="#34D399")
            else:
                self.badge_th.configure(text="⚪ Yapılandırılmadı", fg_color="#1E293B", text_color="#94A3B8")

    def _test_instagram_api(self):
        acc_id = self.entry_ig_id.get().strip()
        token = self.entry_ig_token.get().strip()

        if not acc_id or not token:
            messagebox.showwarning("Eksik Bilgi", "Lütfen önce Instagram Account ID ve User Access Token kutularını doldurun!")
            return

        def test_bg():
            try:
                import requests
                clean_acc_id = acc_id.strip('"').strip("'")
                clean_token = token.strip('"').strip("'").replace("\n", "").replace("\r", "")
                url = f"https://graph.facebook.com/v23.0/{clean_acc_id}"
                params = {
                    "fields": "id,username,name",
                    "access_token": clean_token
                }
                headers = {
                    "Authorization": f"Bearer {clean_token}"
                }
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                data = resp.json()

                if resp.status_code == 200 and "id" in data:
                    username = data.get("username") or data.get("name") or "Bilinmiyor"
                    name = data.get("name", "")
                    msg = f"🟢 Instagram Graph API v23.0 Bağlantısı Başarılı!\n\n• Hesap ID: {data.get('id')}\n• Kullanıcı Adı: @{username}\n• Sayfa Adı: {name or 'Varsayılan'}"
                    if self.log_callback:
                        self.log_callback(f"✅ Instagram Graph API v23.0 Doğrulandı: @{username}")
                    self.after(0, lambda: messagebox.showinfo("Bağlantı Başarılı", msg))
                else:
                    err_msg = data.get("error", {}).get("message", resp.text)
                    msg = f"❌ Instagram Graph API Bağlantı Hatası:\n\n{err_msg}\n\nLütfen Token ve Account ID bilgilerinizi Meta Developer portalından kontrol edin."
                    if self.log_callback:
                        self.log_callback(f"❌ Instagram Graph API Testi Başarısız: {err_msg}")
                    self.after(0, lambda: messagebox.showerror("Bağlantı Başarısız", msg))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Hata", f"İstek gönderilirken hata oluştu:\n{e}"))


        import threading
        threading.Thread(target=test_bg, daemon=True).start()

