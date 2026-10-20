SELECT
    -- Senaryo + işlem kimliğinden birleşik anahtar.
    TO_JSON_STRING(
        STRUCT(
            scenario AS senaryo,
            transaction_id AS islem
        )
    ) AS senaryo_islem_anahtari,

    -- Boyut tablolarıyla kurulacak ilişkilerin anahtarları.
    scenario AS senaryo_id,
    transaction_id AS islem_id,
    operation_id AS operasyon_id,
    sla_target_id AS sla_hedef_id,

    -- İşlemin temel özellikleri.
    complexity_level AS karmasiklik_seviyesi,
    opened_at AS acilis_zamani,
    closed_at AS kapanis_zamani,
    final_status AS islem_durumu,

    -- Power BI ölçülerinde kullanılabilecek göstergeler.
    CASE
        WHEN final_status = 'COMPLETED' THEN 1
        ELSE 0
    END AS tamamlandi_mi,

    CASE
        WHEN final_status = 'OPEN' THEN 1
        ELSE 0
    END AS acik_mi

FROM
    `prefab-bruin-483617-b9.veriqora_bank.vw_senaryo_islemleri`
