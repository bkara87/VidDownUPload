import os
import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.config import BASE_DIR
from src.ui.styles import (
    COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_WARNING, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_TEXT_ACCENT, COLOR_INPUT_BG, COLOR_ACCENT
)

KEYS_FILE = BASE_DIR / "config_keys.json"

class ApiKeysTab(ctk.CTkFrame):
    """
    Social Media Auto-Publish & API Keys Configuration Tab with Step-by-Step Guides
    """
    def __init__(self, master, log_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.log_callback = log_callback

        self.show_keys = False
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
            "instagram_account_id": "",
            "instagram_access_token": "",
            "youtube_client_id": "",
            "youtube_api_key": "",
            "tiktok_open_id": "",
            "tiktok_access_token": ""
        }

    def _save_keys(self):
        data = {
            "instagram_account_id": self.entry_ig_id.get().strip(),
            "instagram_access_token": self.entry_ig_token.get().strip(),
            "youtube_client_id": self.entry_yt_id.get().strip(),
            "youtube_api_key": self.entry_yt_key.get().strip(),
            "tiktok_open_id": self.entry_tt_id.get().strip(),
            "tiktok_access_token": self.entry_tt_token.get().strip()
        }
        try:
            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.keys_data = data
            self._update_status_badges()
            if self.log_callback:
                self.log_callback("✅ Sosyal medya API Anahtarları güvenli şekilde kaydedildi.")
            messagebox.showinfo("Başarılı", "API Anahtarları başarıyla kaydedildi!")
        except Exception as e:
            messagebox.showerror("Hata", f"API Anahtarları kaydedilemedi:\n{e}")

    def _build_ui(self):
        # Header
        lbl_title = ctk.CTkLabel(self, text="🚀 Otomatik Paylaşım & Sosyal Medya API Yönetimi", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_title.pack(anchor="w", padx=20, pady=(15, 2))

        lbl_sub = ctk.CTkLabel(self, text="Instagram, YouTube ve TikTok platformlarına otomatik yükleme yapabilmek için API anahtarlarınızı girin.", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", padx=20, pady=(0, 15))

        # Main Scrollable Body
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=12)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # -------------------------------------------------------------
        # 1. INSTAGRAM GRAPH API CARD
        # -------------------------------------------------------------
        card_ig = ctk.CTkFrame(scroll_frame, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        card_ig.pack(fill="x", pady=8)

        ig_head = ctk.CTkFrame(card_ig, fg_color="transparent")
        ig_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(ig_head, text="📸 Instagram Graph API (Reels & Auto-Publish)", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E1306C").pack(side="left")
        self.badge_ig = ctk.CTkLabel(ig_head, text="⚪ Yapılandırılmadı", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8", fg_color="#1E293B", corner_radius=6, padx=8, pady=2)
        self.badge_ig.pack(side="right")

        f_ig_id = ctk.CTkFrame(card_ig, fg_color="transparent")
        f_ig_id.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_ig_id, text="Instagram Account ID:", width=150, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_ig_id = ctk.CTkEntry(f_ig_id, placeholder_text="17841400000000000", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_ig_id.insert(0, self.keys_data.get("instagram_account_id", ""))
        self.entry_ig_id.pack(side="left", fill="x", expand=True)

        f_ig_tok = ctk.CTkFrame(card_ig, fg_color="transparent")
        f_ig_tok.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(f_ig_tok, text="User Access Token:", width=150, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_ig_token = ctk.CTkEntry(f_ig_tok, placeholder_text="EAAG...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_ig_token.insert(0, self.keys_data.get("instagram_access_token", ""))
        self.entry_ig_token.pack(side="left", fill="x", expand=True)

        # Guide Accordion
        guide_ig = ctk.CTkFrame(card_ig, fg_color="#151C2C", corner_radius=10)
        guide_ig.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(guide_ig, text="📖 Instagram API Key / Token Nasıl Alınır?", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            guide_ig,
            text="1. developers.facebook.com adresine gidin ve yeni bir Meta Uygulaması (App) oluşturun.\n"
                 "2. Uygulamanıza 'Instagram Graph API' ürününü ekleyin ve Instagram İşletme Hesabınızı bağlayın.\n"
                 "3. Tools > Graph API Explorer sayfasından 'instagram_basic' ve 'instagram_content_publish' izinlerini seçip Token üretin.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # -------------------------------------------------------------
        # 2. YOUTUBE DATA API v3 CARD
        # -------------------------------------------------------------
        card_yt = ctk.CTkFrame(scroll_frame, fg_color="#0B101D", corner_radius=14, border_width=1, border_color="#1E293B")
        card_yt.pack(fill="x", pady=8)

        yt_head = ctk.CTkFrame(card_yt, fg_color="transparent")
        yt_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(yt_head, text="▶️ YouTube Data API v3 (Shorts & Video Upload)", font=ctk.CTkFont(size=15, weight="bold"), text_color="#FF0000").pack(side="left")
        self.badge_yt = ctk.CTkLabel(yt_head, text="⚪ Yapılandırılmadı", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8", fg_color="#1E293B", corner_radius=6, padx=8, pady=2)
        self.badge_yt.pack(side="right")

        f_yt_id = ctk.CTkFrame(card_yt, fg_color="transparent")
        f_yt_id.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(f_yt_id, text="Channel ID / Client ID:", width=150, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_yt_id = ctk.CTkEntry(f_yt_id, placeholder_text="UCx...", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_yt_id.insert(0, self.keys_data.get("youtube_client_id", ""))
        self.entry_yt_id.pack(side="left", fill="x", expand=True)

        f_yt_key = ctk.CTkFrame(card_yt, fg_color="transparent")
        f_yt_key.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(f_yt_key, text="API Key / Secret:", width=150, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_yt_key = ctk.CTkEntry(f_yt_key, placeholder_text="AIzaSy...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_yt_key.insert(0, self.keys_data.get("youtube_api_key", ""))
        self.entry_yt_key.pack(side="left", fill="x", expand=True)

        # Guide Accordion
        guide_yt = ctk.CTkFrame(card_yt, fg_color="#151C2C", corner_radius=10)
        guide_yt.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(guide_yt, text="📖 YouTube API Key / OAuth Nasıl Alınır?", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            guide_yt,
            text="1. console.cloud.google.com adresine gidin ve yeni bir Google Cloud Projesi açın.\n"
                 "2. 'Library' sekmesinden 'YouTube Data API v3' hizmetini bulun ve 'Enable' deyin.\n"
                 "3. 'Credentials' > 'Create Credentials' > 'API Key' veya 'OAuth 2.0 Client ID' seçip anahtarınızı kopyalayın.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

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
        ctk.CTkLabel(f_tt_id, text="TikTok Open ID:", width=150, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_tt_id = ctk.CTkEntry(f_tt_id, placeholder_text="act.12345...", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_tt_id.insert(0, self.keys_data.get("tiktok_open_id", ""))
        self.entry_tt_id.pack(side="left", fill="x", expand=True)

        f_tt_tok = ctk.CTkFrame(card_tt, fg_color="transparent")
        f_tt_tok.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(f_tt_tok, text="Access Token:", width=150, anchor="w", text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_tt_token = ctk.CTkEntry(f_tt_tok, placeholder_text="act.token...", show="*", height=36, corner_radius=8, fg_color=COLOR_INPUT_BG)
        self.entry_tt_token.insert(0, self.keys_data.get("tiktok_access_token", ""))
        self.entry_tt_token.pack(side="left", fill="x", expand=True)

        # Guide Accordion
        guide_tt = ctk.CTkFrame(card_tt, fg_color="#151C2C", corner_radius=10)
        guide_tt.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(guide_tt, text="📖 TikTok API Key / Token Nasıl Alınır?", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            guide_tt,
            text="1. developers.tiktok.com portalında bir Geliştirici Hesabı açın.\n"
                 "2. 'Manage Apps' kısmından yeni uygulama oluşturup 'Direct Post' (Content Posting API) iznini ekleyin.\n"
                 "3. İzin onayından sonra aldığınız Access Token ve Open ID bilgisini buraya girin.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Bottom Action Bar (Save & Mask Toggle)
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=20, pady=(5, 10))

        self.chk_show_pass = ctk.CTkCheckBox(bottom_bar, text="Anahtarları Gizle/Göster (show/hide)", command=self._toggle_show_keys)
        self.chk_show_pass.pack(side="left")

        btn_save = ctk.CTkButton(
            bottom_bar,
            text="💾 Tüm API Anahtarlarını Kaydet",
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
        self.entry_ig_token.configure(show=show_char)
        self.entry_yt_key.configure(show=show_char)
        self.entry_tt_token.configure(show=show_char)

    def _update_status_badges(self):
        if self.keys_data.get("instagram_access_token"):
            self.badge_ig.configure(text="🟢 Bağlandı", fg_color="#064E3B", text_color="#34D399")
        else:
            self.badge_ig.configure(text="⚪ Yapılandırılmadı", fg_color="#1E293B", text_color="#94A3B8")

        if self.keys_data.get("youtube_api_key"):
            self.badge_yt.configure(text="🟢 Bağlandı", fg_color="#064E3B", text_color="#34D399")
        else:
            self.badge_yt.configure(text="⚪ Yapılandırılmadı", fg_color="#1E293B", text_color="#94A3B8")

        if self.keys_data.get("tiktok_access_token"):
            self.badge_tt.configure(text="🟢 Bağlandı", fg_color="#064E3B", text_color="#34D399")
        else:
            self.badge_tt.configure(text="⚪ Yapılandırılmadı", fg_color="#1E293B", text_color="#94A3B8")
