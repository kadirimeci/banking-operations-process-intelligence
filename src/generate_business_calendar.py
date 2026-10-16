
from datetime import date, datetime, timedelta
from pathlib import Path

import holidays
import pandas as pd

# Veriqora Bank - Türkiye İş Takvimi
# Kapsam: 01.01.2025 - 31.12.2026

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "pilot"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 12, 31)

# Türkiye resmî tatilleri
tr_holidays = holidays.country_holidays(
    "TR",
    years=[2025, 2026]
)

# Arife ve yarım günler
# Bayram arifeleri ve 28 Ekim öğleden sonrası
HALF_DAYS = {
    date(2025, 3, 29): "Ramazan Bayramı Arifesi",
    date(2025, 6, 5): "Kurban Bayramı Arifesi",
    date(2025, 10, 28): "Cumhuriyet Bayramı Arifesi",
    date(2026, 3, 19): "Ramazan Bayramı Arifesi",
    date(2026, 5, 26): "Kurban Bayramı Arifesi",
    date(2026, 10, 28): "Cumhuriyet Bayramı Arifesi",
}

calendar_rows = []
current_date = START_DATE

while current_date <= END_DATE:

    holiday_name = tr_holidays.get(current_date)

    if current_date in HALF_DAYS and current_date.weekday() < 5:
        day_type = "HALF_DAY"
        is_business_day = True
        business_start = "09:00"
        lunch_start = None
        lunch_end = None
        business_end = "12:00"
        holiday_name = HALF_DAYS[current_date]

    elif holiday_name:
        day_type = "HOLIDAY"
        is_business_day = False
        business_start = None
        lunch_start = None
        lunch_end = None
        business_end = None

    elif current_date.weekday() >= 5:
        day_type = "WEEKEND"
        is_business_day = False
        business_start = None
        lunch_start = None
        lunch_end = None
        business_end = None

    else:
        day_type = "FULL_DAY"
        is_business_day = True
        business_start = "09:00"
        lunch_start = "12:00"
        lunch_end = "13:00"
        business_end = "18:00"

    calendar_rows.append({
        "calendar_date": current_date.isoformat(),
        "day_type": day_type,
        "is_business_day": is_business_day,
        "business_start": business_start,
        "lunch_start": lunch_start,
        "lunch_end": lunch_end,
        "business_end": business_end,
        "holiday_name": holiday_name,
    })

    current_date += timedelta(days=1)

calendar_df = pd.DataFrame(calendar_rows)

output_file = OUTPUT_DIR / "business_calendar.csv"

calendar_df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("Veriqora Bank - İş Takvimi")
print("-" * 40)
print(f"Toplam takvim günü: {len(calendar_df)}")
print("\nGün türü dağılımı:")
print(calendar_df["day_type"].value_counts())
print(f"\nDosya oluşturuldu: {output_file}")
