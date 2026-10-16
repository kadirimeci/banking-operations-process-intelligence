
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
