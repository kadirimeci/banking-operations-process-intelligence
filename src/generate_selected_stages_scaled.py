"""Veriqora Bank | Parametrik süreç aşaması seçimi.

Örnek:
python src/generate_selected_stages_scaled.py --input data/scale_test_1000 --output data/scale_test_1000
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_COLUMNS = ["transaction_id", "operation_id", "team_id", "stage_id",
                  "stage_name", "stage_order", "is_mandatory"]


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if str(value).strip().lower() in ("true", "1"):
        return True
    if str(value).strip().lower() in ("false", "0"):
        return False
    raise ValueError(f"Geçersiz boolean değer: {value!r}")


def generate(input_dir: Path, reference_dir: Path, output_dir: Path):
    input_dir = input_dir.resolve()
    reference_dir = reference_dir.resolve()
    output_dir = output_dir.resolve()
    pilot = (ROOT / "data" / "pilot").resolve()
    if output_dir == pilot:
        raise ValueError("Pilot klasörünün üzerine yazmak yasaktır.")
    tx = pd.read_csv(input_dir / "transactions.csv")
    attrs = pd.read_csv(input_dir / "transaction_attributes.csv")
    stages = pd.read_csv(reference_dir / "process_stages.csv")
    teams = pd.read_csv(reference_dir / "teams.csv")

    if tx.empty or not tx.transaction_id.is_unique or not attrs.transaction_id.is_unique:
        raise ValueError("İşlemler boş veya işlem kimlikleri tekrarlı.")
    if set(tx.transaction_id) != set(attrs.transaction_id):
        raise ValueError("İşlem ve işlem özellikleri bire bir eşleşmiyor.")
    if stages.stage_id.duplicated().any() or stages.duplicated(["operation_id", "stage_order"]).any():
        raise ValueError("Süreç aşaması kimliği veya sırası tekrarlı.")
    if teams.operation_id.duplicated().any():
        raise ValueError("Bir operasyon için birden fazla ekip tanımlanmış.")

    base = tx[["transaction_id", "operation_id"]].merge(
        teams[["operation_id", "team_id"]], on="operation_id", how="left",
        validate="many_to_one"
    )
    if base.team_id.isna().any():
        raise ValueError("Ekibi bulunamayan işlem var.")
    selected = base.merge(
        stages[["operation_id", "stage_id", "stage_name", "stage_order", "is_mandatory"]],
        on="operation_id", how="left", validate="many_to_many"
    ).merge(
        attrs[["transaction_id", "requires_approval", "requires_manual_review"]],
        on="transaction_id", how="left", validate="many_to_one"
    )
    if selected[["stage_id", "requires_approval", "requires_manual_review", "is_mandatory"]].isna().any().any():
        raise ValueError("Süreç aşaması veya gerekli işlem özelliği eksik.")

    mandatory = selected.is_mandatory.map(parse_bool)
    approval = selected.requires_approval.map(parse_bool)
    manual = selected.requires_manual_review.map(parse_bool)
    optional = ~mandatory
    op, order = selected.operation_id, selected.stage_order
    transfer_control = (op == 1) & (order == 3)
    account_approval = (op == 3) & (order == 4)
    control_correction = (op == 6) & (order == 4)
    unknown = optional & ~(transfer_control | account_approval | control_correction)
    if unknown.any():
        examples = selected.loc[unknown, ["operation_id", "stage_order"]].drop_duplicates().to_dict("records")
        raise ValueError(f"Tanımlanmamış isteğe bağlı aşama: {examples}")

    include = mandatory | (transfer_control & (approval | manual)) | (account_approval & approval)
    result = selected.loc[include, OUTPUT_COLUMNS].sort_values(
        ["transaction_id", "stage_order"], kind="stable"
    ).reset_index(drop=True)

    if result.transaction_id.nunique() != len(tx):
        raise AssertionError("Aşaması bulunmayan işlem var.")
    if result.duplicated(["transaction_id", "stage_id"]).any():
        raise AssertionError("İşlem-aşama kaydı tekrarlı.")
    if not result.groupby("transaction_id").stage_order.apply(lambda x: x.is_monotonic_increasing).all():
        raise AssertionError("Aşama sırası bozuk.")

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "selected_stages.csv"
    result.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"VERIQORA | AŞAMA SEÇİMİ | İşlem: {len(tx):,}")
    print(f"Tanımlı eşleşme: {len(selected):,} | Seçilen aşama: {len(result):,}")
    print(f"Atlanan isteğe bağlı aşama: {len(selected)-len(result):,}")
    print("Operasyon bazında seçilen aşamalar:")
    print(result.groupby("operation_id").size().to_string())
    print(f"Kontroller: BAŞARILI | Çıktı: {path}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--reference", default="data/pilot")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    def resolve(path):
        p = Path(path)
        return p if p.is_absolute() else ROOT / p
    generate(resolve(args.input), resolve(args.reference), resolve(args.output))


if __name__ == "__main__":
    main()
