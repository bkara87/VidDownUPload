# Agent Project Context - VidDownUPload Pro (v2.1.0)

## Current Status Summary
- **App Version:** v2.1.0
- **Installer Executable:** `dist/VidDownUPload_Setup_v2.1.0.exe`
- **Main Setup Script:** `build_installer.py`
- **Full Project Documentation:** Refer to [PROJECT_SUMMARY.md](file:///c:/Users/Burak/Desktop/VidDownUPload/PROJECT_SUMMARY.md)

## Recent Accomplishments
1. **Frame Studio**: PNG frame imports stored in `%LOCALAPPDATA%\VidDownUPload\Frames\`, wizard modal, video scale/offset, always-on-top PNG overlay rendering.
2. **Multi-Blur System (B1 - B5)**: 5 independent blur slots, individual checkboxes, canvas drag handles B1..B5, full 100% height/width sliders, sequential FFmpeg filter composition.
3. **Unicode & CharMap Fix**: `safe_print` and UTF-8 stdio configuration preventing Windows `cp1254` `charmap` errors on videos with emojis.
4. **Installer GUI Fix**: `installer_gui.py` fixed button width (`width=180`) and label wraplength (`wraplength=520`).
5. **API Key Dual Persistence**: `config_keys.json` synced between AppData and base dir with `🔄 Yenile` button.
6. **TikTok OAuth Güvenli Giriş (v2.1.0)**: Google'ın WebView2 engellemesi aşıldı — TikTok OAuth artık sistem tarayıcısında açılıyor (`mode='browser'`), popup modu kaldırıldı, tek temiz giriş butonu, token otomatik alınıyor.

## Next Action / Continuation Roadmap
- Implement Batch Processing for queue items.
- Implement Frame Template Export/Import (.zip format).
- Test TikTok Google OAuth flow via `VidDownUPload_Setup_v2.1.0.exe`.
