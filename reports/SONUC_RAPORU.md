# Veriqora Bank — 109. Adım | Nihai kapasite senaryosu değerlendirmesi

**Veri:** 50.000 sentetik işlem, 2025-12-31 18:00 raporlama kesiti. Baseline ve üç alternatif kapasite senaryosu. Bu rapor, simülasyon çıktılarından hesaplanmıştır; gerçek banka sonuçları değildir.

## Karşılaştırma

| Senaryo | Tamamlanan | Açık | Tamamlanma | Operasyonel SLA uyumu* | Uçtan uca SLA uyumu* | Gerçekleşen tahmini işçilik maliyeti |
|---|---:|---:|---:|---:|---:|---:|
| Mevcut | 26.427 | 23.573 | %52,85 | %4,24 | %4,09 | 31.147.197,50 TL |
| Kredi ve Yasal Takip +%50 | 28.542 | 21.458 | %57,08 | %3,78 | %3,64 | 36.856.091,50 TL |
| Kredi ve Yasal Takip +%100 | 30.723 | 19.277 | %61,45 | %3,76 | %3,62 | 41.579.263,17 TL |
| Tüm ekipler +%25 | 36.454 | 13.546 | %72,91 | %14,57 | %14,10 | 39.099.992,83 TL |

\* Yalnızca tamamlanan işlemler üzerinden hesaplanmıştır; açık işlemler başarı sayılmamıştır. İş saatleri 09–12, 13–18 (yarım gün 09–12) ve referans iş takvimi esas alınmıştır. Operasyonel SLA için doğrulanmış, hariç tutulabilir dış kaynak beklemeleri iş dakikası olarak düşülmüştür.

## Önemli bulgular

- Tüm ekiplere yayılan kapasite artışı, mevcut duruma kıyasla 10.027 ek tamamlanan işlem ve +20,05 yüzde puan tamamlanma oranı sağlamıştır.
- Hedefli iki ekip kapasitesini ikiye katlamak, tüm ekiplerdeki artışa kıyasla daha az işlem tamamlamış ve daha yüksek gerçekleşen tahmini işçilik maliyeti üretmiştir.
- Tüm ekipler +%25 senaryosunda gerçekleşen işçilik maliyeti mevcut duruma göre yaklaşık 7,95 milyon TL fazladır; ek tamamlanan işlem başına **ek gerçekleşen işçilik maliyeti** yaklaşık 793 TL'dir. Bu değer personel istihdamının marjinal toplam maliyeti veya net tasarruf değildir.
- SLA performansı tüm ekiplerde artış senaryosunda iyileşmesine rağmen düşük kalmaktadır. Dolayısıyla kapasite artışı tek başına hedeflere ulaşmayı garanti etmez.

## Sınırlar ve metodoloji

1. Simülasyon olay sırası değiştiğinde rastgele kalite olayları da değişebilir. Bu yüzden senaryolar arası farkların tamamı yalnızca kapasiteye atfedilemez; sonuçlar nedensel etki tahmini değildir.
2. Maliyetler `stage_executions.csv` içindeki tamamlanmış aktif çalışma dakikalarına, ekibin saatlik ücretine ve fazla mesai katsayısına göre hesaplanmıştır. Çalışılmamış ama ücretlendirilebilecek ek çalışan kapasitesi, işe alım, yan haklar ve genel giderler dahil değildir.
3. Kesitte devam eden ve `active_minutes` alanı boş olan aralıklar maliyet hesabına alınmamıştır. Bu nedenle maliyet, gerçekleşen iş yükünün ihtiyatlı/eksik bir ölçüsü olabilir.
4. SLA uyumunda payda yalnızca tamamlanan işlemlerdir. Açık işlemlerin yaşlandırması ayrıca dashboard'da izlenmelidir.
5. Günlük çalışan sayısının yukarı yuvarlanması nedeniyle senaryo isimlerindeki %25/%50 artışlar birebir gerçekleşen kapasite yüzdesi değildir.

## Karar ve sonraki aşama

Python simülasyonu ve senaryo karşılaştırması bu aşamada dondurulur. Sonuçlar SQL/BigQuery veri modeline taşınacak, daha sonra Power BI'ın dört rapor sayfasında sunulacaktır. Yalnızca veri aktarımını veya hesap tutarlılığını engelleyen kritik bir hata çıkarsa Python koduna dönülür.

## Dosyalar

- `scenario_comparison.csv`: Dört senaryonun işlem, SLA, maliyet ve çalışma kayıtları karşılaştırması.
- `scenario_by_operation.csv`: Senaryo ve operasyon kırılımında tamamlanan işlem sayıları.
