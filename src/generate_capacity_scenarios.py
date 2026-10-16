"""Veriqora | Kapasite senaryoları; pilot referanslarına dokunmaz."""
from __future__ import annotations
import argparse
import math
import shutil
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REF_FILES = ("business_calendar.csv", "sla_targets.csv", "cost_parameters.csv",
             "teams.csv", "process_stages.csv")
SCENARIOS = {
    "baseline": {},
    "targeted_25": {4: 1.25, 5: 1.25},
    "targeted_50": {4: 1.50, 5: 1.50},
    "targeted_100": {4: 2.00, 5: 2.00},
    "all_25": {i: 1.25 for i in range(1, 7)},
}

def build(reference: Path, destination: Path):
    reference, destination = reference.resolve(), destination.resolve()
    if reference == destination or reference in destination.parents:
        raise ValueError("Çıktı referans klasörünün içine yazılamaz.")
    base = pd.read_csv(reference / "team_capacity.csv")
    required = {"team_id", "capacity_date", "employee_count",
                "available_minutes", "overtime_capacity_minutes"}
    if not required.issubset(base.columns):
        raise ValueError(f"Eksik kapasite alanları: {required - set(base.columns)}")
    if base.duplicated(["team_id", "capacity_date"]).any():
        raise ValueError("Tekrarlanan ekip-gün kaydı.")
    if (base[["employee_count", "available_minutes", "overtime_capacity_minutes"]] < 0).any().any():
        raise ValueError("Negatif kapasite var.")

    summary = []
    for name, factors in SCENARIOS.items():
        df = base.copy()
        for i, row in df.iterrows():
            old = int(row.employee_count)
            if old == 0:
                continue
            multiplier = factors.get(int(row.team_id), 1)
            new = math.ceil(old * multiplier)
            df.at[i, "employee_count"] = new
            df.at[i, "available_minutes"] = round(int(row.available_minutes) * new / old)
            df.at[i, "overtime_capacity_minutes"] = round(
                int(row.overtime_capacity_minutes) * new / old)
        for col in ("employee_count", "available_minutes", "overtime_capacity_minutes"):
            df[col] = df[col].astype("int64")
        target = destination / name
        target.mkdir(parents=True, exist_ok=True)
        for filename in REF_FILES:
            shutil.copy2(reference / filename, target / filename)
        df.to_csv(target / "team_capacity.csv", index=False, encoding="utf-8-sig")
        for team, group in df.groupby("team_id"):
            before = base.loc[base.team_id == team]
            summary.append({
                "scenario": name, "team_id": int(team),
                "baseline_normal_minutes": int(before.available_minutes.sum()),
                "scenario_normal_minutes": int(group.available_minutes.sum()),
                "baseline_overtime_minutes": int(before.overtime_capacity_minutes.sum()),
                "scenario_overtime_minutes": int(group.overtime_capacity_minutes.sum()),
            })
        print(f"{name}: {len(df):,} ekip-gün kapasite kaydı -> {target}")
    pd.DataFrame(summary).to_csv(destination / "scenario_capacity_summary.csv",
                                 index=False, encoding="utf-8-sig")
    print("Senaryolar hazır. Bu adımda simülasyon çalıştırılmadı.")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reference", default="data/pilot")
    p.add_argument("--output", default="data/capacity_scenarios")
    args = p.parse_args()
    def path(value):
        v = Path(value)
        return v if v.is_absolute() else ROOT / v
    build(path(args.reference), path(args.output))

if __name__ == "__main__":
    main()
