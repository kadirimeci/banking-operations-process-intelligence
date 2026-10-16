"""Veriqora: Recalculate five scenario KPIs from existing simulation CSVs.

Run from repository root: python src/veriqora_scenario_audit.py
No simulation is executed. Writes new *_v2 reports, never overwrites original reports.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
BASE = ROOT / 'data' / 'final_50000'
REF = ROOT / 'data' / 'reference'
CUTOFF = pd.Timestamp('2025-12-31 18:00:00')
SCENARIOS = ['baseline', 'targeted_25', 'targeted_50', 'targeted_100', 'all_25']
LABELS = {
    'baseline': 'Mevcut kapasite',
    'targeted_25': 'Kredi ve Yasal Takip +%25',
    'targeted_50': 'Kredi ve Yasal Takip +%50',
    'targeted_100': 'Kredi ve Yasal Takip +%100',
    'all_25': 'Tüm ekipler +%25',
}


def csv(path):
    if not path.is_file():
        raise FileNotFoundError(f'Eksik dosya: {path}')
    return pd.read_csv(path, low_memory=False)


def boolean(s):
    return s.astype('string').str.lower().isin(['true', '1', 'yes'])


def build_calendar():
    cal = csv(REF / 'business_calendar.csv')
    intervals = []
    for r in cal.itertuples(index=False):
        day = pd.Timestamp(r.calendar_date)
        if str(r.day_type) not in ('FULL_DAY', 'HALF_DAY'):
            continue
        if pd.notna(r.business_start) and pd.notna(r.lunch_start):
            intervals.append((pd.Timestamp(f'{r.calendar_date} {r.business_start}'),
                              pd.Timestamp(f'{r.calendar_date} {r.lunch_start}')))
        if str(r.day_type) == 'FULL_DAY' and pd.notna(r.lunch_end) and pd.notna(r.business_end):
            intervals.append((pd.Timestamp(f'{r.calendar_date} {r.lunch_end}'),
                              pd.Timestamp(f'{r.calendar_date} {r.business_end}')))
    intervals.sort()
    starts = np.array([a.value for a, _ in intervals], dtype=np.int64)
    ends = np.array([b.value for _, b in intervals], dtype=np.int64)
    durations = (ends - starts) / 60_000_000_000
    cum = np.concatenate([[0.0], np.cumsum(durations)])
    if len(starts) == 0 or ends[-1] < CUTOFF.value:
        raise ValueError('İş takvimi raporlama kesitini kapsamıyor.')
    return starts, ends, cum


def business_position(ts, calendar):
    starts, ends, cum = calendar
    t = pd.to_datetime(ts, errors='coerce')
    if t.isna().any():
        raise ValueError('SLA için zorunlu tarih alanında boş/geçersiz değer var.')
    ns = t.to_numpy(dtype='datetime64[ns]').astype('int64')
    # Locate the most recent interval START, not the most recent interval END.
    # Searching ends incorrectly leaves most timestamps at the previous
    # cumulative total, making SLA durations zero and pass rates 100%.
    idx = np.searchsorted(starts, ns, side='right') - 1
    positions = np.zeros(len(ns), dtype=float)
    valid = idx >= 0
    if valid.any():
        j = idx[valid]
        elapsed = (np.minimum(ns[valid], ends[j]) - starts[j]) / 60_000_000_000
        positions[valid] = cum[j] + np.maximum(elapsed, 0)
    return positions


def calculate(scenario, calendar, sla, costs, ops):
    folder = BASE / ('simulated' if scenario == 'baseline' else f'scenarios/{scenario}')
    if not folder.exists():
        raise FileNotFoundError(f'Senaryo sonuç klasörü bulunamadı: {folder}')
    tx = csv(folder / 'transactions.csv')
    ex = csv(folder / 'stage_executions.csv')
    waits = csv(folder / 'waiting_intervals.csv')
    if len(tx) != 50000 or not tx.transaction_id.is_unique:
        raise ValueError(f'{scenario}: işlem sayısı/benzersizliği hatalı')
    completed = tx.final_status.eq('COMPLETED')
    txc = tx.loc[completed, ['transaction_id','operation_id','sla_target_id','opened_at','closed_at']].copy()
    txc = txc.merge(sla[['sla_target_id','target_minutes']], on='sla_target_id', how='left', validate='many_to_one')
    if txc.target_minutes.isna().any():
        raise ValueError(f'{scenario}: SLA hedefi eşleşmeyen işlem var')
    txc['e2e_minutes'] = business_position(txc.closed_at, calendar) - business_position(txc.opened_at, calendar)
    if (txc.e2e_minutes < 0).any():
        raise ValueError(f'{scenario}: negatif iş dakikası')
    # Only verified, excludable external waiting is subtracted. Clip waits to
    # the individual transaction's [opened_at, closed_at] interval.
    w = waits.loc[boolean(waits.is_excludable) & boolean(waits.reason_verified) &
                  waits.waiting_type.isin(['EXTERNAL_PARTY', 'CUSTOMER'])].copy()
    w = w.merge(txc[['transaction_id','opened_at','closed_at']], on='transaction_id', how='inner', validate='many_to_one')
    if len(w):
        ws = pd.to_datetime(w.started_at)
        we = pd.to_datetime(w.ended_at).fillna(CUTOFF)
        opening = pd.to_datetime(w.opened_at)
        closing = pd.to_datetime(w.closed_at)
        start = pd.concat([ws, opening], axis=1).max(axis=1)
        end = pd.concat([we, closing], axis=1).min(axis=1)
        valid = end > start
        w = w.loc[valid].copy()
        start, end = start.loc[valid], end.loc[valid]
        # Merge overlapping eligible waits per transaction before subtraction.
        segments = pd.DataFrame({'transaction_id': w.transaction_id.to_numpy(),
                                 'start': start.to_numpy(), 'end': end.to_numpy()})
        totals = {}
        for tx_id, group in segments.sort_values(['transaction_id', 'start', 'end']).groupby('transaction_id', sort=False):
            merged = []
            for row in group.itertuples(index=False):
                a, b = pd.Timestamp(row.start), pd.Timestamp(row.end)
                if merged and a <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], b))
                else:
                    merged.append((a, b))
            begin = pd.Series([a for a, _ in merged])
            finish = pd.Series([b for _, b in merged])
            totals[tx_id] = float((business_position(finish, calendar) - business_position(begin, calendar)).sum())
        excluded = pd.Series(totals, dtype=float)
    else:
        excluded = pd.Series(dtype=float)
    txc['excluded_minutes'] = txc.transaction_id.map(excluded).fillna(0)
    txc['operational_minutes'] = (txc.e2e_minutes - txc.excluded_minutes).clip(lower=0)
    txc['e2e_pass'] = txc.e2e_minutes <= txc.target_minutes
    txc['operational_pass'] = txc.operational_minutes <= txc.target_minutes

    done_ex = ex.loc[ex.execution_status.eq('COMPLETED') & ex.active_minutes.notna()].copy()
    done_ex['active_minutes'] = pd.to_numeric(done_ex.active_minutes, errors='raise')
    if (done_ex.active_minutes < 0).any():
        raise ValueError(f'{scenario}: negatif aktif çalışma süresi')
    done_ex['work_date'] = pd.to_datetime(done_ex.started_at).dt.normalize()
    cost_ref = costs.copy()
    cost_ref['valid_from'] = pd.to_datetime(cost_ref.valid_from)
    cost_ref['valid_to'] = pd.to_datetime(cost_ref.valid_to).fillna(pd.Timestamp.max.normalize())
    # Reference rates may have validity periods; match by team and work date.
    done_ex = done_ex.merge(cost_ref[['team_id','valid_from','valid_to','hourly_cost','overtime_multiplier']],
                            on='team_id', how='left', validate='many_to_many')
    valid_cost = done_ex.work_date.between(done_ex.valid_from, done_ex.valid_to)
    done_ex = done_ex.loc[valid_cost].copy()
    if done_ex.execution_id.duplicated().any() or len(done_ex) != len(ex.loc[ex.execution_status.eq('COMPLETED') & ex.active_minutes.notna()]):
        raise ValueError(f'{scenario}: maliyet parametrelerinde eksik veya çakışan tarih aralığı')
    overtime = done_ex.work_type.eq('OVERTIME')
    done_ex['work_cost'] = done_ex.active_minutes / 60 * done_ex.hourly_cost * np.where(overtime, done_ex.overtime_multiplier, 1.0)
    normal_minutes = done_ex.loc[~overtime, 'active_minutes'].sum()
    overtime_minutes = done_ex.loc[overtime, 'active_minutes'].sum()

    quality = csv(folder / 'quality_events.csv')
    summary = dict(scenario=scenario, transactions=len(tx), completed=int(completed.sum()),
                   open=int((tx.final_status == 'OPEN').sum()),
                   completion_pct=round(completed.mean() * 100, 2),
                   operational_sla_pct=round(txc.operational_pass.mean() * 100, 2),
                   e2e_sla_pct=round(txc.e2e_pass.mean() * 100, 2),
                   actual_work_cost_tl=round(done_ex.work_cost.sum(), 2),
                   normal_minutes=int(normal_minutes), overtime_minutes=int(overtime_minutes),
                   quality_events=len(quality), work_rows=len(ex), waiting_rows=len(waits))
    per_op = tx.groupby('operation_id', as_index=False).agg(
        transactions=('transaction_id','size'),
        completed=('final_status', lambda x: int(x.eq('COMPLETED').sum())),
        open=('final_status', lambda x: int(x.eq('OPEN').sum())))
    per_op['completion_pct'] = (per_op.completed / per_op.transactions * 100).round(2)
    per_op.insert(0, 'scenario', scenario)
    op_sla = txc.groupby('operation_id').agg(
        operational_sla_pct=('operational_pass', lambda x: round(x.mean() * 100, 2)),
        e2e_sla_pct=('e2e_pass', lambda x: round(x.mean() * 100, 2)))
    per_op = per_op.merge(op_sla, on='operation_id', how='left', validate='one_to_one')
    per_op = per_op.merge(ops[['operation_id', 'operation_name']], on='operation_id', how='left', validate='many_to_one') if 'operation_name' in ops.columns else per_op
    return summary, per_op


def main():
    calendar = build_calendar()
    sla = csv(REF / 'sla_targets.csv')
    costs = csv(REF / 'cost_parameters.csv')
    ops = csv(REF / 'operations.csv')
    summaries, breakdowns = [], []
    for scenario in SCENARIOS:
        print(f'Hesaplanıyor: {scenario}', flush=True)
        summary, by_op = calculate(scenario, calendar, sla, costs, ops)
        summaries.append(summary)
        breakdowns.append(by_op)
    comparison = pd.DataFrame(summaries)
    by_operation = pd.concat(breakdowns, ignore_index=True)
    base = comparison.loc[comparison.scenario.eq('baseline')].iloc[0]
    comparison['extra_completed'] = comparison.completed - int(base.completed)
    comparison['extra_actual_work_cost_tl'] = (comparison.actual_work_cost_tl - float(base.actual_work_cost_tl)).round(2)
    comparison['extra_actual_cost_per_extra_completed_tl'] = np.where(
        comparison.extra_completed.ne(0),
        (comparison.extra_actual_work_cost_tl / comparison.extra_completed.replace(0, np.nan)).round(2),
        np.nan)

    if (comparison.completed + comparison.open != comparison.transactions).any():
        raise AssertionError('İşlem sayıları tutarsız')
    previous = csv(REPORTS / 'scenario_comparison.csv')
    columns = ['transactions','completed','open','completion_pct','operational_sla_pct',
               'e2e_sla_pct','actual_work_cost_tl','normal_minutes','overtime_minutes']
    mismatches = []
    for s in ['baseline','targeted_50','targeted_100','all_25']:
        old = previous.loc[previous.scenario.eq(s)]
        new = comparison.loc[comparison.scenario.eq(s)]
        if len(old) != 1:
            raise ValueError(f'Önceki raporda {s} satırı bulunamadı veya tekrarlı')
        for col in columns:
            a, b = float(old.iloc[0][col]), float(new.iloc[0][col])
            tolerance = 0.011 if col in ['completion_pct','operational_sla_pct','e2e_sla_pct','actual_work_cost_tl'] else 0.01
            if not np.isclose(a, b, atol=tolerance, rtol=0):
                mismatches.append((s, col, a, b))
    print('\nYENİDEN HESAPLANAN SONUÇLAR (önizleme, dosya yazılmaz):')
    print(comparison.to_string(index=False))
    print('\nMEVCUT RAPORLA FARKLAR:')
    if mismatches:
        for scenario, field, old, new in mismatches:
            print(f'  {scenario} | {field}: mevcut={old:g}, yeni={new:g}')
        print('UYARI: Farklar araştırılmadan mevcut raporlar değiştirilmemeli.')
    else:
        print('Karşılaştırılan alanlarda fark bulunmadı.')
    # Save a NEW version only; originals remain intact for comparison.
    REPORTS.mkdir(parents=True, exist_ok=True)
    out_comparison = REPORTS / 'scenario_comparison_v2.csv'
    out_operation = REPORTS / 'scenario_by_operation_v2.csv'
    out_md = REPORTS / 'SONUC_RAPORU_v2.md'
    if any(p.exists() for p in (out_comparison, out_operation, out_md)):
        raise FileExistsError('v2 raporlarından biri zaten mevcut. Önce içeriğini kontrol et; üzerine yazılmadı.')
    comparison.to_csv(out_comparison, index=False, encoding='utf-8-sig')
    by_operation.to_csv(out_operation, index=False, encoding='utf-8-sig')
    table = comparison[['scenario','completed','open','completion_pct','operational_sla_pct',
                        'e2e_sla_pct','actual_work_cost_tl']]
    header = '| ' + ' | '.join(table.columns) + ' |'
    sep = '| ' + ' | '.join(['---'] * len(table.columns)) + ' |'
    lines = [header, sep]
    for row in table.itertuples(index=False, name=None):
        lines.append('| ' + ' | '.join(str(v) for v in row) + ' |')
    differences = ['- ' + f'{scenario}: {field} eski={old:g}, yeni={new:g}'
                   for scenario, field, old, new in mismatches]
    notes = [
        '# Veriqora Bank – Beş Senaryo Karşılaştırması (v2)',
        '', '## Kapsam ve yöntem',
        '- Tamamen sentetik 50.000 işlem içeren beş kapasite senaryosu.',
        '- Raporlama kesiti: 31.12.2025 18:00 (simülasyon yerel saatleri).',
        '- Tamamlanma ve SLA oranları farklı metriklerdir. SLA paydası yalnızca tamamlanan işlemlerdir.',
        '- Uçtan uca SLA: açılış–kapanış arasında normal iş takvimi dakikaları; öğle arası, tatil ve fazla mesai hariç.',
        '- Operasyonel SLA: uçtan uca iş dakikalarından yalnızca doğrulanmış ve hariç tutulabilir EXTERNAL_PARTY/CUSTOMER beklemelerinin birleştirilmiş iş dakikaları düşülür.',
        '- SLA hedefi işlem üzerindeki sla_target_id ile eşleştirilir; hedefe eşit süre başarılı sayılır.',
        '- Maliyet: tamamlanan çalışma aralıklarının aktif dakikaları, geçerli saatlik ücret ve fazla mesai çarpanıyla hesaplanır.',
        '- Bu rapor simülasyon sonuçlarını değiştirmez; eski raporlar karşılaştırma için korunur.',
        '', '## Senaryo sonuçları', *lines,
        '', '## Önceki raporla SLA ve metrik farkları',
        *(differences or ['- Karşılaştırılan alanlarda fark yok.']),
        '', '## Yorumlama sınırları',
        '- Önceki raporla farklı SLA değerleri hesaplama yaklaşımı ve tarih/zaman işleme farklarından kaynaklanabilir; eski raporun üretim kodu doğrulanmadığı için kesin neden bilinmiyor.',
        '- Bu sonuçlar sentetik simülasyon çıktılarıdır; gerçek banka performansı veya gerçekleşmiş tasarruf olarak yorumlanmamalıdır.',
        '- Beş senaryonun maliyet ve performansı birlikte değerlendirilmelidir; yalnızca tamamlanma oranına göre karar verilmemelidir.',
    ]
    out_md.write_text('\n'.join(notes) + '\n', encoding='utf-8')
    print('\nYENİ RAPORLAR OLUŞTURULDU (eski dosyalar korunuyor):')
    for path in (out_comparison, out_operation, out_md):
        print(' ', path.relative_to(ROOT))

if __name__ == '__main__':
    main()
