SELECT
  scenario AS senaryo_id,
  transactions AS toplam_islem,
  completed AS tamamlanan_islem,
  open AS acik_islem,

  -- Bu oranlar BigQuery'de 0-100 ölçeğinde tutulmaktadır.
  completion_pct AS tamamlanma_orani_yuzde,
  operational_sla_pct AS operasyonel_sla_yuzde,
  e2e_sla_pct AS e2e_sla_yuzde,

  -- Çalışma maliyeti ve kapasite göstergeleri
  actual_work_cost_tl AS gerceklesen_calisma_maliyeti_tl,
  normal_minutes AS normal_calisma_dakikasi,
  overtime_minutes AS fazla_mesai_dakikasi,

  -- Kalite ve süreç kayıtları
  quality_events AS kalite_olayi_sayisi,
  work_rows AS calisma_kaydi_sayisi,
  waiting_rows AS bekleme_kaydi_sayisi,

  -- Mevcut duruma göre ilave performans
  extra_completed AS ilave_tamamlanan_islem,
  extra_actual_work_cost_tl AS ilave_calisma_maliyeti_tl,
  extra_actual_cost_per_extra_completed_tl
    AS ilave_islem_basina_maliyet_tl

FROM
  `prefab-bruin-483617-b9.veriqora_bank.scenario_comparison`
