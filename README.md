# Veriqora Bank | Bankacılık Operasyonları ve Süreç Analitiği

**50.000 sentetik bankacılık işlemi • 5 kapasite senaryosu • Operasyonel performans, SLA ve maliyet analizi**

> **Önemli:** Veriqora Bank kurgusal bir kurumdur. Bu projedeki işlemler, çalışan kapasitesi, SLA hedefleri ve maliyetler sentetik veya varsayımsaldır. Gerçek müşteri, çalışan ya da banka verisi kullanılmamıştır.

## Projenin amacı

Bankacılık operasyonlarında işlem hacmini tek başına değerlendirmek yerine **tamamlanma oranı, bekleme süreleri, SLA uyumu, ekip kapasitesi ve tahmini işçilik maliyetini** birlikte ele almak. Çalışma, kapasite değişikliklerinin operasyonel çıktılar üzerindeki etkisini karşılaştırmalı simülasyonlarla inceler.

## Kapsam ve yöntem

- 2025 dönemi için üretilmiş **50.000 sentetik işlem** ve **altı operasyon türü**.
- İşlem özellikleri, süreç aşamaları, çalışma aralıkları, beklemeler ve kalite olayları üzerinden koşullara bağlı veri üretimi.
- Türkiye iş takvimiyle hesaplanan **uçtan uca** ve **operasyonel SLA** göstergeleri.
- Ekip kapasitesi, normal/fazla mesai iş yükü ve varsayımsal işçilik maliyeti.
- Sabit raporlama kesiti: **31 Aralık 2025, 18.00 (Türkiye saati)**.

### Kapasite senaryoları

| Senaryo | Kapasite değişikliği |
|---|---|
| Mevcut kapasite | Referans durum |
| Kredi ve Yasal Takip +%25 | İlgili ekiplerde %25 artış |
| Kredi ve Yasal Takip +%50 | İlgili ekiplerde %50 artış |
| Kredi ve Yasal Takip +%100 | İlgili ekiplerde %100 artış |
| Tüm ekipler +%25 | Bütün ekiplerde %25 artış |

## Öne çıkan sonuçlar

| Senaryo | Tamamlanan işlem | Tamamlanma oranı | Operasyonel SLA uyumu | Uçtan uca SLA uyumu |
|---|---:|---:|---:|---:|
| Mevcut kapasite | 26.427 | %52,85 | %4,25 | %4,09 |
| Kredi ve Yasal Takip +%25 | 27.735 | %55,47 | %4,18 | %4,02 |
| Kredi ve Yasal Takip +%50 | 28.542 | %57,08 | %3,80 | %3,66 |
| Kredi ve Yasal Takip +%100 | 30.723 | %61,45 | %3,78 | %3,65 |
| Tüm ekipler +%25 | 36.454 | %72,91 | %14,63 | %14,17 |

**Yorum:** Kapasite artırılan senaryolarda tamamlanan işlem sayısı artmıştır; ancak tamamlanma oranındaki iyileşme her senaryoda SLA uyumunda aynı yönde bir artış anlamına gelmez. Özellikle yalnızca iki operasyonun kapasitesini artırmak, diğer ekiplerdeki darboğazları ortadan kaldırmayabilir. Sonuçlar kullanılan sentetik veri dağılımlarına ve simülasyon kurallarına bağlıdır; gerçek bir bankada aynı sonuçların elde edileceği iddia edilmez.

Ayrıntılı maliyet karşılaştırması, hesaplama yöntemi ve sınırlılıklar için [Sonuç Raporu](reports/SONUC_RAPORU.md) dosyasına bakın.

## Rapor dosyaları

| Dosya | İçerik |
|---|---|
| [`reports/SONUC_RAPORU.md`](reports/SONUC_RAPORU.md) | Türkçe yönetim özeti ve senaryo değerlendirmesi |
| [`reports/scenario_comparison.csv`](reports/scenario_comparison.csv) | Beş senaryonun karşılaştırmalı göstergeleri |
| [`reports/scenario_by_operation.csv`](reports/scenario_by_operation.csv) | Operasyon türü bazında senaryo sonuçları |

CSV dosyalarındaki teknik sütun adları, Python ve sonraki analiz araçlarıyla uyumluluk için İngilizce tutulmuştur; kullanıcıya yönelik açıklamalar Türkçedir.

## Kullanılan araçlar ve çalışma durumu

**Python, pandas, NumPy, Git ve GitHub** veri üretimi, simülasyon ve rapor hesaplamalarında kullanılmıştır. **SQL, Google BigQuery ve Power BI** proje kapsamındaki sonraki analiz ve görselleştirme aşamalarıdır; bu depodaki mevcut çalışmalar tamamlanmış bir Power BI paneli olarak sunulmaz.

## Raporu yeniden üretme

Proje ana dizininde Python bağımlılıklarını kurduktan ve gerekli sentetik veri dosyalarını hazırladıktan sonra:

```powershell
pip install -r requirements.txt
python src/veriqora_scenario_audit.py
```

Bu komut simülasyonu yeniden çalıştırmaz; mevcut senaryo çıktılarından `reports/` altındaki **üç güncel rapor dosyasını yeniden hesaplar ve üzerlerine yazar**. Gerekli işlem, çalışma, bekleme, kalite ve referans CSV dosyalarının yerel ortamda bulunması gerekir.

## Teknik belgeler

- [İş kuralları ve sentetik veri varsayımları](business_rules.md)
- [Veri sözlüğü](data_dictionary.md)
- [Veri modeli ve tablo ilişkileri](data_model.md)

## Çalışmanın sınırları

Simülasyonda kullanılan başlangıç koşulları, iş yükü dağılımları ve maliyet parametreleri varsayımsaldır. Tamamlanma ve SLA oranları rastgele doğrudan atanmaz; üretilen olaylar ile tanımlanan iş kuralları üzerinden hesaplanır. Bulgular, karar destek yaklaşımını göstermek içindir; gerçek bankacılık performansı veya doğrulanmış finansal kazanç olarak değerlendirilmemelidir.

## Proje sahibi

**Kadir İmeci** · [LinkedIn](https://www.linkedin.com/in/kadirimeci) · [GitHub](https://github.com/kadirimeci)
