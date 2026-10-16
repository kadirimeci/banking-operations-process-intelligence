# Veri Sözlüğü — Banking Operations & Process Intelligence

**Kurgusal kurum:** Veriqora Bank  
**Sürüm:** 1.1  
**Durum:** Güncellenmiş mantıksal tasarım; fiziksel uygulama ve pilot test henüz başlamadı.  
**Veri kaynağı:** Tamamen sentetik; gerçek banka, çalışan veya müşteri verisi içermez.

## 1. Amaç

Bu doküman, bankacılık operasyonları ve süreç analitiği projesinde kullanılacak 12 mantıksal tabloyu, veri alanlarını, BigQuery veri tiplerini, ilişkileri ve temel veri bütünlüğü kurallarını tanımlar.

Veri modeli; işlem performansı, iki farklı SLA ölçümü, süreç aşamaları, bekleme süreleri, kalite olayları, ekip kapasitesi ve tahmini işçilik maliyetlerini analiz etmek için tasarlanmıştır.

## 2. Genel standartlar

- Teknik tablo ve sütun adları İngilizcedir; iş açıklamaları Türkçedir.
- Kimlik alanları STRING, tarih alanları DATE, zaman damgaları TIMESTAMP olarak tutulur.
- Süreler dakika cinsinden hesaplanır.
- Parasal değerler NUMERIC veri tipinde saklanır.
- Tarih ve saat yorumlarında Europe/Istanbul saat dilimi kullanılır.
- TIMESTAMP değerleri tek bir zaman standardında saklanır; yerel iş takvimi hesaplamalarında saat dilimi uygulanır.
- NULL kabul edilen alanlar açıkça belirtilir.
- Birincil ve yabancı anahtarlar mantıksal olarak zorunludur. BigQuery üzerinde ilişkisel bütünlük ayrıca veri kalite testleriyle doğrulanır.
- Ana raporlama kesiti 31.12.2025 saat 18.00 (Europe/Istanbul) olarak belirlenmiştir; kesitten sonraki olaylar geçmiş raporlara dahil edilmez.
- İşlem açılışları 2025 yılı içindedir; kapanış ve açık işlem takibi için gerektiğinde 2026 iş takvimi kullanılır.
- Sentetik kayıtlar sabit rastgelelik tohumu kullanılarak yeniden üretilebilir olacaktır.

## 3. Tablo: operations

**Amaç:** Altı bankacılık operasyon türünü tanımlamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| operation_id | STRING | Evet | Birincil anahtar |
| operation_code | STRING | Evet | Benzersiz operasyon kodu |
| operation_name | STRING | Evet | Operasyonun Türkçe adı |
| is_active | BOOL | Evet | Aktiflik durumu |

Operasyonlar: kredi, ödeme ve transfer, hesap işlemleri, müşteri bilgi güncelleme, yasal takip ve operasyonel kontrol.

## 4. Tablo: transactions

**Amaç:** Her operasyonel işlemin ana kaydını saklamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| transaction_id | STRING | Evet | Birincil anahtar |
| operation_id | STRING | Evet | operations tablosuna yabancı anahtar |
| complexity_level | STRING | Evet | LOW, MEDIUM, HIGH; açılışta hesaplanan sınıf |
| opened_at | TIMESTAMP | Evet | Açılış zamanı |
| closed_at | TIMESTAMP | Hayır | Kapanış zamanı |
| final_status | STRING | Evet | COMPLETED, CANCELLED, OPEN |
| sla_target_id | STRING | Evet | Açılışta geçerli SLA hedefi |

**Kurallar:** COMPLETED ve CANCELLED işlemlerinin kapanış zamanı bulunmalıdır. OPEN işlemlerin kapanış zamanı NULL olmalıdır. Kapanış açılıştan önce olamaz. Karmaşıklık açılış anında belirlenir ve daha sonra oluşan hata veya gecikme nedeniyle değişmez. final_status alanı raporlama kesiti itibarıyla yorumlanır; sonraki olaylar geçmiş kesite taşınmaz.

## 5. Tablo: process_stages

**Amaç:** Operasyonlara özgü aşamaları tanımlamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| stage_id | STRING | Evet | Birincil anahtar |
| operation_id | STRING | Evet | İlgili operasyon |
| stage_name | STRING | Evet | Aşamanın Türkçe adı |
| stage_order | INT64 | Evet | Standart iş akışındaki sıra |
| is_mandatory | BOOL | Evet | Aşamanın zorunlu olup olmadığı |

**Kural:** stage_order normal akış sırasını belirtir; yeniden işlem durumunda önceki aşamaya dönüşe izin verilir.

## 6. Tablo: stage_executions

**Amaç:** Bir aşama ziyaretinde gerçekleşen her aktif çalışma zaman aralığını ayrı kayıt olarak saklamak.

**Kayıt düzeyi (grain):** Bir satır = bir aktif çalışma aralığı. Aşama ziyareti, `(transaction_id, stage_id, visit_number)` üçlüsüyle tanımlanır. Aynı ziyarete birden fazla `execution_id` bağlanabilir.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| execution_id | STRING | Evet | Aktif çalışma aralığının benzersiz birincil anahtarı |
| transaction_id | STRING | Evet | İlgili işlem |
| stage_id | STRING | Evet | Gerçekleşen aşama |
| team_id | STRING | Evet | Bu aralıkta çalışmayı yapan ekip |
| visit_number | INT64 | Evet | İlgili işlem ve aşamanın kaçıncı ziyareti; 1'den başlar |
| started_at | TIMESTAMP | Evet | Aktif çalışmanın başlangıcı |
| ended_at | TIMESTAMP | Hayır | Aktif çalışmanın bitişi; sürüyorsa NULL |
| active_minutes | INT64 | Hayır | Tamamlanan aralıkta gerçekleşen toplam dakika; açık aralıkta kesit itibarıyla türetilir |
| execution_status | STRING | Evet | Aktif çalışma aralığının durumu: COMPLETED, IN_PROGRESS, CANCELLED |
| is_rework | BOOL | Evet | Bu çalışma aralığı yeniden işlem ziyaretine mi ait? |
| related_quality_event_id | STRING | Hayır | Yeniden işlemle ilişkili kalite olayının kimliği |

**Kurallar:**

- `execution_id` benzersizdir; `(transaction_id, stage_id, visit_number)` birleşimi **satır bazında benzersiz değildir**.
- Aynı ziyaretin tüm çalışma aralıklarında `is_rework` ve `related_quality_event_id` bilgileri tutarlı olmalıdır.
- `started_at` ve `ended_at` gerçek fiilî çalışma zamanlarıdır; öğle arası veya tatil içinde fiilen çalışıldıysa fazla mesai olarak ayrıştırılır.
- Tamamlanan aralıklarda `active_minutes`, başlangıç ve bitiş arasındaki gerçek dakika ile eşleşir; kesintiler ayrı aralıklar olarak saklanır.
- Açık aralıkta `ended_at` NULL olabilir; süre, raporlama kesitiyle sınırlandırılarak hesaplanır. `active_minutes` kesinleşmemişse NULL tutulur.
- Aktif aralıklar beklemelerle çakışamaz. Ekiplerin eşzamanlı aktif çalışma sayısı o zaman dilimindeki kullanılabilir çalışan sayısını aşamaz.
- Bir çalışma aralığı birden fazla takvim gününe veya normal/fazla mesai penceresine yayılıyorsa ekip-gün kırılımı sorgu sırasında türetilir.
- Aşama ziyaretinin tamamlanma durumu, tek bir `execution_status` değerinden değil ilgili çalışma ve bekleme olaylarının bütünü üzerinden belirlenir.

## 7. Tablo: teams

**Amaç:** Ekip bazlı operasyonel kapasiteyi tanımlamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| team_id | STRING | Evet | Birincil anahtar |
| team_name | STRING | Evet | Ekip adı |
| operation_id | STRING | Evet | Ekibin birincil operasyonu |
| is_active | BOOL | Evet | Aktiflik durumu |

**Kural:** Bir ekibin farklı operasyonların aşamalarını gerçekleştirmesine izin verilir; kapasite gerçek team_id üzerinden hesaplanır.

## 8. Tablo: team_capacity

**Amaç:** Ekiplerin günlük kullanılabilir çalışma kapasitesini saklamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| team_id | STRING | Evet | Birleşik birincil anahtarın parçası |
| capacity_date | DATE | Evet | Birleşik birincil anahtarın parçası |
| employee_count | INT64 | Evet | O gün kullanılabilir çalışan sayısı |
| available_minutes | INT64 | Evet | Normal mesai kapasitesi |
| overtime_capacity_minutes | INT64 | Evet | Planlanan veya izin verilen ek mesai kapasitesi; gerçekleşen fazla mesai değildir |

**Kurallar:** Tüm kapasite alanları negatif olamaz. `available_minutes`, ilgili günün normal çalışma penceresi ve kullanılabilir çalışan sayısı üzerinden hesaplanır (normal gün kişi başı 480, yarım gün 180, tatil 0 dakika). Normal kapasite kullanım oranı **normal mesai içinde gerçekleşen aktif dakikalar / available_minutes** olarak hesaplanır. Gerçekleşen fazla mesai, `stage_executions` zaman aralıklarından türetilir; `overtime_capacity_minutes` ile karıştırılmaz. Sıfır normal kapasitede oran NULL döner. `employee_count` günlük kullanılabilir çalışan sayısıdır; izinli personel bu sayıya dahil edilmez.

## 9. Tablo: waiting_intervals

**Amaç:** İşlem içi ve aşamalar arası beklemeleri, ilgili aşama ziyaretinden bağımsız zaman aralıkları olarak saklamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| waiting_id | STRING | Evet | Birincil anahtar |
| transaction_id | STRING | Evet | İlgili işlem |
| stage_id | STRING | Hayır | İlgili aşama; aşamalar arası beklemede NULL olabilir |
| visit_number | INT64 | Hayır | İlgili aşama ziyaret numarası; `stage_id` ile birlikte dolu veya NULL |
| waiting_type | STRING | Evet | INTERNAL_QUEUE, INTERNAL_APPROVAL, TECHNICAL, EXTERNAL_PARTY, CUSTOMER |
| waiting_reason | STRING | Evet | Bekleme gerekçesi |
| started_at | TIMESTAMP | Evet | Bekleme başlangıcı |
| ended_at | TIMESTAMP | Hayır | Bekleme bitişi; devam ediyorsa NULL |
| is_excludable | BOOL | Evet | Operasyonel SLA'dan düşülebilir mi? |
| reason_verified | BOOL | Evet | Bekleme gerekçesi doğrulandı mı? |

**Kurallar:** `stage_id` ve `visit_number` birlikte kullanılarak aşama ziyaretine bağlanır; herhangi bir tekil aktif çalışma kaydına bağlanmaz. İkisi NULL ise aşamalar arası/işlem düzeyinde beklemedir. Yalnızca EXTERNAL_PARTY veya CUSTOMER türündeki, `is_excludable = TRUE` ve `reason_verified = TRUE` olan beklemeler operasyonel SLA'dan çıkarılır. Çıkarılacak süre, iş takvimi ve raporlama kesitiyle kesişen **birleşik** bekleme aralıklarından hesaplanır. Beklemeler çift sayılmaz; aktif çalışmayla çakışamaz.

## 10. Tablo: quality_events

**Amaç:** Hata, iade ve düzeltme olaylarını izlemek.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| event_id | STRING | Evet | Birincil anahtar |
| transaction_id | STRING | Evet | İlgili işlem |
| stage_id | STRING | Hayır | Olayın ilişkili olduğu aşama; işlem düzeyinde olayda NULL |
| visit_number | INT64 | Hayır | İlgili aşama ziyareti; stage_id ile birlikte dolu veya NULL |
| event_type | STRING | Evet | ERROR, RETURN, CORRECTION |
| error_category | STRING | Hayır | Hata kategorisi |
| detected_at | TIMESTAMP | Evet | Olay tespit zamanı |
| resolved_at | TIMESTAMP | Hayır | Çözüm zamanı |
| requires_rework | BOOL | Evet | Yeniden işlem gerektiriyor mu? |
| root_event_id | STRING | Hayır | İlgili kök kalite olayı |

**Kurallar:** Kalite olayı tekil çalışma aralığına değil, işlem veya `(transaction_id, stage_id, visit_number)` aşama ziyaretine bağlanır. Bir kök hata birden fazla tekrar ziyareti oluşturabilir. Hata sayısı tekrar ziyaret sayısından türetilmez. Kök hata ve ilişkili aksiyonlar ayrı sayılmamalıdır. FTR tamamlanmış ve değerlendirmeye uygun işlemler için hesaplanır.

## 11. Tablo: sla_targets

**Amaç:** Operasyon ve karmaşıklık bazlı SLA hedeflerini saklamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| sla_target_id | STRING | Evet | Birincil anahtar |
| operation_id | STRING | Evet | İlgili operasyon |
| complexity_level | STRING | Evet | LOW, MEDIUM, HIGH |
| target_minutes | INT64 | Evet | SLA hedefi, iş dakikası |
| valid_from | DATE | Evet | Geçerlilik başlangıcı |
| valid_to | DATE | Hayır | Geçerlilik bitişi |

**Kurallar:** target_minutes sıfırdan büyük olmalıdır. Aynı operasyon ve karmaşıklık için geçerlilik aralıkları çakışamaz. İşlem açıldığında seçilen hedef işlem boyunca değişmez.

## 12. Tablo: business_calendar

**Amaç:** İş günü, tatil ve çalışma saatlerini tanımlamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| calendar_date | DATE | Evet | Birincil anahtar |
| is_business_day | BOOL | Evet | En az bir normal çalışma penceresi var mı? |
| day_type | STRING | Evet | FULL_DAY, HALF_DAY, HOLIDAY, WEEKEND |
| business_start | TIME | Hayır | Mesai başlangıcı |
| lunch_start | TIME | Hayır | Öğle arası başlangıcı |
| lunch_end | TIME | Hayır | Öğle arası bitişi |
| business_end | TIME | Hayır | Mesai bitişi |
| holiday_name | STRING | Hayır | Tatil veya yarım gün açıklaması |

**Kurallar:** Normal çalışma saatleri 09.00–12.00 ve 13.00–18.00'dir. HALF_DAY günlerde 09.00–12.00 (180 dakika) çalışılır ve öğle arası alanları NULL olabilir. HOLIDAY ve WEEKEND günlerinde çalışma süresi sıfırdır; saat alanları NULL'dır. 2025 Türkiye resmî tatilleri ve ilgili yarım günler işlenir; 2026'ya taşan işlemler için gerekli takvim günleri de eklenir.

## 13. Tablo: cost_parameters

**Amaç:** Ekip bazlı varsayımsal işçilik maliyetlerini saklamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| cost_parameter_id | STRING | Evet | Birincil anahtar |
| team_id | STRING | Evet | İlgili ekip |
| valid_from | DATE | Evet | Geçerlilik başlangıcı |
| valid_to | DATE | Hayır | Geçerlilik bitişi |
| hourly_cost | NUMERIC | Evet | Varsayımsal saatlik işçilik maliyeti |
| overtime_multiplier | NUMERIC | Evet | Fazla mesai maliyet çarpanı |

**Kurallar:** hourly_cost negatif olamaz; overtime_multiplier en az 1 olmalıdır. Ekip bazlı geçerlilik aralıkları çakışamaz. Maliyet aktif çalışma süresi ve ilgili tarihte geçerli parametrelerle hesaplanır.

## 14. Tablo: transaction_attributes

**Amaç:** İşlem açılışında bilinen, operasyon ve karmaşıklık değerlendirmesinde kullanılabilecek özellikleri saklamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| transaction_id | STRING | Evet | Birincil ve yabancı anahtar |
| request_type | STRING | Evet | Operasyona özgü talep türü; standart dışı/kapsamlı/kimlik-yetki değişikliği bu alandan anlaşılır |
| document_count | INT64 | Hayır | Belge sayısı |
| requires_approval | BOOL | Evet | Onay gerekiyor mu? |
| requires_external_party | BOOL | Evet | Dış taraf gerekiyor mu? |
| requires_manual_review | BOOL | Evet | Manuel inceleme gerekiyor mu? |
| amount_band | STRING | Hayır | LOW, MEDIUM, HIGH; ödeme/transfer için sentetik tutar aralığı |

**Kurallar:** Karmaşıklık yalnızca işlem açılışında bilinen özelliklerden belirlenir. Gerçekleşen süre, hata veya SLA sonucu sınıflandırmada kullanılmaz. Operasyona özgü puanlar ve 0–2 LOW, 3–5 MEDIUM, 6+ HIGH eşikleri `business_rules.md` içerisinde sürümlü olarak belgelenir; bu tablo açılış özelliklerini, `transactions.complexity_level` ise hesaplanan sonucu saklar.

## 15. Temel ilişkiler

- operations (1) → transactions (N)
- operations (1) → process_stages (N)
- operations (1) → sla_targets (N)
- operations (1) → teams (N), birincil operasyon ilişkisi
- transactions (1) → stage_executions (N)
- transactions (1) → waiting_intervals (N)
- transactions (1) → quality_events (N)
- transactions (1) → transaction_attributes (1)
- process_stages (1) → stage_executions (N)
- teams (1) → stage_executions (N)
- teams (1) → team_capacity (N)
- teams (1) → cost_parameters (N)
- (transaction_id, stage_id, visit_number) aşama ziyareti (1) → stage_executions aktif çalışma aralıkları (N)
- (transaction_id, stage_id, visit_number) aşama ziyareti (1) → waiting_intervals (N), isteğe bağlı
- (transaction_id, stage_id, visit_number) aşama ziyareti (1) → quality_events (N), isteğe bağlı
- quality_events (1) → stage_executions (N), related_quality_event_id üzerinden yeniden işlem ilişkisi
- quality_events (1) → quality_events (N), kök olay ilişkisi
- sla_targets (1) → transactions (N)

business_calendar, işlem ve olay zamanlarının iş dakikasına dönüştürülmesinde kullanılır. cost_parameters tarih aralığı ve team_id ile eşleştirilir.

## 16. Türetilmiş KPI'lar

| KPI | Hesaplama yaklaşımı |
|---|---|
| İşlem hacmi | İlgili dönemde açılan benzersiz işlem sayısı |
| Tamamlanma süresi | Açılış ve kapanış arasındaki iş dakikası |
| Uçtan uca SLA kullanım oranı | Uçtan uca iş dakikası / hedef dakika |
| Operasyonel SLA kullanım oranı | (Uçtan uca iş dakikası - doğrulanmış hariç tutulabilir bekleme) / hedef dakika |
| SLA ihlal oranı | Hedefi aşan uygun tamamlanmış işlemler / uygun tamamlanmış işlemler |
| FTR | Yeniden işlem gerektirmeden tamamlanan uygun işlemler / uygun tamamlanmış işlemler |
| Yeniden işlem oranı | Yeniden işlem içeren uygun tamamlanmış işlemler / uygun tamamlanmış işlemler |
| Aktif çalışma süresi | Çalışma aralıklarının gerçek dakikaları toplamı; raporlama kesitinde açık aralıklar sınırlandırılır |
| Normal kapasite kullanım oranı | Ekip-gün normal mesai aktif dakikaları / normal mesai kapasitesi |
| Fazla mesai iş yükü oranı | Ekip-gün fazla mesai aktif dakikaları / toplam aktif dakikalar |
| Toplam iş yükü / normal kapasite | (Normal + fazla mesai aktif dakikaları) / normal kapasite |
| Açık işlem gecikmesi | Raporlama kesitindeki kontrol edilebilir iş dakikaları > SLA hedefi |
| Açık işlem risk sınıfı | Operasyonel hedef kullanımı < %80: normal; %80–%100: risk altında; > %100: gecikmiş |
| Dış bekleme etkisi | Açık işlemde uçtan uca hedef aşılmış ancak operasyonel hedef aşılmamışsa ayrıca işaretlenir |
| Tahmini kalan aktif iş yükü | Benzer operasyon/karmaşıklık/aşama örneklerinden türetilen tahmin; gerçekleşmiş süreden ayrı |
| Tahmini işçilik maliyeti | Normal aktif saat × geçerli saatlik maliyet + fazla mesai aktif saat × saatlik maliyet × geçerli fazla mesai çarpanı |
| Ortalama birim maliyet | Tamamlanmış işlemlere atfedilen maliyet / tamamlanmış işlem sayısı |

Açık işlemlerin gecikme durumu raporlama tarihi itibarıyla ayrıca hesaplanır. Tamamlanmış işlemlerin SLA oranlarına dahil edilmez.

## 17. Veri kalite kuralları

- Birincil anahtarlar benzersiz ve NULL olmayan değerler içermelidir.
- Yabancı anahtarlar mevcut kayıtları göstermelidir.
- Zaman aralıkları kronolojik olarak geçerli olmalıdır.
- Aktif çalışma ve bekleme aralıkları çift sayılmamalıdır.
- İşlem aşamaları ait oldukları operasyonla uyumlu olmalıdır.
- Aşama ziyaret numaraları aynı işlem ve aşamada ardışık olmalıdır; aynı ziyaret birden fazla aktif çalışma satırında tekrar edebilir.
- SLA ve maliyet geçerlilik aralıkları çakışmamalıdır.
- Açık işlemler kapanmış gibi değerlendirilmemelidir.
- Raporlama kesitinden sonraki olaylar geçmiş KPI'lara yansıtılmamalıdır.
- Ekip-gün kapasite ve iş yükü hesaplarında tarih dağılımı korunmalı; normal mesai ve fazla mesai ayrı sayılmalıdır.
- Aynı ekipte eşzamanlı aktif çalışma sayısı kullanılabilir çalışan sayısını aşmamalıdır.
- Açık beklemeler ve açık aktif aralıklar raporlama kesitinde sonlandırılarak hesaplanmalı; geçmiş raporlar gelecekteki olaylarla değiştirilmemelidir.
- Hata sayısı ve yeniden işlem sayısı birbirinden bağımsız hesaplanmalıdır.
- Sentetik veri üretimi sabit seed ile tekrarlanabilir olmalıdır.

## 18. Örnek test senaryoları

| İşlem | Senaryo | Uçtan uca SLA | Operasyonel SLA | FTR |
|---|---|---:|---:|---|
| TXN-001 | Sorunsuz bilgi güncelleme | %75 | %75 | Evet |
| TXN-002 | Belgelenmiş dış beklemeli kredi işlemi | %150 | %87,5 | Evet |
| TXN-003 | Hata ve yeniden işlem içeren hesap işlemi | %125 | %125 | Hayır |

Bu değerler sentetik tasarım testlerine aittir; gerçek banka performansını temsil etmez.

## 19. Onaylanan tasarım kararları ve pilot kontrolü

- **Aktif çalışma:** Tek satır bir aktif çalışma aralığıdır; aşama ziyareti `(transaction_id, stage_id, visit_number)` ile gruplanır.
- **Karmaşıklık:** Açılış özelliklerinden operasyona özel puanlama; LOW 0–2, MEDIUM 3–5, HIGH 6+.
- **İş takvimi:** 2025 Türkiye tatilleri, yarım günler ve Europe/Istanbul; ihtiyaç halinde 2026 günleri.
- **Raporlama kesiti:** 31.12.2025 18.00; açık işlemler ayrı SLA ve iş yükü analizine tabidir.
- **Kapasite:** Normal mesai iş yükü ve gerçekleşmiş fazla mesai ayrı ölçülür; planlanan fazla mesai kapasitesi ayrı saklanır.
- **Maliyet:** Normal ve fazla mesai aktif çalışma süreleri farklı maliyet katsayılarıyla hesaplanır.
- **Sentetik üretim:** Koşullara bağlı, tekrarlanabilir üretim; KPI sonuçları olaylardan türetilir.
- **Pilot:** 300 işlem; 6 operasyon, 3 karmaşıklık seviyesi, 12 mantıksal tablo. Zorunlu sınır durumları ayrıca test edilir.

**Pilot veri kalite kapıları:** Anahtar bütünlüğü, kronolojik tutarlılık, çakışmasız aktif çalışma/bekleme, karmaşıklık tekrar hesaplanabilirliği, tatil/yarım gün SLA örnekleri, açık işlem kesiti, ekip eşzamanlı kapasite sınırı, fazla mesai ayrımı, kalite ve maliyetin çift sayılmaması, aynı seed ile tekrar üretim.

**Fiziksel uygulama notu:** Aşama ziyaretleri ayrı bir fiziksel tablo olmadan üçlü anahtarla temsil edildiğinden, bekleme/kalite kayıtlarının işaret ettiği ziyaretlerin varlığı ve aşama yaşam döngüsü veri kalite testleriyle doğrulanacaktır. Veri üretimi sırasında aşama ziyaretine ait en az bir aktif çalışma aralığı üretilmesi beklenir; sıfır aktif çalışmalı ziyaretler bu modelin kapsamı dışındadır.

Bu kontroller tamamlanmadan 50.000 işlemlik nihai veri seti üretilmeyecektir.
