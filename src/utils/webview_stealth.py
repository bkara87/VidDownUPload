import sys
import json
import traceback

def apply_webview_stealth_patch():
    """
    Monkey-patches pywebview's EdgeChromium backend to inject anti-detection script
    and standard Google Chrome User-Agent header on CoreWebView2 initialization.
    This prevents Google OAuth ('accounts.google.com') from blocking embedded WebView2 windows
    with 'Google, bu hesabın size ait olduğunu doğrulayamadı'.
    """
    try:
        import webview.platforms.edgechromium as edge
    except Exception as e:
        print(f"DEBUG [webview_stealth]: EdgeChromium module not available: {e}")
        return

    if getattr(edge, "_stealth_patched", False):
        return

    original_on_webview_ready = edge.EdgeChrome.on_webview_ready

    def stealth_on_webview_ready(self, sender, args):
        try:
            # 1. Execute original initialization
            original_on_webview_ready(self, sender, args)

            # 2. Inject stealth script into CoreWebView2 for all document creations
            if args.IsSuccess and hasattr(sender, "CoreWebView2") and sender.CoreWebView2:
                core = sender.CoreWebView2

                # Set Chrome User-Agent on CoreWebView2 settings
                try:
                    chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                    core.Settings.UserAgent = chrome_ua
                except Exception as ua_err:
                    print(f"DEBUG [webview_stealth]: UserAgent setting error: {ua_err}")

                stealth_js = """
                (function() {
                    try {
                        const chromeUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
                        const chromeAppVer = '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

                        // Override navigator properties
                        Object.defineProperty(navigator, 'userAgent', { get: () => chromeUA, configurable: true });
                        Object.defineProperty(navigator, 'appVersion', { get: () => chromeAppVer, configurable: true });
                        Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.', configurable: true });
                        Object.defineProperty(navigator, 'platform', { get: () => 'Win32', configurable: true });

                        // Suppress automation / webdriver detection flag
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });

                        // Override navigator.userAgentData to match Desktop Chrome 126
                        const fakeBrands = [
                            { brand: 'Not/A)Brand', version: '8' },
                            { brand: 'Chromium', version: '126' },
                            { brand: 'Google Chrome', version: '126' }
                        ];
                        const fakeFullVersionList = [
                            { brand: 'Not/A)Brand', version: '8.0.0.0' },
                            { brand: 'Chromium', version: '126.0.6478.127' },
                            { brand: 'Google Chrome', version: '126.0.6478.127' }
                        ];

                        const fakeUAData = {
                            brands: fakeBrands,
                            mobile: false,
                            platform: 'Windows',
                            getHighEntropyValues: function(hints) {
                                return Promise.resolve({
                                    architecture: 'x86',
                                    bitness: '64',
                                    brands: fakeBrands,
                                    fullVersionList: fakeFullVersionList,
                                    mobile: false,
                                    model: '',
                                    platform: 'Windows',
                                    platformVersion: '15.0.0',
                                    uaFullVersion: '126.0.6478.127'
                                });
                            },
                            toJSON: function() {
                                return { brands: fakeBrands, mobile: false, platform: 'Windows' };
                            }
                        };

                        Object.defineProperty(navigator, 'userAgentData', {
                            get: () => fakeUAData,
                            configurable: true
                        });

                        // Completely remove / delete window.chrome.webview on Google / TikTok auth domains
                        if (window.chrome) {
                            try {
                                const host = (window.location && window.location.hostname) ? window.location.hostname : '';
                                if (host.includes('google.com') || host.includes('gstatic.com') || host.includes('tiktok.com')) {
                                    delete window.chrome.webview;
                                    delete window.chrome.csi;
                                    delete window.chrome.loadTimes;
                                    delete window.chrome;
                                } else {
                                    delete window.chrome.webview;
                                }
                            } catch(e) {}
                        }

                        // Remove CDC / ChromeDriver automation signatures
                        for (let prop in window) {
                            if (prop.match(/^cdc_/i) || prop.match(/^__$|^__$|__driver_|__webdriver_/i)) {
                                try { delete window[prop]; } catch(e){}
                            }
                        }

                        // Override navigator.plugins and languages
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                            configurable: true
                        });
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['tr-TR', 'tr', 'en-US', 'en'],
                            configurable: true
                        });
                    } catch(err) {
                        console.error('Stealth error:', err);
                    }
                })();
                """
                core.AddScriptToExecuteOnDocumentCreatedAsync(stealth_js)
                print("DEBUG [webview_stealth]: Successfully injected Google OAuth stealth script into CoreWebView2.")

                # Intercept new window requests (window.open / popups) to prevent pywebview embedded popups
                # and launch them in the real external Chrome/Edge browser instead!
                try:
                    def on_new_window_requested(sender_core, nw_args):
                        try:
                            target_uri = str(nw_args.Uri or "")
                            print(f"DEBUG [webview_stealth]: NewWindowRequested intercepted URI = {target_uri}")
                            nw_args.Handled = True  # Block pywebview from spawning an embedded child window!
                            if target_uri:
                                from src.uploader.tiktokapi import _open_url_in_browser
                                _open_url_in_browser(target_uri)
                        except Exception as nw_err:
                            print(f"DEBUG [webview_stealth]: NewWindowRequested handler error: {nw_err}")

                    core.NewWindowRequested += on_new_window_requested
                    print("DEBUG [webview_stealth]: NewWindowRequested handler attached successfully.")
                except Exception as nw_attach_err:
                    print(f"DEBUG [webview_stealth]: NewWindowRequested attach error: {nw_attach_err}")
        except Exception as e:
            print(f"DEBUG [webview_stealth]: Error in stealth_on_webview_ready: {e}\\n{traceback.format_exc()}")

    edge.EdgeChrome.on_webview_ready = stealth_on_webview_ready
    edge._stealth_patched = True
    print("DEBUG [webview_stealth]: EdgeChromium stealth patch applied successfully.")
