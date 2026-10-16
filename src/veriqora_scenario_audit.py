"""Veriqora: Beş senaryonun sonuçlarını mevcut simülasyon verilerinden hesaplar.

Proje ana klasöründen çalıştırın: python src/veriqora_scenario_audit.py
Simülasyonu yeniden çalıştırmaz; reports klasöründeki üç nihai raporu günceller.
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
    # Üç standart rapor dışında sürüm dosyası oluşturulmaz.
    REPORTS.mkdir(parents=True, exist_ok=True)
    out_comparison = REPORTS / 'scenario_comparison.csv'
    out_operation = REPORTS / 'scenario_by_operation.csv'
    out_md = REPORTS / 'SONUC_RAPORU.md'

    def sayi(value, digits=0):
        return f'{value:,.{digits}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

    def yuzde(value):
        return f'%{sayi(value, 2)}'

    def para(value):
        return f'{sayi(value, 2)} TL'

    lines = [
        '| Senaryo | Tamamlanan | Açık | Tamamlanma | Operasyonel SLA uyumu* | Uçtan uca SLA uyumu* | Gerçekleşen tahmini işçilik maliyeti |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for r in comparison.itertuples(index=False):
        lines.append(
            f'| {LABELS[r.scenario]} | {sayi(r.completed)} | {sayi(r.open)} | '
            f'{yuzde(r.completion_pct)} | {yuzde(r.operational_sla_pct)} | '
            f'{yuzde(r.e2e_sla_pct)} | {para(r.actual_work_cost_tl)} |'
        )

    base_completed = int(base.completed)
    base_cost = float(base.actual_work_cost_tl)
    effects = [
        '| Senaryo | İlave tamamlanan işlem | İlave işçilik maliyeti | İlave tamamlanan işlem başına maliyet |',
        '|---|---:|---:|---:|',
    ]
    for r in comparison.itertuples(index=False):
        unit_cost = '—' if pd.isna(r.extra_actual_cost_per_extra_completed_tl) else para(r.extra_actual_cost_per_extra_completed_tl)
        effects.append(
            f'| {LABELS[r.scenario]} | {sayi(r.extra_completed)} | '
            f'{para(r.extra_actual_work_cost_tl)} | {unit_cost} |'
        )

    best = comparison.loc[comparison.completion_pct.idxmax()]
    notes = [
        '# Veriqora Bank – Bankacılık Operasyonları Senaryo Analizi',
        '',
        '## Yönetici özeti',
        '',
        'Bu çalışma, sentetik olarak oluşturulan 50.000 bankacılık işlemi üzerinde beş farklı çalışan kapasitesi senaryosunu karşılaştırmaktadır. '
        'İşlem tamamlama oranı, hizmet seviyesi hedeflerine (SLA) uyum ve tahmini işçilik maliyetleri birlikte değerlendirilmiştir.',
        '',
        f'- Mevcut kapasitede {sayi(base_completed)} işlem tamamlanmış, tamamlanma oranı {yuzde(base.completion_pct)} olmuştur.',
        f'- En yüksek tamamlanma oranı **{LABELS[best.scenario]}** senaryosunda {yuzde(best.completion_pct)} olarak hesaplanmıştır.',
        f'- Bu senaryoda mevcut kapasiteye kıyasla **{sayi(int(best.completed) - base_completed)} ilave işlem** tamamlanmıştır.',
        '- Tamamlanma oranındaki artış, tek başına SLA hedeflerinin karşılandığı anlamına gelmez; iki gösterge ayrı değerlendirilmelidir.',
        '',
        '## Senaryo karşılaştırması',
        '',
        *lines,
        '',
        '*SLA uyum oranları yalnızca tamamlanan işlemler üzerinden hesaplanmıştır.',
        '',
        '## Kapasite artışının maliyet ve çıktı etkisi',
        '',
        *effects,
        '',
        'Mevcut kapasite senaryosunda ilave tamamlanan işlem bulunmadığından işlem başına ilave maliyet hesaplanmaz; tabloda bu değer “—” olarak gösterilmiştir.',
        '',
        '## Bulguların değerlendirilmesi',
        '',
        'Çalışmada kullanılan işlemler gerçek banka kayıtları değildir. Belirlenen iş kuralları ve rastgelelik içeren yöntemlerle üretilmiş **sentetik verilerdir**. '
        'Bu nedenle sonuçlar, veri üretiminde kullanılan işlem yoğunluğu, işlem süreleri, beklemeler ve ekip kapasitesi varsayımlarından etkilenir.',
        '',
        'Çalışan kapasitesinin artırıldığı senaryolarda tamamlanan işlem sayısının yükseldiği görülmektedir. '
        'Bu durumun olası açıklaması, kapasite artışının işlem kuyruklarını ve kaynak kısıtlarını hafifletmesidir. '
        'Ancak gözlenen artışın yalnızca veri üretimindeki rastgelelikten veya yalnızca çalışan sayısından kaynaklandığı bu analizle kesin olarak söylenemez. '
        'Etkileri ayrıştırmak için farklı rastgele başlangıç değerleriyle tekrarlı simülasyonlar ve duyarlılık analizleri yapılabilir.',
        '',
        'Kapasite artışının verimlilik açısından değerlendirilmesinde ilave tamamlanan işlem sayısı ile ilave işçilik maliyetinin birlikte incelenmesi gerekir. '
        'SLA uyum oranlarının düşük kalması, tamamlanan işlem sayısındaki artışın hizmet seviyesi hedeflerine aynı ölçüde yansımadığını göstermektedir.',
        '',
        '## Hesaplama yöntemi',
        '',
        '- **Raporlama kesiti:** 31.12.2025 saat 18.00 (simülasyon yerel saati).',
        '- **Tamamlanma oranı:** Tamamlanan işlem sayısı / toplam işlem sayısı.',
        '- **Uçtan uca SLA:** İşlemin açılışı ile kapanışı arasındaki normal iş takvimi dakikaları esas alınır. Öğle arası, hafta sonu, tatil ve fazla mesai SLA süresine dahil edilmez.',
        '- **Operasyonel SLA:** Uçtan uca iş dakikalarından yalnızca doğrulanmış, hariç tutulabilir müşteri ve dış taraf beklemelerinin çakışmayan iş dakikaları çıkarılır.',
        '- **SLA başarısı:** İşlem süresi, ilgili hedef süreye eşit veya daha kısa ise başarılı kabul edilir.',
        '- **İşçilik maliyeti:** Tamamlanan çalışma aşamalarındaki aktif süreler, geçerli saatlik maliyet ve fazla mesai çarpanıyla hesaplanır.',
        '- **İlave işlem başına maliyet:** Mevcut kapasiteye göre ilave işçilik maliyeti / ilave tamamlanan işlem sayısı.',
        '',
        '## Sınırlılıklar',
        '',
        'Bulgular sentetik veri ve simülasyon varsayımlarına dayanmaktadır. Gerçek bir bankada aynı kapasite değişikliğinin aynı sonuçları vereceği garanti edilemez. '
        'Hesaplanan işçilik maliyetleri de gerçek muhasebe gideri veya gerçekleşmiş tasarruf olarak yorumlanmamalıdır.',
        '',
        'Operasyon bazında ayrıntılı sonuçlar `scenario_by_operation.csv`, senaryo düzeyindeki hesaplama çıktıları ise `scenario_comparison.csv` dosyasında yer almaktadır.',
    ]

    # Önce içerikler bellekte hazırlanır, ardından standart dosyalar güncellenir.
    report_text = '\n'.join(notes) + '\n'
    comparison.to_csv(out_comparison, index=False, encoding='utf-8-sig')
    by_operation.to_csv(out_operation, index=False, encoding='utf-8-sig')
    out_md.write_text(report_text, encoding='utf-8')
    print('\nÜÇ GÜNCEL RAPOR OLUŞTURULDU:')
    for path in (out_comparison, out_operation, out_md):
        print(' ', path.relative_to(ROOT))

if __name__ == '__main__':
    main()
