"""Veriqora Bank | 300 işlemli olay tabanlı pilot süreç simülasyonu.
Çalıştırma: python src/run_pilot.py
Bağımsızdır: eski simulate_processes.py test rezervasyonlarını kullanmaz.
"""
from __future__ import annotations
import heapq
from collections import defaultdict
from itertools import count
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'pilot'
OUT = DATA / 'simulated'
SEED = 2025
CUTOFF = pd.Timestamp('2025-12-31 18:00:00')


def load():
    names = ['transactions','transaction_attributes','selected_stages','team_capacity','business_calendar','sla_targets','cost_parameters']
    d = {name:pd.read_csv(DATA / f'{name}.csv') for name in names}
    assert len(d['transactions']) == 300
    assert len(d['selected_stages']) == 1375
    for name in ['transactions','transaction_attributes']:
        assert d[name]['transaction_id'].is_unique
    assert d['team_capacity'][['team_id','capacity_date']].duplicated().sum() == 0
    return d


def simulate(d):
    rng = np.random.default_rng(SEED)
    cal = d['business_calendar'].set_index('calendar_date').to_dict('index')
    cap = {(int(r.team_id),str(r.capacity_date)):r for r in d['team_capacity'].itertuples(index=False)}
    tx = d['transactions'].set_index('transaction_id')
    attrs = d['transaction_attributes'].set_index('transaction_id')
    stages = {int(k):g.sort_values('stage_order').to_dict('records') for k,g in d['selected_stages'].groupby('transaction_id')}
    queue = []
    seq = count()
    # Bir çalışan aynı anda bir iş yapabilir; her ekip-gün için çalışma bitişleri.
    employees = {}
    used = defaultdict(int)
    execution_rows, wait_rows, quality_rows = [], [], []
    completion = {}
    previous_employee = {}
    execution_id = count(1)
    waiting_id = count(1)
    event_id = count(1)
    stages_finished = defaultdict(int)

    def push(t, typ, tid, index, visit=1, root=None):
        heapq.heappush(queue,(pd.Timestamp(t),next(seq),typ,int(tid),int(index),int(visit),root))

    def windows(day, team):
        date = day.strftime('%Y-%m-%d')
        info = cal.get(date)
        if info is None:
            raise ValueError(f'İş takvimi dışında: {date}')
        if info['day_type'] in ('HOLIDAY','WEEKEND'):
            return []
        start = day.normalize()
        result = [(start+pd.Timedelta(hours=9),start+pd.Timedelta(hours=12),'NORMAL')]
        if info['day_type']=='FULL_DAY':
            result.append((start+pd.Timedelta(hours=13),start+pd.Timedelta(hours=18),'NORMAL'))
        capacity = cap.get((team,date))
        if capacity and int(capacity.overtime_capacity_minutes)>0:
            if info['day_type']=='FULL_DAY':
                result.append((start+pd.Timedelta(hours=18),start+pd.Timedelta(hours=21),'OVERTIME'))
            elif info['day_type']=='HALF_DAY':
                result.append((start+pd.Timedelta(hours=12),start+pd.Timedelta(hours=15),'OVERTIME'))
        return result

    def allocate(team, ready, duration, preferred=None):
        """Kronolojik olay sırasında çalışma parçalarını rezerve eder.
        Günlük kişi sayısı, pencere ve ekip kapasitesi korunur.
        """
        remaining = int(duration)
        cursor = pd.Timestamp(ready)
        pieces = []
        last_employee = preferred
        while remaining:
            if cursor > pd.Timestamp('2026-12-31 23:59:59'):
                raise ValueError('Planlama takvim sınırını aştı')
            day = cursor.normalize()
            date = day.strftime('%Y-%m-%d')
            capacity = cap.get((team,date))
            if capacity is None:
                raise ValueError(f'Ekip kapasitesi eksik: {team}, {date}')
            n = int(capacity.employee_count)
            if n:
                key = (team,date)
                if key not in employees:
                    employees[key] = {i:day for i in range(1,n+1)}
                for begin,end,kind in windows(day,team):
                    if end<=cursor:
                        continue
                    limit = int(capacity.available_minutes if kind=='NORMAL' else capacity.overtime_capacity_minutes)
                    budget = limit-used[(team,date,kind)]
                    if budget<=0:
                        continue
                    candidates=[]
                    for emp,free_at in employees[key].items():
                        start=max(cursor,begin,free_at)
                        if start<end:
                            candidates.append((start,0 if emp==last_employee else 1,emp))
                    if not candidates:
                        continue
                    start,_,emp=min(candidates)
                    minutes=min(remaining,int((end-start).total_seconds()//60),budget)
                    if minutes<=0:
                        continue
                    finish=start+pd.Timedelta(minutes=minutes)
                    assert employees[key][emp]<=start
                    employees[key][emp]=finish
                    used[(team,date,kind)]+=minutes
                    pieces.append((start,finish,emp,kind))
                    remaining-=minutes
                    cursor=finish
                    last_employee=emp
                    break
                else:
                    cursor=day+pd.Timedelta(days=1)
                    continue
            else:
                cursor=day+pd.Timedelta(days=1)
        return pieces

    for tid,r in tx.iterrows():
        push(r.opened_at,'STAGE_READY',tid,0)

    while queue:
        time,_,kind,tid,index,visit,root=heapq.heappop(queue)
        if kind=='STAGE_DONE':
            stages_finished[tid]+=1
            if index+1<len(stages[tid]):
                push(time,'STAGE_READY',tid,index+1)
            else:
                completion[tid]=time
            continue
        if kind!='STAGE_READY':
            raise AssertionError(kind)
        stage=stages[tid][index]
        team=int(stage['team_id'])
        stage_id=int(stage['stage_id'])
        a=attrs.loc[tid]
        complexity=str(tx.loc[tid,'complexity_level'])
        multiplier={'LOW':1,'MEDIUM':1.6,'HIGH':2.4}[complexity]
        # Süreler KPI hedefinden türetilmez; operasyon, karmaşıklık ve özelliklere bağlıdır.
        base={1:12,2:17,3:21,4:26,5:29,6:18}[int(tx.loc[tid,'operation_id'])]
        manual = 1.25 if bool(a.requires_manual_review) else 1
        approval = 1.12 if bool(a.requires_approval) else 1
        duration=max(5,int(round(base*multiplier*manual*approval*rng.lognormal(0,0.22))))
        # Gerçek dış taraf beklemesi yalnızca bu özelliği taşıyan işlemlerde oluşabilir.
        if index==0 and bool(a.requires_external_party) and rng.random()<0.45:
            hours=int(rng.integers(2,24))
            finish_wait=time+pd.Timedelta(hours=hours)
            wait_rows.append(dict(waiting_id=next(waiting_id),transaction_id=tid,stage_id=stage_id,
                                  visit_number=visit,waiting_type='EXTERNAL_PARTY',waiting_reason='THIRD_PARTY_RESPONSE',
                                  started_at=time,ended_at=finish_wait,is_excludable=True,reason_verified=True))
            time=finish_wait
        pieces=allocate(team,time,duration,previous_employee.get(tid))
        assert pieces
        first_start=pieces[0][0]
        if first_start>time:
            wait_rows.append(dict(waiting_id=next(waiting_id),transaction_id=tid,stage_id=stage_id,
                                  visit_number=visit,waiting_type='INTERNAL_QUEUE',waiting_reason='CAPACITY_OR_CALENDAR',
                                  started_at=time,ended_at=first_start,is_excludable=False,reason_verified=True))
        for start,end,emp,work_type in pieces:
            execution_rows.append(dict(execution_id=next(execution_id),transaction_id=tid,stage_id=stage_id,
                    team_id=team,visit_number=visit,started_at=start,ended_at=end,
                    active_minutes=int((end-start).total_seconds()/60),execution_status='COMPLETED',
                    is_rework=visit>1,related_quality_event_id=root,work_type=work_type,
                    employee_id=emp))
        previous_employee[tid]=pieces[-1][2]
        done=pieces[-1][1]
        # Sınırlı, tekrarlanabilir kalite olayı; bir kez yeniden işleme döner.
        risk=0.015+({'LOW':0,'MEDIUM':0.012,'HIGH':0.025}[complexity])+(0.012 if bool(a.requires_manual_review) else 0)
        if visit==1 and rng.random()<risk:
            eid=next(event_id)
            quality_rows.append(dict(event_id=eid,transaction_id=tid,stage_id=stage_id,visit_number=visit,
                    event_type='RETURN',error_category='DOCUMENT_OR_VALIDATION',detected_at=done,
                    resolved_at=None,requires_rework=True,root_event_id=None))
            push(done,'STAGE_READY',tid,index,2,eid)
        else:
            if root is not None:
                for q in reversed(quality_rows):
                    if q['event_id']==root:
                        q['resolved_at']=done
                        break
            push(done,'STAGE_DONE',tid,index,visit)

    executions=pd.DataFrame(execution_rows)
    waits=pd.DataFrame(wait_rows,columns=['waiting_id','transaction_id','stage_id','visit_number','waiting_type','waiting_reason','started_at','ended_at','is_excludable','reason_verified'])
    quality=pd.DataFrame(quality_rows,columns=['event_id','transaction_id','stage_id','visit_number','event_type','error_category','detected_at','resolved_at','requires_rework','root_event_id'])
    result=d['transactions'].copy()
    result['closed_at']=result['transaction_id'].map(completion)
    result['final_status']=np.where(result['closed_at']<=CUTOFF,'COMPLETED','OPEN')
    result.loc[result['final_status']=='OPEN','closed_at']=pd.NaT
    # Rapor kesitinden sonraki çalışma parçalarını çıktıdan çıkar; açık aralıkları kesit anında durdur.
    executions=executions.loc[executions.started_at<CUTOFF].copy()
    mask=executions.ended_at>CUTOFF
    executions.loc[mask,'ended_at']=pd.NaT
    executions.loc[mask,'active_minutes']=pd.NA
    executions.loc[mask,'execution_status']='IN_PROGRESS'
    waits=waits.loc[waits.started_at<CUTOFF].copy()
    waits.loc[waits.ended_at>CUTOFF,'ended_at']=pd.NaT
    quality=quality.loc[quality.detected_at<CUTOFF].copy()
    quality.loc[quality.resolved_at>CUTOFF,'resolved_at']=pd.NaT
    return result,executions,waits,quality,used


def validate(d,tx,ex,w,q,used):
    assert len(tx)==300 and tx.transaction_id.is_unique
    assert ex.execution_id.is_unique
    assert ex.transaction_id.isin(tx.transaction_id).all()
    assert w.transaction_id.isin(tx.transaction_id).all()
    assert q.transaction_id.isin(tx.transaction_id).all()
    assert (ex['started_at']>=ex.transaction_id.map(d['transactions'].set_index('transaction_id')['opened_at'].pipe(pd.to_datetime))).all()
    completed=ex[ex.execution_status=='COMPLETED']
    assert (pd.to_datetime(completed.ended_at)>pd.to_datetime(completed.started_at)).all()
    assert (completed.active_minutes>0).all()
    assert not ex[['transaction_id','stage_id','visit_number','started_at']].duplicated().any()
    assert not w[['waiting_id']].duplicated().any()
    assert not q[['event_id']].duplicated().any()
    # Çalışan bazında çakışma kontrolü
    for _,g in completed.sort_values('started_at').groupby(['team_id','employee_id']):
        # Farklı günler dahil tüm aralıklar kontrol edilir.
        ends=pd.to_datetime(g.ended_at).to_numpy()
        starts=pd.to_datetime(g.started_at).to_numpy()
        assert all(starts[i]>=ends[i-1] for i in range(1,len(g)))
    caps=d['team_capacity'].set_index(['team_id','capacity_date'])
    for (team,date,kind),minutes in used.items():
        row=caps.loc[(team,date)]
        limit=row.available_minutes if kind=='NORMAL' else row.overtime_capacity_minutes
        assert minutes<=limit
    assert tx.final_status.isin(['OPEN','COMPLETED']).all()
    assert tx.loc[tx.final_status=='COMPLETED','closed_at'].notna().all()
    assert tx.loc[tx.final_status=='OPEN','closed_at'].isna().all()
    assert set(tx.loc[tx.final_status=='COMPLETED','transaction_id'])==set(tx.transaction_id)-set(tx.loc[tx.final_status=='OPEN','transaction_id'])


def main():
    d=load()
    tx,ex,w,q,used=simulate(d)
    validate(d,tx,ex,w,q,used)
    OUT.mkdir(parents=True,exist_ok=True)
    for name,frame in [('transactions',tx),('stage_executions',ex),('waiting_intervals',w),('quality_events',q)]:
        frame.to_csv(OUT/f'{name}.csv',index=False,encoding='utf-8-sig')
    print('VERIQORA | PILOT SIMÜLASYON')
    print(f'İşlem: {len(tx)} | Tamamlanan: {(tx.final_status=="COMPLETED").sum()} | Açık: {(tx.final_status=="OPEN").sum()}')
    print(f'Aktif çalışma aralığı: {len(ex)} | Bekleme: {len(w)} | Kalite olayı: {len(q)}')
    print(f'Çıktı: {OUT}')
    print('Temel bütünlük ve kapasite kontrolleri: BAŞARILI')

if __name__=='__main__':
    main()
