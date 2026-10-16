
from pathlib import Path

import numpy as np
import pandas as pd

# Veriqora Bank - Süreç Simülasyonu
# Pilot: 300 sentetik işlem
# Çalışma modeli: Kontrollü fazla mesai

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pilot"

RANDOM_SEED = 2025
rng = np.random.default_rng(RANDOM_SEED)

REPORT_CUTOFF = pd.Timestamp("2025-12-31 18:00:00")

# Referans ve işlem tablolarını yükle
transactions_df = pd.read_csv(
    DATA_DIR / "transactions.csv"
)

attributes_df = pd.read_csv(
    DATA_DIR / "transaction_attributes.csv"
)

stages_df = pd.read_csv(
    DATA_DIR / "process_stages.csv"
)

teams_df = pd.read_csv(
    DATA_DIR / "teams.csv"
)

capacity_df = pd.read_csv(
    DATA_DIR / "team_capacity.csv"
)

calendar_df = pd.read_csv(
    DATA_DIR / "business_calendar.csv"
)

cost_df = pd.read_csv(
    DATA_DIR / "cost_parameters.csv"
)

# Tarih alanlarını dönüştür
transactions_df["opened_at"] = pd.to_datetime(
    transactions_df["opened_at"]
)

capacity_df["capacity_date"] = pd.to_datetime(
    capacity_df["capacity_date"]
)

calendar_df["calendar_date"] = pd.to_datetime(
    calendar_df["calendar_date"]
)

# Temel bütünlük kontrolleri
assert len(transactions_df) == 300, (
    "Pilot işlem sayısı 300 olmalı."
)

assert transactions_df["transaction_id"].is_unique, (
    "Tekrarlanan işlem kimliği bulundu."
)

assert set(transactions_df["transaction_id"]) == set(
    attributes_df["transaction_id"]
), "İşlem ve özellik kayıtları eşleşmiyor."

assert not transactions_df["opened_at"].isna().any(), (
    "Açılış zamanı boş işlem bulundu."
)

print("Veriqora Bank - Süreç Simülasyonu")
print("-" * 40)
print(f"Pilot işlem sayısı: {len(transactions_df)}")
print(f"Tanımlı aşama sayısı: {len(stages_df)}")
print(f"Ekip sayısı: {len(teams_df)}")
print(f"Kapasite kaydı: {len(capacity_df)}")
print(f"Takvim günü: {len(calendar_df)}")
print(f"Maliyet parametresi: {len(cost_df)}")
print("Çalışma modeli: Kontrollü fazla mesai")
print("Simülasyon veri hazırlığı tamamlandı.")



# İşlemleri sorumlu operasyon ekipleriyle eşleştir

team_assignment_df = transactions_df[
    ["transaction_id", "operation_id", "opened_at"]
].merge(
    teams_df[["team_id", "operation_id"]],
    on="operation_id",
    how="left",
    validate="many_to_one"
)

# Her işlemin bir sorumlu ekibi olmalı
assert team_assignment_df["team_id"].notna().all(), (
    "Sorumlu ekibi bulunamayan işlem var."
)

# Her işlem yalnızca bir kez eşleştirilmeli
assert len(team_assignment_df) == len(transactions_df), (
    "Ekip eşleştirmesi sırasında işlem sayısı değişti."
)

print("\nİşlem - Ekip Eşleştirmesi")
print("-" * 40)

print(
    team_assignment_df.groupby("team_id")
    .size()
    .to_string()
)

print(
    f"\nEşleştirilen toplam işlem: "
    f"{len(team_assignment_df)}"
)



# Operasyonlara ait süreç aşamalarını hazırlama

stages_sorted_df = stages_df.sort_values(
    ["operation_id", "stage_order"]
).copy()

# Aşama kimlikleri benzersiz olmalı
assert stages_sorted_df["stage_id"].is_unique, (
    "Tekrarlanan aşama kimliği bulundu."
)

# Aynı operasyonda aynı sıra numarası bulunmamalı
assert not stages_sorted_df.duplicated(
    ["operation_id", "stage_order"]
).any(), (
    "Aynı operasyonda tekrarlanan aşama sırası bulundu."
)

# İşlemleri ait oldukları operasyonun aşamalarıyla eşleştir
transaction_stages_df = team_assignment_df.merge(
    stages_sorted_df[
        [
            "stage_id",
            "operation_id",
            "stage_name",
            "stage_order",
            "is_mandatory"
        ]
    ],
    on="operation_id",
    how="left",
    validate="many_to_many"
)

# Her işlem için aşama tanımı bulunmalı
assert transaction_stages_df["stage_id"].notna().all(), (
    "Aşama tanımı bulunamayan işlem var."
)

transaction_stages_df = transaction_stages_df.sort_values(
    ["transaction_id", "stage_order"]
).reset_index(drop=True)

print("\nİşlem - Süreç Aşaması Eşleştirmesi")
print("-" * 40)

print(
    transaction_stages_df.groupby("operation_id")
    .agg(
        islem_sayisi=("transaction_id", "nunique"),
        asama_kaydi=("stage_id", "count")
    )
    .to_string()
)

print(
    "\nToplam işlem-aşama eşleşmesi:",
    len(transaction_stages_df)
)



# İsteğe bağlı süreç aşamalarını belirleme

# İşlem özelliklerini aşama eşleşmelerine ekle
stage_decisions_df = transaction_stages_df.merge(
    attributes_df[
        [
            "transaction_id",
            "requires_approval",
            "requires_manual_review"
        ]
    ],
    on="transaction_id",
    how="left",
    validate="many_to_one"
)

# Özellik alanları eksik olmamalı
assert stage_decisions_df[
    ["requires_approval", "requires_manual_review"]
].notna().all().all(), (
    "İşlem özelliklerinde eksik değer bulundu."
)

# CSV dosyasından gelen değerleri güvenli şekilde yorumla
def to_bool(value):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    if str(value).strip().lower() in ("true", "1"):
        return True

    if str(value).strip().lower() in ("false", "0"):
        return False

    raise ValueError(f"Geçersiz boolean değer: {value}")


def should_include_stage(row):
    mandatory = to_bool(row["is_mandatory"])

    if mandatory:
        return True

    operation_id = int(row["operation_id"])
    stage_order = int(row["stage_order"])

    requires_approval = to_bool(row["requires_approval"])
    requires_manual_review = to_bool(
        row["requires_manual_review"]
    )

    # Ödeme ve Transferler - Kontrol
    if operation_id == 1 and stage_order == 3:
        return requires_approval or requires_manual_review

    # Hesap İşlemleri - Onay
    if operation_id == 3 and stage_order == 4:
        return requires_approval

    # Operasyonel Kontroller - Düzeltme
    # Kalite olayları oluşturulduktan sonra belirlenecek
    if operation_id == 6 and stage_order == 4:
        return False

    raise ValueError(
        f"Tanımlanmamış isteğe bağlı aşama: "
        f"operation_id={operation_id}, "
        f"stage_order={stage_order}"
    )


stage_decisions_df["include_stage"] = (
    stage_decisions_df.apply(
        should_include_stage,
        axis=1
    )
)

# Başlangıçta seçilen aşamaları al
selected_stages_df = stage_decisions_df[
    stage_decisions_df["include_stage"]
].copy()

print("\nSüreç Aşaması Seçim Sonuçları")
print("-" * 40)

print("Toplam tanımlı eşleşme:", len(stage_decisions_df))
print("Başlangıçta seçilen aşama:", len(selected_stages_df))
print(
    "Seçilmeyen isteğe bağlı aşama:",
    len(stage_decisions_df) - len(selected_stages_df)
)

print("\nOperasyon bazında seçilen aşamalar:")
print(
    selected_stages_df.groupby("operation_id")
    .size()
    .to_string()
)

# Hiçbir işlem aşamasız kalmamalı
assert (
    selected_stages_df["transaction_id"].nunique()
    == len(transactions_df)
), "Aşaması bulunmayan işlem var."



# Seçilen süreç aşamalarını pilot çıktı olarak kaydet

selected_stages_output = selected_stages_df[
    [
        "transaction_id",
        "operation_id",
        "team_id",
        "stage_id",
        "stage_name",
        "stage_order",
        "is_mandatory"
    ]
].copy()

selected_stages_output = selected_stages_output.sort_values(
    ["transaction_id", "stage_order"]
)

output_path = DATA_DIR / "selected_stages.csv"

selected_stages_output.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("\nSeçilen süreç aşamaları kaydedildi!")
print(f"Dosya: {output_path}")
print(f"Toplam kayıt: {len(selected_stages_output)}")



# Ekip bazında günlük kapasite hazırlığı

daily_capacity_df = capacity_df.merge(
    calendar_df[
        [
            "calendar_date",
            "day_type",
            "is_business_day",
        ]
    ],
    left_on="capacity_date",
    right_on="calendar_date",
    how="left",
    validate="many_to_one"
)

assert daily_capacity_df["day_type"].notna().all(), (
    "Kapasite kaydı için iş takvimi bulunamadı."
)

# Kapasite değerleri negatif olamaz
capacity_columns = [
    "employee_count",
    "available_minutes",
    "overtime_capacity_minutes",
]

assert daily_capacity_df[capacity_columns].ge(0).all().all(), (
    "Negatif kapasite değeri bulundu."
)

# Çalışılmayan günlerde normal kapasite sıfır olmalı
non_working = daily_capacity_df[
    daily_capacity_df["day_type"].isin(
        ["HOLIDAY", "WEEKEND"]
    )
]

assert (non_working["available_minutes"] == 0).all(), (
    "Çalışılmayan günde normal kapasite bulundu."
)

# Planlanan toplam kapasite
daily_capacity_df["planned_total_minutes"] = (
    daily_capacity_df["available_minutes"]
    + daily_capacity_df["overtime_capacity_minutes"]
)

print("\nGünlük Kapasite Hazırlığı")
print("-" * 40)

print(
    "Toplam ekip-gün kaydı:",
    len(daily_capacity_df)
)

print(
    "Normal kapasite (dakika):",
    daily_capacity_df["available_minutes"].sum()
)

print(
    "Planlanan fazla mesai (dakika):",
    daily_capacity_df["overtime_capacity_minutes"].sum()
)

print(
    "Toplam planlanan kapasite (dakika):",
    daily_capacity_df["planned_total_minutes"].sum()
)



# Ekiplerin günlük kapasitesine hızlı erişim

team_daily_capacity = {}

for row in daily_capacity_df.itertuples(index=False):

    key = (
        int(row.team_id),
        pd.Timestamp(row.capacity_date).date()
    )

    team_daily_capacity[key] = {
        "employee_count": int(row.employee_count),
        "normal_capacity_minutes": int(row.available_minutes),
        "overtime_capacity_minutes": int(
            row.overtime_capacity_minutes
        ),
        "day_type": row.day_type,
    }


def get_team_capacity(team_id, current_time):
    """
    Belirli bir ekip ve tarih için
    günlük kapasite bilgilerini döndürür.
    """

    current_date = pd.Timestamp(current_time).date()

    key = (int(team_id), current_date)

    return team_daily_capacity.get(key)


# Örnek kapasite sorgusu
sample_capacity = get_team_capacity(
    team_id=1,
    current_time="2025-01-02 10:00:00"
)

print("\nEkip Kapasitesi Sorgusu")
print("-" * 40)
print("Ekip: 1")
print("Tarih: 2025-01-02")
print(sample_capacity)



# İş takvimine göre normal çalışma pencereleri

calendar_lookup = {
    pd.Timestamp(row.calendar_date).date(): row.day_type
    for row in calendar_df.itertuples(index=False)
}


def get_normal_work_windows(current_date):
    """
    Verilen tarih için normal mesai aralıklarını döndürür.
    Başlangıç dahil, bitiş hariçtir.
    """

    day = pd.Timestamp(current_date).normalize()
    day_type = calendar_lookup.get(day.date())

    if day_type is None:
        raise ValueError(
            f"İş takviminde tarih bulunamadı: {day.date()}"
        )

    if day_type in ("HOLIDAY", "WEEKEND"):
        return []

    morning = (
        day + pd.Timedelta(hours=9),
        day + pd.Timedelta(hours=12)
    )

    if day_type == "HALF_DAY":
        return [morning]

    if day_type == "FULL_DAY":
        afternoon = (
            day + pd.Timedelta(hours=13),
            day + pd.Timedelta(hours=18)
        )
        return [morning, afternoon]

    raise ValueError(f"Bilinmeyen gün türü: {day_type}")


print("\nNormal Çalışma Pencereleri")
print("-" * 40)

for sample_date in [
    "2025-01-01",
    "2025-01-02",
    "2025-06-05",
]:
    windows = get_normal_work_windows(sample_date)

    formatted = [
        (
            start.strftime("%H:%M"),
            end.strftime("%H:%M")
        )
        for start, end in windows
    ]

    print(f"{sample_date}: {formatted}")



# Kontrollü fazla mesai zaman pencereleri

def get_overtime_work_windows(team_id, current_date):
    """
    Ekip ve tarih için planlı fazla mesai
    uygulanabilecek zaman pencerelerini döndürür.

    Bu fonksiyon kapasite tüketmez.
    """

    day = pd.Timestamp(current_date).normalize()

    capacity = get_team_capacity(team_id, day)

    if capacity is None:
        raise ValueError(
            f"Kapasite kaydı bulunamadı: "
            f"team_id={team_id}, date={day.date()}"
        )

    overtime_minutes = capacity[
        "overtime_capacity_minutes"
    ]

    if overtime_minutes <= 0:
        return []

    day_type = capacity["day_type"]

    if day_type == "FULL_DAY":
        return [
            (
                day + pd.Timedelta(hours=18),
                day + pd.Timedelta(hours=21)
            )
        ]

    if day_type == "HALF_DAY":
        return [
            (
                day + pd.Timedelta(hours=12),
                day + pd.Timedelta(hours=15)
            )
        ]

    # Tatil ve hafta sonu için şimdilik fazla mesai yok
    return []


print("\nFazla Mesai Penceresi Kontrolü")
print("-" * 40)

overtime_days = daily_capacity_df[
    (daily_capacity_df["team_id"] == 1)
    & (daily_capacity_df["overtime_capacity_minutes"] > 0)
].sort_values("capacity_date")

sample_overtime_day = overtime_days.iloc[0]

sample_team_id = int(sample_overtime_day["team_id"])
sample_date = sample_overtime_day["capacity_date"]

windows = get_overtime_work_windows(
    sample_team_id,
    sample_date
)

print("Ekip:", sample_team_id)
print("Tarih:", sample_date.date())
print(
    "Planlanan fazla mesai (dakika):",
    int(sample_overtime_day["overtime_capacity_minutes"])
)

print(
    "Fazla mesai pencereleri:",
    [
        (
            start.strftime("%H:%M"),
            end.strftime("%H:%M")
        )
        for start, end in windows
    ]
)


# Fazla mesai kapasitesi ve pencere tutarlılığı

overtime_records = daily_capacity_df[
    daily_capacity_df["overtime_capacity_minutes"] > 0
]

invalid_overtime_records = []

for row in overtime_records.itertuples(index=False):

    windows = get_overtime_work_windows(
        row.team_id,
        row.capacity_date
    )

    if not windows:
        invalid_overtime_records.append(
            (row.team_id, row.capacity_date)
        )
        continue

    window_minutes = sum(
        (end - start).total_seconds() / 60
        for start, end in windows
    )

    # Pencere süresi tek çalışan için geçerlidir.
    # Toplam kapasite, çalışan sayısıyla sınırlıdır.
    maximum_possible_minutes = (
        window_minutes * row.employee_count
    )

    if row.overtime_capacity_minutes > maximum_possible_minutes:
        invalid_overtime_records.append(
            (row.team_id, row.capacity_date)
        )

assert not invalid_overtime_records, (
    "Fazla mesai kapasitesi pencere sınırlarıyla "
    f"uyuşmuyor: {invalid_overtime_records[:5]}"
)

print("\nFazla Mesai Kapasite Kontrolü")
print("-" * 40)
print(
    "Kontrol edilen fazla mesai kaydı:",
    len(overtime_records)
)
print(
    "Geçersiz kapasite kaydı:",
    len(invalid_overtime_records)
)
print("Fazla mesai kapasite kontrolü başarılı.")



# Sanal çalışan müsaitliği takibi

# Anahtar: (team_id, tarih)
# Değer: Her çalışanın en erken müsait olduğu zaman
employee_availability = {}


def initialize_team_employees(team_id, current_date):
    """
    Ekipteki sanal çalışanların müsaitlik
    kayıtlarını ilgili gün için hazırlar.
    """

    day = pd.Timestamp(current_date).normalize()
    key = (int(team_id), day.date())

    if key not in employee_availability:

        capacity = get_team_capacity(team_id, day)

        if capacity is None:
            raise ValueError(
                f"Kapasite bulunamadı: {key}"
            )

        employee_count = capacity["employee_count"]

        employee_availability[key] = {
            employee_id: day
            for employee_id in range(1, employee_count + 1)
        }

    return employee_availability[key]


def get_available_employee(team_id, current_time):
    """
    Belirtilen anda müsait bir sanal çalışan
    varsa numarasını döndürür.

    Yoksa None döndürür.
    """

    current_time = pd.Timestamp(current_time)

    employees = initialize_team_employees(
        team_id,
        current_time
    )

    for employee_id, available_at in employees.items():

        if available_at <= current_time:
            return employee_id

    return None


def reserve_employee(
    team_id,
    employee_id,
    start_time,
    end_time
):
    """
    Çalışanı belirtilen zaman aralığında
    meşgul olarak işaretler.
    """

    start_time = pd.Timestamp(start_time)
    end_time = pd.Timestamp(end_time)

    if end_time <= start_time:
        raise ValueError(
            "Çalışma bitişi başlangıçtan sonra olmalı."
        )

    if start_time.date() != end_time.date():
        raise ValueError(
            "Bu aşamada çalışma aynı gün içinde bitmeli."
        )

    employees = initialize_team_employees(
        team_id,
        start_time
    )

    if employee_id not in employees:
        raise ValueError(
            "Ekipte bulunmayan çalışan numarası."
        )

    if employees[employee_id] > start_time:
        raise ValueError(
            "Çalışan bu zaman aralığında müsait değil."
        )

    employees[employee_id] = end_time


# Örnek: 2 Ocak tarihinde birinci ekibin
# ilk çalışanına 30 dakikalık iş ata

sample_start = pd.Timestamp("2025-01-02 10:00:00")
sample_end = pd.Timestamp("2025-01-02 10:30:00")

employee_id = get_available_employee(
    team_id=1,
    current_time=sample_start
)

assert employee_id is not None

reserve_employee(
    team_id=1,
    employee_id=employee_id,
    start_time=sample_start,
    end_time=sample_end
)

print("\nÇalışan Müsaitliği Kontrolü")
print("-" * 40)
print("Ekip:", 1)
print("Atanan sanal çalışan:", employee_id)
print("Başlangıç:", sample_start)
print("Bitiş:", sample_end)
print(
    "Aynı çalışanın 10.15'te müsaitlik durumu:",
    employee_availability[
        (1, sample_start.date())
    ][employee_id] <= pd.Timestamp(
        "2025-01-02 10:15:00"
    )
)


# Çalışma saatlerine uygun güvenli rezervasyon

def reserve_employee_in_work_window(
    team_id,
    employee_id,
    start_time,
    end_time
):
    """
    Çalışmanın izin verilen bir mesai penceresinde
    gerçekleştiğini kontrol eder.

    Bu aşamada günlük kapasite tüketimi henüz
    uygulanmaz.
    """

    start_time = pd.Timestamp(start_time)
    end_time = pd.Timestamp(end_time)

    if end_time <= start_time:
        raise ValueError(
            "Çalışma bitişi başlangıçtan sonra olmalı."
        )

    if start_time.date() != end_time.date():
        raise ValueError(
            "Çalışma tek takvim günü içinde olmalı."
        )

    normal_windows = get_normal_work_windows(
        start_time
    )

    overtime_windows = get_overtime_work_windows(
        team_id,
        start_time
    )

    allowed_windows = (
        normal_windows + overtime_windows
    )

    valid_window = any(
        start_time >= window_start
        and end_time <= window_end
        for window_start, window_end in allowed_windows
    )

    if not valid_window:
        raise ValueError(
            "Çalışma izin verilen mesai saatleri dışında."
        )

    reserve_employee(
        team_id=team_id,
        employee_id=employee_id,
        start_time=start_time,
        end_time=end_time
    )


# Yeni gün üzerinde örnek kontrol
test_day = "2025-01-03"

test_employee = get_available_employee(
    team_id=1,
    current_time=f"{test_day} 10:00:00"
)

reserve_employee_in_work_window(
    team_id=1,
    employee_id=test_employee,
    start_time=f"{test_day} 10:00:00",
    end_time=f"{test_day} 10:30:00"
)

print("\nMesai Saatine Uygun Rezervasyon")
print("-" * 40)
print("10.00–10.30 çalışma rezervasyonu başarılı.")

# Öğle arasında çalışma engellenmeli
try:
    reserve_employee_in_work_window(
        team_id=1,
        employee_id=test_employee,
        start_time=f"{test_day} 12:15:00",
        end_time=f"{test_day} 12:45:00"
    )
except ValueError:
    print("12.15–12.45 öğle arası rezervasyonu engellendi.")
else:
    raise AssertionError(
        "Öğle arasında çalışma yanlışlıkla kabul edildi."
    )



# Günlük çalışma kapasitesi tüketim takibi

capacity_usage = {}


def get_capacity_usage(team_id, current_date):
    day = pd.Timestamp(current_date).date()
    key = (int(team_id), day)

    if key not in capacity_usage:
        capacity_usage[key] = {
            "normal_used_minutes": 0,
            "overtime_used_minutes": 0,
        }

    return capacity_usage[key]


def reserve_with_capacity(
    team_id,
    employee_id,
    start_time,
    end_time
):
    """
    Çalışma penceresini, çalışan müsaitliğini
    ve günlük toplam kapasiteyi kontrol ederek
    rezervasyon oluşturur.
    """

    start_time = pd.Timestamp(start_time)
    end_time = pd.Timestamp(end_time)

    if end_time <= start_time:
        raise ValueError("Geçersiz çalışma süresi.")

    if start_time.date() != end_time.date():
        raise ValueError("Çalışma aynı gün içinde bitmeli.")

    capacity = get_team_capacity(team_id, start_time)

    if capacity is None:
        raise ValueError("Günlük kapasite bulunamadı.")

    normal_windows = get_normal_work_windows(start_time)
    overtime_windows = get_overtime_work_windows(
        team_id, start_time
    )

    def fits(windows):
        return any(
            start_time >= window_start
            and end_time <= window_end
            for window_start, window_end in windows
        )

    if fits(normal_windows):
        usage_key = "normal_used_minutes"
        limit = capacity["normal_capacity_minutes"]

    elif fits(overtime_windows):
        usage_key = "overtime_used_minutes"
        limit = capacity["overtime_capacity_minutes"]

    else:
        raise ValueError(
            "Çalışma geçerli bir mesai penceresinde değil."
        )

    duration = int(
        (end_time - start_time).total_seconds() / 60
    )

    if duration <= 0:
        raise ValueError(
            "Çalışma süresi en az bir tam dakika olmalı."
        )

    usage = get_capacity_usage(team_id, start_time)

    if usage[usage_key] + duration > limit:
        raise ValueError(
            "Planlanan günlük kapasite aşılıyor."
        )

    # Önce çalışan rezervasyonu doğrulanır.
    # Başarısızsa kapasite tüketilmez.
    reserve_employee_in_work_window(
        team_id,
        employee_id,
        start_time,
        end_time
    )

    usage[usage_key] += duration


# Örnek: 9 Ocak 2025, ekip 1
# 240 dakika planlı fazla mesai kapasitesi

sample_day = "2025-01-09"

employee = get_available_employee(
    1, f"{sample_day} 18:00:00"
)

reserve_with_capacity(
    1,
    employee,
    f"{sample_day} 18:00:00",
    f"{sample_day} 19:00:00"
)

usage = get_capacity_usage(1, sample_day)

print("\nGünlük Kapasite Tüketimi")
print("-" * 40)
print("Ekip: 1")
print("Tarih:", sample_day)
print("Kullanılan fazla mesai:", usage["overtime_used_minutes"])
print(
    "Kalan fazla mesai:",
    get_team_capacity(1, sample_day)[
        "overtime_capacity_minutes"
    ] - usage["overtime_used_minutes"]
)


# En erken müsait çalışanı bulma

def get_earliest_available_employee(team_id, current_time):
    """
    Bir ekipte en erken müsait olacak çalışanı
    ve müsaitlik zamanını döndürür.

    Henüz mesai penceresi veya kapasite
    uygunluğu değerlendirilmez.
    """

    current_time = pd.Timestamp(current_time)

    employees = initialize_team_employees(
        team_id,
        current_time
    )

    if not employees:
        return None, None

    employee_id = min(
        employees,
        key=lambda emp_id: employees[emp_id]
    )

    available_at = max(
        current_time,
        employees[employee_id]
    )

    return employee_id, available_at


# Bağımsız bir test günü kullanalım
test_date = "2025-01-06"

# Ekip 1'deki tüm çalışanları aynı anda meşgul et
employees = initialize_team_employees(
    1,
    test_date
)

for employee_id in employees:
    reserve_with_capacity(
        team_id=1,
        employee_id=employee_id,
        start_time=f"{test_date} 10:00:00",
        end_time=f"{test_date} 10:30:00"
    )

# Saat 10.15'te yeni işlem geliyor
arrival_time = pd.Timestamp(
    f"{test_date} 10:15:00"
)

next_employee, available_at = (
    get_earliest_available_employee(
        team_id=1,
        current_time=arrival_time
    )
)

waiting_minutes = int(
    (available_at - arrival_time).total_seconds() / 60
)

print("\nEkip Kuyruğu İlk Kontrol")
print("-" * 40)
print("İşlem geliş zamanı:", arrival_time)
print("Atanabilecek çalışan:", next_employee)
print("En erken müsaitlik:", available_at)
print("Bekleme süresi (dakika):", waiting_minutes)

assert waiting_minutes == 15, (
    "Beklenen kuyruk süresi 15 dakika olmalı."
)


# Normal mesai pencerelerine göre işi parçalara ayırma

def split_work_across_normal_windows(start_time, work_minutes):
    """
    İşin ihtiyaç duyduğu aktif çalışma süresini
    normal mesai pencerelerine dağıtır.

    Çalışan ve günlük ekip kapasitesi bu fonksiyonda
    henüz değerlendirilmez.
    """

    current_time = pd.Timestamp(start_time)
    remaining_minutes = int(work_minutes)

    if remaining_minutes <= 0:
        raise ValueError(
            "Aktif çalışma süresi pozitif olmalı."
        )

    work_intervals = []

    while remaining_minutes > 0:

        windows = get_normal_work_windows(current_time)

        for window_start, window_end in windows:

            actual_start = max(current_time, window_start)

            if actual_start >= window_end:
                continue

            available_minutes = int(
                (window_end - actual_start).total_seconds() / 60
            )

            used_minutes = min(
                remaining_minutes,
                available_minutes
            )

            actual_end = actual_start + pd.Timedelta(
                minutes=used_minutes
            )

            work_intervals.append(
                (actual_start, actual_end)
            )

            remaining_minutes -= used_minutes
            current_time = actual_end

            if remaining_minutes == 0:
                break

        if remaining_minutes > 0:
            current_time = (
                current_time.normalize()
                + pd.Timedelta(days=1)
            )

    return work_intervals


# Öğle arası senaryosu

sample_intervals = split_work_across_normal_windows(
    "2025-01-07 11:50:00",
    30
)

print("\nÖğle Arası İş Bölme Kontrolü")
print("-" * 40)

for start, end in sample_intervals:
    print(
        start.strftime("%Y-%m-%d %H:%M"),
        "->",
        end.strftime("%Y-%m-%d %H:%M")
    )

total_active_minutes = sum(
    int((end - start).total_seconds() / 60)
    for start, end in sample_intervals
)

print("Toplam aktif çalışma:", total_active_minutes)

assert total_active_minutes == 30
assert len(sample_intervals) == 2



# Bölünmüş çalışma aralıklarını kapasiteye bağlama


def reserve_split_work(team_id, employee_id, intervals):
    """
    Bölünmüş çalışma aralıklarını atomik olarak
    rezerve eder.

    Bir aralık başarısız olursa çalışan müsaitliği
    ve kapasite tüketimi eski durumuna döner.
    """

    import copy

    if not intervals:
        raise ValueError("Çalışma aralığı bulunamadı.")

    # Rezervasyon öncesindeki tüm durumu sakla
    availability_backup = copy.deepcopy(
        employee_availability
    )

    usage_backup = copy.deepcopy(
        capacity_usage
    )

    try:
        for start_time, end_time in intervals:
            reserve_with_capacity(
                team_id=team_id,
                employee_id=employee_id,
                start_time=start_time,
                end_time=end_time
            )

    except Exception:
        # Herhangi bir hata oluşursa eski duruma dön
        employee_availability.clear()
        employee_availability.update(
            availability_backup
        )

        capacity_usage.clear()
        capacity_usage.update(
            usage_backup
        )

        raise



# Önceki testlerden bağımsız bir tarih seçiyoruz.
test_intervals = split_work_across_normal_windows(
    "2025-01-08 11:50:00",
    30
)

test_employee = get_available_employee(
    team_id=1,
    current_time=test_intervals[0][0]
)

assert test_employee is not None

reserve_split_work(
    team_id=1,
    employee_id=test_employee,
    intervals=test_intervals
)

test_usage = get_capacity_usage(
    team_id=1,
    current_date="2025-01-08"
)

print("\nBölünmüş İş Kapasite Rezervasyonu")
print("-" * 40)
print("Ekip:", 1)
print("Sanal çalışan:", test_employee)
print("Çalışma aralığı sayısı:", len(test_intervals))
print(
    "Kullanılan normal kapasite:",
    test_usage["normal_used_minutes"]
)

assert len(test_intervals) == 2
assert test_usage["normal_used_minutes"] == 30



# Atomik rezervasyon geri alma testi

rollback_day = "2025-01-10"

rollback_employee = get_available_employee(
    team_id=1,
    current_time=f"{rollback_day} 11:50:00"
)

assert rollback_employee is not None

# İlk aralık geçerli, ikinci aralık öğle arasında
# olduğu için reddedilmeli.
invalid_intervals = [
    (
        pd.Timestamp(f"{rollback_day} 11:50:00"),
        pd.Timestamp(f"{rollback_day} 12:00:00")
    ),
    (
        pd.Timestamp(f"{rollback_day} 12:15:00"),
        pd.Timestamp(f"{rollback_day} 12:35:00")
    )
]

usage_before = get_capacity_usage(
    1, rollback_day
)["normal_used_minutes"]

availability_before = (
    initialize_team_employees(1, rollback_day)[
        rollback_employee
    ]
)

try:
    reserve_split_work(
        team_id=1,
        employee_id=rollback_employee,
        intervals=invalid_intervals
    )
except ValueError:
    print("\nAtomik Rezervasyon Kontrolü")
    print("-" * 40)
    print("Geçersiz ikinci aralık reddedildi.")
else:
    raise AssertionError(
        "Geçersiz rezervasyon kabul edildi."
    )

usage_after = get_capacity_usage(
    1, rollback_day
)["normal_used_minutes"]

availability_after = (
    initialize_team_employees(1, rollback_day)[
        rollback_employee
    ]
)

assert usage_before == usage_after
assert availability_before == availability_after

print("Kapasite tüketimi geri alındı.")
print("Çalışan müsaitliği geri alındı.")
print("Atomik rezervasyon testi başarılı.")



# Bir sonraki normal mesai başlangıcını bulma

def find_next_normal_work_time(current_time):
    """
    Verilen zamandan itibaren çalışılabilecek
    ilk normal mesai zamanını döndürür.

    Çalışan müsaitliği ve ekip kapasitesi
    bu fonksiyonda henüz değerlendirilmez.
    """

    current_time = pd.Timestamp(current_time)

    # İş takvimimiz 2025-2026 dönemini kapsıyor.
    # Takvim dışına çıkarsak sessizce devam etmiyoruz.
    for _ in range(730):

        windows = get_normal_work_windows(current_time)

        for window_start, window_end in windows:

            possible_start = max(
                current_time,
                window_start
            )

            if possible_start < window_end:
                return possible_start

        current_time = (
            current_time.normalize()
            + pd.Timedelta(days=1)
        )

    raise ValueError(
        "İş takvimi içerisinde uygun çalışma zamanı bulunamadı."
    )


# Üç farklı senaryoyu kontrol edelim

sample_times = [
    "2025-01-07 12:15:00",
    "2025-01-07 18:30:00",
    "2025-01-04 10:00:00",
]

print("\nSonraki Normal Mesai Kontrolü")
print("-" * 40)

for arrival in sample_times:

    next_work_time = find_next_normal_work_time(
        arrival
    )

    print(
        arrival,
        "->",
        next_work_time
    )


assert find_next_normal_work_time(
    "2025-01-07 12:15:00"
) == pd.Timestamp("2025-01-07 13:00:00")

assert find_next_normal_work_time(
    "2025-01-07 18:30:00"
) == pd.Timestamp("2025-01-08 09:00:00")

assert find_next_normal_work_time(
    "2025-01-04 10:00:00"
) == pd.Timestamp("2025-01-06 09:00:00")



# Normal mesai ve çalışan müsaitliğini birleştirme

def find_next_employee_work_time(team_id, arrival_time):
    """
    Normal mesai içinde en erken müsait çalışanı
    ve uygun başlangıç zamanını döndürür.

    Günlük kapasite tüketimi ve işin tamamını
    gerçekleştirecek süre henüz değerlendirilmez.
    """

    candidate_time = pd.Timestamp(arrival_time)

    for _ in range(730):

        candidate_time = find_next_normal_work_time(
            candidate_time
        )

        employees = initialize_team_employees(
            team_id,
            candidate_time
        )

        if not employees:
            candidate_time = (
                candidate_time.normalize()
                + pd.Timedelta(days=1)
            )
            continue

        # O anda veya sonrasında en erken müsait çalışan
        employee_id, available_at = (
            get_earliest_available_employee(
                team_id,
                candidate_time
            )
        )

        # Çalışanın müsait olacağı zamanı da
        # mesai takvimine göre düzelt
        next_work_time = find_next_normal_work_time(
            available_at
        )

        if next_work_time.date() == candidate_time.date():
            return employee_id, next_work_time

        candidate_time = next_work_time

    raise ValueError(
        "Uygun çalışan ve çalışma zamanı bulunamadı."
    )


# Önceki örneklerden bağımsız bir gün kullanalım
queue_test_day = "2025-01-13"

# Ekip 1'deki tüm çalışanları 10.00-10.30
# arasında meşgul edelim
queue_test_employees = initialize_team_employees(
    1,
    queue_test_day
)

for employee_id in queue_test_employees:
    reserve_with_capacity(
        team_id=1,
        employee_id=employee_id,
        start_time=f"{queue_test_day} 10:00:00",
        end_time=f"{queue_test_day} 10:30:00"
    )

# Yeni işlem 10.15'te geliyor
queue_arrival = pd.Timestamp(
    f"{queue_test_day} 10:15:00"
)

next_employee, next_start = (
    find_next_employee_work_time(
        team_id=1,
        arrival_time=queue_arrival
    )
)

queue_wait_minutes = int(
    (next_start - queue_arrival).total_seconds() / 60
)

print("\nMesai ve Çalışan Müsaitliği Kontrolü")
print("-" * 40)
print("İşlem geliş zamanı:", queue_arrival)
print("Atanabilecek çalışan:", next_employee)
print("Uygun başlangıç:", next_start)
print("Kuyruk bekleme süresi:", queue_wait_minutes)

assert next_start == pd.Timestamp(
    "2025-01-13 10:30:00"
)

assert queue_wait_minutes == 15



# Günlük kalan ekip kapasitesini hesaplama

def get_remaining_team_capacity(team_id, current_date):
    """
    Ekip ve tarih için kalan normal mesai
    ve fazla mesai kapasitesini döndürür.

    Bu fonksiyon rezervasyon oluşturmaz.
    """

    capacity = get_team_capacity(
        team_id,
        current_date
    )

    if capacity is None:
        raise ValueError(
            "İlgili ekip ve tarih için kapasite bulunamadı."
        )

    usage = get_capacity_usage(
        team_id,
        current_date
    )

    normal_remaining = (
        capacity["normal_capacity_minutes"]
        - usage["normal_used_minutes"]
    )

    overtime_remaining = (
        capacity["overtime_capacity_minutes"]
        - usage["overtime_used_minutes"]
    )

    if normal_remaining < 0 or overtime_remaining < 0:
        raise ValueError(
            "Kapasite tüketimi planlanan sınırı aşmış."
        )

    return {
        "normal_remaining_minutes": normal_remaining,
        "overtime_remaining_minutes": overtime_remaining,
        "total_remaining_minutes": (
            normal_remaining + overtime_remaining
        )
    }


# Önceki testte kullanılan 13 Ocak tarihini inceleyelim

remaining = get_remaining_team_capacity(
    team_id=1,
    current_date="2025-01-13"
)

print("\nKalan Günlük Kapasite Kontrolü")
print("-" * 40)
print("Ekip: 1")
print("Tarih: 2025-01-13")
print("Kalan normal kapasite:",
      remaining["normal_remaining_minutes"])
print("Kalan fazla mesai kapasitesi:",
      remaining["overtime_remaining_minutes"])
print("Toplam kalan kapasite:",
      remaining["total_remaining_minutes"])

# Önceki testte her çalışan 30 dakika çalıştı.
capacity = get_team_capacity(1, "2025-01-13")
employee_count = capacity["employee_count"]

assert (
    remaining["normal_remaining_minutes"]
    == capacity["normal_capacity_minutes"]
    - employee_count * 30
)

assert remaining["normal_remaining_minutes"] >= 0
assert remaining["overtime_remaining_minutes"] >= 0



# Tek çalışma aralığı için uygun yer bulma

def find_next_work_slot(team_id, arrival_time, work_minutes):
    """
    Normal mesai içinde, çalışan ve günlük kapasite
    sınırlarına uygun ilk çalışma aralığını bulur.

    Rezervasyon yapmaz.
    Fazla mesaiyi henüz kullanmaz.
    """

    arrival_time = pd.Timestamp(arrival_time)
    work_minutes = int(work_minutes)

    if work_minutes <= 0:
        raise ValueError("Çalışma süresi pozitif olmalı.")

    candidate = arrival_time

    # En fazla 730 takvim günü boyunca arama
    for _ in range(730):

        candidate = find_next_normal_work_time(candidate)

        capacity = get_team_capacity(team_id, candidate)

        if capacity is None:
            raise ValueError("Günlük kapasite bulunamadı.")

        remaining = get_remaining_team_capacity(
            team_id, candidate
        )["normal_remaining_minutes"]

        windows = get_normal_work_windows(candidate)

        employees = initialize_team_employees(
            team_id, candidate
        )

        for window_start, window_end in windows:

            earliest_start = max(candidate, window_start)

            if earliest_start >= window_end:
                continue

            for employee_id, available_at in sorted(
                employees.items(),
                key=lambda item: item[1]
            ):

                start = max(earliest_start, available_at)

                end = start + pd.Timedelta(
                    minutes=work_minutes
                )

                if (
                    end <= window_end
                    and remaining >= work_minutes
                ):
                    return {
                        "employee_id": employee_id,
                        "start_time": start,
                        "end_time": end,
                        "waiting_minutes": int(
                            (start - arrival_time).total_seconds() / 60
                        )
                    }

        candidate = (
            candidate.normalize()
            + pd.Timedelta(days=1)
        )

    raise ValueError(
        "Uygun çalışma aralığı bulunamadı."
    )


# Bağımsız test: Ekip 1, 14 Ocak 2025
slot = find_next_work_slot(
    team_id=1,
    arrival_time="2025-01-14 11:50:00",
    work_minutes=30
)

print("\nOtomatik Çalışma Aralığı Kontrolü")
print("-" * 40)
print("Sanal çalışan:", slot["employee_id"])
print("Başlangıç:", slot["start_time"])
print("Bitiş:", slot["end_time"])
print("Bekleme süresi:", slot["waiting_minutes"])

assert slot["start_time"] == pd.Timestamp(
    "2025-01-14 13:00:00"
)

assert slot["end_time"] == pd.Timestamp(
    "2025-01-14 13:30:00"
)

assert slot["waiting_minutes"] == 70



# Uygun çalışma aralığını bul ve rezerve et

def schedule_single_work(
    team_id,
    arrival_time,
    work_minutes
):
    """
    Normal mesai içerisinde uygun çalışma
    aralığını bulur ve rezervasyon oluşturur.

    Başarılı rezervasyondan sonra çalışan
    müsaitliği ve günlük kapasite güncellenir.
    """

    slot = find_next_work_slot(
        team_id=team_id,
        arrival_time=arrival_time,
        work_minutes=work_minutes
    )

    reserve_with_capacity(
        team_id=team_id,
        employee_id=slot["employee_id"],
        start_time=slot["start_time"],
        end_time=slot["end_time"]
    )

    return slot


# Bağımsız test günü
schedule_test_day = "2025-01-15"

usage_before = get_capacity_usage(
    1, schedule_test_day
)["normal_used_minutes"]

# İlk işlem: 10.00'da gelen 30 dakikalık iş
first_slot = schedule_single_work(
    team_id=1,
    arrival_time=f"{schedule_test_day} 10:00:00",
    work_minutes=30
)

# İkinci işlem: aynı anda gelen başka bir iş
second_slot = schedule_single_work(
    team_id=1,
    arrival_time=f"{schedule_test_day} 10:00:00",
    work_minutes=30
)

usage_after = get_capacity_usage(
    1, schedule_test_day
)["normal_used_minutes"]

print("\nOtomatik İş Rezervasyonu")
print("-" * 40)

print(
    "Birinci işlem:",
    first_slot["employee_id"],
    first_slot["start_time"],
    first_slot["end_time"]
)

print(
    "İkinci işlem:",
    second_slot["employee_id"],
    second_slot["start_time"],
    second_slot["end_time"]
)

print(
    "Tüketilen normal kapasite:",
    usage_after - usage_before
)

assert first_slot["start_time"] == pd.Timestamp(
    "2025-01-15 10:00:00"
)

assert second_slot["start_time"] == pd.Timestamp(
    "2025-01-15 10:00:00"
)

assert (
    first_slot["employee_id"]
    != second_slot["employee_id"]
), "Eş zamanlı işler aynı çalışana atanamaz."

assert usage_after - usage_before == 60



# Tam kapasitede otomatik kuyruk testi

queue_day = "2025-01-16"
queue_team_id = 1

capacity = get_team_capacity(
    queue_team_id,
    queue_day
)

employee_count = capacity["employee_count"]

# Bütün çalışanlara aynı anda 30 dakikalık iş ata
initial_slots = []

for _ in range(employee_count):
    slot = schedule_single_work(
        team_id=queue_team_id,
        arrival_time=f"{queue_day} 10:00:00",
        work_minutes=30
    )
    initial_slots.append(slot)

# Tüm çalışanlar meşgulken yeni işlem gelsin
queued_slot = schedule_single_work(
    team_id=queue_team_id,
    arrival_time=f"{queue_day} 10:15:00",
    work_minutes=20
)

print("\nTam Kapasitede Kuyruk Testi")
print("-" * 40)
print("Ekip:", queue_team_id)
print("Çalışan sayısı:", employee_count)
print("İlk atanan işlem:", len(initial_slots))
print("Yeni işlemin geliş zamanı: 10:15")
print("Yeni işlemin başlangıcı:", queued_slot["start_time"])
print("Yeni işlemin bitişi:", queued_slot["end_time"])
print("Kuyruk bekleme süresi:", queued_slot["waiting_minutes"])

assert len(initial_slots) == employee_count

assert len({
    slot["employee_id"]
    for slot in initial_slots
}) == employee_count

assert queued_slot["start_time"] == pd.Timestamp(
    "2025-01-16 10:30:00"
)

assert queued_slot["end_time"] == pd.Timestamp(
    "2025-01-16 10:50:00"
)

assert queued_slot["waiting_minutes"] == 15

print("Tam kapasitede kuyruk testi başarılı.")



# Uzun işleri birden fazla normal mesai aralığına bölme

def plan_multi_day_work(start_time, work_minutes):
    """
    Aktif çalışma süresini normal mesai
    pencerelerine böler.

    Çalışan müsaitliği ve ekip kapasitesi
    bu aşamada değerlendirilmez.
    """

    start_time = pd.Timestamp(start_time)
    work_minutes = int(work_minutes)

    if work_minutes <= 0:
        raise ValueError(
            "Çalışma süresi pozitif olmalı."
        )

    intervals = split_work_across_normal_windows(
        start_time,
        work_minutes
    )

    total_minutes = sum(
        int((end - start).total_seconds() / 60)
        for start, end in intervals
    )

    if total_minutes != work_minutes:
        raise AssertionError(
            "Planlanan aktif çalışma süresi hatalı."
        )

    return intervals


# Örnek: 16 Ocak 16.30'da başlayan 180 dakikalık iş

multi_day_intervals = plan_multi_day_work(
    start_time="2025-01-16 16:30:00",
    work_minutes=180
)

print("\nÇok Günlü Çalışma Planı")
print("-" * 40)

for start, end in multi_day_intervals:
    duration = int(
        (end - start).total_seconds() / 60
    )

    print(
        start.strftime("%Y-%m-%d %H:%M"),
        "->",
        end.strftime("%Y-%m-%d %H:%M"),
        f"({duration} dakika)"
    )

assert len(multi_day_intervals) == 2

assert multi_day_intervals[0] == (
    pd.Timestamp("2025-01-16 16:30:00"),
    pd.Timestamp("2025-01-16 18:00:00")
)

assert multi_day_intervals[1] == (
    pd.Timestamp("2025-01-17 09:00:00"),
    pd.Timestamp("2025-01-17 10:30:00")
)

print("Çok günlü çalışma planı başarılı.")



# Tercih edilen çalışanı destekleyen iş planlayıcı

def schedule_work_with_preference(
    team_id,
    arrival_time,
    work_minutes,
    preferred_employee_id=None
):
    """
    Tercih edilen çalışan uygunsa işi ona atar.
    Uygun değilse mevcut planlayıcıyla
    en erken müsait çalışana yönlendirir.

    Yalnızca normal mesai kullanılır.
    """

    slot = find_next_work_slot(
        team_id=team_id,
        arrival_time=arrival_time,
        work_minutes=work_minutes
    )

    if preferred_employee_id is not None:

        candidate_start = find_next_normal_work_time(
            arrival_time
        )

        employees = initialize_team_employees(
            team_id,
            candidate_start
        )

        preferred_available_at = employees.get(
            preferred_employee_id
        )

        if preferred_available_at is not None:

            preferred_start = max(
                candidate_start,
                preferred_available_at
            )

            preferred_end = preferred_start + pd.Timedelta(
                minutes=work_minutes
            )

            windows = get_normal_work_windows(
                preferred_start
            )

            remaining = get_remaining_team_capacity(
                team_id,
                preferred_start
            )["normal_remaining_minutes"]

            preferred_is_valid = any(
                preferred_start >= window_start
                and preferred_end <= window_end
                for window_start, window_end in windows
            )

            # Aynı çalışan, en erken başlangıcı
            # geciktirmiyorsa tercih edilir.
            if (
                preferred_is_valid
                and remaining >= work_minutes
                and preferred_start <= slot["start_time"]
            ):
                slot = {
                    "employee_id": preferred_employee_id,
                    "start_time": preferred_start,
                    "end_time": preferred_end,
                    "waiting_minutes": int(
                        (
                            preferred_start
                            - pd.Timestamp(arrival_time)
                        ).total_seconds() / 60
                    )
                }

    reserve_with_capacity(
        team_id=team_id,
        employee_id=slot["employee_id"],
        start_time=slot["start_time"],
        end_time=slot["end_time"]
    )

    return slot



# Çok günlü işlerin kapasiteye göre rezervasyonu

def schedule_multi_day_work(
    team_id,
    arrival_time,
    work_minutes,
    chunk_minutes=30
):
    """
    Uzun bir işi küçük çalışma parçalarına böler.

    Her parçayı çalışan müsaitliği ve normal
    mesai kapasitesine göre sırayla rezerve eder.

    Fazla mesai henüz kullanılmaz.
    """

    import copy

    work_minutes = int(work_minutes)
    chunk_minutes = int(chunk_minutes)

    if work_minutes <= 0 or chunk_minutes <= 0:
        raise ValueError(
            "Çalışma ve parça süreleri pozitif olmalı."
        )

    availability_backup = copy.deepcopy(
        employee_availability
    )
    usage_backup = copy.deepcopy(capacity_usage)

    remaining = work_minutes
    current_time = pd.Timestamp(arrival_time)
    scheduled_intervals = []
    preferred_employee_id = None

    try:
        while remaining > 0:

            # Tek parça 30 dakikayı geçmez.
            duration = min(remaining, chunk_minutes)

            slot = schedule_work_with_preference(
                team_id=team_id,
                arrival_time=current_time,
                work_minutes=duration,
                preferred_employee_id=preferred_employee_id
            )
            # İlk atanan çalışanı sonraki parçalarda tercih et.
            # Gerekirse yeni atanan çalışan tercih edilen kişi olur.
            preferred_employee_id = slot["employee_id"]

            scheduled_intervals.append(slot)

            remaining -= duration

            # Aynı işin sonraki parçası,
            # önceki parça bitmeden başlayamaz.
            current_time = slot["end_time"]

    except Exception:
        employee_availability.clear()
        employee_availability.update(
            availability_backup
        )

        capacity_usage.clear()
        capacity_usage.update(usage_backup)

        raise

    return scheduled_intervals


        # Bağımsız bir test günü kullanıyoruz.
        # 20 Ocak 2025 tarihinde 180 dakikalık iş

multi_slots = schedule_multi_day_work(
    team_id=1,
    arrival_time="2025-01-20 16:30:00",
    work_minutes=180,
    chunk_minutes=30
)

print("\nKapasiteye Bağlı Çok Günlü İş")
print("-" * 40)

for slot in multi_slots:
    print(
        slot["start_time"],
        "->",
        slot["end_time"],
        "| Çalışan:",
        slot["employee_id"]
    )

total_scheduled_minutes = sum(
    int(
        (
            slot["end_time"] - slot["start_time"]
        ).total_seconds() / 60
    )
    for slot in multi_slots
)

print("Toplam aktif çalışma:", total_scheduled_minutes)
print("Çalışma parçası sayısı:", len(multi_slots))

assert total_scheduled_minutes == 180
assert len(multi_slots) == 6

print("Kapasiteye bağlı çok günlü iş testi başarılı.")


# Çok günlü işlerde çalışan devamlılığı analizi

def analyze_employee_continuity(scheduled_intervals):
    """
    Aynı işin çalışma parçaları arasında
    kaç defa çalışan değiştiğini hesaplar.
    """

    if not scheduled_intervals:
        return {
            "employee_changes": 0,
            "unique_employees": 0,
            "continuity_rate": 0.0
        }

    employee_ids = [
        slot["employee_id"]
        for slot in scheduled_intervals
    ]

    employee_changes = sum(
        employee_ids[i] != employee_ids[i - 1]
        for i in range(1, len(employee_ids))
    )

    possible_changes = max(len(employee_ids) - 1, 1)

    continuity_rate = (
        1 - employee_changes / possible_changes
    ) * 100

    return {
        "employee_changes": employee_changes,
        "unique_employees": len(set(employee_ids)),
        "continuity_rate": round(continuity_rate, 2)
    }


continuity = analyze_employee_continuity(multi_slots)

print("\nÇalışan Devamlılığı Analizi")
print("-" * 40)
print("Çalışan değişim sayısı:",
      continuity["employee_changes"])
print("Farklı çalışan sayısı:",
      continuity["unique_employees"])
print("Devamlılık oranı (%):",
      continuity["continuity_rate"])

assert continuity["employee_changes"] == 0
assert continuity["unique_employees"] == 1
assert continuity["continuity_rate"] == 100.0

print("Çalışan devamlılığı kontrolü başarılı.")


continuity_test_day = "2025-01-22"

first_preferred_slot = schedule_work_with_preference(
    team_id=1,
    arrival_time=f"{continuity_test_day} 10:00:00",
    work_minutes=30
)

second_preferred_slot = schedule_work_with_preference(
    team_id=1,
    arrival_time=first_preferred_slot["end_time"],
    work_minutes=30,
    preferred_employee_id=first_preferred_slot["employee_id"]
)

print("\nTercih Edilen Çalışan Kontrolü")
print("-" * 40)

print(
    "İlk çalışan:",
    first_preferred_slot["employee_id"]
)

print(
    "İkinci çalışan:",
    second_preferred_slot["employee_id"]
)

print(
    "İkinci iş başlangıcı:",
    second_preferred_slot["start_time"]
)

assert (
    first_preferred_slot["employee_id"]
    == second_preferred_slot["employee_id"]
)

assert second_preferred_slot["start_time"] == (
    first_preferred_slot["end_time"]
)

print("Çalışan devamlılığı testi başarılı.")



# Çok günlü işte çalışan devamlılığı testi

continuity_slots = schedule_multi_day_work(
    team_id=1,
    arrival_time="2025-01-23 16:30:00",
    work_minutes=180,
    chunk_minutes=30
)

continuity_result = analyze_employee_continuity(
    continuity_slots
)

total_minutes = sum(
    int(
        (slot["end_time"] - slot["start_time"]).total_seconds()
        / 60
    )
    for slot in continuity_slots
)

print("\nÇok Günlü Çalışan Devamlılığı")
print("-" * 40)

for slot in continuity_slots:
    print(
        slot["start_time"],
        "->",
        slot["end_time"],
        "| Çalışan:",
        slot["employee_id"]
    )

print("Toplam aktif çalışma:", total_minutes)
print(
    "Çalışan değişim sayısı:",
    continuity_result["employee_changes"]
)
print(
    "Devamlılık oranı (%):",
    continuity_result["continuity_rate"]
)

assert total_minutes == 180
assert len(continuity_slots) == 6
assert continuity_result["employee_changes"] == 0
assert continuity_result["continuity_rate"] == 100.0

print("Çok günlü çalışan devamlılığı testi başarılı.")



# Kronolojik pilot işlem kuyruğu

def prepare_pilot_queue():
    transactions_df = pd.read_csv(
        "data/pilot/transactions.csv"
    )

    selected_stages_df = pd.read_csv(
        "data/pilot/selected_stages.csv"
    )

    transactions_df["opened_at"] = pd.to_datetime(
        transactions_df["opened_at"]
    )

    # İşlemleri açılış zamanına göre sırala.
    # Aynı zamanda açılanlarda transaction_id belirleyicidir.
    transactions_df = transactions_df.sort_values(
        ["opened_at", "transaction_id"],
        kind="stable"
    ).reset_index(drop=True)

    # Seçilen aşamaları işlemlerle eşleştir.
    pilot_queue = transactions_df.merge(
        selected_stages_df,
        on="transaction_id",
        how="left",
        validate="one_to_many"
    )

    # Aşama sırasını koru.
    pilot_queue = pilot_queue.sort_values(
        ["opened_at", "transaction_id", "stage_order"],
        kind="stable"
    ).reset_index(drop=True)

    return transactions_df, pilot_queue


pilot_transactions, pilot_queue = prepare_pilot_queue()

print("\nKronolojik Pilot İşlem Kuyruğu")
print("-" * 40)
print("Toplam işlem:", len(pilot_transactions))
print("Toplam seçilmiş aşama:", len(pilot_queue))

print("\nİlk 5 işlem:")
print(
    pilot_transactions[
        ["transaction_id", "opened_at", "operation_id"]
    ].head(5).to_string(index=False)
)

assert len(pilot_transactions) == 300
assert len(pilot_queue) == 1375
assert pilot_queue["stage_id"].notna().all()

print("Kronolojik pilot kuyruk testi başarılı.")



# Olay tabanlı simülasyon kuyruğu

import heapq
from itertools import count


def prepare_event_queue(transactions_df):
    """
    İşlemlerin açılış olaylarını zaman sırasına koyar.

    Henüz çalışan rezervasyonu yapmaz.
    """

    event_queue = []
    sequence = count()

    for row in transactions_df.itertuples(index=False):
        heapq.heappush(
            event_queue,
            (
                pd.Timestamp(row.opened_at),
                next(sequence),
                "TRANSACTION_OPENED",
                int(row.transaction_id)
            )
        )

    return event_queue


event_queue = prepare_event_queue(
    pilot_transactions
)

print("\nOlay Tabanlı Simülasyon Kuyruğu")
print("-" * 40)
print("Toplam açılış olayı:", len(event_queue))

first_events = []

for _ in range(5):
    event = heapq.heappop(event_queue)
    first_events.append(event)

    print(
        event[0],
        "|",
        event[2],
        "| İşlem:",
        event[3]
    )

assert len(first_events) == 5
assert len(event_queue) == 295

assert all(
    first_events[i][0] <= first_events[i + 1][0]
    for i in range(len(first_events) - 1)
)

assert all(
    event[2] == "TRANSACTION_OPENED"
    for event in first_events
)

print("Olay tabanlı kuyruk testi başarılı.")
