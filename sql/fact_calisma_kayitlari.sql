SELECT
    -- Çalışma kaydının kimliği.
    execution_id AS calisma_id,

    -- İşlem tablosuyla eşleşecek birleşik anahtar.
    TO_JSON_STRING(
        STRUCT(
            scenario AS senaryo,
            transaction_id AS islem
        )
    ) AS senaryo_islem_anahtari,

    -- Boyut tablolarıyla ilişki anahtarları.
    scenario AS senaryo_id,
    transaction_id AS islem_id,
    team_id AS ekip_id,
    stage_id AS asama_id,

    -- Çalışma detayları.
    visit_number AS ziyaret_numarasi,
    started_at AS baslangic_zamani,
    ended_at AS bitis_zamani,
    execution_status AS calisma_durumu,
    work_type AS calisma_turu,

    -- Aktif çalışma süresi.
    active_minutes AS aktif_calisma_dakikasi,

    ROUND(
        active_minutes / 60.0,
        4
    ) AS aktif_calisma_saati,

    -- Yeniden işleme göstergesi.
    CASE
        WHEN is_rework IS TRUE THEN 1
        ELSE 0
    END AS yeniden_isleme_mi,

    -- Kalite olayıyla bağlantı için kaynak kimlik.
    related_quality_event_id AS ilgili_kalite_olayi_id,

    -- Çalışmayı gerçekleştiren personel kimliği.
    employee_id AS personel_id

FROM
    `prefab-bruin-483617-b9.veriqora_bank.vw_senaryo_calisma_kayitlari`
