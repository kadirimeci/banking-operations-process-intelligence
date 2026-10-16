"""Veriqora Bank | pilot olaylardan denetlenebilir KPI üretimi.
Çalıştırma: python src/analyze_pilot.py
Girdi: data/pilot/{business_calendar,sla_targets,cost_parameters,team_capacity}.csv
       data/pilot/simulated/{transactions,stage_executions,waiting_intervals,quality_events}.csv
Çıktı: data/pilot/analytics/*.csv; hiçbir kaynak CSV üzerine yazılmaz.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

CUTOFF = pd.Timestamp('2025-12-31 18:00:00')


def read_csv(path):
    if not path.is_file():
        raise FileNotFoundError(f'Eksik veri dosyası: {path}')
    return pd.read_csv(path)


def time_cols(df, columns):
    for c in columns:
        df[c] = pd.to_datetime(df[c], errors='coerce')
    return df


def true_bool(x):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if str(x).strip().lower() in ('true', '1'):
        return True
    if str(x).strip().lower() in ('false', '0'):
        return False
    raise ValueError(f'Geçersiz boolean: {x}')


def work_windows(calendar):
    windows = []
    for r in calendar.itertuples(index=False):
        day = pd.Timestamp(r.calendar_date)
        if r.day_type not in ('FULL_DAY', 'HALF_DAY'):
            continue
        windows.append((day + pd.Timedelta(hours=9), day + pd.Timedelta(hours=12)))
        if r.day_type == 'FULL_DAY':
            windows.append((day + pd.Timedelta(hours=13), day + pd.Timedelta(hours=18)))
    return sorted(windows)


def business_minutes(start, end, windows):
    if pd.isna(start) or pd.isna(end) or end <= start:
        return 0.0
    return sum(max(0.0, (min(end, b) - max(start, a)).total_seconds() / 60)
               for a, b in windows if a < end and b > start)


def union_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if not result or start > result[-1][1]:
            result.append([start, end])
        elif end > result[-1][1]:
            result[-1][1] = end
    return result


def active_cost(row, cost):
    valid = cost[(cost.team_id == row.team_id) &
                 (cost.valid_from <= row.started_at.normalize()) &
                 (cost.valid_to.isna() | (cost.valid_to >= row.started_at.normalize()))]
    if len(valid) != 1:
        raise ValueError(f'Geçerli maliyet parametresi tekil değil: execution_id={row.execution_id}')
    c = valid.iloc[0]
    return row.active_minutes / 60 * float(c.hourly_cost) * (float(c.overtime_multiplier) if row.work_type == 'OVERTIME' else 1.0)


def run(project_root: Path):
    pilot = project_root / 'data' / 'pilot'
    sim = pilot / 'simulated'
    out = pilot / 'analytics'
    tx = time_cols(read_csv(sim / 'transactions.csv'), ['opened_at', 'closed_at'])
    ex = time_cols(read_csv(sim / 'stage_executions.csv'), ['started_at', 'ended_at'])
    waits = time_cols(read_csv(sim / 'waiting_intervals.csv'), ['started_at', 'ended_at'])
    quality = time_cols(read_csv(sim / 'quality_events.csv'), ['detected_at', 'resolved_at'])
    cal = read_csv(pilot / 'business_calendar.csv')
    sla = time_cols(read_csv(pilot / 'sla_targets.csv'), ['valid_from', 'valid_to'])
    costs = time_cols(read_csv(pilot / 'cost_parameters.csv'), ['valid_from', 'valid_to'])
    capacity = read_csv(pilot / 'team_capacity.csv')
    capacity['capacity_date'] = pd.to_datetime(capacity['capacity_date'])
    windows = work_windows(cal)
    checks = []
    def check(name, condition, details=''):
        checks.append({'control': name, 'status': 'PASS' if condition else 'FAIL', 'details': details})
    check('transaction_id unique', tx.transaction_id.is_unique)
    check('execution_id unique', ex.execution_id.is_unique)
    check('waiting_id unique', waits.waiting_id.is_unique)
    check('event_id unique', quality.event_id.is_unique)
    ids = set(tx.transaction_id)
    check('all child transaction_ids valid', all(set(df.transaction_id).issubset(ids) for df in (ex, waits, quality)))
    check('transaction dates', bool((tx.opened_at <= CUTOFF).all() and
          (tx.loc[tx.final_status == 'COMPLETED', 'closed_at'].notna().all()) and
          (tx.loc[tx.final_status == 'OPEN', 'closed_at'].isna().all())))
    check('execution time consistency', bool((ex.ended_at > ex.started_at).all() and
          np.allclose((ex.ended_at-ex.started_at).dt.total_seconds()/60, ex.active_minutes)))
    check('execution not after cutoff', bool((ex.ended_at <= CUTOFF).all()))
    check('quality not after cutoff', bool((quality.detected_at <= CUTOFF).all()))
    check('waiting dates valid', bool((waits.started_at <= CUTOFF).all() and
          (waits.ended_at.isna() | (waits.ended_at > waits.started_at)).all()))
    check('valid work_type', bool(ex.work_type.isin(['NORMAL','OVERTIME']).all()))
    check('nonnegative active minutes', bool((ex.active_minutes > 0).all()))
    check('valid quality links', set(ex.related_quality_event_id.dropna().astype(int)).issubset(set(quality.event_id)))
    check('rework flag and quality link', bool((ex.is_rework.map(true_bool) == ex.related_quality_event_id.notna()).all()))
    check('valid external exclusion', all((not true_bool(r.is_excludable)) or
          (r.waiting_type in ('EXTERNAL_PARTY','CUSTOMER') and true_bool(r.reason_verified))
          for r in waits.itertuples(index=False)))

    # Aynı sanal çalışan aynı anda iki aktif işte bulunamaz.
    overlaps = []
    for key, group in ex.groupby(['team_id', 'employee_id']):
        ordered = group.sort_values('started_at')
        active = []
        for r in ordered.itertuples(index=False):
            active = [(end, eid) for end, eid in active if end > r.started_at]
            if active:
                overlaps.append((key, active[0][1], r.execution_id))
            active.append((r.ended_at, r.execution_id))
    check('employee interval overlaps', not overlaps, str(overlaps[:5]))

    # Bir işlem aynı anda aktif çalışıyor ve bekliyor olamaz.
    cross = []
    for tid, group in ex.groupby('transaction_id'):
        wgroup = waits[waits.transaction_id == tid]
        for e in group.itertuples(index=False):
            for w in wgroup.itertuples(index=False):
                wend = CUTOFF if pd.isna(w.ended_at) else min(w.ended_at, CUTOFF)
                if max(e.started_at, w.started_at) < min(e.ended_at, wend):
                    cross.append((tid, e.execution_id, w.waiting_id))
    check('active-wait overlap', not cross, str(cross[:5]))

    # Günlük normal/OT kapasite tüketimi.
    daily = ex.assign(capacity_date=ex.started_at.dt.normalize()).groupby(
        ['team_id', 'capacity_date', 'work_type'], as_index=False)['active_minutes'].sum()
    pivot = daily.pivot_table(index=['team_id','capacity_date'], columns='work_type',
                              values='active_minutes', aggfunc='sum', fill_value=0).reset_index()
    pivot.columns.name = None
    for col in ('NORMAL','OVERTIME'):
        if col not in pivot:
            pivot[col] = 0.0
    cap = capacity.merge(pivot, on=['team_id','capacity_date'], how='left')
    cap[['NORMAL','OVERTIME']] = cap[['NORMAL','OVERTIME']].fillna(0)
    cap['normal_utilization'] = cap['NORMAL'] / cap.available_minutes.replace(0,np.nan)
    cap['overtime_utilization'] = cap['OVERTIME'] / cap.overtime_capacity_minutes.replace(0,np.nan)
    check('normal capacity limits', bool((cap.NORMAL <= cap.available_minutes + 1e-8).all()))
    check('overtime capacity limits', bool((cap.OVERTIME <= cap.overtime_capacity_minutes + 1e-8).all()))
    # Mesai tipi gerçek takvim pencerelerine uymalı.
    valid_windows = True
    for r in ex.itertuples(index=False):
        if r.work_type == 'NORMAL':
            valid_windows &= any(r.started_at >= a and r.ended_at <= b for a,b in windows)
        else:
            d = r.started_at.normalize()
            day_type = cal.loc[cal.calendar_date == d.strftime('%Y-%m-%d'), 'day_type']
            if day_type.empty:
                valid_windows = False
                continue
            hour = 18 if day_type.iloc[0] == 'FULL_DAY' else 12
            valid_windows &= bool(day_type.iloc[0] in ('FULL_DAY','HALF_DAY') and
                                  r.started_at >= d+pd.Timedelta(hours=hour) and
                                  r.ended_at <= d+pd.Timedelta(hours=hour+3))
    check('work window classifications', valid_windows)

    # SLA eşlemesi açılış tarihi itibarıyla tekil olmalı.
    targets = []
    for r in tx.itertuples(index=False):
        match = sla[(sla.sla_target_id == r.sla_target_id) &
                    (sla.operation_id == r.operation_id) &
                    (sla.complexity_level == r.complexity_level) &
                    (sla.valid_from <= r.opened_at) &
                    (sla.valid_to.isna() | (sla.valid_to >= r.opened_at))]
        targets.append(float(match.iloc[0].target_minutes) if len(match)==1 else np.nan)
    tx['sla_target_minutes'] = targets
    check('SLA target mapping', bool(tx.sla_target_minutes.notna().all()))

    # Maliyet: aktif dakika üzerinden; rework maliyeti zaten toplamın içindedir.
    ex['estimated_cost_tl'] = [active_cost(r, costs) for r in ex.itertuples(index=False)]
    ex['is_rework'] = ex.is_rework.map(true_bool)
    ex['is_overtime'] = ex.work_type.eq('OVERTIME')
    sums = ex.groupby('transaction_id').agg(
        active_minutes=('active_minutes','sum'),
        overtime_minutes=('active_minutes', lambda x: x[ex.loc[x.index,'is_overtime']].sum()),
        rework_minutes=('active_minutes', lambda x: x[ex.loc[x.index,'is_rework']].sum()),
        estimated_cost_tl=('estimated_cost_tl','sum'),
        stage_execution_rows=('execution_id','size')).reset_index()
    tx = tx.merge(sums, on='transaction_id', how='left')
    for c in ['active_minutes','overtime_minutes','rework_minutes','estimated_cost_tl','stage_execution_rows']:
        tx[c] = tx[c].fillna(0)
    tx['quality_event_count'] = tx.transaction_id.map(quality.groupby('transaction_id').size()).fillna(0).astype(int)
    tx['waiting_event_count'] = tx.transaction_id.map(waits.groupby('transaction_id').size()).fillna(0).astype(int)
    tx['had_rework'] = tx.rework_minutes.gt(0)

    excluded = defaultdict(list)
    for r in waits.itertuples(index=False):
        if (r.waiting_type in ('EXTERNAL_PARTY','CUSTOMER') and
                true_bool(r.is_excludable) and true_bool(r.reason_verified)):
            excluded[r.transaction_id].append((r.started_at, CUTOFF if pd.isna(r.ended_at) else r.ended_at))
    e2e, external, operational = [], [], []
    for r in tx.itertuples(index=False):
        end = min(r.closed_at, CUTOFF) if pd.notna(r.closed_at) else CUTOFF
        gross = business_minutes(r.opened_at, end, windows)
        intervals = [(max(r.opened_at, a), min(end, b)) for a,b in excluded[r.transaction_id]
                     if max(r.opened_at, a) < min(end,b)]
        deductible = sum(business_minutes(a,b,windows) for a,b in union_intervals(intervals))
        e2e.append(gross);external.append(deductible);operational.append(max(0.0,gross-deductible))
    tx['e2e_business_minutes'] = e2e
    tx['verified_external_business_minutes'] = external
    tx['operational_business_minutes'] = operational
    tx['e2e_sla_breached'] = tx.e2e_business_minutes > tx.sla_target_minutes
    tx['operational_sla_breached'] = tx.operational_business_minutes > tx.sla_target_minutes
    tx['operational_target_utilization'] = tx.operational_business_minutes / tx.sla_target_minutes
    tx['open_risk_status'] = np.where(tx.final_status != 'OPEN','NOT_APPLICABLE',
                           np.where(tx.operational_target_utilization > 1,'OVERDUE',
                           np.where(tx.operational_target_utilization >= 0.8,'AT_RISK','NORMAL')))
    check('operational SLA nonnegative and <= e2e', bool((tx.operational_business_minutes >= 0).all() and
          (tx.operational_business_minutes <= tx.e2e_business_minutes + 1e-8).all()))
    check('SLA subtraction identity', bool(np.allclose(tx.e2e_business_minutes - tx.verified_external_business_minutes,
                                                     tx.operational_business_minutes)))
    completed = tx[tx.final_status == 'COMPLETED']
    overview = pd.DataFrame([{
        'report_cutoff': CUTOFF, 'total_transactions':len(tx),
        'completed_transactions':len(completed), 'open_transactions':int((tx.final_status=='OPEN').sum()),
        'cancelled_transactions':int((tx.final_status=='CANCELLED').sum()),
        'completed_e2e_sla_breach_count':int(completed.e2e_sla_breached.sum()),
        'completed_operational_sla_breach_count':int(completed.operational_sla_breached.sum()),
        'completed_e2e_sla_compliance_rate':float((~completed.e2e_sla_breached).mean()) if len(completed) else np.nan,
        'completed_operational_sla_compliance_rate':float((~completed.operational_sla_breached).mean()) if len(completed) else np.nan,
        'total_active_minutes':float(tx.active_minutes.sum()),
        'total_overtime_minutes':float(tx.overtime_minutes.sum()),
        'total_rework_minutes':float(tx.rework_minutes.sum()),
        'total_estimated_cost_tl':float(tx.estimated_cost_tl.sum()),
        'completed_cost_per_transaction_tl':float(completed.estimated_cost_tl.sum()/len(completed)) if len(completed) else np.nan,
        'quality_events':len(quality), 'waiting_intervals':len(waits),
        'first_time_right_rate':float((~completed.had_rework).mean()) if len(completed) else np.nan,
        'overtime_workload_share':float(tx.overtime_minutes.sum()/tx.active_minutes.sum()) if tx.active_minutes.sum() else np.nan
    }])
    operations = tx.groupby('operation_id').agg(
        transactions=('transaction_id','size'),completed=('final_status',lambda s:(s=='COMPLETED').sum()),
        e2e_breaches=('e2e_sla_breached',lambda s: int((s & tx.loc[s.index,'final_status'].eq('COMPLETED')).sum())),
        operational_breaches=('operational_sla_breached',lambda s: int((s & tx.loc[s.index,'final_status'].eq('COMPLETED')).sum())),
        active_minutes=('active_minutes','sum'),overtime_minutes=('overtime_minutes','sum'),
        rework_minutes=('rework_minutes','sum'),estimated_cost_tl=('estimated_cost_tl','sum')).reset_index()
    report = pd.DataFrame(checks)
    out.mkdir(parents=True,exist_ok=True)
    tx.to_csv(out/'transaction_kpis.csv',index=False,encoding='utf-8-sig')
    ex.to_csv(out/'execution_costs.csv',index=False,encoding='utf-8-sig')
    cap.to_csv(out/'capacity_utilization.csv',index=False,encoding='utf-8-sig')
    operations.to_csv(out/'operation_kpis.csv',index=False,encoding='utf-8-sig')
    overview.to_csv(out/'pilot_overview.csv',index=False,encoding='utf-8-sig')
    report.to_csv(out/'validation_report.csv',index=False,encoding='utf-8-sig')
    print('VERIQORA | 96. ADIM - KPI & DOGRULAMA')
    print(f'Islem: {len(tx)} | Tamamlanan: {len(completed)} | Acik: {(tx.final_status=="OPEN").sum()}')
    print(f'Operasyonel SLA ihlali (tamamlanan): {int(completed.operational_sla_breached.sum())}')
    print(f'Tahmini toplam maliyet: {tx.estimated_cost_tl.sum():,.2f} TL')
    print(f'Kontroller: {(report.status=="PASS").sum()} PASS / {(report.status=="FAIL").sum()} FAIL')
    if (report.status=='FAIL').any():
        print(report[report.status=='FAIL'].to_string(index=False))
    print(f'CSV ciktilari: {out}')
    return report, overview


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    report, _ = run(args.project_root)
    if (report.status=='FAIL').any():
        raise SystemExit('Veri dogrulama hatasi: validation_report.csv dosyasini inceleyin.')
