# Veriqora Bank – Bankacılık Operasyonları Senaryo Analizi

## Yönetici özeti

Bu çalışma, sentetik olarak oluşturulan 50.000 bankacılık işlemi üzerinde beş farklı çalışan kapasitesi senaryosunu karşılaştırmaktadır. İşlem tamamlama oranı, hizmet seviyesi hedeflerine (SLA) uyum ve tahmini işçilik maliyetleri birlikte değerlendirilmiştir.

- Mevcut kapasitede 26.427 işlem tamamlanmış, tamamlanma oranı %52,85 olmuştur.
- En yüksek tamamlanma oranı **Tüm ekipler +%25** senaryosunda %72,91 olarak hesaplanmıştır.
- Bu senaryoda mevcut kapasiteye kıyasla **10.027 ilave işlem** tamamlanmıştır.
- Tamamlanma oranındaki artış, tek başına SLA hedeflerinin karşılandığı anlamına gelmez; iki gösterge ayrı değerlendirilmelidir.

## Senaryo karşılaştırması

| Senaryo | Tamamlanan | Açık | Tamamlanma | Operasyonel SLA uyumu* | Uçtan uca SLA uyumu* | Gerçekleşen tahmini işçilik maliyeti |
|---|---:|---:|---:|---:|---:|---:|
| Mevcut kapasite | 26.427 | 23.573 | %52,85 | %4,25 | %4,09 | 31.147.197,50 TL |
| Kredi ve Yasal Takip +%25 | 27.735 | 22.265 | %55,47 | %4,18 | %4,02 | 34.839.305,83 TL |
| Kredi ve Yasal Takip +%50 | 28.542 | 21.458 | %57,08 | %3,80 | %3,66 | 36.856.091,50 TL |
| Kredi ve Yasal Takip +%100 | 30.723 | 19.277 | %61,45 | %3,78 | %3,65 | 41.579.263,17 TL |
| Tüm ekipler +%25 | 36.454 | 13.546 | %72,91 | %14,63 | %14,17 | 39.099.992,83 TL |

*SLA uyum oranları yalnızca tamamlanan işlemler üzerinden hesaplanmıştır.

## Kapasite artışının maliyet ve çıktı etkisi

| Senaryo | İlave tamamlanan işlem | İlave işçilik maliyeti | İlave tamamlanan işlem başına maliyet |
|---|---:|---:|---:|
| Mevcut kapasite | 0 | 0,00 TL | — |
| Kredi ve Yasal Takip +%25 | 1.308 | 3.692.108,33 TL | 2.822,71 TL |
| Kredi ve Yasal Takip +%50 | 2.115 | 5.708.894,00 TL | 2.699,24 TL |
| Kredi ve Yasal Takip +%100 | 4.296 | 10.432.065,67 TL | 2.428,32 TL |
| Tüm ekipler +%25 | 10.027 | 7.952.795,33 TL | 793,14 TL |

Mevcut kapasite senaryosunda ilave tamamlanan işlem bulunmadığından işlem başına ilave maliyet hesaplanmaz; tabloda bu değer “—” olarak gösterilmiştir.

## Bulguların değerlendirilmesi

Çalışmada kullanılan işlemler gerçek banka kayıtları değildir. Belirlenen iş kuralları ve rastgelelik içeren yöntemlerle üretilmiş **sentetik verilerdir**. Bu nedenle sonuçlar, veri üretiminde kullanılan işlem yoğunluğu, işlem süreleri, beklemeler ve ekip kapasitesi varsayımlarından etkilenir.

Çalışan kapasitesinin artırıldığı senaryolarda tamamlanan işlem sayısının yükseldiği görülmektedir. Bu durumun olası açıklaması, kapasite artışının işlem kuyruklarını ve kaynak kısıtlarını hafifletmesidir. Ancak gözlenen artışın yalnızca veri üretimindeki rastgelelikten veya yalnızca çalışan sayısından kaynaklandığı bu analizle kesin olarak söylenemez. Etkileri ayrıştırmak için farklı rastgele başlangıç değerleriyle tekrarlı simülasyonlar ve duyarlılık analizleri yapılabilir.

Kapasite artışının verimlilik açısından değerlendirilmesinde ilave tamamlanan işlem sayısı ile ilave işçilik maliyetinin birlikte incelenmesi gerekir. SLA uyum oranlarının düşük kalması, tamamlanan işlem sayısındaki artışın hizmet seviyesi hedeflerine aynı ölçüde yansımadığını göstermektedir.

## Hesaplama yöntemi

- **Raporlama kesiti:** 31.12.2025 saat 18.00 (simülasyon yerel saati).
- **Tamamlanma oranı:** Tamamlanan işlem sayısı / toplam işlem sayısı.
- **Uçtan uca SLA:** İşlemin açılışı ile kapanışı arasındaki normal iş takvimi dakikaları esas alınır. Öğle arası, hafta sonu, tatil ve fazla mesai SLA süresine dahil edilmez.
- **Operasyonel SLA:** Uçtan uca iş dakikalarından yalnızca doğrulanmış, hariç tutulabilir müşteri ve dış taraf beklemelerinin çakışmayan iş dakikaları çıkarılır.
- **SLA başarısı:** İşlem süresi, ilgili hedef süreye eşit veya daha kısa ise başarılı kabul edilir.
- **İşçilik maliyeti:** Tamamlanan çalışma aşamalarındaki aktif süreler, geçerli saatlik maliyet ve fazla mesai çarpanıyla hesaplanır.
- **İlave işlem başına maliyet:** Mevcut kapasiteye göre ilave işçilik maliyeti / ilave tamamlanan işlem sayısı.

## Sınırlılıklar

Bulgular sentetik veri ve simülasyon varsayımlarına dayanmaktadır. Gerçek bir bankada aynı kapasite değişikliğinin aynı sonuçları vereceği garanti edilemez. Hesaplanan işçilik maliyetleri de gerçek muhasebe gideri veya gerçekleşmiş tasarruf olarak yorumlanmamalıdır.

Operasyon bazında ayrıntılı sonuçlar `scenario_by_operation.csv`, senaryo düzeyindeki hesaplama çıktıları ise `scenario_comparison.csv` dosyasında yer almaktadır.
