
# İş Gereksinimleri Dokümanı (BRD)

**Proje:** Bankacılık Operasyonları ve Süreç Analitiği  
**Kurgusal kurum:** NovaBank  
**Sürüm:** 1.1  
**Durum:** Tasarım onaylandı, teknik geliştirme bekleniyor

## 1. Projenin Amacı

Bankacılık operasyonlarında işlem hacmi, tamamlanma süreleri, SLA performansı, beklemeler, işlem kalitesi, ekip kapasitesi ve tahmini işçilik maliyetlerini birlikte değerlendirerek iyileştirme fırsatlarını belirlemek.

## 2. İş Problemi

Yalnızca tamamlanan işlem sayısı ve ortalama işlem süresi üzerinden yapılan değerlendirmeler, iç ve dış kaynaklı beklemeleri, yeniden işlem maliyetlerini ve kapasite darboğazlarını yeterince açıklamayabilir.

Bu proje, süreç performansını operasyon ve aşama seviyesinde inceleyerek gecikmelerin nedenlerini ve iyileştirme önceliklerini ortaya koymayı hedefler.

## 3. Kapsam

- 2025 yılına ait planlanan 50.000 sentetik işlem
- Altı operasyon: kredi, ödeme ve transfer, hesap, müşteri bilgi güncelleme, yasal takip ve operasyonel kontrol
- Düşük, orta ve yüksek işlem karmaşıklığı
- Operasyona özgü ve tekrar ziyaret içerebilen iş akışları
- Uçtan uca ve kontrol edilebilir operasyonel SLA
- Ekip bazlı günlük kapasite ve aktif çalışma süresi
- Kalite olayları, iade ve yeniden işlem analizi
- Tahmini işçilik maliyeti ve süreç iyileştirme önerileri

## 4. Kapsam Dışı

- Gerçek banka, müşteri veya çalışan verileri
- Bireysel çalışan performansı değerlendirmesi
- Canlı bankacılık sistemleriyle entegrasyon
- Makine öğrenmesiyle tahmin veya otomatik karar verme
- Gerçek finansal maliyet ya da kârlılık beyanı

## 5. Paydaşlar

- Üst yönetim: genel operasyonel görünüm ve iyileştirme öncelikleri
- Operasyon yöneticileri: iş yükü, bekleme ve kapasite analizi
- Süreç iyileştirme ekipleri: darboğaz ve yeniden işlem analizi
- Kalite ve kontrol ekipleri: hata türleri ve kalite göstergeleri
- Veri analizi ve BI ekipleri: tutarlı veri modeli ve raporlama

## 6. Temel İş Gereksinimleri

**BR-01:** Operasyonlara göre işlem hacmi ve tamamlanma durumları izlenmelidir.

**BR-02:** İşlemler operasyon türü ve açılışta belirlenen karmaşıklık seviyesine göre analiz edilebilmelidir.

**BR-03:** Süreç aşamaları, tekrar ziyaretler ve aşama bazlı aktif çalışma süreleri izlenmelidir.

**BR-04:** İç ve dış beklemeler nedenleriyle birlikte ayrıştırılmalıdır.

**BR-05:** Uçtan uca ve kontrol edilebilir operasyonel SLA ayrı ayrı hesaplanmalıdır.

**BR-06:** Hata, iade, yeniden işlem ve ilk seferde doğru tamamlama göstergeleri hesaplanmalıdır.

**BR-07:** Günlük ekip kapasitesi ve aktif iş yükü karşılaştırılmalıdır.

**BR-08:** Ekip çalışma sürelerinden tahmini işçilik maliyeti hesaplanmalıdır.

**BR-09:** Operasyon, karmaşıklık, dönem ve ekip kırılımlarında analiz yapılabilmelidir.

**BR-10:** Bulgulara dayalı, ölçülebilir en az üç süreç iyileştirme önerisi sunulmalıdır.

## 7. Temel İş Kuralları

### 7.1 İş takvimi

Standart çalışma saatleri hafta içi 09.00–12.00 ve 13.00–18.00 olarak kabul edilir. Tatiller ve yarım günler iş takviminde ayrıca tanımlanır.

### 7.2 SLA

Uçtan uca SLA, işlem açılışı ile kapanışı arasındaki iş takvimi süresidir.

Kontrol edilebilir operasyonel SLA, uçtan uca süreden yalnızca doğrulanmış ve hariç tutulabilir müşteri veya dış taraf beklemelerinin çıkarılmasıyla hesaplanır.

İç kuyruk, iç onay ve iç teknik beklemeler iki SLA hesabına da dahildir.

SLA hedefi işlem açılışında belirlenir ve işlem boyunca sabit kalır.

### 7.3 Kalite ve yeniden işlem

Bir hata birden fazla aşama tekrarına yol açabilir. Tekrar ziyaret sayısı doğrudan hata sayısı olarak kabul edilmez.

İlk seferde doğru tamamlama (FTR), yeniden işlem gerektirmeden tamamlanan uygun işlemler üzerinden hesaplanır.

### 7.4 Kapasite

Kapasite çalışan bazında değil ekip bazında ölçülür. Aktif çalışma süresi, işlemi gerçekleştiren ekibe ve ilgili güne atanır. Normal mesai ve fazla mesai ayrı izlenir.

### 7.5 Raporlama kesiti

Raporlar seçilen tarih itibarıyla bilinen kayıtları kullanır. Açık işlemler tamamlanmış işlemlerle karıştırılmaz. Gelecekteki olaylar geçmiş raporlara dahil edilmez.

## 8. SLA Hedefleri (İş Saati)

| Operasyon | Düşük | Orta | Yüksek |
|---|---:|---:|---:|
| Kredi operasyonları | 4 | 8 | 16 |
| Ödeme ve transferler | 1 | 2 | 4 |
| Hesap işlemleri | 2 | 4 | 8 |
| Müşteri bilgi güncellemeleri | 1 | 3 | 6 |
| Yasal takip operasyonları | 8 | 16 | 32 |
| Operasyonel kontroller | 2 | 6 | 12 |

Bu hedefler yalnızca proje için belirlenmiş varsayımsal değerlerdir.

## 9. Veri ve Raporlama Tasarımı

Veri modeli 12 mantıksal tablodan oluşur. Planlanan rapor sayfaları:

1. Yönetici Özeti
2. Süreç Performansı ve Darboğaz Analizi
3. Ekip Kapasitesi ve İş Yükü Analizi
4. İşlem Kalitesi ve İyileştirme Fırsatları

## 10. Kabul Kriterleri

- Altı operasyon karşılaştırılabilmelidir.
- İşlem ve aşama bazında aktif süre ve bekleme süreleri ayrıştırılabilmelidir.
- İki SLA türü tutarlı biçimde hesaplanmalıdır.
- Karmaşıklık ve yeniden işlemin performansa etkisi incelenebilmelidir.
- Ekip kapasitesi ve tahmini maliyetler hesaplanabilmelidir.
- En az üç iyileştirme önerisi nicel bulgularla desteklenmelidir.
- Sentetik veriler tekrar üretilebilir ve veri bütünlüğü kontrollerinden geçebilir olmalıdır.

## 11. Varsayımlar ve Sınırlılıklar

NovaBank kurgusal bir bankadır. Tüm işlem kayıtları ve parametreler sentetiktir. Sonuçlar gerçek bir bankanın performansı olarak yorumlanmamalıdır.

Bu doküman iş gereksinimlerini tanımlar. Ayrıntılı veri alanları, ilişkiler ve teknik hesaplama kuralları ayrı dokümanlarda tutulacaktır.
