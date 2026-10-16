
from pathlib import Path

import numpy as np
import pandas as pd

# Veriqora Bank - Ekip Kapasitesi
# Sentetik veri üretimi

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pilot"

# Tekrarlanabilir sonuçlar için sabit seed
rng = np.random.default_rng(2025)

# Referans tablolarını oku
teams_df = pd.read_csv(DATA_DIR / "teams.csv")
calendar_df = pd.read_csv(DATA_DIR / "business_calendar.csv")

# Ekip bazında başlangıç çalışan sayıları
BASE_EMPLOYEE_COUNTS = {
    1: 8,   # Ödeme ve Transfer
    2: 6,   # Müşteri Bilgi Yönetimi
    3: 7,   # Hesap Operasyonları
    4: 6,   # Kredi Operasyonları
    5: 5,   # Yasal Takip
    6: 4,   # Operasyonel Kontrol
}

capacity_rows = []

for _, day in calendar_df.iterrows():

    capacity_date = day["calendar_date"]
    day_type = day["day_type"]

    if day_type == "FULL_DAY":
        daily_minutes = 480
    elif day_type == "HALF_DAY":
        daily_minutes = 180
    else:
        daily_minutes = 0

    for _, team in teams_df.iterrows():

        team_id = int(team["team_id"])
        base_count = BASE_EMPLOYEE_COUNTS[team_id]

        # Günlük çalışan sayısında küçük değişiklikler
        if daily_minutes > 0:
            employee_count = max(
                1,
                base_count + int(rng.choice(
                    [-1, 0, 1],
                    p=[0.15, 0.70, 0.15]
                ))
            )
        else:
            employee_count = 0

        available_minutes = employee_count * daily_minutes

        # Planlanan fazla mesai kapasitesi
        # Gerçekleşen fazla mesai değildir.
        if daily_minutes > 0 and rng.random() < 0.15:
            overtime_capacity_minutes = (
                employee_count * 30
            )
        else:
            overtime_capacity_minutes = 0

        capacity_rows.append({
            "team_id": team_id,
            "capacity_date": capacity_date,
            "employee_count": employee_count,
            "available_minutes": available_minutes,
            "overtime_capacity_minutes": overtime_capacity_minutes,
        })

capacity_df = pd.DataFrame(capacity_rows)

output_file = DATA_DIR / "team_capacity.csv"

capacity_df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("Veriqora Bank - Ekip Kapasitesi")
print("-" * 40)
print(f"Toplam ekip: {len(teams_df)}")
print(f"Toplam takvim günü: {len(calendar_df)}")
print(f"Toplam kapasite kaydı: {len(capacity_df)}")
print(f"\nDosya oluşturuldu: {output_file}")
