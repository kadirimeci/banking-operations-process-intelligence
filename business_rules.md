# İş Kuralları ve Sentetik Veri Üretim İlkeleri

**Proje:** Bankacılık Operasyonları ve Süreç Analitiği  
**Kurgusal kurum:** Veriqora Bank  
**Sürüm:** 1.1  
**Durum:** Onaylanan mantıksal tasarım; pilot veri üretimi henüz başlamadı  
**Veri kaynağı:** Tamamen sentetik. Gerçek banka, müşteri veya çalışan verisi kullanılmaz.

## 1. Amaç

Bu belge, sentetik işlem verilerinin üretiminde ve analizinde uygulanacak iş kurallarını tanımlar. Hedef, sonuçları önceden belirlenmiş KPI değerleri üretmek değil; tutarlı operasyonel olaylardan hesaplanabilir sonuçlar elde etmektir. Bu belgedeki dağılım ve maliyetler kurgusal varsayımlardır; gerçek bankacılık istatistiği olarak yorumlanamaz.

## 2. Veri kapsamı

2025 yılı içinde açılan toplam **50.000** sentetik işlem planlanmaktadır. 31.12.2025 saat 18.00 (Europe/Istanbul) itibarıyla tamamlanan, açık ve iptal edilen işlemler ayrı değerlendirilir.

| Operasyon | Planlanan işlem sayısı | Pay |
|---|---:|---:|
| Ödeme ve transferler | 15.000 | %30 |
| Müşteri bilgi güncellemeleri | 10.000 | %20 |
| Hesap işlemleri | 9.000 | %18 |
| Kredi operasyonları | 7.500 | %15 |
| Yasal takip operasyonları | 5.000 | %10 |
| Operasyonel kontroller | 3.500 | %7 |
| **Toplam** | **50.000** | **%100** |

Günlük açılış sayıları eşit dağıtılmaz. Haftanın günü, ay sonu, resmî tatil sonrası birikim ve operasyon türü talep yoğunluğunu etkileyebilir. Yıllık operasyon toplamları korunur; günlük dağılım ağırlıkları normalize edilir.

## 3. Karmaşıklık sınıflandırması

Karmaşıklık yalnızca işlem açılışında bilinen `transaction_attributes` özelliklerinden hesaplanır. Her operasyonda toplam puan: **0–2 = LOW**, **3–5 = MEDIUM**, **6 ve üzeri = HIGH**. İlgili olmayan özellikler sıfır puan getirir. Belge sayısı için belirtilen bantlar birbirini dışlar; aynı özellikten iki ayrı belge puanı alınmaz.

| Operasyon | Açılışta bilinen koşul | Puan |
|---|---|---:|
| Kredi | Belge sayısı 4–6 | +2 |
| Kredi | Belge sayısı ≥7 (4–6 yerine) | +3 |
| Kredi | Manuel inceleme gerekiyor | +2 |
| Kredi | Ek onay gerekiyor | +2 |
| Kredi | Dış taraf koordinasyonu gerekiyor | +2 |
| Ödeme ve transfer | Standart dışı talep | +2 |
| Ödeme ve transfer | Tutar bandı MEDIUM | +1 |
| Ödeme ve transfer | Tutar bandı HIGH (MEDIUM yerine) | +2 |
| Ödeme ve transfer | Ek onay gerekiyor | +2 |
| Ödeme ve transfer | Manuel inceleme gerekiyor | +2 |
| Hesap işlemleri | Standart dışı talep | +2 |
| Hesap işlemleri | Belge sayısı 3–4 | +1 |
| Hesap işlemleri | Belge sayısı ≥5 (3–4 yerine) | +2 |
| Hesap işlemleri | Ek onay gerekiyor | +2 |
| Hesap işlemleri | Manuel inceleme gerekiyor | +2 |
| Bilgi güncelleme | Kimlik/yetki değişikliği | +2 |
| Bilgi güncelleme | Belge sayısı 2–3 | +1 |
| Bilgi güncelleme | Belge sayısı ≥4 (2–3 yerine) | +2 |
| Bilgi güncelleme | Manuel inceleme gerekiyor | +2 |
| Bilgi güncelleme | Ek onay gerekiyor | +2 |
| Yasal takip | Standart dışı talep | +2 |
| Yasal takip | Belge sayısı 4–6 | +1 |
| Yasal takip | Belge sayısı ≥7 (4–6 yerine) | +2 |
| Yasal takip | Dış taraf koordinasyonu gerekiyor | +2 |
| Yasal takip | Manuel inceleme gerekiyor | +2 |
| Operasyonel kontrol | Kapsamlı kontrol | +2 |
| Operasyonel kontrol | Belge sayısı 4–6 | +1 |
| Operasyonel kontrol | Belge sayısı ≥7 (4–6 yerine) | +2 |
| Operasyonel kontrol | Manuel inceleme gerekiyor | +2 |
| Operasyonel kontrol | Ek onay gerekiyor | +2 |

`request_type`, ilgili operasyon için standart dışı talep, kimlik/yetki değişikliği veya kapsamlı kontrol ayrımını taşıyacak şekilde tanımlanır. Karmaşıklık açılışta hesaplanıp sabitlenir. Hata, yeniden işlem, gerçekleşen süre veya SLA ihlali puanı geriye dönük değiştirmez.

**Kalibrasyon hedefleri (zorunlu etiket kotaları değil):**

| Operasyon | LOW | MEDIUM | HIGH |
|---|---:|---:|---:|
| Kredi | %30 | %45 | %25 |
| Ödeme ve transfer | %65 | %25 | %10 |
| Hesap işlemleri | %50 | %35 | %15 |
| Bilgi güncelleme | %70 | %23 | %7 |
| Yasal takip | %25 | %45 | %30 |
| Operasyonel kontrol | %45 | %40 | %15 |

Önce açılış özellikleri üretilir, sonra puan hesaplanır. Dağılım hedeflerden saparsa açılış özelliklerinin üretim olasılıkları kalibre edilir; sonradan sınıf etiketi zorla değiştirilmez.

## 4. İş akışları ve aşama ziyaretleri

| Operasyon | Standart akış |
|---|---|
| Kredi | Talep → Belge kontrolü → Operasyonel inceleme → Onay → Tamamlama |
| Ödeme ve transfer | Talep → Doğrulama → İsteğe bağlı kontrol → İşleme alma → Kapanış |
| Hesap işlemleri | Talep → Kimlik/yetki kontrolü → Hesap işlemi → İsteğe bağlı onay → Tamamlama |
| Bilgi güncelleme | Talep → Bilgi kontrolü → Güncelleme → Doğrulama → Tamamlama |
| Yasal takip | Dosya kaydı → Belge kontrolü → İnceleme → Dış koordinasyon → Kapanış |
| Operasyonel kontrol | Kontrol kaydı → İnceleme → Bulgu değerlendirme → İsteğe bağlı düzeltme → Kapanış |

İsteğe bağlı aşamalar, açılış özellikleri ve oluşan olaylara göre devreye girer. Yeniden işlem, daha önce ziyaret edilmiş aşamaya dönüş oluşturabilir.

`stage_executions` tablosunda **bir satır bir aktif çalışma aralığıdır**. Bir aşama ziyareti `(transaction_id, stage_id, visit_number)` üçlüsüyle tanımlanır ve birden çok çalışma aralığı içerebilir. Aynı üçlü birden çok satırda bulunabilir; `execution_id` her aralıkta benzersizdir. `visit_number` aynı işlem ve aşamada 1'den başlayarak artar. Beklemeler ve kalite olayları ilgili aşama ziyaretine `stage_id` + `visit_number` üzerinden bağlanır; tek bir aktif aralığa bağlanmaz. Aşama ziyaretlerinin en az bir aktif çalışma aralığı vardır; sıfır aktif çalışmalı ziyaretler mevcut model kapsamı dışındadır.

## 5. İş takvimi ve zaman aralıkları

- Saat dilimi `Europe/Istanbul` olarak yorumlanır; TIMESTAMP değerleri tek bir zaman standardında saklanır.
- Normal iş günü pazartesi–cuma **09.00–12.00 ve 13.00–18.00**: kişi başı **480 dakika**.
- Yarım gün **09.00–12.00**: kişi başı **180 dakika**.
- Tam tatil ve hafta sonu: **0 normal iş dakikası**.
- `business_calendar.day_type`: `FULL_DAY`, `HALF_DAY`, `HOLIDAY`, `WEEKEND`.
- İşlem mesai dışında açılabilir; SLA saati sadece tanımlı normal çalışma pencerelerinde ilerler.
- Fiilen normal pencere dışında yapılan aktif çalışma, **fazla mesai** olarak sınıflandırılır; SLA saatini ilerletmez.
- İşlem açılışları 2025 yılı içindedir; yıl sonuna yakın açılan işlemlerin sonraki takibi için 2026 takvim günleri de oluşturulur.

**2025 takvim kapsamı:** 1 Ocak; 29 Mart Ramazan Bayramı arifesi (cumartesi olduğundan normal iş süresi sıfır); 30 Mart–1 Nisan Ramazan Bayramı; 23 Nisan; 1 Mayıs; 19 Mayıs; **5 Haziran Kurban Bayramı arifesi yarım gün**; 6–9 Haziran Kurban Bayramı; 15 Temmuz; 30 Ağustos; **28 Ekim yarım gün**; 29 Ekim. Tarihler fiziksel takvim oluşturulmadan önce resmî kaynakla tekrar doğrulanır. Hafta sonuna denk gelen resmî tatiller için normal çalışma dakikası yine sıfırdır.

## 6. SLA kuralları

### 6.1 Hedefler

| Operasyon | LOW | MEDIUM | HIGH |
|---|---:|---:|---:|
| Kredi | 240 dk | 480 dk | 960 dk |
| Ödeme ve transfer | 60 dk | 120 dk | 240 dk |
| Hesap işlemleri | 120 dk | 240 dk | 480 dk |
| Bilgi güncelleme | 60 dk | 180 dk | 360 dk |
| Yasal takip | 480 dk | 960 dk | 1.920 dk |
| Operasyonel kontrol | 120 dk | 360 dk | 720 dk |

İşlem açılırken geçerli `sla_targets` kaydı seçilir; hedef sonradan değişmez.

### 6.2 Uçtan uca ve kontrol edilebilir operasyonel SLA

**Uçtan uca iş dakikası:** İşlem açılışı ile kapanışı (açık işlemde raporlama kesiti) arasındaki iş takvimi dakikaları.

**Operasyonel iş dakikası:** Uçtan uca iş dakikası − doğrulanmış ve hariç tutulabilir `EXTERNAL_PARTY` / `CUSTOMER` beklemelerinin **birleşik iş dakikaları**. İç kuyruk, iç onay ve teknik bekleme çıkarılmaz. Bekleme süreleri işlem yaşam aralığı ve raporlama kesitiyle sınırlandırılır; çakışmalar bir kez düşülür. Operasyonel süre sıfırın altına inemez.

Her iki süre de açılışta seçilen **aynı SLA hedefiyle** karşılaştırılır. Hedefin tam karşılığı ihlal değildir; **hedefi aşmak** ihlaldir. Tamamlanmış işlem gerçekleşen SLA performansına, açık işlem ise kesit itibarıyla risk/gecikme analizine girer. `CANCELLED` işlemler tamamlanma SLA oranından ayrıdır.

### 6.3 Açık işlemler

Raporlama kesiti **31.12.2025 18.00 Europe/Istanbul**. Kesitte `COMPLETED`, `OPEN`, `CANCELLED` durumları ayrı gösterilir. Açık işlemin kesin tamamlanma süresi yoktur; yalnızca kesite kadar geçen uçtan uca ve operasyonel iş süresi vardır.

Operasyonel hedef kullanımına göre açık işlem sınıfları:

- **NORMAL:** kullanım <%80.
- **AT_RISK:** kullanım ≥%80 ve ≤%100.
- **OVERDUE:** kullanım >%100.

Dış bekleme etkisi, risk sınıfından ayrı bir göstergedir. Tahmini kalan aktif çalışma, benzer tamamlanmış işlemlerden türetilen bir **tahmindir**, gerçekleşmiş süre değildir. Kesit sonrasındaki kapanış, kalite veya bekleme olayları geçmiş rapora taşınmaz.

## 7. Bekleme kuralları

Bekleme türleri: `INTERNAL_QUEUE`, `INTERNAL_APPROVAL`, `TECHNICAL`, `EXTERNAL_PARTY`, `CUSTOMER`.

Her beklemenin gerekçesi, başlangıcı ve varsa bitişi saklanır. Açık beklemede `ended_at` NULL olabilir. Yalnızca `EXTERNAL_PARTY` veya `CUSTOMER` türü, `is_excludable = TRUE` ve `reason_verified = TRUE` beklemeler operasyonel SLA'dan düşülür. İç kuyruk ve iç onay düşülmez. Aktif çalışma ile bekleme aynı işlemde aynı anda gerçekleşmez; örtüşen beklemeler çift sayılmaz. Aşama içi bekleme `(transaction_id, stage_id, visit_number)` ile, aşamalar arası bekleme yalnızca `transaction_id` ile ilişkilendirilebilir.

## 8. Kalite ve yeniden işlem

Kalite olayları `ERROR`, `RETURN`, `CORRECTION` olarak saklanır. Tek kök hata birden fazla düzeltme aksiyonuna ve aşama ziyaretine neden olabilir. `root_event_id` olay ailesini, `related_quality_event_id` ise yeniden işlemle ilişkili kalite olayını gösterir. Bir olay birden çok aktif çalışma aralığına neden olabilir; bu aralıklar yeni hata olarak sayılmaz.

**FTR:** Uygun tamamlanmış işlemler arasında yeniden işlem gerektirmeden tamamlananların oranı. Hata, iade, yeniden işlem içeren işlem sayısı ve yeniden işlem ziyaret sayısı ayrı ölçülür. Operasyonel kontrolün bağımsız işlem türü olması, başka operasyonların kalite olaylarını ikinci kez işlem hacmine eklemez.

## 9. Ekip kapasitesi ve fazla mesai

Kapasite ekip ve gün düzeyinde izlenir; bireysel performans ölçülmez. `team_capacity.employee_count` ilgili gün kullanılabilir çalışan sayısıdır. `available_minutes = employee_count × o günün normal kişi başı çalışma dakikası`. `overtime_capacity_minutes` planlanan/izin verilen ek mesai kapasitesidir; **gerçekleşen fazla mesai değildir**.

Aktif çalışma aralıkları gün ve normal/fazla mesai pencerelerine bölünür. Gerçekleşen fazla mesai dakikaları aktif çalışma kayıtlarından hesaplanır.

| Gösterge | Hesaplama |
|---|---|
| Normal kapasite kullanım oranı | Normal mesai aktif dakika / normal kapasite dakika |
| Fazla mesai iş yükü payı | Fazla mesai aktif dakika / toplam aktif dakika |
| Toplam iş yükü / normal kapasite | (Normal + fazla mesai aktif dakika) / normal kapasite dakika |

Payda sıfırsa oran NULL'dır. Fazla mesai nedeniyle toplam iş yükü/normal kapasite %100'ü aşabilir; bu tek başına veri hatası değildir. Ancak **eşzamanlı aktif iş sayısı**, o zaman dilimindeki kullanılabilir çalışan sayısını aşamaz. Normal kapasite kullanımı, doğru kapasite planıyla %100'ü aşmamalıdır.

## 10. Tahmini maliyet

Maliyetler varsayımsaldır; gerçek banka personel gideri değildir. Örnek başlangıç parametreleri: **600 TL/saat normal maliyet**, **1,5 fazla mesai çarpanı** (900 TL/saat). Gerçek hesaplamada ilgili ekip ve tarihte geçerli `cost_parameters` kullanılır.

**Tahmini maliyet = normal aktif saat × saatlik maliyet + fazla mesai aktif saat × saatlik maliyet × fazla mesai çarpanı.**

Yeniden işlem maliyeti toplam maliyetin içindedir; ikinci kez eklenmez. Tamamlanan işlem başına maliyette yalnızca tamamlanan işlemlere atfedilen maliyetler paya, aynı işlemler paydaya alınır. Açık ve iptal edilen işlemlerin maliyetleri ayrı izlenebilir.

## 11. Koşullara bağlı sentetik veri üretimi ve kalibrasyon

**Üretim sırası:** (1) işlem açılış talebi ve özellikleri, (2) karmaşıklık puanı, (3) aşama/ekip ataması, (4) kapasiteye bağlı aktif çalışma ve bekleme zamanları, (5) kalite ve yeniden işlem olayları, (6) kapanış veya kesitte açık kalma, (7) kaynak olaylardan KPI hesaplama.

- Sabit rastgelelik tohumu (`seed = 2025`) ile tekrar üretilebilirlik sağlanır.
- Açılış yoğunluğu haftanın günü, ay sonu, tatil sonrası ve operasyon türüne bağlı olabilir. Başlangıç kalibrasyon aralıkları: günlük baz hacim çevresinde yaklaşık ±%20; ilgili operasyonlarda ay sonu +%10–25; tatil sonrası ilk uygun iş günlerinde +%10–30. Bunlar **zorunlu sonuç oranları değildir**.
- Karmaşıklık ve aşama özellikleri aktif çalışma süresi dağılımını etkiler. Yüksek karmaşıklık için düşük karmaşıklığa kıyasla yaklaşık 1,8–3 kat süre etkisi ilk kalibrasyon varsayımıdır; her işlem için sabit çarpan değildir.
- Ekipte mevcut iş yükü yükselirse iç kuyrukta bekleme eğilimi artar. Ekipte eşzamanlı aktif iş sayısı kapasite sınırına tabidir.
- Dış koordinasyon gereksinimi dış bekleme olasılığını; karmaşıklık, iş yükü ve aşama niteliği hata/yeniden işlem olasılığını etkileyebilir.
- Hata nedeniyle oluşan yeniden işlem ek aktif zaman ve maliyet tüketir. Kalite olayları ile tekrar ziyaretler birbirinden bağımsız rastgele etiketlenmez.
- İşlemlere rastgele **SLA ihlali**, **FTR sonucu** veya **nihai maliyet** atanmaz; bunlar zaman aralıkları ve olaylardan türetilir.
- Dağılım kalibrasyonu açılış özelliklerinin ve olay üretim mekanizmasının parametreleriyle yapılır; geriye dönük sonuç düzeltmesiyle yapılmaz.

## 12. Pilot veri seti

Tam ölçekli 50.000 işlem öncesinde **300 işlemlik pilot** üretilir:

| Operasyon | Pilot işlem sayısı |
|---|---:|
| Ödeme ve transferler | 90 |
| Müşteri bilgi güncellemeleri | 60 |
| Hesap işlemleri | 54 |
| Kredi operasyonları | 45 |
| Yasal takip operasyonları | 30 |
| Operasyonel kontroller | 21 |
| **Toplam** | **300** |

Pilotun dağılımları yıllık evrenin birebir istatistiksel temsili olmak zorunda değildir. Normal tamamlanma, iki SLA ölçümünün ayrışması, iç kuyruk, doğrulanmış dış bekleme, hata, yeniden işlem, iptal, açık işlem, yarım gün, tam tatil, yıl sonu devri ve fazla mesai gibi **zorunlu sınır durumları** ayrı test senaryolarıyla doğrulanır; bu senaryoların eklenmesi normal dağılımın performans istatistiklerini yapay olarak bozmayacak şekilde raporlanır.

## 13. Veri kalite kabul kriterleri

1. Tüm birincil anahtarlar benzersiz ve NULL değildir; yabancı anahtarlar mevcut kayıtlara işaret eder.
2. İşlem, aşama, çalışma, bekleme ve kalite olayları kronolojik olarak tutarlıdır.
3. Aynı işlemde aktif çalışma ve bekleme aralıkları çakışmaz; süreler çift sayılmaz.
4. Aşama ziyaretleri işlem operasyonuyla uyumludur; aynı ziyaret birden çok çalışma aralığı içerebilir.
5. Karmaşıklık, açılış özelliklerinden aynı kurallarla yeniden hesaplanabilir.
6. SLA hedefi işlem açılışındaki geçerli hedefle eşleşir; sınır eşitliği ihlal değildir.
7. Tatil, yarım gün, öğle arası ve fazla mesai normal SLA iş dakikalarını yanlış ilerletmez.
8. Hariç tutulabilir beklemeler yalnızca uygun ve doğrulanmış dış/müşteri beklemeleridir.
9. Açık işlemler raporlama kesitinde değerlendirilir; gelecekteki olaylar geçmişe taşınmaz.
10. Eşzamanlı ekip aktif iş sayısı kullanılabilir çalışan sayısını aşmaz; normal ve fazla mesai ayrımı doğrudur.
11. Kalite olayı, yeniden işlem ziyareti ve yeniden işlem aktif süresi ayrı sayılır; maliyet çift sayılmaz.
12. Aynı seed ve parametrelerle aynı veri üretilir.
13. Örnek KPI hesaplamaları bağımsız elle hesaplanan sınır senaryolarıyla eşleşir.
14. Pilotun tüm zorunlu sınır durumları kapsanır; istatistiksel kalibrasyon hedefleri kesin veri bütünlüğü kurallarıyla karıştırılmaz.

## 14. Uygulama öncesi son durum

Karmaşıklık, aktif çalışma aralığı, tatil/yarım gün, açık işlem kesiti, kapasite/fazla mesai ve koşullara bağlı sentetik üretim yaklaşımı tasarım düzeyinde belirlenmiştir. **Kod yazılmamış ve pilot henüz üretilmemiştir.** Fiziksel uygulamadan önce `data_dictionary.md`, `data_model.md` ve bu belgedeki alan adlarının aynı sürümü temsil ettiği kontrol edilecek; ardından 300 işlemlik pilot oluşturulup kabul testleri çalıştırılacaktır.

Bu belge, veri üretimi ve analiz aşamasında temel iş kuralı kaynağıdır.
