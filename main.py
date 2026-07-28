import sys
import os
import io
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()

# Force UTF-8 encoding for stdout/stderr to prevent charmap encoding errors with emojis on Windows
if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import webview
from pathlib import Path

# Add root directory to python path
BASE_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.api_bridge import ApiBridge
from src.config import APP_NAME, APP_VERSION
from src.utils.webview_stealth import apply_webview_stealth_patch


def main():
    apply_webview_stealth_patch()
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
    api = ApiBridge()
    html_file = BASE_DIR / "web" / "index.html"

    if not html_file.exists():
        print(f"ERROR: HTML UI file not found at {html_file}")
        sys.exit(1)

    # Create chromeless standalone window using Edge WebView2 (no address bar)
    window = webview.create_window(
        title=f"{APP_NAME} Studio v{APP_VERSION}",
        url=html_file.resolve().as_uri(),
        js_api=api,
        width=1080,
        height=820,
        min_size=(900, 660),
        resizable=True,
        text_select=True,
        frameless=False,      # OS native titlebar (for move/resize/close)
        easy_drag=False,
        background_color='#05080F'
    )

    api.set_window(window)

    # Start PyWebView using native Windows Edge WebView2 engine with standard Chrome User-Agent
    chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    webview.start(debug=False, user_agent=chrome_ua, private_mode=False)


if __name__ == "__main__":
    main()
