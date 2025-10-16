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
