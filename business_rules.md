# İş Kuralları ve Sentetik Veri Üretim İlkeleri

**Proje:** Bankacılık Operasyonları ve Süreç Analitiği  
**Kurgusal kurum:** NovaBank  
**Sürüm:** 1.0  
**Durum:** Tasarım aşaması — teknik uygulama öncesi

## 1. Amaç

Bu belge, sentetik işlem verilerinin üretiminde ve analizinde uygulanacak iş kurallarını tanımlar. Hedef, sonuçları önceden belirlenmiş KPI değerleri üretmek değil; gerçekçi operasyonel davranışlardan hesaplanabilir sonuçlar elde etmektir.

## 2. Veri kapsamı

2025 yılı içerisinde açılan toplam 50.000 sentetik işlem planlanmaktadır.

| Operasyon | Planlanan işlem sayısı |
|---|---:|
| Ödeme ve transferler | 15.000 |
| Müşteri bilgi güncellemeleri | 10.000 |
| Hesap işlemleri | 9.000 |
| Kredi operasyonları | 7.500 |
| Yasal takip operasyonları | 5.000 |
| Operasyonel kontroller | 3.500 |
| **Toplam** | **50.000** |

Bu dağılım gerçek banka istatistiği değildir.

## 3. Karmaşıklık sınıflandırması

Karmaşıklık LOW, MEDIUM ve HIGH olarak üç seviyede tutulur. Sınıflandırma yalnızca işlem açılışında bilinen özelliklere dayanır.

| Operasyon | Düşük karmaşıklık | Orta karmaşıklık | Yüksek karmaşıklık |
|---|---|---|---|
| Kredi | Standart talep, az belge, ek inceleme yok | Daha fazla belge veya ek onay | Çoklu kontrol, manuel inceleme ve dış taraf gereksinimi |
| Ödeme ve transfer | Standart transfer, ek kontrol yok | Ek doğrulama veya onay | Birden fazla kontrol ve manuel inceleme |
| Hesap işlemleri | Standart hesap talebi | Yetki kontrolü veya ek onay | Çok aşamalı onay ve manuel inceleme |
| Bilgi güncelleme | Basit iletişim bilgisi güncellemesi | Belge veya ek doğrulama | Çoklu bilgi değişikliği ve manuel inceleme |
| Yasal takip | Standart kayıt ve belge kontrolü | Ek belge veya dış koordinasyon | Çoklu belge, manuel inceleme ve dış koordinasyon |
| Operasyonel kontrol | Rutin kontrol | İlave kontrol veya onay | Çok aşamalı inceleme ve düzeltme gereksinimi |

**Önemli:** Hata gerçekleşmesi, yeniden işlem veya SLA ihlali karmaşıklık seviyesini geriye dönük değiştirmez. Yukarıdaki açıklamalar kavramsal sınıflardır; kesin karar sırası ve eşik değerleri küçük test veri seti öncesinde netleştirilecektir.

## 4. İş akışları

Her operasyon kendine ait aşamalardan oluşur. Aşamalar normal sırada ilerleyebilir, isteğe bağlı olabilir veya yeniden işlem nedeniyle tekrarlanabilir.

| Operasyon | Standart akış |
|---|---|
| Kredi | Talep → Belge kontrolü → Operasyonel inceleme → Onay → Tamamlama |
| Ödeme ve transfer | Talep → Doğrulama → İsteğe bağlı kontrol → İşleme alma → Kapanış |
| Hesap işlemleri | Talep → Kimlik/yetki kontrolü → Hesap işlemi → İsteğe bağlı onay → Tamamlama |
| Bilgi güncelleme | Talep → Bilgi kontrolü → Güncelleme → Doğrulama → Tamamlama |
| Yasal takip | Dosya kaydı → Belge kontrolü → İnceleme → Dış koordinasyon → Kapanış |
| Operasyonel kontrol | Kontrol kaydı → İnceleme → Bulgu değerlendirme → İsteğe bağlı düzeltme → Kapanış |

Aşama ziyareti ve kalite olayı farklı kavramlardır. Bir hata birden fazla aşama tekrarına neden olabilir.

## 5. Çalışma takvimi

- Standart çalışma günleri pazartesi–cumadır.
- Normal mesai 09.00–12.00 ve 13.00–18.00 aralığındadır.
- Öğle arası iş süresine dahil edilmez.
- Tam gün resmî tatillerde iş süresi sıfırdır.
- Yarım günler takvimdeki geçerli çalışma saatleriyle temsil edilir.
- Zaman damgaları Europe/Istanbul yerel saatine dönüştürülerek iş takvimine uygulanır.
- İşlemler mesai dışında açılabilir; SLA süresi yalnızca tanımlı çalışma pencerelerinde ilerler.

## 6. SLA kuralları

### 6.1 Hedef süreler

| Operasyon | LOW | MEDIUM | HIGH |
|---|---:|---:|---:|
| Kredi | 4 saat | 8 saat | 16 saat |
| Ödeme ve transfer | 1 saat | 2 saat | 4 saat |
| Hesap işlemleri | 2 saat | 4 saat | 8 saat |
| Bilgi güncelleme | 1 saat | 3 saat | 6 saat |
| Yasal takip | 8 saat | 16 saat | 32 saat |
| Operasyonel kontrol | 2 saat | 6 saat | 12 saat |

### 6.2 Uçtan uca SLA

İşlem açılışından kapanışına kadar geçen iş takvimi dakikalarının, açılışta belirlenen hedef dakikaya oranıdır.

### 6.3 Kontrol edilebilir operasyonel SLA

Uçtan uca iş süresinden yalnızca belgelenmiş, doğrulanmış ve hariç tutulabilir müşteri veya dış taraf beklemeleri çıkarılır.

İç kuyruk, iç onay ve iç teknik bekleme süreleri çıkarılmaz.

Aynı zaman dilimi birden fazla bekleme kaydında bulunuyorsa çifte düşüm yapılamaz.

### 6.4 SLA ihlali

Hesaplanan iş süresi hedefi aşıyorsa ihlal vardır. Hedefe tam eşit süre ihlal sayılmaz.

Tamamlanmış işlemlerin gerçekleşen SLA performansı ile açık işlemlerin raporlama tarihi itibarıyla gecikme durumu ayrı değerlendirilir.

## 7. Bekleme kuralları

Beklemeler INTERNAL_QUEUE, INTERNAL_APPROVAL, TECHNICAL, EXTERNAL_PARTY ve CUSTOMER olarak sınıflandırılır.

Bekleme gerekçesi, başlangıcı ve bitişi kaydedilir. Devam eden beklemelerde bitiş zamanı NULL olabilir.

SLA'dan düşülebilmesi için beklemenin dış taraf veya müşteri kaynaklı olması, hariç tutulabilir olarak işaretlenmesi ve gerekçesinin doğrulanması gerekir.

Aktif çalışma ile bekleme aralıkları aynı zaman diliminde çakışamaz.

## 8. Kalite ve yeniden işlem

Kalite olayları ERROR, RETURN ve CORRECTION türlerinde saklanır.

- Tek bir kök hata birden fazla aksiyona neden olabilir.
- Tekrar ziyaretler otomatik olarak yeni hata sayılmaz.
- Yeniden işlem gerektiren ziyaretler is_rework ile işaretlenir.
- İlgili kalite olayı varsa related_quality_event_id ile bağlanır.
- FTR, yeniden işlem gerektirmeden tamamlanan uygun işlemlerin oranıdır.
- Hata sayısı, iade sayısı ve yeniden işlem oranı ayrı hesaplanır.

Operasyonel kontrolün bağımsız bir işlem türü olması, başka operasyonlarda kaydedilen kalite olaylarının ikinci kez işlem hacmine eklenmesi anlamına gelmez.

## 9. Ekip kapasitesi

Kapasite ekip ve gün seviyesinde izlenir. Bireysel çalışan performansı değerlendirilmez.

Normal mesai kapasitesi, o gün kullanılabilir çalışan sayısı ve kişi başına kullanılabilir çalışma süresine göre belirlenir.

Aktif çalışma dakikaları, çalışmayı yapan ekibe ve gerçekleştiği güne atanır.

**Temel kapasite kullanım oranı:** Aktif çalışma dakikaları / normal mesai kullanılabilir dakikaları.

Fazla mesai ayrıca gösterilir. Normal mesai kapasitesinin aşılması otomatik veri hatası kabul edilmez; fazla mesai ve kapasite varsayımlarıyla birlikte incelenir.

## 10. Tahmini maliyet

Tahmini işçilik maliyeti, aktif çalışma süresi ile ilgili tarihte geçerli ekip saatlik maliyetinin çarpımından elde edilir.

Fazla mesai maliyetleri uygun çarpanla ayrı hesaplanır.

Yeniden işlem maliyeti toplam işçilik maliyetinin bir bileşenidir; ikinci kez eklenmez.

Tamamlanan işlem başına maliyet hesaplanırken pay ve paydanın aynı işlem kümesini temsil etmesi gerekir.

Maliyetler varsayımsaldır; gerçek banka maliyetleri olarak yorumlanamaz.

## 11. Sentetik veri üretim ilkeleri

- Sabit rastgelelik tohumu kullanılarak tekrar üretilebilir veri oluşturulur.
- İşlem türü, karmaşıklık, aşama sayısı ve aktif çalışma süresi arasında anlamlı ilişkiler kurulur.
- İş yükü arttığında iç kuyruk sürelerinin artma olasılığı yükselir.
- Yüksek karmaşıklıkta manuel inceleme ve yeniden işlem olasılığı daha yüksek olabilir.
- Dış taraf gerektiren işlemlerde dış bekleme olasılığı artabilir.
- Otomasyona uygun standart işlemlerde aktif çalışma süresi daha düşük olabilir.
- Hata ve yeniden işlem kapasite tüketimini artırır.
- SLA ihlal durumu doğrudan rastgele atanmaz; oluşan olay zamanlarından hesaplanır.
- FTR ve maliyet gibi KPI'lar da kaynak olaylardan türetilir.
- Üretilen dağılımlar gerçek banka istatistiği olarak sunulmaz.

## 12. Raporlama kesiti ve açık işlemler

Ana raporlama tarihi 31.12.2025'tir.

Bu tarihte henüz kapanmamış işlemler açık kabul edilir. Sonraki tarihte gerçekleşen kapanış veya düzeltme olayları geçmiş raporlara yansıtılmaz.

İptal edilen işlemler, tamamlanan işlem performansından ayrı tutulur.

## 13. Veri kalite kabul kuralları

1. Tüm birincil anahtarlar benzersiz olmalıdır.
2. Yabancı anahtarlar geçerli kayıtları göstermelidir.
3. İşlem ve aşama zamanları kronolojik olarak tutarlı olmalıdır.
4. Aktif çalışma ve bekleme süreleri çift sayılmamalıdır.
5. Aşamalar ilgili operasyonun tanımlı iş akışına uygun olmalıdır.
6. SLA hedefi açılış tarihindeki geçerli kayıttan seçilmelidir.
7. Dış beklemelerin hariç tutulma koşulları doğrulanmalıdır.
8. Yeniden işlem ile hata olayları ayrı sayılmalıdır.
9. Ekip kapasitesi ve aktif iş yükü aynı gün bazında karşılaştırılmalıdır.
10. Gelecekteki olaylar geçmiş raporlara dahil edilmemelidir.
11. Aynı seed ile aynı sentetik veri yeniden üretilebilmelidir.
12. Kaynak veriden hesaplanan KPI'lar örnek test senaryolarıyla tutarlı olmalıdır.

## 14. Teknik geliştirme öncesi son kararlar

Aşağıdaki ayrıntılar ilk küçük veri üretiminden önce kesinleştirilecektir:

- Karmaşıklık sınıflandırmasındaki kesin eşikler ve öncelik kuralları
- Aktif çalışmanın zaman aralığı ve ekip-gün dağılımı
- Yarım gün tatil takviminin temsil yöntemi
- Açık aşama ve beklemelerin raporlama kesitinde ele alınması
- Normal mesai ile fazla mesainin ayrıştırılması
- Sentetik dağılımların kalibrasyonu ve veri kalite testleri

Bu belge, veri üretimi ve analiz aşamasında temel iş kuralı kaynağı olarak kullanılacaktır.
