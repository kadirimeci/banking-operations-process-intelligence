SELECT
    scenario AS senaryo_id,

    CASE scenario
        WHEN 'baseline' THEN 'Mevcut Durum'
        WHEN 'targeted_25' THEN 'Hedefli Kapasite +%25'
        WHEN 'targeted_50' THEN 'Hedefli Kapasite +%50'
        WHEN 'targeted_100' THEN 'Hedefli Kapasite +%100'
        WHEN 'all_25' THEN 'Tüm Ekiplere +%25'
        ELSE scenario
    END AS senaryo_adi,

    CASE scenario
        WHEN 'baseline' THEN 1
        WHEN 'targeted_25' THEN 2
        WHEN 'targeted_50' THEN 3
        WHEN 'targeted_100' THEN 4
        WHEN 'all_25' THEN 5
        ELSE 99
    END AS senaryo_sirasi

FROM
    `prefab-bruin-483617-b9.veriqora_bank.scenario_comparison`
