import os
import sys
import shutil
import winreg
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_NAME = "VidDownUPload"

class UninstallerWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} Kaldırma Sihirbazı")
        self.geometry("520x300")
        self.resizable(False, False)
        self.configure(fg_color="#0F172A")

        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=0, height=70)
        header.pack(fill="x")

        lbl_title = ctk.CTkLabel(
            header,
            text=f"🗑️ {APP_NAME} Uygulamasını Kaldır",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#F8FAFC"
        )
        lbl_title.pack(anchor="w", padx=25, pady=(15, 2))

        lbl_sub = ctk.CTkLabel(
            header,
            text="Bu işlem uygulamayı ve oluşturulan tüm kısayolları bilgisayarınızdan kaldıracaktır.",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        lbl_sub.pack(anchor="w", padx=25, pady=(0, 15))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=25, pady=20)

        self.lbl_msg = ctk.CTkLabel(
            body,
            text=f"{APP_NAME} uygulamasını ve tüm bileşenlerini kaldırmak istediğinizden emin misiniz?",
            font=ctk.CTkFont(size=13),
            wraplength=460,
            text_color="#E2E8F0"
        )
        self.lbl_msg.pack(anchor="w", pady=(10, 15))

        bottom_frame = ctk.CTkFrame(self, fg_color="#1E293B", height=60, corner_radius=0)
        bottom_frame.pack(fill="x", side="bottom")

        self.btn_cancel = ctk.CTkButton(
            bottom_frame,
            text="Vazgeç",
            fg_color="#475569",
            hover_color="#334155",
            width=100,
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(10, 25), pady=12)

        self.btn_uninstall = ctk.CTkButton(
            bottom_frame,
            text="Kaldır",
            fg_color="#EF4444",
            hover_color="#DC2626",
            width=120,
            font=ctk.CTkFont(weight="bold"),
            command=self._start_uninstall
        )
        self.btn_uninstall.pack(side="right", pady=12)

    def _start_uninstall(self):
        try:
            # 1. Remove Desktop shortcut
            desktop_lnk = Path(os.environ.get("USERPROFILE", ".")) / "Desktop" / f"{APP_NAME}.lnk"
            if desktop_lnk.exists():
                desktop_lnk.unlink()

            # 2. Remove Start Menu shortcut
            start_lnk = Path(os.environ.get("APPDATA", ".")) / r"Microsoft\Windows\Start Menu\Programs" / f"{APP_NAME}.lnk"
            if start_lnk.exists():
                start_lnk.unlink()

            # 3. Remove Windows Uninstall Registry key
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + APP_NAME
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_path)
            except Exception:
                pass

            # 4. Schedule directory removal after exit via CMD batch script
            curr_dir = Path(__file__).parent.parent.parent if getattr(sys, 'frozen', False) else Path(sys.argv[0]).parent
            cmd_script = f'''@echo off
timeout /t 2 /nobreak > nul
rmdir /s /q "{curr_dir}"
'''
            bat_path = Path(os.environ.get("TEMP", ".")) / "clean_viddownupload.bat"
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(cmd_script)

            subprocess.Popen(["cmd.exe", "/c", str(bat_path)], creationflags=subprocess.CREATE_NO_WINDOW)

            messagebox.showinfo("Kaldırıldı", f"{APP_NAME} bilgisayarınızdan başarıyla kaldırıldı!")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Hata", f"Kaldırma işlemi sırasında bir hata oluştu:\n{e}")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    app = UninstallerWindow()
    app.mainloop()
