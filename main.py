import sys
import os
import webview
from pathlib import Path

# Add root directory to python path
BASE_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.api_bridge import ApiBridge
from src.config import APP_NAME, APP_VERSION


def main():
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

    # Start PyWebView using native Windows Edge WebView2 engine (no address bar)
    webview.start(debug=False)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
