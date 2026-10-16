
from pathlib import Path

import pandas as pd
import pytest

# Veriqora Bank - Referans Veri Kalite Testleri

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pilot"

EXPECTED_COUNTS = {
    "operations.csv": 6,
    "process_stages.csv": 30,
    "teams.csv": 6,
    "sla_targets.csv": 18,
    "business_calendar.csv": 730,
    "team_capacity.csv": 4380,
    "cost_parameters.csv": 6,
}


@pytest.mark.parametrize(
    "filename, expected_count",
    EXPECTED_COUNTS.items()
)
def test_file_exists_and_row_count(filename, expected_count):

    file_path = DATA_DIR / filename

    assert file_path.exists(), (
        f"Dosya bulunamadı: {filename}"
    )

    df = pd.read_csv(file_path)

    assert len(df) == expected_count, (
        f"{filename}: Beklenen {expected_count}, "
        f"bulunan {len(df)} kayıt."
    )



# Referans tabloları arasındaki yabancı anahtar kontrolleri

@pytest.mark.parametrize(
    "child_file, child_column, parent_file, parent_column",
    [
        ("process_stages.csv", "operation_id",
         "operations.csv", "operation_id"),

        ("teams.csv", "operation_id",
         "operations.csv", "operation_id"),

        ("sla_targets.csv", "operation_id",
         "operations.csv", "operation_id"),

        ("team_capacity.csv", "team_id",
         "teams.csv", "team_id"),

        ("cost_parameters.csv", "team_id",
         "teams.csv", "team_id"),
    ]
)
def test_foreign_key_integrity(
    child_file,
    child_column,
    parent_file,
    parent_column
):
    child_df = pd.read_csv(DATA_DIR / child_file)
    parent_df = pd.read_csv(DATA_DIR / parent_file)

    valid_ids = set(parent_df[parent_column].dropna())

    invalid_ids = set(
        child_df[child_column].dropna()
    ) - valid_ids

    assert not child_df[child_column].isna().any(), (
        f"{child_file}.{child_column} boş değer içeriyor."
    )

    assert not invalid_ids, (
        f"{child_file}.{child_column}: "
        f"Geçersiz referanslar: {invalid_ids}"
    )




# Birincil anahtar benzersizlik ve boş değer kontrolleri

@pytest.mark.parametrize(
    "filename, primary_key_columns",
    [
        ("operations.csv", ["operation_id"]),
        ("process_stages.csv", ["stage_id"]),
        ("teams.csv", ["team_id"]),
        ("sla_targets.csv", ["sla_target_id"]),
        ("business_calendar.csv", ["calendar_date"]),
        ("team_capacity.csv", ["team_id", "capacity_date"]),
        ("cost_parameters.csv", ["cost_parameter_id"]),
    ]
)
def test_primary_key_integrity(filename, primary_key_columns):

    df = pd.read_csv(DATA_DIR / filename)

    # Birincil anahtar alanları boş olamaz
    assert not df[primary_key_columns].isna().any().any(), (
        f"{filename}: Birincil anahtarda boş değer bulundu."
    )

    # Aynı birincil anahtar tekrar edemez
    duplicates = df.duplicated(
        subset=primary_key_columns,
        keep=False
    )

    assert not duplicates.any(), (
        f"{filename}: Tekrarlanan birincil anahtar bulundu."
    )



# İş takvimi ve ekip kapasitesi tutarlılık testi

def test_team_capacity_calendar_consistency():

    calendar_df = pd.read_csv(
        DATA_DIR / "business_calendar.csv"
    )

    capacity_df = pd.read_csv(
        DATA_DIR / "team_capacity.csv"
    )

    # Kapasite kayıtlarına gün türlerini ekle
    merged_df = capacity_df.merge(
        calendar_df[["calendar_date", "day_type"]],
        left_on="capacity_date",
        right_on="calendar_date",
        how="left",
        validate="many_to_one"
    )

    # Takvimde karşılığı olmayan tarih bulunmamalı
    assert merged_df["day_type"].notna().all(), (
        "Takvimde bulunmayan kapasite tarihi var."
    )

    daily_minutes = {
        "FULL_DAY": 480,
        "HALF_DAY": 180,
        "HOLIDAY": 0,
        "WEEKEND": 0,
    }

    expected_minutes = (
        merged_df["employee_count"]
        * merged_df["day_type"].map(daily_minutes)
    )

    # Normal kapasite doğru hesaplanmış mı?
    assert (
        merged_df["available_minutes"] == expected_minutes
    ).all(), (
        "Normal kapasite ile iş takvimi uyuşmuyor."
    )

    # Tatil ve hafta sonlarında normal kapasite sıfır olmalı
    non_working_days = merged_df[
        merged_df["day_type"].isin(["HOLIDAY", "WEEKEND"])
    ]

    assert (
        non_working_days["available_minutes"] == 0
    ).all(), (
        "Çalışılmayan günlerde normal kapasite sıfır değil."
    )

    # Planlanan fazla mesai kapasitesi negatif olamaz
    assert (
        merged_df["overtime_capacity_minutes"] >= 0
    ).all(), (
        "Negatif fazla mesai kapasitesi bulundu."
    )


# Pilot işlem açılış tarihleri ve SLA kontrolleri

def test_pilot_transaction_opening_dates():

    transactions_df = pd.read_csv(
        DATA_DIR / "transactions.csv"
    )

    attributes_df = pd.read_csv(
        DATA_DIR / "transaction_attributes.csv"
    )

    sla_df = pd.read_csv(
        DATA_DIR / "sla_targets.csv"
    )

    # 300 işlem ve 300 özellik kaydı bulunmalı
    assert len(transactions_df) == 300
    assert len(attributes_df) == 300

    # İşlem kimlikleri benzersiz ve eşleşiyor olmalı
    assert transactions_df["transaction_id"].is_unique
    assert attributes_df["transaction_id"].is_unique

    assert set(transactions_df["transaction_id"]) == set(
        attributes_df["transaction_id"]
    )

    # Açılış tarihleri 2025 içerisinde olmalı
    opened_at = pd.to_datetime(
        transactions_df["opened_at"]
    )

    assert opened_at.notna().all()

    assert (
        (opened_at >= pd.Timestamp("2025-01-01"))
        & (opened_at < pd.Timestamp("2026-01-01"))
    ).all()

    # SLA hedefleri geçerli operasyon ve karmaşıklığa ait olmalı
    merged_df = transactions_df.merge(
        sla_df[
            ["sla_target_id", "operation_id", "complexity_level",
             "valid_from", "valid_to"]
        ],
        on="sla_target_id",
        how="left",
        suffixes=("_transaction", "_sla"),
        validate="many_to_one"
    )

    assert merged_df["operation_id_sla"].notna().all()

    assert (
        merged_df["operation_id_transaction"]
        == merged_df["operation_id_sla"]
    ).all()

    assert (
        merged_df["complexity_level_transaction"]
        == merged_df["complexity_level_sla"]
    ).all()

    valid_from = pd.to_datetime(merged_df["valid_from"])
    valid_to = pd.to_datetime(merged_df["valid_to"])

    assert (
        (opened_at >= valid_from)
        & (valid_to.isna() | (opened_at < valid_to))
    ).all()



# İşlem açılışlarının iş takvimiyle uyumluluğu

def test_transaction_opening_calendar_categories():

    transactions_df = pd.read_csv(
        DATA_DIR / "transactions.csv"
    )

    calendar_df = pd.read_csv(
        DATA_DIR / "business_calendar.csv"
    )

    transactions_df["opened_at"] = pd.to_datetime(
        transactions_df["opened_at"]
    )

    transactions_df["calendar_date"] = (
        transactions_df["opened_at"].dt.strftime("%Y-%m-%d")
    )

    merged_df = transactions_df.merge(
        calendar_df[["calendar_date", "day_type"]],
        on="calendar_date",
        how="left",
        validate="many_to_one"
    )

    assert merged_df["day_type"].notna().all(), (
        "Takvimde bulunmayan işlem açılış tarihi var."
    )

    def classify_opening(row):
        hour = row["opened_at"].hour
        day_type = row["day_type"]

        if day_type in ["HOLIDAY", "WEEKEND"]:
            return "NON_WORKING_DAY"

        if day_type == "HALF_DAY":
            if 9 <= hour < 12:
                return "BUSINESS_HOURS"
            return "WEEKDAY_OFF_HOURS"

        if 9 <= hour < 12 or 13 <= hour < 18:
            return "BUSINESS_HOURS"

        return "WEEKDAY_OFF_HOURS"

    categories = merged_df.apply(
        classify_opening,
        axis=1
    )

    counts = categories.value_counts()

    assert len(categories) == 300

    assert set(categories).issubset({
        "BUSINESS_HOURS",
        "WEEKDAY_OFF_HOURS",
        "NON_WORKING_DAY",
    })

    # Pilot için geniş kabul aralıkları
    proportions = counts / len(categories)

    assert 0.65 <= proportions.get(
        "BUSINESS_HOURS", 0
    ) <= 0.85

    assert 0.08 <= proportions.get(
        "WEEKDAY_OFF_HOURS", 0
    ) <= 0.25

    assert 0.05 <= proportions.get(
        "NON_WORKING_DAY", 0
    ) <= 0.20
