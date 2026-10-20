SELECT
    t.team_id AS ekip_id,

    t.team_name AS ekip_adi,

    t.operation_id AS operasyon_id,

    o.operation_name AS operasyon_adi,

    t.is_active AS aktif_mi

FROM
    `prefab-bruin-483617-b9.veriqora_bank.teams` AS t

LEFT JOIN
    `prefab-bruin-483617-b9.veriqora_bank.operations` AS o
    ON t.operation_id = o.operation_id
