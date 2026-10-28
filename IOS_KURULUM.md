# iPhone sesli asistanı

Bu bir Safari web uygulamasıdır; App Store uygulaması değildir. iPhone'a Python kurulmaz.

## İlk sürüm

Ana ekran `/` artık Türkçe sesli asistandır. Önceki Windows çalışma masası `/desk` adresinde yerel kullanım için korunmuştur. Open Yazılım bu sesli asistanın kapsamı dışındadır.

Mikrofon → konuş → metni kontrol et → gönder → yanıtı oku/dinle. İlk sürümde kendiliğinden işlem yapılmaz. WhatsApp, teklifler ve portallar sonraki aşamadır.

Konuşma yalnızca sekmenin belleğinde tutulur. Yeni sohbet, yenileme veya sekmeyi kapatma konuşmayı siler. Sunucu konuşmaları diske yazmaz. Metin ve yakın konuşma geçmişi Google Gemini'ye gönderilir; sağlayıcının veri işleme koşulları ayrıca geçerlidir. Ses tanıma tarayıcı/işletim sistemi hizmetine bağlıdır. Ekran kilitliyken veya arka planda sürekli dinleme yapılmaz.

## Gerçek yanıt almak için

Sunucuda `ACENTE_AI_KEY` ortam değişkeni gereklidir. Anahtar Google AI Studio'dan alınır: https://aistudio.google.com/apikey . Ücret/kota hesabınıza ve seçilen modele bağlıdır. Anahtarı sohbete, GitHub'a veya telefondaki erişim kodu alanına yazmayın. Yönetici sunucunun gizli değişken ayarına girmelidir.

Varsayılan model `gemini-2.5-flash`; gerektiğinde `ACENTE_AI_MODEL` ile değiştirilebilir. Bağlantı yalnızca gerçek bir yanıt alınırsa doğrulanmış sayılır. Anahtar yokken arayüz bunu açıkça gösterir ve sahte yanıt üretmez.

## Telefonda açılması için gereken kurulum

GitHub dosyaları saklar; GitHub Pages bu Python sunucusunu çalıştıramaz. iPhone'dan kullanım için Python sunucusunun çalıştığı HTTPS destekli bir barındırma hizmeti gerekir. Bu çalışma böyle bir hizmete dağıtılmadı ve halka açık kullanım adresi oluşturulmadı.

Sunucu hazırlayacak kişi için:

1. Python 3.12, `python -m pip install -r requirements.txt`.
2. Gizli sunucu değişkeni: `ACENTE_AI_KEY`.
3. Güçlü ve rastgele en az 16 karakterli `ACENTE_ACCESS_CODE` (API anahtarından farklı bir erişim kodu). Bu kodu yalnızca yetkili kullanıcılarla paylaşın. Proxy tarafından yerine konan bir sahte değer değil, sunucunun okuyabildiği gerçek bir gizli değişken olmalıdır.
4. `ACENTE_PUBLIC_ORIGIN=https://size-ayrilan-alan-adi` (sonunda `/` yok), `ACENTE_HOST=0.0.0.0`; hizmet gerekirse `PORT` sağlar.
5. `python server.py`; önüne HTTPS sonlandıran ters proxy/barındırma hizmeti koyun. Python sunucusunu doğrudan internete açmayın. Hizmette istek boyutu, bağlantı süresi ve kaynak sınırları uygulayın. Bu küçük prototipte 12 istek/dakika ve 2 eşzamanlı AI isteği sınırı tüm kullanıcılar için ortaktır.
6. Telefondan HTTPS adresini Safari'de açın. Dişli simgesine dokunup erişim kodunu girin. API anahtarı girilmez. Paylaş → Ana Ekrana Ekle ile kısayol oluşturabilirsiniz. Çevrimdışı AI desteği yoktur.

Paylaşılan kod ilk deneme için erişim kontrolüdür; kişi bazlı hesap/yetki/kota sistemi değildir. 2–3 kişi aynı kodla deneme yapabilir; gerçek müşteri verileriyle kullanmadan önce bireysel kullanıcı hesapları ve veri politikası hazırlanmalıdır. Dış erişim etkin olduğunda eski kayıt/belge API'leri kapalı tutulur.

## iPhone'da ses

- Mikrofon izni ve destekleyen Safari sürümü gerekir. Safari web uygulamasında ve ana ekran modunda davranış farklı olabilir; gerçek cihaz testi yapılmalıdır.
- Ses tanıma kullanılamazsa mesaj alanını açıp iPhone klavyesindeki dikte mikrofonunu kullanın.
- Otomatik ses başlamazsa **Yanıtı sesli dinle** düğmesine dokunun. Türkçe ses bulunması iOS'un yüklü seslerine bağlıdır.
- Tarayıcı testleri fiziksel iPhone mikrofon/ses testinin yerini tutmaz.

## Yerel geliştirme ve doğrulama

Mevcut `/workspace/DENE` checkout'unu kullanın. Kullanıcı istemedikçe worktree oluşturmayın. `.venv/bin/python server.py`, `.venv/bin/python -m unittest discover -s tests -v`, `node --check static/voice.js`.

HTTP ve sağlayıcı adaptörü testlerinde dış AI yanıtları taklit edilir; bunlar canlı Gemini doğrulaması değildir. Çalışan sürecin yeni görevde yeniden başlatılması gerekir. Erişim kodunu veya API anahtarını loglamayın.
