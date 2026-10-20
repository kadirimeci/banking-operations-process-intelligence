SELECT
    -- Bekleme kaydının kaynak kimliği.
    waiting_id AS bekleme_id,

    -- İşlem görünümüyle eşleşecek birleşik anahtar.
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

    -- Bekleme detayları.
    visit_number AS ziyaret_numarasi,
    waiting_type AS bekleme_turu,
    waiting_reason AS bekleme_nedeni,

    started_at AS baslangic_zamani,
    ended_at AS bitis_zamani,

    -- Yalnızca geçerli ve tamamlanmış beklemeler için süre.
    CASE
        WHEN started_at IS NOT NULL
         AND ended_at IS NOT NULL
         AND ended_at >= started_at
        THEN TIMESTAMP_DIFF(
            ended_at,
            started_at,
            SECOND
        ) / 60.0
        ELSE NULL
    END AS bekleme_dakikasi,

    CASE
        WHEN started_at IS NOT NULL
         AND ended_at IS NOT NULL
         AND ended_at >= started_at
        THEN ROUND(
            TIMESTAMP_DIFF(
                ended_at,
                started_at,
                SECOND
            ) / 3600.0,
            4
        )
        ELSE NULL
    END AS bekleme_saati,

    -- Henüz sona ermemiş beklemeleri işaretle.
    CASE
        WHEN ended_at IS NULL THEN 1
        ELSE 0
    END AS acik_bekleme_mi,

    -- SLA hariç tutma değerlendirmesinde kullanılacak alanlar.
    is_excludable AS haric_tutulabilir_mi,
    reason_verified AS neden_dogrulandi_mi

FROM
    `prefab-bruin-483617-b9.veriqora_bank.vw_senaryo_bekleme_kayitlari`
