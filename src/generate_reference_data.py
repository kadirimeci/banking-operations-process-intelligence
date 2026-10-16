# Veriqora Bank
# Bankacılık Operasyonları ve Süreç Analitiği
# Referans veri üretimi

OPERATIONS = [
    {
        "operation_id": 1,
        "operation_code": "PAYMENT_TRANSFER",
        "operation_name": "Ödeme ve Transferler",
        "is_active": True
    },
    {
        "operation_id": 2,
        "operation_code": "CUSTOMER_UPDATE",
        "operation_name": "Müşteri Bilgi Güncellemeleri",
        "is_active": True
    },
    {
        "operation_id": 3,
        "operation_code": "ACCOUNT_OPERATIONS",
        "operation_name": "Hesap İşlemleri",
        "is_active": True
    },
    {
        "operation_id": 4,
        "operation_code": "CREDIT_OPERATIONS",
        "operation_name": "Kredi Operasyonları",
        "is_active": True
    },
    {
        "operation_id": 5,
        "operation_code": "LEGAL_FOLLOWUP",
        "operation_name": "Yasal Takip Operasyonları",
        "is_active": True
    },
    {
        "operation_id": 6,
        "operation_code": "OPERATIONAL_CONTROL",
        "operation_name": "Operasyonel Kontroller",
        "is_active": True
    }
]

print("Veriqora Bank - Operasyon Tanımları")
print("-" * 40)

for operation in OPERATIONS:
    print(
        f"{operation['operation_id']} - "
        f"{operation['operation_name']}"
    )

print(f"\nToplam operasyon sayısı: {len(OPERATIONS)}")

# -----------------------------------------------------------------------------

import pandas as pd
from pathlib import Path

# Projenin ana klasörünü bul
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Pilot verilerin kaydedileceği klasör
OUTPUT_DIR = PROJECT_ROOT / "data" / "pilot"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Operasyon listesini tabloya dönüştür
operations_df = pd.DataFrame(OPERATIONS)

# CSV dosyasını oluştur
output_file = OUTPUT_DIR / "operations.csv"

operations_df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("\noperations.csv başarıyla oluşturuldu!")
print(f"Kaydedilen kayıt sayısı: {len(operations_df)}")
print(f"Dosya konumu: {output_file}")

# -----------------------------------------------------------------------------

# Süreç aşamalarının tanımlanması
# Her operasyon için aşama sırası ve zorunluluk bilgisi

STAGE_DEFINITIONS = {
    1: [
        ("Talep", True),
        ("Doğrulama", True),
        ("Kontrol", False),
        ("İşleme alma", True),
        ("Kapanış", True),
    ],
    2: [
        ("Talep", True),
        ("Bilgi kontrolü", True),
        ("Güncelleme", True),
        ("Doğrulama", True),
        ("Tamamlama", True),
    ],
    3: [
        ("Talep", True),
        ("Kimlik/yetki kontrolü", True),
        ("Hesap işlemi", True),
        ("Onay", False),
        ("Tamamlama", True),
    ],
    4: [
        ("Talep", True),
        ("Belge kontrolü", True),
        ("Operasyonel inceleme", True),
        ("Onay", True),
        ("Tamamlama", True),
    ],
    5: [
        ("Dosya kaydı", True),
        ("Belge kontrolü", True),
        ("İnceleme", True),
        ("Dış koordinasyon", True),
        ("Kapanış", True),
    ],
    6: [
        ("Kontrol kaydı", True),
        ("İnceleme", True),
        ("Bulgu değerlendirme", True),
        ("Düzeltme", False),
        ("Kapanış", True),
    ],
}

stage_rows = []
stage_id = 1

for operation_id, stages in STAGE_DEFINITIONS.items():
    for stage_order, (stage_name, is_mandatory) in enumerate(stages, start=1):
        stage_rows.append({
            "stage_id": stage_id,
            "operation_id": operation_id,
            "stage_name": stage_name,
            "stage_order": stage_order,
            "is_mandatory": is_mandatory,
        })
        stage_id += 1

stages_df = pd.DataFrame(stage_rows)

stages_file = OUTPUT_DIR / "process_stages.csv"
stages_df.to_csv(stages_file, index=False, encoding="utf-8-sig")

print("\nprocess_stages.csv başarıyla oluşturuldu!")
print(f"Toplam aşama tanımı: {len(stages_df)}")

# -----------------------------------------------------------------------------
# Ekip tanımları
# Her ekibin birincil sorumlu olduğu operasyon bulunur.

TEAMS = [
    {
        "team_id": 1,
        "team_name": "Ödeme ve Transfer Operasyon Ekibi",
        "operation_id": 1,
        "is_active": True,
    },
    {
        "team_id": 2,
        "team_name": "Müşteri Bilgi Yönetimi Ekibi",
        "operation_id": 2,
        "is_active": True,
    },
    {
        "team_id": 3,
        "team_name": "Hesap Operasyonları Ekibi",
        "operation_id": 3,
        "is_active": True,
    },
    {
        "team_id": 4,
        "team_name": "Kredi Operasyonları Ekibi",
        "operation_id": 4,
        "is_active": True,
    },
    {
        "team_id": 5,
        "team_name": "Yasal Takip Operasyon Ekibi",
        "operation_id": 5,
        "is_active": True,
    },
    {
        "team_id": 6,
        "team_name": "Operasyonel Kontrol Ekibi",
        "operation_id": 6,
        "is_active": True,
    },
]

# Ekip listesini tabloya dönüştür
teams_df = pd.DataFrame(TEAMS)

# CSV olarak kaydet
teams_file = OUTPUT_DIR / "teams.csv"

teams_df.to_csv(
    teams_file,
    index=False,
    encoding="utf-8-sig"
)

print("\nteams.csv başarıyla oluşturuldu!")
print(f"Toplam ekip sayısı: {len(teams_df)}")


# SLA hedef tanımları
# Süreler iş dakikası cinsindendir.

SLA_DEFINITIONS = {
    1: {"LOW": 60, "MEDIUM": 120, "HIGH": 240},
    2: {"LOW": 60, "MEDIUM": 180, "HIGH": 360},
    3: {"LOW": 120, "MEDIUM": 240, "HIGH": 480},
    4: {"LOW": 240, "MEDIUM": 480, "HIGH": 960},
    5: {"LOW": 480, "MEDIUM": 960, "HIGH": 1920},
    6: {"LOW": 120, "MEDIUM": 360, "HIGH": 720},
}

sla_rows = []
sla_target_id = 1

for operation_id, complexity_targets in SLA_DEFINITIONS.items():
    for complexity_level, target_minutes in complexity_targets.items():
        sla_rows.append({
            "sla_target_id": sla_target_id,
            "operation_id": operation_id,
            "complexity_level": complexity_level,
            "target_minutes": target_minutes,
            "valid_from": "2025-01-01",
            "valid_to": None,
        })
        sla_target_id += 1

sla_df = pd.DataFrame(sla_rows)

sla_file = OUTPUT_DIR / "sla_targets.csv"

sla_df.to_csv(
    sla_file,
    index=False,
    encoding="utf-8-sig"
)

print("\nsla_targets.csv başarıyla oluşturuldu!")
print(f"Toplam SLA hedefi: {len(sla_df)}")

# -----------------------------------------------------------------------------
