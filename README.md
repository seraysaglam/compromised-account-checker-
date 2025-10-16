# Compromised Account Checker — Bulk Login Validator

**Kısa açıklama**  
Bu proje, bir Excel dosyasındaki kullanıcı adı / şifre kombinasyonlarını ve hedef URL'leri kullanarak bir dizi web uygulamasında otomatik giriş denemesi yapar. Pop-up, cookie consent ve bazı modal engelleyicileri otomatik kapatmaya çalışır. Her denemenin sonucu Excel'e yazılır ve işlemler bir log dosyasına kaydedilir.

> Uyarı: Bu araç yalnızca yetkiniz veya izniniz olan sistemlerde kullanılmalıdır. İzinsiz kullanımlar yasa dışı olabilir.

---

## Özeti
- Excel dosyasından credential ve hedef URL bilgilerini okur.
- Her satır için hedef siteyi açar, olası pop-up/cookie pencerelerini kapatır.
- Kullanıcı adı ve şifre alanlarını doldurup giriş butonuna tıklar.
- Giriş sonucunu `status` sütununa yazar ve tüm aktiviteleri `login_logs.txt` dosyasına kaydeder.
- Sonuçlar `login_results.xlsx` olarak dışa aktarılır.

---

## Özellikler
- Başlıklı (`header`) veya başlıksız Excel dosyalarını destekler.
- Birden fazla domain/URL içeren Excel dosyaları ile çalışır.
- Yaygın cookie / consent dialoglarını denemeyle kapatma yeteneği.
- Otomasyon, Selenium + `webdriver-manager` kullanır (ChromeDriver otomatik indirme).
- Eğer Excel dosyası belirtilmezse, çalıştırıldığı dizindeki en son değiştirilen `.xlsx` dosyasını kullanır.

---

## Gereksinimler
- Python 3.9+ önerilir
- Google Chrome yüklü olmalı
- İnternet erişimi (ilk çalışmada ChromeDriver indirmek için)
- Python paketleri:
  - pandas
  - openpyxl
  - selenium
  - webdriver-manager

`requirements.txt` dosyasındaki paketler yeterlidir.

---

## Kurulum
1. Repo'yu klonlayın:
```bash
git clone https://github.com/<kullanici>/compromised-account-checker.git
cd compromised-account-checker

# Güvenlik & Etik uyarıları
Bu araç saldırı amaçlı kullanılmamalıdır. Sadece yetkili olduğunuz ortamlar ve hesaplar üzerinde test yapınız.
Toplu credential testleri (credential stuffing, brute force) birçok site için yasa dışı ve servis şartlarına aykırıdır. Yalnızca sahip olduğunuz veya izinli test ortamlarında kullanın.
Kullanıcı verilerini (şifreleri) güvenli şekilde saklayın; log dosyalarını veya çıktı Excel’lerini yetkisiz kişilerle paylaşmayın.
Eğer hedef site CAPTCHA, 2FA veya WAF/Cloudflare koruması kullanıyorsa script beklenen sonucu veremeyebilir.

#Hata ayıklama / Sık karşılaşılan sorunlar
chromedriver not found / sürüm uyumsuzluğu: webdriver-manager otomatik indirir; internete erişiminiz yoksa manuel indirme gerekebilir.
Eleman bulunamıyor (NoSuchElementException): XPATH değerleri hedef site ile uyuşmuyor. İlgili siteyi inspect edip XPATHS sözlüğünü güncelleyin.
Pop-up kapanmıyor: handle_popups()’a siteye özel selector’lar eklemek gerekebilir (örn. OneTrust .onetrust-accept-btn-handler).
Excel dosyası bulunamıyor: Script çalışma dizininde .xlsx yoksa dosya yolunu argümanla verin.
Hukuki uyarı: Toplu login girişimleri hedef servisin güvenliğini/erişimini etkileyebilir — testleri düşük hızlı, aralıklarla yapın.
