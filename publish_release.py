import os
import sys
import json
import shutil
import subprocess
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent

def get_current_version():
    ver_json = BASE_DIR / "version.json"
    if ver_json.exists():
        with open(ver_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version", "1.0.1")
    return "1.0.1"

def get_git_token():
    try:
        p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, _ = p.communicate(input='protocol=https\nhost=github.com\nusername=BURAKKARABULUT87\n\n')
        for line in stdout.splitlines():
            if line.startswith('password='):
                return line.split('password=')[1]
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN")

def publish_release(token=None):
    version = get_current_version()
    tag_name = f"v{version}"
    print(f"[RELEASE] Automatic Release Publishing Process Starting for {tag_name}...")

    # 1. Build Executable & Setup Installer
    print("\n1. Derleniyor: Executable & Setup Installer...")
    subprocess.run([sys.executable, "build_installer.py"], check=True)

    # 2. Git Commit and Push to main
    print("\n2. GitHub'a Push Ediliyor (main branch)...")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Release {tag_name}"], check=False)
    subprocess.run(["git", "push", "-u", "origin", "main"], check=True)

    # 3. Create & Push Git Tag
    print(f"\n3. Git Tag Oluşturuluyor: {tag_name}...")
    subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=False)
    subprocess.run(["git", "push", "origin", tag_name], check=False)

    # 4. Direct GitHub API Upload
    github_token = token or get_git_token()
    owner = "BURAKKARABULUT87"
    repo = "VidDownUPload"

    if github_token:
        print("\n4. GitHub API ile Otomatik Release ve EXE Yükleniyor...")
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Create Release via API
        rel_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        rel_data = {
            "tag_name": tag_name,
            "target_commitish": "main",
            "name": f"{tag_name} - Otomatik Sürüm Güncellemesi",
            "body": f"VidDownUPload Otomatik Güncelleme Paketi ({tag_name})\n\nYenilikler ve performans güncellemeleri içerir.",
            "draft": False,
            "prerelease": False
        }
        res = requests.post(rel_url, headers=headers, json=rel_data)
        if res.status_code in [200, 201]:
            rel_info = res.json()
            upload_url_template = rel_info.get("upload_url", "")
            upload_url = upload_url_template.split("{")[0]
            
            # Upload Setup EXE asset
            setup_exe = BASE_DIR / "dist" / f"VidDownUPload_Setup_{tag_name}.exe"
            if setup_exe.exists():
                print(f"Uploading {setup_exe.name} asset to GitHub Release...")
                with open(setup_exe, "rb") as f:
                    u_headers = headers.copy()
                    u_headers["Content-Type"] = "application/octet-stream"
                    u_res = requests.post(f"{upload_url}?name={setup_exe.name}", headers=u_headers, data=f)
                    if u_res.status_code in [200, 201]:
                        print("[OK] Setup EXE asset uploaded successfully to GitHub!")
                    else:
                        print(f"Asset upload status: {u_res.status_code}")
        else:
            print(f"Release API Status: {res.status_code}")
    else:
        print("\n[INFO] Tag GitHub'a gonderildi. GitHub Actions otomatik olarak Release ve EXE ekleyecektir!")

    print("\n==========================================")
    print(f"[OK] {tag_name} OTOMATIK YAYINLAMA TAMAMLANDI!")
    print("==========================================")

if __name__ == "__main__":
    token_arg = sys.argv[1] if len(sys.argv) > 1 else None
    publish_release(token_arg)
