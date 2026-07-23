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
            return data.get("version", "1.0.0")
    return "1.0.0"

def publish_release(token=None):
    version = get_current_version()
    tag_name = f"v{version}"
    print(f"[RELEASE] Automatic Release Publishing Process Starting for {tag_name}...")

    # 1. Build Installer Executable
    print("\n1. Derleniyor: Executable & Setup Installer...")
    subprocess.run([sys.executable, "build_installer.py"], check=True)

    # 2. Git Commit and Push
    print("\n2. GitHub'a Push Ediliyor (main branch)...")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Release {tag_name}"], check=False)
    subprocess.run(["git", "push", "-u", "origin", "main"], check=True)

    # 3. Create & Push Git Tag
    print(f"\n3. Git Tag Oluşturuluyor: {tag_name}...")
    subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=False)
    subprocess.run(["git", "push", "origin", tag_name], check=True)

    # 4. Direct GitHub API Upload if Token Provided
    github_token = token or os.environ.get("GITHUB_TOKEN")
    owner = "BURAKKARABULUT87"
    repo = "VidDownUPload"

    if github_token:
        print("\n4. GitHub API ile Doğrudan Release Oluşturuluyor...")
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Create Release via API
        rel_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        rel_data = {
            "tag_name": tag_name,
            "target_commitish": "main",
            "name": f"{repo} {tag_name}",
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
                print(f"Uploading {setup_exe.name} asset...")
                with open(setup_exe, "rb") as f:
                    u_headers = headers.copy()
                    u_headers["Content-Type"] = "application/octet-stream"
                    u_res = requests.post(f"{upload_url}?name={setup_exe.name}", headers=u_headers, data=f)
                    if u_res.status_code in [200, 201]:
                        print("✅ Setup EXE asset uploaded successfully!")
                    else:
                        print(f"Asset upload status: {u_res.status_code}")
        else:
            print(f"Release API Status: {res.status_code} - {res.text}")
    else:
        print("\nℹ️ Tag GitHub'a gönderildi. GitHub Actions otomatik olarak Release ve EXE ekleyecektir!")

    print("\n🎉==========================================")
    print(f"[OK] {tag_name} Otomatik Yayınlama Süreci Tamamlandı!")
    print("==========================================")

if __name__ == "__main__":
    token_arg = sys.argv[1] if len(sys.argv) > 1 else None
    publish_release(token_arg)
