# Veri Sözlüğü — Banking Operations & Process Intelligence

**Kurgusal kurum:** NovaBank  
**Sürüm:** 1.0  
**Durum:** Mantıksal veri modeli onaylandı; fiziksel uygulama henüz başlamadı.  
**Veri kaynağı:** Tamamen sentetik

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
- Raporlama kesiti 31.12.2025 olarak planlanmıştır; kesitten sonraki olaylar geçmiş raporlara dahil edilmez.
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
| complexity_level | STRING | Evet | LOW, MEDIUM, HIGH |
| opened_at | TIMESTAMP | Evet | Açılış zamanı |
| closed_at | TIMESTAMP | Hayır | Kapanış zamanı |
| final_status | STRING | Evet | COMPLETED, CANCELLED, OPEN |
| sla_target_id | STRING | Evet | Açılışta geçerli SLA hedefi |

**Kurallar:** COMPLETED ve CANCELLED işlemlerinin kapanış zamanı bulunmalıdır. OPEN işlemlerin kapanış zamanı NULL olmalıdır. Kapanış açılıştan önce olamaz. Karmaşıklık açılış anında belirlenir.

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

**Amaç:** İşlemlerin gerçekleşen aşama ziyaretlerini ve aktif çalışma sürelerini saklamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| execution_id | STRING | Evet | Birincil anahtar |
| transaction_id | STRING | Evet | İlgili işlem |
| stage_id | STRING | Evet | Gerçekleşen aşama |
| team_id | STRING | Evet | Çalışmayı gerçekleştiren ekip |
| visit_number | INT64 | Evet | Aynı aşamaya kaçıncı giriş |
| started_at | TIMESTAMP | Evet | Aşama başlangıcı |
| ended_at | TIMESTAMP | Hayır | Aşama bitişi |
| active_minutes | INT64 | Evet | Bu aşamada harcanan aktif dakika |
| execution_status | STRING | Evet | COMPLETED, IN_PROGRESS, CANCELLED |
| is_rework | BOOL | Evet | Yeniden işlem ziyareti mi? |
| related_quality_event_id | STRING | Hayır | Yeniden işleme neden olan kalite olayı |

**Kurallar:** active_minutes negatif olamaz. Aynı işlem ve aşamada visit_number benzersizdir. Aşama, işlemin operasyonuna ait olmalıdır. related_quality_event_id mevcut bir kalite olayına bağlanmalıdır. Aşama farklı günlere taşıyorsa aktif dakikaların ekip-gün dağılımı zaman aralıkları üzerinden hesaplanmalıdır.

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
| overtime_minutes | INT64 | Evet | Fazla mesai kapasitesi |

**Kurallar:** Tüm kapasite alanları negatif olamaz. Temel kullanım oranı aktif çalışma dakikası / normal mesai kapasitesi olarak hesaplanır. Fazla mesai ayrıca raporlanır. Sıfır kapasitede oran NULL döner.

## 9. Tablo: waiting_intervals

**Amaç:** İşlem içi ve aşamalar arası beklemeleri saklamak.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| waiting_id | STRING | Evet | Birincil anahtar |
| transaction_id | STRING | Evet | İlgili işlem |
| execution_id | STRING | Hayır | İlgili aşama; aşamalar arası beklemede NULL olabilir |
| waiting_type | STRING | Evet | INTERNAL_QUEUE, INTERNAL_APPROVAL, TECHNICAL, EXTERNAL_PARTY, CUSTOMER |
| waiting_reason | STRING | Evet | Bekleme gerekçesi |
| started_at | TIMESTAMP | Evet | Bekleme başlangıcı |
| ended_at | TIMESTAMP | Hayır | Bekleme bitişi |
| is_excludable | BOOL | Evet | Operasyonel SLA'dan düşülebilir mi? |
| reason_verified | BOOL | Evet | Bekleme gerekçesi doğrulandı mı? |

**Kurallar:** Yalnızca EXTERNAL_PARTY veya CUSTOMER türündeki, is_excludable ve reason_verified değerleri TRUE olan beklemeler operasyonel SLA'dan çıkarılır. Bekleme aralıkları iş takvimine göre hesaplanır. Çakışan aralıklar çift sayılmaz. Bekleme, aktif çalışmayla aynı anda sayılmaz.

## 10. Tablo: quality_events

**Amaç:** Hata, iade ve düzeltme olaylarını izlemek.

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| event_id | STRING | Evet | Birincil anahtar |
| transaction_id | STRING | Evet | İlgili işlem |
| execution_id | STRING | Hayır | Hatanın tespit edildiği aşama |
| event_type | STRING | Evet | ERROR, RETURN, CORRECTION |
| error_category | STRING | Hayır | Hata kategorisi |
| detected_at | TIMESTAMP | Evet | Olay tespit zamanı |
| resolved_at | TIMESTAMP | Hayır | Çözüm zamanı |
| requires_rework | BOOL | Evet | Yeniden işlem gerektiriyor mu? |
| root_event_id | STRING | Hayır | İlgili kök kalite olayı |

**Kurallar:** Bir kök hata birden fazla tekrar ziyareti oluşturabilir. Hata sayısı tekrar ziyaret sayısından türetilmez. Kök hata ve ilişkili aksiyonlar ayrı sayılmamalıdır. FTR tamamlanmış ve değerlendirmeye uygun işlemler için hesaplanır.

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
| is_business_day | BOOL | Evet | Çalışma günü mü? |
| business_start | TIME | Hayır | Mesai başlangıcı |
| lunch_start | TIME | Hayır | Öğle arası başlangıcı |
| lunch_end | TIME | Hayır | Öğle arası bitişi |
| business_end | TIME | Hayır | Mesai bitişi |
| holiday_name | STRING | Hayır | Tatil veya yarım gün açıklaması |

**Kurallar:** Normal çalışma saatleri 09.00–12.00 ve 13.00–18.00'dir. Tam tatillerde çalışma süresi sıfırdır. Yarım günler için geçerli saatler ayrıca tanımlanır.

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
| request_type | STRING | Evet | Talep türü |
| document_count | INT64 | Hayır | Belge sayısı |
| requires_approval | BOOL | Evet | Onay gerekiyor mu? |
| requires_external_party | BOOL | Evet | Dış taraf gerekiyor mu? |
| requires_manual_review | BOOL | Evet | Manuel inceleme gerekiyor mu? |
| amount_band | STRING | Hayır | Tutar aralığı; gerçek tutar veya müşteri verisi değil |

**Kurallar:** Karmaşıklık yalnızca işlem açılışında bilinen özelliklerden belirlenir. Gerçekleşen süre, hata veya SLA sonucu karmaşıklık sınıflandırmasında kullanılmaz.

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
- stage_executions (1) → waiting_intervals (N), isteğe bağlı
- stage_executions (1) → quality_events (N), isteğe bağlı
- quality_events (1) → stage_executions (N), yeniden işlem ilişkisi
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
| Aktif çalışma süresi | Aşama ziyaretlerindeki aktif dakikaların toplamı |
| Kapasite kullanım oranı | Ekip-gün aktif çalışma dakikası / normal mesai kapasitesi |
| Tahmini işçilik maliyeti | Aktif çalışma saatleri × geçerli ekip saatlik maliyeti |
| Ortalama birim maliyet | Tamamlanmış işlemlere atfedilen maliyet / tamamlanmış işlem sayısı |

Açık işlemlerin gecikme durumu raporlama tarihi itibarıyla ayrıca hesaplanır. Tamamlanmış işlemlerin SLA oranlarına dahil edilmez.

## 17. Veri kalite kuralları

- Birincil anahtarlar benzersiz ve NULL olmayan değerler içermelidir.
- Yabancı anahtarlar mevcut kayıtları göstermelidir.
- Zaman aralıkları kronolojik olarak geçerli olmalıdır.
- Aktif çalışma ve bekleme aralıkları çift sayılmamalıdır.
- İşlem aşamaları ait oldukları operasyonla uyumlu olmalıdır.
- Tekrar ziyaret numaraları aynı işlem ve aşamada benzersiz olmalıdır.
- SLA ve maliyet geçerlilik aralıkları çakışmamalıdır.
- Açık işlemler kapanmış gibi değerlendirilmemelidir.
- Raporlama kesitinden sonraki olaylar geçmiş KPI'lara yansıtılmamalıdır.
- Ekip-gün kapasite ve iş yükü hesaplarında tarih dağılımı korunmalıdır.
- Hata sayısı ve yeniden işlem sayısı birbirinden bağımsız hesaplanmalıdır.
- Sentetik veri üretimi sabit seed ile tekrarlanabilir olmalıdır.

## 18. Örnek test senaryoları

| İşlem | Senaryo | Uçtan uca SLA | Operasyonel SLA | FTR |
|---|---|---:|---:|---|
| TXN-001 | Sorunsuz bilgi güncelleme | %75 | %75 | Evet |
| TXN-002 | Belgelenmiş dış beklemeli kredi işlemi | %150 | %87,5 | Evet |
| TXN-003 | Hata ve yeniden işlem içeren hesap işlemi | %125 | %125 | Hayır |

Bu değerler sentetik tasarım testlerine aittir; gerçek banka performansını temsil etmez.

## 19. Uygulama öncesi doğrulanacak ayrıntılar

Bu sözlük mantıksal modelin temelini oluşturur. Fiziksel veri üretimi öncesinde şu konular ayrıca netleştirilecektir:

1. Aşama aktif dakikalarının gün ve ekip bazında doğru dağıtılması için zaman aralığı ayrıntısı.
2. Aşama başlangıç/bitişleri ile beklemeler arasındaki zaman bütünlüğü.
3. Açık aşamalar ve açık beklemelerin raporlama kesitinde hesaplanması.
4. Normal mesai ve fazla mesai maliyetlerinin ayrıştırılması.
5. Operasyona özgü karmaşıklık kurallarının kesinleştirilmesi.

Bu kontroller tamamlanmadan 50.000 işlemlik nihai veri seti üretilmeyecektir.
