import os
import sys
import shutil
import zipfile
import winreg
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def get_current_version():
    try:
        base = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent.parent.parent
        v_json = base / "version.json"
        if v_json.exists():
            with open(v_json, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "2.0.1")
    except Exception:
        pass
    return "2.0.1"

APP_NAME = "VidDownUPload"
APP_VERSION = get_current_version()
PUBLISHER = "bkara87"

DEFAULT_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\Public")) / APP_NAME

def create_shortcut(target_path, shortcut_path, icon_path=None, description=""):
    """Create Windows .lnk shortcut using VBScript"""
    vbs_script = f'''
    Set WshShell = CreateObject("WScript.Shell")
    Set shortcut = WshShell.CreateShortcut("{shortcut_path}")
    shortcut.TargetPath = "{target_path}"
    shortcut.WorkingDirectory = "{Path(target_path).parent}"
    shortcut.Description = "{description}"
    '''
    if icon_path and os.path.exists(icon_path):
        vbs_script += f'\nshortcut.IconLocation = "{icon_path}"'
    vbs_script += '\nshortcut.Save'

    temp_vbs = Path(os.environ.get("TEMP", ".")) / "create_shortcut.vbs"
    with open(temp_vbs, "w", encoding="utf-8") as f:
        f.write(vbs_script)
    
    subprocess.run(["cscript", "//Nologo", str(temp_vbs)], capture_output=True, shell=True)
    if temp_vbs.exists():
        temp_vbs.unlink()

def register_uninstaller(install_dir, exe_path, uninstaller_path, icon_path):
    """Register application in Windows Add/Remove Programs (Programs and Features)"""
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + APP_NAME
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, f"{APP_NAME} - Video İndirici & Filigran Düzenleyici")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(icon_path))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_path}"')
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Registry error: {e}")

class SetupWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} Kurulum Sihirbazı (v{APP_VERSION})")
        self.geometry("580x420")
        self.resizable(False, False)
        self.configure(fg_color="#0F172A")

        self.install_dir_var = tk.StringVar(value=str(DEFAULT_INSTALL_DIR))
        self.chk_desktop_var = tk.BooleanVar(value=True)
        self.chk_start_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        # Header Banner
        header = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=0, height=80)
        header.pack(fill="x")

        lbl_title = ctk.CTkLabel(
            header,
            text=f"⚡ {APP_NAME} v{APP_VERSION} Kurulumu",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#F8FAFC"
        )
        lbl_title.pack(anchor="w", padx=25, pady=(15, 2))

        lbl_sub = ctk.CTkLabel(
            header,
            text="Video İndirici & Otomatik Filigran Düzenleme Yazılımı",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        lbl_sub.pack(anchor="w", padx=25, pady=(0, 15))

        # Main Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=25, pady=20)

        # Target Dir Selection
        lbl_dir = ctk.CTkLabel(body, text="Kurulum Dizini:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#E2E8F0")
        lbl_dir.pack(anchor="w", pady=(0, 5))

        dir_frame = ctk.CTkFrame(body, fg_color="transparent")
        dir_frame.pack(fill="x", pady=(0, 15))

        entry_dir = ctk.CTkEntry(dir_frame, textvariable=self.install_dir_var, height=36, corner_radius=8)
        entry_dir.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Checkboxes
        chk_desktop = ctk.CTkCheckBox(body, text="Masaüstü kısayolu oluştur", variable=self.chk_desktop_var)
        chk_desktop.pack(anchor="w", pady=5)

        chk_start = ctk.CTkCheckBox(body, text="Başlat Menüsü kısayolu oluştur", variable=self.chk_start_var)
        chk_start.pack(anchor="w", pady=5)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(body, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(20, 5))
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(
            body,
            text="Kuruluma başlamak için 'Kurulumu Başlat' butonuna basın.",
            text_color="#94A3B8",
            font=ctk.CTkFont(size=12),
            wraplength=520,
            justify="left"
        )
        self.lbl_status.pack(anchor="w", pady=(2, 0))

        # Bottom Buttons
        bottom_frame = ctk.CTkFrame(self, fg_color="#1E293B", height=60, corner_radius=0)
        bottom_frame.pack(fill="x", side="bottom")

        self.btn_install = ctk.CTkButton(
            bottom_frame,
            text="🚀 Kurulumu Başlat",
            fg_color="#0284C7",
            hover_color="#0369A1",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=180,
            corner_radius=8,
            command=self._start_installation
        )
        self.btn_install.pack(side="right", padx=25, pady=10)

    def _safe_extract_zip(self, zip_path, target_dir):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                out_path = Path(target_dir) / member.filename
                if member.is_dir():
                    out_path.mkdir(parents=True, exist_ok=True)
                    continue

                out_path.parent.mkdir(parents=True, exist_ok=True)

                if out_path.exists():
                    try:
                        out_path.unlink()
                    except Exception:
                        try:
                            renamed_bak = out_path.with_name(f"{out_path.name}.old_{int(time.time())}")
                            out_path.rename(renamed_bak)
                        except Exception:
                            pass

                try:
                    with zip_ref.open(member) as source, open(out_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                except Exception as e:
                    print(f"Warning writing file {out_path}: {e}")

    def _start_installation(self):
        install_dir = Path(self.install_dir_var.get().strip())
        self.btn_install.configure(state="disabled", text="Yükleniyor...")
        self.lbl_status.configure(text="Dosyalar kopyalanıyor...")
        self.progress_bar.set(0.2)
        self.update_idletasks()

        try:
            # Terminate any running instance of the app to prevent file lock Permission Denied error
            try:
                if os.name == 'nt':
                    subprocess.run(
                        ['taskkill', '/F', '/IM', f"{APP_NAME}.exe"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=0x08000000
                    )
                    time.sleep(0.5)
            except Exception:
                pass

            install_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract bundled app zip if frozen, or copy from dist/VidDownUPload
            bundle_zip = Path(getattr(sys, '_MEIPASS', '.')) / "app_payload.zip"
            if bundle_zip.exists():
                self._safe_extract_zip(bundle_zip, install_dir)
            else:
                src_dist = Path("dist") / APP_NAME
                if src_dist.exists():
                    shutil.copytree(src_dist, install_dir, dirs_exist_ok=True)

            self.progress_bar.set(0.6)
            self.lbl_status.configure(text="Kısayollar ve kayıt defteri ayarlanıyor...")
            self.update_idletasks()

            exe_path = install_dir / f"{APP_NAME}.exe"
            icon_path = install_dir / "assets" / "icon.ico"
            uninstaller_exe = install_dir / "uninstall.exe"

            # Create Desktop Shortcut
            if self.chk_desktop_var.get():
                desktop_dir = Path(os.environ.get("USERPROFILE", ".")) / "Desktop"
                shortcut_path = desktop_dir / f"{APP_NAME}.lnk"
                create_shortcut(exe_path, shortcut_path, icon_path, f"{APP_NAME} Video İndirici")

            # Create Start Menu Shortcut
            if self.chk_start_var.get():
                start_dir = Path(os.environ.get("APPDATA", ".")) / r"Microsoft\Windows\Start Menu\Programs"
                shortcut_path = start_dir / f"{APP_NAME}.lnk"
                create_shortcut(exe_path, shortcut_path, icon_path, f"{APP_NAME} Video İndirici")

            # Register Windows Uninstaller
            register_uninstaller(install_dir, exe_path, uninstaller_exe, icon_path)

            self.progress_bar.set(1.0)
            self.lbl_status.configure(text="🎉 Kurulum Başarıyla Tamamlandı!")
            
            ans = messagebox.askyesno(
                "Kurulum Tamamlandı",
                f"🎉 {APP_NAME} v{APP_VERSION} başarıyla kuruldu!\n\nUygulamayı şimdi çalıştırmak istiyor musunuz?",
                icon="info"
            )
            if ans:
                try:
                    subprocess.Popen([str(exe_path)])
                except Exception as ex:
                    print(f"Error launching app: {ex}")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Hata", f"Kurulum sırasında bir hata oluştu:\n{e}")
            self.btn_install.configure(state="normal", text="Tekrar Dene")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    app = SetupWindow()
    app.mainloop()
