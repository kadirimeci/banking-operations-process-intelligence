# Veriqora Bank | Bankacılık Operasyonları ve Süreç Analitiği

**50.000 sentetik bankacılık işlemi · 5 kapasite senaryosu · Python, BigQuery SQL ve Power BI ile uçtan uca operasyonel performans analizi**

> **Önemli:** Veriqora Bank tamamen kurgusal bir kurumdur. Projede kullanılan işlem, ekip kapasitesi, SLA ve maliyet verileri sentetik veya varsayımsaldır. Gerçek müşterilere, çalışanlara veya herhangi bir finans kuruluşuna ait gizli veriler kullanılmamıştır. Bulgular gerçek bankacılık performansını temsil etmez.

## Projenin amacı

Bankacılık operasyonlarını yalnızca işlem hacmi üzerinden değil; **tamamlanma oranı, açık işlem yükü, SLA uyumu, kalite olayları, kapasite kullanımı ve tahmini çalışma maliyeti** ile birlikte değerlendiren bir karar destek çalışması geliştirmek.

Proje, aynı sentetik işlem kümesinin farklı ekip kapasitesi koşullarında nasıl sonuçlar ürettiğini karşılaştırır. Amaç, **kapasite artışının işlem tamamlama, SLA ve maliyet üzerindeki etkilerinin her zaman aynı yönde ilerlemediğini** görünür kılmaktır.

## Kapsam ve yöntem

- **Dönem:** 2025; sabit raporlama kesiti **31 Aralık 2025, 18.00 (Türkiye saati)**.
- **Veri:** Altı operasyon türüne dağıtılmış **50.000 sentetik işlem**.
- **Model:** İşlem karmaşıklığı, operasyon türüne göre süreç aşamaları, çalışma ve bekleme kayıtları, kalite olayları, ekip kapasiteleri ve iş takvimi.
- **Ölçümler:** Tamamlanan/açık işlem sayıları, operasyonel ve uçtan uca (E2E) SLA, kalite göstergeleri, normal/fazla mesai ve varsayımsal çalışma maliyetleri.
- **Karşılaştırma:** Aynı 50.000 işlem kümesi **beş kapasite senaryosunda** değerlendirilir. Senaryoların toplamı 250.000 bağımsız gerçek işlem anlamına gelmez.

### İncelenen operasyonlar

1. Ödeme ve Transferler
2. Müşteri Bilgi Güncellemeleri
3. Hesap İşlemleri
4. Kredi Operasyonları
5. Yasal Takip Operasyonları
6. Operasyonel Kontroller

### Kapasite senaryoları

| Senaryo | Modeldeki değişiklik |
|---|---|
| Mevcut Durum (`baseline`) | Referans kapasite |
| Hedefli Kapasite +%25 (`targeted_25`) | Kredi ve Yasal Takip ekiplerinde %25 kapasite artışı |
| Hedefli Kapasite +%50 (`targeted_50`) | Kredi ve Yasal Takip ekiplerinde %50 kapasite artışı |
| Hedefli Kapasite +%100 (`targeted_100`) | Kredi ve Yasal Takip ekiplerinde %100 kapasite artışı |
| Tüm Ekiplere +%25 (`all_25`) | Bütün ekiplerde %25 kapasite artışı |

## Öne çıkan sonuçlar

| Senaryo | Tamamlanan | Açık | Tamamlanma | Operasyonel SLA | E2E SLA |
|---|---:|---:|---:|---:|---:|
| Mevcut Durum | 26.427 | 23.573 | %52,85 | %4,25 | %4,09 |
| Hedefli Kapasite +%25 | 27.735 | 22.265 | %55,47 | %4,18 | %4,02 |
| Hedefli Kapasite +%50 | 28.542 | 21.458 | %57,08 | %3,80 | %3,66 |
| Hedefli Kapasite +%100 | 30.723 | 19.277 | %61,45 | %3,78 | %3,65 |
| Tüm Ekiplere +%25 | 36.454 | 13.546 | %72,91 | %14,63 | %14,17 |

### Maliyet ve ilave performans

| Senaryo | Tahmini çalışma maliyeti | Mevcut duruma göre ilave tamamlanan | İlave işlem başına ek çalışma maliyeti |
|---|---:|---:|---:|
| Mevcut Durum | 31.147.197,50 TL | — | — |
| Hedefli Kapasite +%25 | 34.839.305,83 TL | 1.308 | 2.822,71 TL |
| Hedefli Kapasite +%50 | 36.856.091,50 TL | 2.115 | 2.699,24 TL |
| Hedefli Kapasite +%100 | 41.579.263,17 TL | 4.296 | 2.428,32 TL |
| Tüm Ekiplere +%25 | 39.099.992,83 TL | 10.027 | 793,14 TL |

**Temel çıkarım:** Modellenen koşullarda **Tüm Ekiplere +%25** senaryosu hem en yüksek tamamlanma oranını hem de ilave tamamlanan işlem başına en düşük ek çalışma maliyetini üretmiştir. Buna rağmen bu senaryoda bile SLA uyumu sınırlıdır. **Daha fazla işlem tamamlamak, SLA hedeflerinin otomatik olarak karşılandığı anlamına gelmez.**

Bu karşılaştırmalar bir gerçek banka için personel artışı önerisi veya gerçekleşmiş finansal tasarruf iddiası değildir. Ayrıntılar için [Sonuç Raporu](reports/SONUC_RAPORU.md) dosyasına bakılabilir.

## Teknik mimari ve kullanılan araçlar

| Katman | Araçlar | Projedeki rolü |
|---|---|---|
| Sentetik veri ve simülasyon | Python, pandas, NumPy | İşlem ve olay kayıtları, senaryo üretimi ve kontrol süreçleri |
| Analitik veri katmanı | Google BigQuery, SQL | Kaynak tablolar, raporlamaya uygun boyut/olgu görünümleri |
| Veri modeli ve görselleştirme | Power BI, DAX | İlişkisel model, KPI hesaplamaları ve altı sayfalık yönetim raporu |
| Sürüm kontrolü ve dokümantasyon | Git, GitHub, Markdown | Kaynak kodu, SQL tanımları, rapor ve teknik belgelerin paylaşımı |

### BigQuery / SQL katmanı

Power BI için oluşturulmuş **10 SQL görünüm tanımı** [`sql/`](sql/) klasöründe yer alır:

- **Boyut görünümleri:** `dim_senaryo`, `dim_operasyon`, `dim_ekip`, `dim_surec_asamasi`, `dim_sla_hedefi`
- **Olgu görünümleri:** `fact_islemler`, `fact_calisma_kayitlari`, `fact_bekleme_kayitlari`, `fact_kalite_olaylari`
- **Performans özeti:** `pbi_senaryo_performans_ozeti`

SQL dosyaları, BigQuery'de kullanılan **görünüm sorgularını** içerir. Bunlar tek başlarına kaynak tabloları veya sentetik veriyi oluşturmaz; sorguların çalıştırılması için ilgili BigQuery veri kümesi ve kaynak tablolar gereklidir. Kaynak proje kimliği SQL dosyalarında açıkça belirtilmiştir.

### Power BI raporu

**Rapor dosyası:** [`powerbi/Veriqora_Bank_Operations_Intelligence.pbix`](powerbi/Veriqora_Bank_Operations_Intelligence.pbix)

Raporun altı sayfası:

1. **Yönetici Özeti:** Temel işlem ve SLA göstergeleri, operasyon bazlı performans.
2. **Operasyon Analizi:** Tamamlanan ve açık işlemlerin operasyonlar arasında dağılımı.
3. **SLA ve Kalite Analizi:** SLA başarısı, kalite olayları ve operasyon bazlı kalite karşılaştırmaları.
4. **Kapasite ve Maliyet Analizi:** Senaryolara göre çalışma maliyeti, tamamlanan işlemler ve marjinal maliyet.
5. **Senaryo Karşılaştırması:** Beş kapasite senaryosunun ortak KPI'larla karşılaştırılması.
6. **Bulgular ve Öneriler:** Analiz sonuçları, yönetimsel değerlendirmeler ve simülasyon sınırları.

> **Not:** `.pbix` dosyası raporun incelenmesi için paylaşılmıştır. BigQuery'den veri yenileme işlemi, uygun erişim yetkileri ve bağlantı yapılandırması gerektirebilir.

## Rapor çıktıları

| Dosya | İçerik |
|---|---|
| [`reports/SONUC_RAPORU.md`](reports/SONUC_RAPORU.md) | Türkçe sonuç raporu ve senaryo değerlendirmesi |
| [`reports/scenario_comparison.csv`](reports/scenario_comparison.csv) | Senaryoların karşılaştırmalı göstergeleri |
| [`reports/scenario_by_operation.csv`](reports/scenario_by_operation.csv) | Operasyon bazında senaryo çıktıları |

CSV dosyalarındaki teknik alan adları, Python ve diğer analiz araçlarıyla uyumluluk için İngilizce tutulmuştur; açıklamalar Türkçedir.

## Rapor çıktılarını yeniden oluşturma

Proje ana dizininde, gerekli Python ortamı ve **yerel sentetik veri / referans CSV dosyaları hazır olduğunda**:

```powershell
pip install -r requirements.txt
python src/veriqora_scenario_audit.py
```

Bu komut **simülasyonu baştan çalıştırmaz**. Mevcut senaryo çıktılarından `reports/` altındaki üç rapor dosyasını yeniden hesaplayarak **üzerlerine yazar**. İşlem, çalışma, bekleme, kalite ve referans verilerinin yerel ortamda bulunması gerekir. Tüm veri üretim sürecini yalnızca bu iki komutla yeniden oluşturmak mümkün olmayabilir.

## Teknik belgeler

- [İş kuralları ve sentetik veri varsayımları](business_rules.md)
- [Veri sözlüğü](data_dictionary.md)
- [Veri modeli ve tablo ilişkileri](data_model.md)

## Bulguların yorumlanması ve sınırlılıklar

- **Sentetik model:** Süreler, kapasite dağılımları, SLA hedefleri ve maliyet parametreleri varsayımsaldır; gerçek banka verisiyle kalibre edilmiş performans tahminleri olarak değerlendirilmemelidir.
- **Teknik doğrulama:** Veri bütünlüğü ve iş kurallarına yönelik kontroller, modelin gerçek operasyonları temsil ettiğini veya aynı sonuçların sahada tekrarlanacağını garanti etmez.
- **Süre ölçümleri:** Özellikle simüle edilmiş çalışma ve bekleme süreleri gerçek operasyonel verimlilik veya darboğaz kanıtı olarak kullanılmamalıdır.
- **Senaryo yorumu:** Farklı senaryoların maliyet ve performans sonuçları yalnızca bu çalışmanın varsayımları altında karşılaştırılabilir. Gerçek bir kurum için karar alınmadan önce saha verileriyle ayrıca doğrulama gerekir.
- **Gizlilik:** Gerçek müşteri bilgileri, personel kayıtları veya bir finans kuruluşuna ait gizli veriler kullanılmamıştır.

## Proje sahibi

**Kadir İmeci** · [LinkedIn](https://www.linkedin.com/in/kadirimeci) · [GitHub](https://github.com/kadirimeci)
