"""Veriqora Bank: non-destructive pilot SLA scenario analysis.
Run from repository root: python src/analyze_sla_scenarios.py
Requires data/pilot/analytics/transaction_kpis.csv and data/pilot/sla_targets.csv.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / 'data' / 'pilot'
OUT = PILOT / 'analytics' / 'sla_scenarios'

# Explicit counterfactual targets: NOT approved operational SLA changes.
SCENARIOS = {
    'BASELINE': {},
    'CUSTOMER_UPDATE_LOW_90': {(2, 'LOW'): 90},
    'CUSTOMER_UPDATE_LOW_120': {(2, 'LOW'): 120},
}

def main():
    tx = pd.read_csv(PILOT / 'analytics' / 'transaction_kpis.csv', encoding='utf-8-sig')
    targets = pd.read_csv(PILOT / 'sla_targets.csv', encoding='utf-8-sig')
    needed = {'transaction_id','operation_id','complexity_level','final_status','sla_target_minutes','operational_business_minutes','e2e_business_minutes'}
    missing = needed - set(tx.columns)
    if missing: raise ValueError(f'Missing transaction KPI columns: {sorted(missing)}')
    if tx.transaction_id.duplicated().any(): raise ValueError('Duplicate transaction_id')
    if targets.duplicated(['operation_id','complexity_level']).any():
        raise ValueError('Ambiguous SLA target records: this script expects one target per operation and complexity')
    tx = tx.loc[tx.final_status.eq('COMPLETED')].copy()
    if tx.empty: raise ValueError('No completed transactions')
    if tx[['sla_target_minutes','operational_business_minutes','e2e_business_minutes']].isna().any().any():
        raise ValueError('Completed transaction has missing duration/target')
    rows=[]; details=[]
    for name, changes in SCENARIOS.items():
        frame=tx.copy()
        frame['scenario']=name
        frame['scenario_target_minutes']=frame['sla_target_minutes'].astype(float)
        for (op, complexity), value in changes.items():
            mask=frame.operation_id.eq(op) & frame.complexity_level.eq(complexity)
            frame.loc[mask,'scenario_target_minutes']=value
        frame['scenario_operational_breach']=frame.operational_business_minutes > frame.scenario_target_minutes
        frame['scenario_e2e_breach']=frame.e2e_business_minutes > frame.scenario_target_minutes
        details.append(frame[['scenario','transaction_id','operation_id','complexity_level','sla_target_minutes','scenario_target_minutes','operational_business_minutes','e2e_business_minutes','scenario_operational_breach','scenario_e2e_breach']])
        for (op,level),group in frame.groupby(['operation_id','complexity_level']):
            rows.append({'scenario':name,'operation_id':op,'complexity_level':level,'completed':len(group),'original_target_minutes':group.sla_target_minutes.iloc[0],'scenario_target_minutes':group.scenario_target_minutes.iloc[0], 'median_operational_minutes':round(group.operational_business_minutes.median(),2),'p90_operational_minutes':round(group.operational_business_minutes.quantile(.9),2),'operational_breaches':int(group.scenario_operational_breach.sum()),'operational_breach_rate_pct':round(group.scenario_operational_breach.mean()*100,2),'e2e_breaches':int(group.scenario_e2e_breach.sum())})
    details=pd.concat(details,ignore_index=True)
    result=pd.DataFrame(rows)
    summary=(details.groupby('scenario',sort=False).agg(completed=('transaction_id','size'),operational_breaches=('scenario_operational_breach','sum'),e2e_breaches=('scenario_e2e_breach','sum')).reset_index())
    summary['operational_compliance_pct']=((1-summary.operational_breaches/summary.completed)*100).round(2)
    summary['e2e_compliance_pct']=((1-summary.e2e_breaches/summary.completed)*100).round(2)
    OUT.mkdir(parents=True,exist_ok=True)
    result.to_csv(OUT/'scenario_by_operation.csv',index=False,encoding='utf-8-sig')
    summary.to_csv(OUT/'scenario_summary.csv',index=False,encoding='utf-8-sig')
    details.to_csv(OUT/'scenario_transaction_detail.csv',index=False,encoding='utf-8-sig')
    print('\nSLA senaryo karşılaştırması (yalnızca tamamlanan işlemler):')
    print(summary.to_string(index=False))
    print('\nÇıktı klasörü:',OUT)
    print('Not: Bu çalışma mevcut SLA hedeflerini ve kaynak CSV dosyalarını değiştirmez.')

if __name__=='__main__': main()
