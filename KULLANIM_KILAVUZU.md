# VidDownUPload Kullanım ve Derleme Kılavuzu

Bu proje, **Instagram, YouTube ve TikTok** platformlarından video indirmenizi, eski filigranları maskelemenizi, yeni logonuzu/filigranınızı eklemenizi ve GitHub üzerinden otomatik güncelleme altyapısını kullanmanızı sağlar.

---

## 🚀 1. Hızlı Başlangıç (Geliştirici Modu)

### Bağımlılıkları Yükleme
Terminallerinizi veya Komut İstemi'ni açıp proje klasörüne gidin ve bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

### Uygulamayı Çalıştırma
```bash
python main.py
```

---

## 📦 2. Uygulamayı .EXE Olarak Derleme

Uygulamayı tek tıkla çalışabilen bir Windows `.exe` paketi haline getirmek için:
```bash
python build_exe.py
```
Derleme tamamlandığında çıktınız `dist/VidDownUPload/VidDownUPload.exe` konumunda hazır olacaktır.

---

## 🔄 3. GitHub Otomatik Güncelleme Altyapısının Kurulumu

Uygulamanız yeni güncellemeleri GitHub hesabınız üzerinden otomatik olarak denetler ve indirir.

1. **GitHub Yapılandırması**:
   - `src/config.py` dosyasını açın.
   - `GITHUB_OWNER = "GitHubKullaniciAdiniz"` kısmına kendi GitHub kullanıcı adınızı yazın.
   - `GITHUB_REPO = "VidDownUPload"` kısmını kendi repository adınızla güncelleyin.

2. **Yeni Güncelleme Yayınlama (GitHub Release)**:
   - GitHub üzerinde bir **Release** oluşturun (Örnek Etiket / Tag: `v1.0.1`).
   - Derlediğiniz `VidDownUPload.exe` dosyasını Release varlıkları (Assets) kısmına ekleyin.
   - `version.json` dosyasındaki versiyon numarasını `1.0.1` olarak güncelleyip ana depoya push edin.
   - Kullanıcı uygulamasındaki **"🔄 Güncelleme Kontrol Et"** butonuna bastığında yeni sürüm tespit edilecek ve oto-güncelleme devreye girecektir.

---

## 🎬 4. Özellikler ve Kullanım

- **Video İndirme**: Instagram Reels/Post, YouTube Video/Shorts veya TikTok linkini yapıştırın ve "Videoyu İndir" butonuna basın.
- **Filigran Maskeleme**: İndirilen videodaki eski filigran alanına otomatik maske/blur kutusu uygular.
- **Yeni Filigran / Logo**: Kendi sayfa logonuzu (PNG) veya metin filigranınızı istediğiniz köşeye ekleyin.
- **Kişisel Saklama**: Videolarınız `processed/` klasörüne yüksek kalitede kaydedilir.
