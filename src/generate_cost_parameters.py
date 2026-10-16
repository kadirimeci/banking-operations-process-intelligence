
from pathlib import Path

import pandas as pd

# Veriqora Bank - Maliyet Parametreleri
# Tüm maliyetler varsayımsaldır.

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "pilot"

HOURLY_COSTS = {
    1: 420.0,
    2: 390.0,
    3: 410.0,
    4: 480.0,
    5: 460.0,
    6: 440.0,
}

cost_rows = []

for cost_parameter_id, (team_id, hourly_cost) in enumerate(
    HOURLY_COSTS.items(),
    start=1
):
    cost_rows.append({
        "cost_parameter_id": cost_parameter_id,
        "team_id": team_id,
        "valid_from": "2025-01-01",
        "valid_to": None,
        "hourly_cost": hourly_cost,
        "overtime_multiplier": 1.5,
    })

cost_df = pd.DataFrame(cost_rows)

output_file = OUTPUT_DIR / "cost_parameters.csv"

cost_df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("Veriqora Bank - Maliyet Parametreleri")
print("-" * 40)
print(f"Toplam maliyet parametresi: {len(cost_df)}")
print(f"Dosya oluşturuldu: {output_file}")
