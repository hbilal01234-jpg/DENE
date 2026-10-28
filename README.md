# DENE

## Yeni: iPhone sesli asistanı

Ana sayfa artık iPhone'a uygun Türkçe sesli sohbet ekranıdır. Sunucu tarafında Gemini bağlantısı, tarayıcıda konuşmayı yazıya çevirme ve sesli yanıt eklendi. Gerçek yanıt için sunucuda API anahtarı, telefondan erişim için HTTPS barındırma gerekir. Henüz canlı hizmete dağıtılmadı; gerçek iPhone testi ve canlı AI doğrulaması yapılmadı. [iPhone kurulum ve kullanım bilgileri](IOS_KURULUM.md).

Önceki prototip aşağıda açıklanmaktadır; yerel çalışma masası `/desk` adresine taşındı. Open Yazılım entegrasyonu yeni sesli asistanın kapsamı dışındadır.

# Acente yardımcısı — ilk prototip

Windows üzerinde kullanılacak acente asistanının ilk çalışma masası. JARVIS arşivinden kod veya varlık kopyalanmadı; arşivde proje lisansı net olmadığı için bu prototip bağımsız yazıldı.

## Windows'ta başlatma

Python 3.12 kurulu olmalı. `BASLAT.bat` dosyasına çift tıklayın. Kurulum paket indirmek için internet ister. Tarayıcı erken açılırsa kurulum bittikten sonra sayfayı yenileyin. Sunucuyu kapatmak için terminalde Ctrl+C kullanın.

Alternatif: `py -3.12 -m venv .venv`, ardından `.venv\Scripts\python -m pip install -r requirements.txt` ve `.venv\Scripts\python server.py`.

## Çalışan kapsam

- Trafik, kasko, sağlık, DASK, konut ve diğer branşlarda yerel SQLite iş kayıtları; durum güncelleme.
- İki metin içeren PDF veya UTF-8 TXT'den prim, teminat, muafiyet ve istisna ifadelerini sayfa referansıyla yan yana gösterme. Bu, anahtar kelime taramasıdır; AI değerlendirmesi değildir. Taranmış PDF için OCR yoktur. Yüklenen belgeler sunucuda kalıcı saklanmaz.
- WhatsApp taslağını alıcı kontrolünden sonra açma. Normal/Business hesap seçimini açılan uygulamada kullanıcı yapar. Otomatik gönderim yoktur.
- Destekleyen tarayıcıda Türkçe ses tanıma; komut metnini kontrol edip ilgili bölüme geçme. Genel konuşma veya sesli cevap henüz yoktur. Tarayıcı konuşma hizmeti sesi dışarıya gönderebilir.

## Henüz bağlı olmayanlar

Open Yazılım masaüstü otomasyonu, şirket portallarından teklif alma, anlamsal AI karşılaştırması, görsel OCR, poliçe kesimi, kullanıcı girişi, yetkilendirme ve denetim kayıtları. Gerçek müşteri verisi kullanmayın. Sunucu yalnızca 127.0.0.1 üzerinde dinler; 2–3 kişinin ağdan kullanımı henüz açılmadı. Ortak kullanım için önce kimlik doğrulama, erişim kontrolleri, TLS ve yedekleme hazırlanmalıdır.

Sonraki entegrasyon için: Open Yazılım'ın tam ürün/sürüm bilgisi, kişisel bilgileri kapatılmış ekran örnekleri, teklifin Open içinden mi şirket portalından mı çalıştırıldığı ve WhatsApp hesaplarının kullanım şekli gerekir. Şifreleri kaynak koduna veya sohbete koymayın.

## Geliştirme

Linux: `python -m venv .venv` → `.venv/bin/python -m pip install -r requirements.txt` → `.venv/bin/python server.py`.

Kontroller: `.venv/bin/python -m unittest discover -s tests -v`, `node --check static/app.js`.

Her görev zaten izole ortamda çalışır; mevcut checkout'u kullanın, kullanıcı istemedikçe Git worktree oluşturmayın. `data/` yerel kayıtlarını koruyun. Canlı süreçler yeni görevlerde yeniden başlatılmalıdır.
