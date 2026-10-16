
from pathlib import Path

import numpy as np
import pandas as pd

# Veriqora Bank - Sentetik İşlem Üretimi
# Pilot hedef: 300 işlem
# Sabit seed: 2025

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pilot"

rng = np.random.default_rng(2025)

# Operasyon bazında pilot işlem sayıları
OPERATION_COUNTS = {
    1: 90,
    2: 60,
    3: 54,
    4: 45,
    5: 30,
    6: 21,
}

# Operasyonlara özgü talep türleri
REQUEST_TYPES = {
    1: ["STANDARD_TRANSFER", "HIGH_VALUE_TRANSFER",
        "INTERNATIONAL_TRANSFER", "NON_STANDARD_TRANSFER"],
    2: ["CONTACT_UPDATE", "ADDRESS_UPDATE",
        "IDENTITY_UPDATE", "MULTIPLE_INFO_UPDATE"],
    3: ["ACCOUNT_OPENING", "ACCOUNT_CLOSURE",
        "AUTHORITY_CHANGE", "NON_STANDARD_ACCOUNT"],
    4: ["STANDARD_CREDIT", "CREDIT_RESTRUCTURING",
        "COLLATERAL_REVIEW", "NON_STANDARD_CREDIT"],
    5: ["STANDARD_FOLLOWUP", "DOCUMENT_REVIEW",
        "EXTERNAL_COORDINATION", "COMPLEX_LEGAL_CASE"],
    6: ["ROUTINE_CONTROL", "ADDITIONAL_CONTROL",
        "MULTI_STAGE_REVIEW", "CORRECTION_REQUEST"],
}

# Standart dışı veya kapsamlı talepler
COMPLEX_REQUEST_TYPES = {
    "INTERNATIONAL_TRANSFER",
    "NON_STANDARD_TRANSFER",
    "MULTIPLE_INFO_UPDATE",
    "AUTHORITY_CHANGE",
    "NON_STANDARD_ACCOUNT",
    "CREDIT_RESTRUCTURING",
    "COLLATERAL_REVIEW",
    "NON_STANDARD_CREDIT",
    "EXTERNAL_COORDINATION",
    "COMPLEX_LEGAL_CASE",
    "MULTI_STAGE_REVIEW",
    "CORRECTION_REQUEST",
}

def calculate_complexity(attributes):
    score = 0

    if attributes["request_type"] in COMPLEX_REQUEST_TYPES:
        score += 2

    if attributes["requires_approval"]:
        score += 1

    if attributes["requires_external_party"]:
        score += 2

    if attributes["requires_manual_review"]:
        score += 2

    document_count = attributes["document_count"]

    if document_count >= 6:
        score += 2
    elif document_count >= 3:
        score += 1

    if attributes["amount_band"] == "HIGH":
        score += 1

    if score >= 6:
        return "HIGH"
    elif score >= 3:
        return "MEDIUM"
    else:
        return "LOW"

print("Veriqora Bank - İşlem Üretim Hazırlığı")
print("-" * 40)
print(f"Planlanan pilot işlem: {sum(OPERATION_COUNTS.values())}")
print(f"Tanımlanan operasyon: {len(REQUEST_TYPES)}")
print("Karmaşıklık puanlama fonksiyonu hazır.")



# Operasyonlara göre başlangıç olasılıkları
# Sıra: ek onay, dış taraf, manuel inceleme
OPERATION_PROBABILITIES = {
    1: (0.20, 0.10, 0.15),
    2: (0.15, 0.05, 0.15),
    3: (0.25, 0.10, 0.20),
    4: (0.55, 0.30, 0.45),
    5: (0.35, 0.60, 0.50),
    6: (0.30, 0.10, 0.40),
}

# Belge sayısı için operasyon bazlı aralıklar
DOCUMENT_RANGES = {
    1: (0, 3),
    2: (0, 4),
    3: (1, 5),
    4: (2, 9),
    5: (2, 10),
    6: (1, 6),
}

attribute_rows = []
transaction_id = 1

for operation_id, transaction_count in OPERATION_COUNTS.items():

    approval_prob, external_prob, manual_prob = (
        OPERATION_PROBABILITIES[operation_id]
    )

    min_docs, max_docs = DOCUMENT_RANGES[operation_id]

    for _ in range(transaction_count):

        request_type = str(
            rng.choice(REQUEST_TYPES[operation_id])
        )

        document_count = int(
            rng.integers(min_docs, max_docs + 1)
        )

        requires_approval = bool(
            rng.random() < approval_prob
        )

        requires_external_party = bool(
            rng.random() < external_prob
        )

        requires_manual_review = bool(
            rng.random() < manual_prob
        )

        # Tutar kategorisi yalnızca ilgili operasyonlarda kullanılır
        if operation_id in [1, 3, 4]:
            amount_band = str(
                rng.choice(
                    ["LOW", "MEDIUM", "HIGH"],
                    p=[0.50, 0.35, 0.15]
                )
            )
        else:
            amount_band = None

        attribute_rows.append({
            "transaction_id": transaction_id,
            "request_type": request_type,
            "document_count": document_count,
            "requires_approval": requires_approval,
            "requires_external_party": requires_external_party,
            "requires_manual_review": requires_manual_review,
            "amount_band": amount_band,
        })

        transaction_id += 1

attributes_df = pd.DataFrame(attribute_rows)

attributes_file = DATA_DIR / "transaction_attributes.csv"

attributes_df.to_csv(
    attributes_file,
    index=False,
    encoding="utf-8-sig"
)

print("\ntransaction_attributes.csv oluşturuldu!")
print(f"Toplam işlem özelliği kaydı: {len(attributes_df)}")



# İşlem özelliklerinden karmaşıklık seviyesini hesapla

complexity_rows = []
transaction_id = 1

for operation_id, transaction_count in OPERATION_COUNTS.items():

    for _ in range(transaction_count):

        attributes = attributes_df.loc[
            attributes_df["transaction_id"] == transaction_id
        ].iloc[0]

        complexity_level = calculate_complexity(attributes)

        complexity_rows.append({
            "transaction_id": transaction_id,
            "operation_id": operation_id,
            "complexity_level": complexity_level,
        })

        transaction_id += 1

complexity_df = pd.DataFrame(complexity_rows)

# SLA referans tablosunu oku
sla_df = pd.read_csv(DATA_DIR / "sla_targets.csv")

# Her işlem için operasyon ve karmaşıklığa uygun SLA hedefini bul
transaction_sla_df = complexity_df.merge(
    sla_df[
        ["sla_target_id", "operation_id", "complexity_level"]
    ],
    on=["operation_id", "complexity_level"],
    how="left",
    validate="many_to_one"
)

# Eşleşmeyen SLA hedefi bulunmamalı
assert transaction_sla_df["sla_target_id"].notna().all(), (
    "Bazı işlemler için SLA hedefi bulunamadı."
)

# Henüz kapanış bilgisi üretmiyoruz
transaction_sla_df["opened_at"] = None
transaction_sla_df["closed_at"] = None
transaction_sla_df["final_status"] = None

# Veri sözlüğündeki sütun sırasını kullan
transaction_sla_df = transaction_sla_df[
    [
        "transaction_id",
        "operation_id",
        "complexity_level",
        "opened_at",
        "closed_at",
        "final_status",
        "sla_target_id",
    ]
]

# Geçici işlem tablosunu kaydet
output_file = DATA_DIR / "transactions.csv"

transaction_sla_df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("\ntransactions.csv oluşturuldu!")
print(f"Toplam işlem: {len(transaction_sla_df)}")

print("\nKarmaşıklık dağılımı:")
print(
    transaction_sla_df["complexity_level"].value_counts()
)




# 2025 yılı için gerçekçi işlem açılış zamanları

calendar_df = pd.read_csv(
    DATA_DIR / "business_calendar.csv"
)

calendar_df["calendar_date"] = pd.to_datetime(
    calendar_df["calendar_date"]
)

calendar_2025 = calendar_df[
    calendar_df["calendar_date"].dt.year == 2025
].copy()

# Çalışma günü ve mesai saatlerini esas alan örnekleme
# Mesai içi: %75
# Hafta içi mesai dışı: %15
# Hafta sonu ve resmî tatiller: %10

def get_opening_category(day, hour):
    day_type = day["day_type"]

    if day_type in ["HOLIDAY", "WEEKEND"]:
        return "NON_WORKING_DAY"

    if day_type == "HALF_DAY":
        if 9 <= hour < 12:
            return "BUSINESS_HOURS"
        return "WEEKDAY_OFF_HOURS"

    if 9 <= hour < 12 or 13 <= hour < 18:
        return "BUSINESS_HOURS"

    return "WEEKDAY_OFF_HOURS"


opening_slots = {
    "BUSINESS_HOURS": [],
    "WEEKDAY_OFF_HOURS": [],
    "NON_WORKING_DAY": [],
}

for _, day in calendar_2025.iterrows():
    for hour in range(24):
        category = get_opening_category(day, hour)

        opening_slots[category].append(
            day["calendar_date"] + pd.Timedelta(hours=hour)
        )

category_names = [
    "BUSINESS_HOURS",
    "WEEKDAY_OFF_HOURS",
    "NON_WORKING_DAY",
]

category_probabilities = [0.75, 0.15, 0.10]

opening_dates = []

for _ in range(len(transaction_sla_df)):
    category = rng.choice(
        category_names,
        p=category_probabilities
    )

    selected_slot = rng.choice(
        opening_slots[category]
    )

    # Saat dilimi içerisindeki dakika ve saniyeyi belirle
    opened_at = (
        pd.Timestamp(selected_slot)
        + pd.Timedelta(
            minutes=int(rng.integers(0, 60)),
            seconds=int(rng.integers(0, 60))
        )
    )

    opening_dates.append(opened_at)

transaction_sla_df["opened_at"] = opening_dates

# SLA hedefinin işlem açılışında geçerli olduğunu doğrula
sla_validity_df = transaction_sla_df.merge(
    sla_df[
        ["sla_target_id", "valid_from", "valid_to"]
    ],
    on="sla_target_id",
    how="left",
    validate="many_to_one"
)

opened_at = pd.to_datetime(sla_validity_df["opened_at"])
valid_from = pd.to_datetime(sla_validity_df["valid_from"])
valid_to = pd.to_datetime(sla_validity_df["valid_to"])

valid_sla = (
    (opened_at >= valid_from)
    & (
        valid_to.isna()
        | (opened_at < valid_to)
    )
)

assert valid_sla.all(), (
    "Açılış tarihinde geçerli olmayan SLA hedefi bulundu."
)

transaction_sla_df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("\nİşlem açılış tarihleri güncellendi!")
print("Toplam işlem:", len(transaction_sla_df))

# Gerçekleşen kategori dağılımını kontrol et
actual_categories = []

calendar_lookup = calendar_2025.set_index(
    "calendar_date"
)

for opened_at in transaction_sla_df["opened_at"]:
    day = calendar_lookup.loc[opened_at.normalize()]
    actual_categories.append(
        get_opening_category(day, opened_at.hour)
    )

category_distribution = (
    pd.Series(actual_categories)
    .value_counts()
    .reindex(category_names, fill_value=0)
)

print("\nAçılış zamanı dağılımı (%):")
print(
    (category_distribution / len(transaction_sla_df) * 100)
    .round(1)
)
