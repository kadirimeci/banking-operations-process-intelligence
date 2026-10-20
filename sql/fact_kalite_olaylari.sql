SELECT
    -- Kalite olayının kaynak kimliği.
    event_id AS kalite_olayi_id,

    -- İşlem olgu görünümüyle eşleşecek birleşik anahtar.
    TO_JSON_STRING(
        STRUCT(
            scenario AS senaryo,
            transaction_id AS islem
        )
    ) AS senaryo_islem_anahtari,

    -- Boyut tablolarıyla ilişki anahtarları.
    scenario AS senaryo_id,
    transaction_id AS islem_id,
    stage_id AS asama_id,

    -- Kalite olayının ayrıntıları.
    visit_number AS ziyaret_numarasi,
    event_type AS olay_turu,
    error_category AS hata_kategorisi,

    detected_at AS tespit_zamani,
    resolved_at AS cozum_zamani,

    -- Yeniden işleme gereksinimi.
    CASE
        WHEN requires_rework IS TRUE THEN 1
        ELSE 0
    END AS yeniden_isleme_gerekli_mi,

    -- Kök olay bağlantısı için kaynak görünümdeki değer.
    root_event_id AS kok_olay_id,

    -- Çözüm süresi: yalnızca geçerli tarihler için.
    CASE
        WHEN detected_at IS NOT NULL
         AND resolved_at IS NOT NULL
         AND resolved_at >= detected_at
        THEN ROUND(
            TIMESTAMP_DIFF(
                resolved_at,
                detected_at,
                SECOND
            ) / 3600.0,
            4
        )
        ELSE NULL
    END AS cozum_suresi_saat

FROM
    `prefab-bruin-483617-b9.veriqora_bank.vw_senaryo_kalite_olaylari`
