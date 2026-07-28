# 📌 VidDownUPload Pro — Proje Özeti & Geliştirme Durumu (v2.0.1)

**Son Güncelleme Tarihi:** 27 Temmuz 2026  
**Sürüm:** v2.0.1  
**Geliştirici:** Antigravity AI & Burak  

---

## 🎯 1. Projenin Amacı ve Mimarisi

- **Yazılım Adı:** VidDownUPload Pro (v2.0.1)
- **Teknoloji Yığını:** Python 3.12 + PyWebView (Windows Edge Chromium WebView2 Engine) + HTML5 / Vanilla CSS / JavaScript (ES6+) + FFmpeg 7.0 + OpenCV (cv2) + yt-dlp + PyInstaller + CustomTkinter.
- **Hedef:** Instagram Reels, YouTube Shorts, TikTok ve Facebook için otomatik yüksek kalitede dikey (9:16) video indirme, otomatik filigran/logo temizleme (Multi-Blur), Özel Çerçeve Şablonu (Frame Studio) giydirme, otomatik 59s kırpma ve sosyal medya yükleme platformu.

---

## 🚀 2. Son Yapılan İşler & Tamamlanan Geliştirmeler (Tam Liste)

### 🖼️ A. Profesyonel Çerçeve Şablonu Stüdyosu (Frame Studio)
1. **Modüler Çerçeve Depolama (`src/processor/frame_manager.py`)**:
   - Özel PNG çerçeveleri ve `config.json` ayarlarını `%LOCALAPPDATA%\VidDownUPload\Frames\<ŞablonAdı>\` dizininde kalıcı olarak saklar.
   - Sınırsız sayıda çevrimdışı Canva, Photoshop veya Illustrator PNG çerçevelerinin yüklenmesini destekler.
2. **Çerçeve Oluşturma Sihirbazı (Frame Creation Wizard)**:
   - Arayüzde (`web/index.html` & `web/app.js`) tuval üzerine **kırmızı dikdörtgen (`videoArea`)** sürüklenip boyutlandırılarak videonun görüneceği pencere alanı seçilir ve şablon olarak kaydedilir.
3. **Canlı 60 FPS Önizleme & Katman Garantisi**:
   - Önizlemede HTML5 `<video>` akışı 60 FPS `requestAnimationFrame` döngüsüyle canlı akarken transparan PNG çerçeve **HER ZAMAN EN ÜST KATMAN** olarak videonun üstünde kalır.
   - İnce konumlandırma kontrolleri eklendi: Video Zoom (%50-%200), Yatay Kaydırma (X), Dikey Kaydırma (Y).
4. **FFmpeg Kompozit Render (`src/processor/ffmpeg_utils.py`)**:
   - Orijinal video çerçevenin `videoArea` sınırlarına oturtulup kesilir, üzerine PNG çerçeve overlay olarak eklenir.

---

### 🔲 B. Çoklu Blur Maskeleme Sistemi (B1 — B5)
1. **5 Bağımsız Blur Sekmesi (B1, B2, B3, B4, B5)**:
   - Stüdyo kartı 5 bağımsız blur sekmesine dönüştürüldü. Her birinin kendi **Aktif Et** tiki (`chkActiveBlur`) bulunmaktadır.
2. **Tuval Üzerinde Etiketli Sürükleme**:
   - Canlı önizleme tuvalinde aktif olan tüm blur kutuları kendi etiketleriyle (`B1`, `B2`, `B3`, `B4`, `B5`) tutamaç olarak çizilir ve sürüklenir.
3. **%100 Tam Boy Blur Yüksekliği & Genişliği**:
   - Slider üst sınırı %35'ten **%100'e** çıkarıldı. Ekran boyu dikey blur şeridi oluşturulabilir.
4. **FFmpeg Çoklu Render Zinciri**:
   - Aktifleşen tüm blur kutuları FFmpeg motorunda sıralı split/crop/avgblur zincirinde işlenerek aynı anda render edilir.

---

### 🔤 C. Windows CharMap Unicode & Emoji Hatası Çözümü
- Video başlıklarında gülme emoji'leri (`😂`, `😅`) geçtiğinde Windows konsolundaki `cp1254` kodlamasından kaynaklanan `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f602'` hatası çözüldü.
- `src/config.py` ve `src/processor/ffmpeg_utils.py` dosyalarına `safe_print` fonksiyonu ve `UTF-8 / errors='replace'` standart stdio koruması eklendi.

---

### 🎨 D. Kurulum Sihirbazı Görsel Hizalaması (`installer_gui.py`)
- CustomTkinter kurulum sihirbazında `Yükleniyor...` mavi butonunun genişliği (`width=180`) sabitlendi, metin değiştiğinde butonun taşması engellendi.
- İlerleme metninin (`lbl_status`) birbirinin üzerine binme sorunu `wraplength=520` ve `justify="left"` eklenerek düzeltildi.

---

### 🔒 E. API Anahtarları Çift Depolama Kalıcılığı (`api_bridge.py`)
- `config_keys.json` hem `%LOCALAPPDATA%\VidDownUPload\config_keys.json` hem de yerel uygulama klasöründe çift yedekli ve otomatik birleştirmeli saklanır. Uygulama güncellense veya silinip tekrar kurulsa bile API key'ler ve token'lar kaybolmaz.
- API Yönetimi sekmesine **`🔄 Yenile`** butonu eklendi.

---

### 🔑 F. Google OAuth WebView2 Stealth Yaması (`webview_stealth.py`)
- Google girişlerinde `disallowed_useragent` engeline takılmamak için Edge WebView2 üzerinde Chrome 126 User-Agent spoofing ve `navigator.webdriver` gizleme yaması eklendi.

---

### ✂️ G. Otomatik 59 Saniye Video Kırpma
- 1 dakikadan uzun videolar YouTube Shorts süresi sınırı ve telif telafi önlemi olarak otomatik 59. saniyeden kesilmektedir.

---

## 📁 3. Önemli Proje Dosyaları ve Görevleri

| Dosya Yolu | Açıklama |
| :--- | :--- |
| `main.py` | PyWebView ana pencere başlatıcısı ve stealth yama tetikleyicisi. |
| `src/api_bridge.py` | JavaScript ↔ Python PyWebView iletişim köprü metotları. |
| `src/processor/frame_manager.py` | Özel PNG Çerçeve şablonlarını yöneten ve diskte saklayan modül. |
| `src/processor/ffmpeg_utils.py` | FFmpeg 7.0 kompozit render motoru (Frame Overlay, Multi-Blur B1-B5, Logo, Yazı, 59s Trim). |
| `src/installer/installer_gui.py` | Kurulum sihirbazı GUI (CustomTkinter). |
| `web/index.html` | Uygulama ana kullanıcı arayüzü ve modal yapıları. |
| `web/app.js` | 60 FPS canlı önizleme tuvali, Frame Wizard, Multi-Blur sürükleme ve UI mantığı. |
| `build_installer.py` | Tek tıkla `VidDownUPload_Setup_v2.0.1.exe` kurulum paketini derleyen Python betiği. |

---

## 📌 4. Yarın Kaldığımız Yerden Devam Etmek İçin Roadmap (Sonraki Adımlar)

1. **TikTok Otomatik Paylaşım Testi**:
   - TikTok Google giriş akışını ve token alma/otomatik video yükleme işlevini canlıda test etmek.
2. **Toplu Video İşleme (Batch Processing)**:
   - İndirilen tüm videoları seçip belirlenen Frame ve Multi-Blur ayarlarıyla tek tıkla toplu işleme almak.
3. **Şablon Paketleme (.zip Export/Import)**:
   - Kullanıcıların oluşturduğu PNG çerçeve şablonlarını `.zip` olarak dışa/içe aktarabilmesini sağlamak.

---

### 📦 Güncel Kurulum Dosyaları
- **Setup Installer:** `dist/VidDownUPload_Setup_v2.0.1.exe`
- **Portable Klasör:** `dist/VidDownUPload/`
