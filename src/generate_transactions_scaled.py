"""Veriqora Bank | Parametrik sentetik işlem üreticisi.

Örnek: python src/generate_transactions_scaled.py --count 1000 --output data/scale_test_1000
Mevcut data/pilot dosyalarına yazmaz.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {1: 90, 2: 60, 3: 54, 4: 45, 5: 30, 6: 21}
REQUEST_TYPES = {
    1: ["STANDARD_TRANSFER", "HIGH_VALUE_TRANSFER", "INTERNATIONAL_TRANSFER", "NON_STANDARD_TRANSFER"],
    2: ["CONTACT_UPDATE", "ADDRESS_UPDATE", "IDENTITY_UPDATE", "MULTIPLE_INFO_UPDATE"],
    3: ["ACCOUNT_OPENING", "ACCOUNT_CLOSURE", "AUTHORITY_CHANGE", "NON_STANDARD_ACCOUNT"],
    4: ["STANDARD_CREDIT", "CREDIT_RESTRUCTURING", "COLLATERAL_REVIEW", "NON_STANDARD_CREDIT"],
    5: ["STANDARD_FOLLOWUP", "DOCUMENT_REVIEW", "EXTERNAL_COORDINATION", "COMPLEX_LEGAL_CASE"],
    6: ["ROUTINE_CONTROL", "ADDITIONAL_CONTROL", "MULTI_STAGE_REVIEW", "CORRECTION_REQUEST"],
}
COMPLEX_REQUEST_TYPES = {
    "INTERNATIONAL_TRANSFER", "NON_STANDARD_TRANSFER", "MULTIPLE_INFO_UPDATE", "AUTHORITY_CHANGE",
    "NON_STANDARD_ACCOUNT", "CREDIT_RESTRUCTURING", "COLLATERAL_REVIEW", "NON_STANDARD_CREDIT",
    "EXTERNAL_COORDINATION", "COMPLEX_LEGAL_CASE", "MULTI_STAGE_REVIEW", "CORRECTION_REQUEST",
}
PROBABILITIES = {1: (.20,.10,.15), 2: (.15,.05,.15), 3: (.25,.10,.20), 4: (.55,.30,.45), 5: (.35,.60,.50), 6: (.30,.10,.40)}
DOCUMENT_RANGES = {1:(0,3),2:(0,4),3:(1,5),4:(2,9),5:(2,10),6:(1,6)}


def complexity(a):
    score = 2 * (a['request_type'] in COMPLEX_REQUEST_TYPES)
    score += int(a['requires_approval']) + 2 * int(a['requires_external_party']) + 2 * int(a['requires_manual_review'])
    score += 2 if a['document_count'] >= 6 else (1 if a['document_count'] >= 3 else 0)
    score += int(a['amount_band'] == 'HIGH')
    return 'HIGH' if score >= 6 else ('MEDIUM' if score >= 3 else 'LOW')


def distribute(total):
    """Largest-remainder: toplamı tam tutarken pilot operasyon oranlarını korur."""
    ids = list(WEIGHTS)
    raw = np.array([WEIGHTS[i] for i in ids], dtype=float) * total / sum(WEIGHTS.values())
    counts = np.floor(raw).astype(int)
    for idx in np.argsort(-(raw - counts), kind='stable')[:total-int(counts.sum())]:
        counts[idx] += 1
    return dict(zip(ids, counts.tolist()))


def opening_category(day_type, hour):
    if day_type in ('HOLIDAY', 'WEEKEND'):
        return 'NON_WORKING_DAY'
    if day_type == 'HALF_DAY':
        return 'BUSINESS_HOURS' if 9 <= hour < 12 else 'WEEKDAY_OFF_HOURS'
    return 'BUSINESS_HOURS' if 9 <= hour < 12 or 13 <= hour < 18 else 'WEEKDAY_OFF_HOURS'


def generate(count, seed, reference_dir, output_dir):
    if count < 1:
        raise ValueError('--count pozitif olmalıdır')
    if output_dir.resolve() == reference_dir.resolve() or output_dir.resolve() == (ROOT / 'data' / 'pilot').resolve():
        raise ValueError('Pilot klasörünün üzerine yazmak yasaktır')
    rng = np.random.default_rng(seed)
    sla = pd.read_csv(reference_dir / 'sla_targets.csv')
    calendar = pd.read_csv(reference_dir / 'business_calendar.csv', parse_dates=['calendar_date'])
    calendar = calendar.loc[calendar.calendar_date.dt.year == 2025]
    slots = {'BUSINESS_HOURS': [], 'WEEKDAY_OFF_HOURS': [], 'NON_WORKING_DAY': []}
    for row in calendar.itertuples(index=False):
        for hour in range(24):
            slots[opening_category(row.day_type, hour)].append(row.calendar_date + pd.Timedelta(hours=hour))
    assert all(slots.values()), '2025 iş takvimi eksik'
    rows = []
    tx_rows = []
    tid = 0
    for operation, n in distribute(count).items():
        p_approval, p_external, p_manual = PROBABILITIES[operation]
        low, high = DOCUMENT_RANGES[operation]
        for _ in range(n):
            tid += 1
            a = dict(transaction_id=tid, request_type=str(rng.choice(REQUEST_TYPES[operation])),
                     document_count=int(rng.integers(low, high+1)),
                     requires_approval=bool(rng.random()<p_approval),
                     requires_external_party=bool(rng.random()<p_external),
                     requires_manual_review=bool(rng.random()<p_manual),
                     amount_band=str(rng.choice(['LOW','MEDIUM','HIGH'],p=[.50,.35,.15])) if operation in (1,3,4) else None)
            rows.append(a)
            tx_rows.append(dict(transaction_id=tid,operation_id=operation,complexity_level=complexity(a)))
    attrs = pd.DataFrame(rows)
    tx = pd.DataFrame(tx_rows).merge(sla[['sla_target_id','operation_id','complexity_level','valid_from','valid_to']],
                                     on=['operation_id','complexity_level'],how='left',validate='many_to_one')
    if tx.sla_target_id.isna().any():
        raise ValueError('SLA eşleşmesi eksik')
    cats = ['BUSINESS_HOURS','WEEKDAY_OFF_HOURS','NON_WORKING_DAY']
    # Kategori örneklemesi ve saat/dakika dağılımı mevcut pilot mantığıyla aynıdır.
    dates = []
    for _ in range(count):
        cat = str(rng.choice(cats,p=[.75,.15,.10]))
        slot = rng.choice(slots[cat])
        dates.append(pd.Timestamp(slot)+pd.Timedelta(minutes=int(rng.integers(60)),seconds=int(rng.integers(60))))
    tx['opened_at'] = dates
    valid_from = pd.to_datetime(tx.valid_from)
    valid_to = pd.to_datetime(tx.valid_to)
    if not ((tx.opened_at>=valid_from)&(valid_to.isna()|(tx.opened_at<valid_to))).all():
        raise ValueError('Açılış tarihinde geçersiz SLA hedefi')
    tx['closed_at'] = pd.NaT
    tx['final_status'] = pd.NA
    tx = tx[['transaction_id','operation_id','complexity_level','opened_at','closed_at','final_status','sla_target_id']]
    if tx.transaction_id.duplicated().any() or attrs.transaction_id.duplicated().any() or len(tx)!=count:
        raise AssertionError('Veri bütünlüğü hatası')
    output_dir.mkdir(parents=True,exist_ok=True)
    tx.to_csv(output_dir/'transactions.csv',index=False,encoding='utf-8-sig')
    attrs.to_csv(output_dir/'transaction_attributes.csv',index=False,encoding='utf-8-sig')
    print(f'VERIQORA | İŞLEM ÜRETİMİ | {count:,} işlem | seed={seed}')
    print('Operasyon dağılımı:',distribute(count))
    print('Karmaşıklık dağılımı:',tx.complexity_level.value_counts().to_dict())
    print('Dosyalar:',output_dir)
    print('NOT: selected_stages.csv ve simülasyon çıktıları henüz üretilmedi.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--count',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=2025)
    parser.add_argument('--reference',type=Path,default=ROOT/'data'/'pilot')
    parser.add_argument('--output',type=Path,default=ROOT/'data'/'scale_test_1000')
    args=parser.parse_args()
    generate(args.count,args.seed,args.reference,args.output)

if __name__=='__main__':
    main()
