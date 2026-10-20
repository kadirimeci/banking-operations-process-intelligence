SELECT
    s.sla_target_id AS sla_hedef_id,

    s.operation_id AS operasyon_id,

    o.operation_name AS operasyon_adi,

    s.complexity_level AS karmasiklik_seviyesi,

    s.target_minutes AS hedef_dakika,

    ROUND(
        s.target_minutes / 60.0,
        2
    ) AS hedef_saat,

    s.valid_from AS gecerlilik_baslangici,

    SAFE_CAST(s.valid_to AS DATE) AS gecerlilik_bitisi

FROM
    `prefab-bruin-483617-b9.veriqora_bank.sla_targets` AS s

LEFT JOIN
    `prefab-bruin-483617-b9.veriqora_bank.operations` AS o
    ON s.operation_id = o.operation_id
