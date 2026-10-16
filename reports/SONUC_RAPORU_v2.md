# Veriqora Bank – Beş Senaryo Karşılaştırması (v2)

## Kapsam ve yöntem
- Tamamen sentetik 50.000 işlem içeren beş kapasite senaryosu.
- Raporlama kesiti: 31.12.2025 18:00 (simülasyon yerel saatleri).
- Tamamlanma ve SLA oranları farklı metriklerdir. SLA paydası yalnızca tamamlanan işlemlerdir.
- Uçtan uca SLA: açılış–kapanış arasında normal iş takvimi dakikaları; öğle arası, tatil ve fazla mesai hariç.
- Operasyonel SLA: uçtan uca iş dakikalarından yalnızca doğrulanmış ve hariç tutulabilir EXTERNAL_PARTY/CUSTOMER beklemelerinin birleştirilmiş iş dakikaları düşülür.
- SLA hedefi işlem üzerindeki sla_target_id ile eşleştirilir; hedefe eşit süre başarılı sayılır.
- Maliyet: tamamlanan çalışma aralıklarının aktif dakikaları, geçerli saatlik ücret ve fazla mesai çarpanıyla hesaplanır.
- Bu rapor simülasyon sonuçlarını değiştirmez; eski raporlar karşılaştırma için korunur.

## Senaryo sonuçları
| scenario | completed | open | completion_pct | operational_sla_pct | e2e_sla_pct | actual_work_cost_tl |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 26427 | 23573 | 52.85 | 4.25 | 4.09 | 31147197.5 |
| targeted_25 | 27735 | 22265 | 55.47 | 4.18 | 4.02 | 34839305.83 |
| targeted_50 | 28542 | 21458 | 57.08 | 3.8 | 3.66 | 36856091.5 |
| targeted_100 | 30723 | 19277 | 61.45 | 3.78 | 3.65 | 41579263.17 |
| all_25 | 36454 | 13546 | 72.91 | 14.63 | 14.17 | 39099992.83 |

## Önceki raporla SLA ve metrik farkları
- targeted_50: operational_sla_pct eski=3.78, yeni=3.8
- targeted_50: e2e_sla_pct eski=3.64, yeni=3.66
- targeted_100: operational_sla_pct eski=3.76, yeni=3.78
- targeted_100: e2e_sla_pct eski=3.62, yeni=3.65
- all_25: operational_sla_pct eski=14.57, yeni=14.63
- all_25: e2e_sla_pct eski=14.1, yeni=14.17

## Yorumlama sınırları
- Önceki raporla farklı SLA değerleri hesaplama yaklaşımı ve tarih/zaman işleme farklarından kaynaklanabilir; eski raporun üretim kodu doğrulanmadığı için kesin neden bilinmiyor.
- Bu sonuçlar sentetik simülasyon çıktılarıdır; gerçek banka performansı veya gerçekleşmiş tasarruf olarak yorumlanmamalıdır.
- Beş senaryonun maliyet ve performansı birlikte değerlendirilmelidir; yalnızca tamamlanma oranına göre karar verilmemelidir.
