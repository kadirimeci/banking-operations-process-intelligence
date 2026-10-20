SELECT
    p.stage_id AS asama_id,

    p.stage_name AS asama_adi,

    p.stage_order AS asama_sirasi,

    p.operation_id AS operasyon_id,

    o.operation_name AS operasyon_adi,

    p.is_mandatory AS zorunlu_mu

FROM
    `prefab-bruin-483617-b9.veriqora_bank.process_stages` AS p

LEFT JOIN
    `prefab-bruin-483617-b9.veriqora_bank.operations` AS o
    ON p.operation_id = o.operation_id
