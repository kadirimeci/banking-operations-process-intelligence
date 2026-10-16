
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pilot"


def test_optional_stage_selection():

    transactions = pd.read_csv(
        DATA_DIR / "transactions.csv"
    )

    attributes = pd.read_csv(
        DATA_DIR / "transaction_attributes.csv"
    )

    stages = pd.read_csv(
        DATA_DIR / "process_stages.csv"
    )

    df = transactions[
        ["transaction_id", "operation_id"]
    ].merge(
        attributes[
            [
                "transaction_id",
                "requires_approval",
                "requires_manual_review"
            ]
        ],
        on="transaction_id",
        validate="one_to_one"
    ).merge(
        stages[
            [
                "operation_id",
                "stage_id",
                "stage_order",
                "is_mandatory"
            ]
        ],
        on="operation_id",
        validate="many_to_many"
    )

    def as_bool(value):
        if isinstance(value, bool):
            return value
        if str(value).lower() in ("true", "1"):
            return True
        if str(value).lower() in ("false", "0"):
            return False
        raise ValueError(f"Geçersiz değer: {value}")

    def expected_selection(row):
        if as_bool(row["is_mandatory"]):
            return True

        op = int(row["operation_id"])
        order = int(row["stage_order"])

        if op == 1 and order == 3:
            return (
                as_bool(row["requires_approval"])
                or as_bool(row["requires_manual_review"])
            )

        if op == 3 and order == 4:
            return as_bool(row["requires_approval"])

        if op == 6 and order == 4:
            return False

        raise ValueError("Tanımsız isteğe bağlı aşama")

    df["selected"] = df.apply(
        expected_selection,
        axis=1
    )

    assert len(df) == 1500
    assert df["transaction_id"].nunique() == 300

    # Mevcut pilot veri için beklenen seçim sayıları
    assert int(df["selected"].sum()) == 1375

    selected_counts = (
        df[df["selected"]]
        .groupby("operation_id")
        .size()
        .to_dict()
    )

    assert selected_counts == {
        1: 386,
        2: 300,
        3: 230,
        4: 225,
        5: 150,
        6: 84,
    }

    # Düzeltme aşaması başlangıçta seçilmemeli
    corrections = df[
        (df["operation_id"] == 6)
        & (df["stage_order"] == 4)
    ]

    assert not corrections["selected"].any()



def test_saved_stage_selection_matches_attributes():

    selected = pd.read_csv(
        DATA_DIR / "selected_stages.csv"
    )

    transactions = pd.read_csv(
        DATA_DIR / "transactions.csv"
    )

    attributes = pd.read_csv(
        DATA_DIR / "transaction_attributes.csv"
    )

    stages = pd.read_csv(
        DATA_DIR / "process_stages.csv"
    )

    # Her işlem ve aşama birleşimi benzersiz olmalı
    assert not selected.duplicated(
        ["transaction_id", "stage_id"]
    ).any()

    # Kaydedilen aşamalar geçerli referanslardan gelmeli
    expected = transactions[
        ["transaction_id", "operation_id"]
    ].merge(
        attributes[
            [
                "transaction_id",
                "requires_approval",
                "requires_manual_review"
            ]
        ],
        on="transaction_id",
        validate="one_to_one"
    ).merge(
        stages[
            [
                "operation_id",
                "stage_id",
                "stage_order",
                "is_mandatory"
            ]
        ],
        on="operation_id",
        validate="many_to_many"
    )

    def as_bool(value):
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in ("true", "1"):
            return True
        if str(value).strip().lower() in ("false", "0"):
            return False
        raise ValueError(f"Geçersiz değer: {value}")

    def should_select(row):
        if as_bool(row["is_mandatory"]):
            return True

        operation_id = int(row["operation_id"])
        stage_order = int(row["stage_order"])

        if operation_id == 1 and stage_order == 3:
            return (
                as_bool(row["requires_approval"])
                or as_bool(row["requires_manual_review"])
            )

        if operation_id == 3 and stage_order == 4:
            return as_bool(row["requires_approval"])

        if operation_id == 6 and stage_order == 4:
            return False

        raise ValueError(
            "Tanımlanmamış isteğe bağlı aşama"
        )

    expected["should_select"] = expected.apply(
        should_select,
        axis=1
    )

    expected_pairs = set(
        expected.loc[
            expected["should_select"],
            ["transaction_id", "stage_id"]
        ].itertuples(index=False, name=None)
    )

    actual_pairs = set(
        selected[
            ["transaction_id", "stage_id"]
        ].itertuples(index=False, name=None)
    )

    assert actual_pairs == expected_pairs, (
        "Kaydedilen aşamalar işlem özellikleriyle uyuşmuyor."
    )

    assert len(selected) == len(expected_pairs)
    assert selected["transaction_id"].nunique() == 300
