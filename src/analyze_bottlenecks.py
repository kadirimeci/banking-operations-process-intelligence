"""Veriqora Bank | aşama bazlı darboğaz ve duyarlılık analizi.
Kullanım: proje kökünden `python src/analyze_bottlenecks.py`
Kaynak CSV'ler değiştirilmez. Yalnızca data/pilot/analytics/bottleneck_analysis/ üretilir.
"""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / 'data' / 'pilot'
SIM = PILOT / 'simulated'
ANA = PILOT / 'analytics'
OUT = ANA / 'bottleneck_analysis'
TARGET_OPERATION = 2


def load(path):
    if not path.is_file():
        raise FileNotFoundError(f'Eksik veri dosyası: {path}')
    return pd.read_csv(path)


def main():
    executions = load(SIM / 'stage_executions.csv')
    waits = load(SIM / 'waiting_intervals.csv')
    quality = load(SIM / 'quality_events.csv')
    kpis = load(ANA / 'transaction_kpis.csv')
    stages = load(PILOT / 'process_stages.csv')
    operations = load(PILOT / 'operations.csv')

    assert executions.execution_id.is_unique, 'execution_id tekrarlanıyor'
    assert kpis.transaction_id.is_unique, 'transaction_id tekrarlanıyor'
    assert executions.stage_id.isin(stages.stage_id).all(), 'Tanımsız aşama var'
    assert executions.transaction_id.isin(kpis.transaction_id).all(), 'Tanımsız işlem var'

    # Her çalışma satırı bir aktif zaman aralığıdır; aynı aşamanın birden fazla
    # parçası ve yeniden işleme ziyaretleri toplanır.
    x = executions.merge(stages[['stage_id','operation_id','stage_order','stage_name']],
                         on='stage_id', how='left', validate='many_to_one')
    x['active_minutes'] = pd.to_numeric(x['active_minutes'], errors='raise')
    x['is_rework'] = x['is_rework'].astype(bool)
    x['rework_active_minutes'] = x.active_minutes.where(x.is_rework, 0)
    x['overtime_active_minutes'] = x.active_minutes.where(x.work_type.eq('OVERTIME'), 0)

    stage_by_tx = x.groupby(['operation_id','transaction_id','stage_id','stage_order','stage_name'], as_index=False).agg(
        active_minutes=('active_minutes','sum'),
        rework_minutes=('rework_active_minutes','sum'),
        overtime_minutes=('overtime_active_minutes','sum'),
        execution_rows=('execution_id','count'),
        visits=('visit_number','nunique'))

    stage_summary = stage_by_tx.groupby(['operation_id','stage_id','stage_order','stage_name'], as_index=False).agg(
        transactions=('transaction_id','nunique'),
        total_active_minutes=('active_minutes','sum'),
        median_active_minutes_per_transaction=('active_minutes','median'),
        mean_active_minutes_per_transaction=('active_minutes','mean'),
        total_rework_minutes=('rework_minutes','sum'),
        total_overtime_minutes=('overtime_minutes','sum'),
        total_execution_rows=('execution_rows','sum'))
    stage_summary['share_of_operation_active_pct'] = (100 * stage_summary.total_active_minutes /
        stage_summary.groupby('operation_id').total_active_minutes.transform('sum')).round(2)
    stage_summary = stage_summary.sort_values(['operation_id','stage_order'])

    # Bekleme süresi: takvim dakikasıdır, iş dakikası değildir.
    # SLA'daki iş dakikası hesabıyla doğrudan toplanmamalıdır.
    waits['started_at'] = pd.to_datetime(waits.started_at)
    waits['ended_at'] = pd.to_datetime(waits.ended_at)
    # Raporlama tarihinde hâlâ açık beklemeler, kesit anına kadar ölçülür.
    waits['is_open_at_cutoff'] = waits['ended_at'].isna()
    waits['ended_at'] = waits['ended_at'].fillna(pd.Timestamp('2025-12-31 18:00:00'))
    waits['calendar_wait_minutes'] = (waits.ended_at - waits.started_at).dt.total_seconds()/60
    if (waits.calendar_wait_minutes < 0).any():
        raise ValueError('Negatif bekleme aralığı bulundu')
    w = waits.merge(stages[['stage_id','operation_id','stage_order','stage_name']],
                    on='stage_id', how='left', validate='many_to_one')
    wait_summary = w.groupby(['operation_id','stage_id','stage_order','stage_name','waiting_type'],
                              dropna=False, as_index=False).agg(
        wait_events=('waiting_id','count'),
        affected_transactions=('transaction_id','nunique'),
        total_calendar_wait_minutes=('calendar_wait_minutes','sum'),
        median_calendar_wait_minutes=('calendar_wait_minutes','median'))

    q = quality.merge(stages[['stage_id','operation_id','stage_order','stage_name']],
                      on='stage_id', how='left', validate='many_to_one')
    quality_summary = q.groupby(['operation_id','stage_id','stage_order','stage_name','event_type'],
                                 dropna=False, as_index=False).agg(
        quality_events=('event_id','count'), affected_transactions=('transaction_id','nunique'))

    # İşlem seviyesinde: aktif süre ile operasyonel SLA iş dakikaları
    # arasındaki farkı ayrıca raporla. Bekleme zamanını aktif çalışma sayma.
    t = kpis[kpis.operation_id.eq(TARGET_OPERATION)].copy()
    tx_stage = stage_by_tx[stage_by_tx.operation_id.eq(TARGET_OPERATION)]
    stage_rank = stage_summary[stage_summary.operation_id.eq(TARGET_OPERATION)].sort_values(
        'total_active_minutes', ascending=False)
    if stage_rank.empty:
        raise ValueError('Hedef operasyonda aşama kaydı yok')
    bottleneck = stage_rank.iloc[0]
    target_stage_id = bottleneck.stage_id
    reduction = tx_stage[tx_stage.stage_id.eq(target_stage_id)][['transaction_id','active_minutes']].copy()
    reduction = reduction.rename(columns={'active_minutes':'bottleneck_stage_active_minutes'})
    t = t.merge(reduction, on='transaction_id', how='left', validate='one_to_one')
    t['bottleneck_stage_active_minutes'] = t.bottleneck_stage_active_minutes.fillna(0)

    completed = t[t.final_status.eq('COMPLETED')].copy()
    if completed.empty:
        raise ValueError('Hedef operasyonda tamamlanan işlem yok')
    scenarios = []
    for pct in [0, 10, 15, 20]:
        saved = completed.bottleneck_stage_active_minutes * pct / 100
        hypothetical = (completed.operational_business_minutes - saved).clip(lower=0)
        breaches = hypothetical.gt(completed.sla_target_minutes)
        scenarios.append({
            'scenario': f'STAGE_ACTIVE_MINUS_{pct}PCT',
            'target_operation_id': TARGET_OPERATION,
            'target_stage_id': target_stage_id,
            'reduction_pct': pct,
            'completed_transactions': len(completed),
            'hypothetical_total_saved_active_minutes': round(float(saved.sum()), 2),
            'hypothetical_operational_breaches': int(breaches.sum()),
            'hypothetical_operational_compliance_pct': round(100 * (1 - breaches.mean()), 2),
        })
    scenario_df = pd.DataFrame(scenarios)

    # Duyarlılık analizi, yeniden planlama / kuyruk etkilerini modellemez.
    # Diğer ekipleri, işlem sırasını veya uçtan uca süreleri değiştirmez.
    checks = [
        ('execution_stage_links', bool(executions.stage_id.isin(stages.stage_id).all())),
        ('execution_transaction_links', bool(executions.transaction_id.isin(kpis.transaction_id).all())),
        ('nonnegative_active_minutes', bool(x.active_minutes.ge(0).all())),
        ('nonnegative_wait_intervals', bool(waits.calendar_wait_minutes.ge(0).all())),
        ('target_completed_count', bool(len(completed) > 0)),
        ('baseline_matches_transaction_kpis', bool(
            scenario_df.iloc[0].hypothetical_operational_breaches ==
            int(completed.operational_sla_breached.sum()))),
    ]
    check_df = pd.DataFrame(checks, columns=['control','passed'])
    if not check_df.passed.all():
        raise AssertionError(check_df.to_string(index=False))

    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in [
        ('stage_by_transaction.csv',stage_by_tx),
        ('stage_summary.csv',stage_summary),
        ('waiting_by_stage.csv',wait_summary),
        ('quality_by_stage.csv',quality_summary),
        ('improvement_scenarios.csv',scenario_df),
        ('validation_report.csv',check_df),
    ]:
        df.to_csv(OUT/name, index=False, encoding='utf-8-sig')

    op_name = operations.loc[operations.operation_id.eq(TARGET_OPERATION),'operation_name'].iloc[0]
    print('VERIQORA | 98. ADIM - DARBOGAZ ANALIZI')
    print(f'Operasyon: {op_name} (ID {TARGET_OPERATION})')
    print(f'En yuksek toplam aktif sureli asama: {bottleneck.stage_name} (ID {target_stage_id})')
    print(f'Toplam aktif sure: {bottleneck.total_active_minutes:.1f} dk')
    print('\nVarsayimsal iyilestirme senaryolari (yalnizca hedef operasyon):')
    print(scenario_df[['scenario','hypothetical_operational_breaches',
                       'hypothetical_operational_compliance_pct']].to_string(index=False))
    print(f'Kontroller: {int(check_df.passed.sum())} PASS / {int((~check_df.passed).sum())} FAIL')
    print(f'CSV ciktilari: {OUT}')
    print('NOT: Senaryolar kuyruk ve yeniden planlama etkilerini kapsamaz.')

if __name__ == '__main__':
    main()
