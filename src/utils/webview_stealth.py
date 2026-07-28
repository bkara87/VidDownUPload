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

                        // Hide window.chrome.webview when on accounts.google.com
                        if (window.chrome) {
                            const rawWV = window.chrome.webview;
                            Object.defineProperty(window.chrome, 'webview', {
                                get: function() {
                                    try {
                                        const h = (window.location && window.location.hostname) ? window.location.hostname : '';
                                        if (h.includes('google.com') || h.includes('gstatic.com')) {
                                            return undefined;
                                        }
                                    } catch(e){}
                                    return rawWV;
                                },
                                configurable: true,
                                enumerable: false
                            });
                        }
                    } catch(err) {
                        console.error('Stealth error:', err);
                    }
                })();
                """
                core.AddScriptToExecuteOnDocumentCreatedAsync(stealth_js)
                print("DEBUG [webview_stealth]: Successfully injected Google OAuth stealth script into CoreWebView2.")
        except Exception as e:
            print(f"DEBUG [webview_stealth]: Error in stealth_on_webview_ready: {e}\\n{traceback.format_exc()}")

    edge.EdgeChrome.on_webview_ready = stealth_on_webview_ready
    edge._stealth_patched = True
    print("DEBUG [webview_stealth]: EdgeChromium stealth patch applied successfully.")
