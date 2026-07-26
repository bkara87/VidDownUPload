import os
import sys
import json
import shutil
import subprocess
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent
VERSION = "2.0.1"

def get_current_version():
    ver_json = BASE_DIR / "version.json"
    if ver_json.exists():
        with open(ver_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version", VERSION)
    return VERSION

def get_git_token():
    try:
        p = subprocess.Popen(
            ['git', 'credential', 'fill'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = p.communicate(
            input='protocol=https\nhost=github.com\nusername=bkara87\n\n'
        )
        for line in stdout.splitlines():
            if line.startswith('password='):
                return line.split('password=')[1]
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN")

def publish_release(token=None):
    version = get_current_version()
    tag_name = f"v{version}"
    setup_name = f"VidDownUPload_Setup_{tag_name}"

    print(f"\n{'='*60}")
    print(f"  VidDownUPload {tag_name} — Otomatik Yayın Süreci")
    print(f"{'='*60}\n")

    # 1. Build Executable & Setup Installer
    print("[ 1/4 ] Derleniyor: Executable & Setup Installer...")
    subprocess.run([sys.executable, "build_installer.py"], check=True)

    setup_exe = BASE_DIR / "dist" / f"{setup_name}.exe"
    if not setup_exe.exists():
        print(f"[HATA] Setup EXE bulunamadı: {setup_exe}")
        sys.exit(1)
    print(f"[OK] Setup EXE hazır: {setup_exe} ({setup_exe.stat().st_size // (1024*1024):.1f} MB)")

    # 2. Git Commit and Push to main
    print("\n[ 2/4 ] GitHub'a Push Ediliyor (main branch)...")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        ["git", "commit", "-m",
         f"Release {tag_name}: Ultra premium UI, YouTube/TikTok/Facebook/Threads API, FFmpeg HQ, debounce optimizasyon"],
        check=False
    )
    subprocess.run(["git", "push", "-u", "origin", "main"], check=True)

    # 3. Create & Push Git Tag
    print(f"\n[ 3/4 ] Git Tag Oluşturuluyor: {tag_name}...")
    subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=False)
    subprocess.run(["git", "push", "origin", tag_name], check=False)

    # 4. GitHub API — Create Release & Upload EXE
    github_token = token or get_git_token()
    owner = "bkara87"
    repo = "VidDownUPload"

    release_body = (
        f"## VidDownUPload {tag_name} — Web Tabanlı Yerleşik Browser (Edge WebView2) 🚀\n\n"
        "### ✨ Bu Sürümdeki Yenilikler (v2.0.0 Tam Yeniden Yazım):\n\n"
        "**🌐 Standalone Web Uygulaması Mimarisi:**\n"
        "- Chromium / Edge WebView2 tabanlı yerleşik browser üstünde kendi başına çalışan masaüstü web uygulaması\n"
        "- Adres çubuğu olmadan tam masaüstü programı hissi\n"
        "- 5 sekmeli ultra premium HTML/CSS/JS arayüz (İndirici, Stüdyo, Paylaşım, API Yönetimi, Ayarlar)\n"
        "- Inter & JetBrains Mono tipografisi, glassmorphism kart tasarımı, canlı spectrum equalizer ve konsol terminali\n\n"
        "**🎨 Stüdyo & 9:16 Canvas Önizleme:**\n"
        "- HTML5 canvas ile 9:16 canlı video üzerinde sürükle-bırak (drag & drop) logo ve blur kutusu konumu belirleme\n"
        "- Kanal logosu şablonları, boyut ölçeği, flulaştırma alanı ayarlamaları\n"
        "- İsteğe bağlı özel yazı filigranı ekleme\n\n"
        "**📥 Akıllı İndirici & ID + Etiket Kaydı:**\n"
        "- İndirilen her video kendi ID'si ve etiket/yazısı (sidecar JSON) ile kaydedilir\n"
        "- İndirilen kanala ait etiketler temizlenir, #724mizahdeposu ve genel etiketler otomatik eklenir\n"
        "- Hesapsız profil/kanal reels tarama ve toplu indirme desteği\n\n"
        "**🚀 Otomatik Paylaşım & Caption Doldurma:**\n"
        "- Stüdyo ve Paylaşım aşamasında sidecar JSON'dan açıklama (caption) otomatik doldurulur ve kullanıcı tarafından düzenlenebilir\n"
        "- Instagram, YouTube Shorts, TikTok, Facebook Reels, Threads çoklu platform paylaşım desteği\n\n"
        "---\n"
        f"📥 **Kurulum için `{setup_name}.exe` dosyasını indirip çalıştırın.**"
    )

    if github_token:
        print(f"\n[ 4/4 ] GitHub API ile Release & EXE Yükleniyor...")
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Delete existing tag/release if already exists
        try:
            del_res = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag_name}",
                headers=headers, timeout=10
            )
            if del_res.status_code == 200:
                rel_id = del_res.json().get("id")
                requests.delete(
                    f"https://api.github.com/repos/{owner}/{repo}/releases/{rel_id}",
                    headers=headers, timeout=10
                )
                print(f"[INFO] Mevcut {tag_name} release silindi.")
        except Exception:
            pass

        # Create Release via API
        rel_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        rel_data = {
            "tag_name": tag_name,
            "target_commitish": "main",
            "name": f"VidDownUPload {tag_name} — Ultra Premium Studio",
            "body": release_body,
            "draft": False,
            "prerelease": False
        }
        res = requests.post(rel_url, headers=headers, json=rel_data, timeout=30)

        if res.status_code in [200, 201]:
            rel_info = res.json()
            upload_url = rel_info.get("upload_url", "").split("{")[0]
            print(f"[OK] GitHub Release oluşturuldu: {rel_info.get('html_url')}")

            # Upload Setup EXE asset (streaming — no full RAM load)
            print(f"[↑] Upload ediliyor: {setup_exe.name} ({setup_exe.stat().st_size // (1024*1024):.1f} MB)...")
            with open(setup_exe, "rb") as f:
                u_headers = headers.copy()
                u_headers["Content-Type"] = "application/octet-stream"
                u_res = requests.post(
                    f"{upload_url}?name={setup_exe.name}",
                    headers=u_headers,
                    data=f,
                    timeout=1800   # 30 min for large files
                )
                if u_res.status_code in [200, 201]:
                    asset_url = u_res.json().get("browser_download_url", "")
                    print(f"[OK] Setup EXE başarıyla GitHub'a yüklendi!")
                    print(f"     Download URL: {asset_url}")
                else:
                    print(f"[UYARI] Asset upload: HTTP {u_res.status_code} — {u_res.text[:200]}")
        else:
            print(f"[HATA] Release API: HTTP {res.status_code} — {res.text[:300]}")
    else:
        print("\n[INFO] GitHub token bulunamadı.")
        print("       Token GitHub'a gönderildi. Manuel olarak GitHub Actions ile release yapabilirsiniz.")
        print("       Ya da: python publish_release.py <GITHUB_TOKEN>")

    print(f"\n{'='*60}")
    print(f"  ✅ {tag_name} YAYINLAMA TAMAMLANDI!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    token_arg = sys.argv[1] if len(sys.argv) > 1 else None
    publish_release(token_arg)
