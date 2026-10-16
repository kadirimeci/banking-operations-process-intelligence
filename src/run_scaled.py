"""Veriqora Bank - chronological, capacity-limited discrete event simulation.

Usage: python src/run_scaled.py --input data/final_50000 --output data/output_test/simulated
Does not write to data/pilot. Ready jobs only acquire capacity at the actual work time.
"""
from __future__ import annotations
import argparse
import heapq
from collections import defaultdict, deque
from itertools import count
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = pd.Timestamp('2025-12-31 18:00:00')
SEED = 2025


def load(data_dir, reference_dir):
    names = ['transactions', 'transaction_attributes', 'selected_stages', 'team_capacity',
             'business_calendar', 'sla_targets', 'cost_parameters']
    d = {n: pd.read_csv((data_dir if n in names[:3] else reference_dir) / (n + '.csv')) for n in names}
    tx, attrs, sel = d['transactions'], d['transaction_attributes'], d['selected_stages']
    if tx.empty or not tx.transaction_id.is_unique or not attrs.transaction_id.is_unique:
        raise ValueError('Missing transactions or duplicate transaction IDs')
    if set(tx.transaction_id) != set(attrs.transaction_id):
        raise ValueError('Transaction attributes do not match transactions')
    if set(sel.transaction_id) != set(tx.transaction_id) or sel.duplicated(['transaction_id','stage_id']).any():
        raise ValueError('Missing or duplicate selected stages')
    if d['team_capacity'].duplicated(['team_id', 'capacity_date']).any():
        raise ValueError('Duplicate team/day capacity')
    return d


def simulate(d):
    rng = np.random.default_rng(SEED)
    calendar = d['business_calendar'].set_index('calendar_date').to_dict('index')
    capacity = {(int(r.team_id), str(r.capacity_date)): r for r in d['team_capacity'].itertuples(index=False)}
    tx = d['transactions'].set_index('transaction_id')
    attrs = d['transaction_attributes'].set_index('transaction_id')
    stages = {int(k): g.sort_values('stage_order').to_dict('records')
              for k, g in d['selected_stages'].groupby('transaction_id')}
    events = []
    serial = count()
    job_id = count(1)
    execution_id = count(1)
    waiting_id = count(1)
    quality_id = count(1)
    jobs = {}
    pending = defaultdict(deque)
    # Busy workers are tracked for their whole team, across dates. Worker ID is stable.
    busy = defaultdict(dict)  # team -> employee_id -> job_id
    used = defaultdict(int)   # team, date, NORMAL/OVERTIME -> reserved minutes
    wake_scheduled = {}       # team -> earliest pending wake timestamp
    ex_rows, wait_rows, quality_rows = [], [], []
    completion = {}
    prior_employee = {}
    quality_lookup = {}
    stats = {'dispatches': 0, 'wake_events': 0}

    def emit(when, kind, *args):
        heapq.heappush(events, (pd.Timestamp(when), next(serial), kind, args))

    def windows(day, team):
        date = day.strftime('%Y-%m-%d')
        c = calendar.get(date)
        if c is None:
            raise ValueError(f'Business calendar missing: {date}')
        if c['day_type'] in ('HOLIDAY', 'WEEKEND'):
            return []
        row = capacity.get((team, date))
        if row is None:
            raise ValueError(f'Team capacity missing: {team} {date}')
        start = day.normalize()
        result = [(start + pd.Timedelta(hours=9), start + pd.Timedelta(hours=12), 'NORMAL')]
        if c['day_type'] == 'FULL_DAY':
            result.append((start + pd.Timedelta(hours=13), start + pd.Timedelta(hours=18), 'NORMAL'))
        if int(row.overtime_capacity_minutes) > 0:
            if c['day_type'] == 'FULL_DAY':
                result.append((start + pd.Timedelta(hours=18), start + pd.Timedelta(hours=21), 'OVERTIME'))
            elif c['day_type'] == 'HALF_DAY':
                result.append((start + pd.Timedelta(hours=12), start + pd.Timedelta(hours=15), 'OVERTIME'))
        return result

    def available_slot(team, when):
        """Current window only; never reserves a future interval."""
        day = when.normalize()
        row = capacity.get((team, day.strftime('%Y-%m-%d')))
        if row is None:
            raise ValueError(f'Team capacity missing: {team}, {day.date()}')
        if int(row.employee_count) <= 0:
            return None
        for start, end, kind in windows(day, team):
            if start <= when < end:
                limit = int(row.available_minutes if kind == 'NORMAL' else row.overtime_capacity_minutes)
                budget = limit - used[(team, day.strftime('%Y-%m-%d'), kind)]
                if budget > 0:
                    return end, kind, budget, int(row.employee_count)
        return None

    def next_window(team, after):
        """Earliest later working window with a positive remaining budget."""
        cursor = pd.Timestamp(after)
        while cursor < CUTOFF:
            day = cursor.normalize()
            date = day.strftime('%Y-%m-%d')
            row = capacity.get((team, date))
            if row is None:
                raise ValueError(f'Team capacity missing before reporting cutoff: {team}, {date}')
            if int(row.employee_count) == 0:
                cursor = day + pd.Timedelta(days=1)
                continue
            for start, end, kind in windows(day, team):
                if end <= cursor:
                    continue
                limit = int(row.available_minutes if kind == 'NORMAL' else row.overtime_capacity_minutes)
                if used[(team, date, kind)] >= limit:
                    continue
                candidate = max(start, cursor)
                if candidate < min(end, CUTOFF):
                    return candidate
            cursor = day + pd.Timedelta(days=1)
        return None  # No work window before reporting cutoff

    def wake(team, when):
        if when is None or pd.Timestamp(when) >= CUTOFF:
            return
        old = wake_scheduled.get(team)
        if old is None or when < old:
            wake_scheduled[team] = when
            emit(when, 'WAKE', team)

    def start_job(tid, stage_index, visit, root, ready):
        stage = stages[tid][stage_index]
        a = attrs.loc[tid]
        complexity = str(tx.loc[tid, 'complexity_level'])
        mult = {'LOW': 1, 'MEDIUM': 1.6, 'HIGH': 2.4}[complexity]
        base = {1: 12, 2: 17, 3: 21, 4: 26, 5: 29, 6: 18}[int(tx.loc[tid, 'operation_id'])]
        manual = 1.25 if bool(a.requires_manual_review) else 1
        approval = 1.12 if bool(a.requires_approval) else 1
        duration = max(5, int(round(base * mult * manual * approval * rng.lognormal(0, 0.22))))
        if stage_index == 0 and visit == 1 and bool(a.requires_external_party) and rng.random() < .45:
            finish = ready + pd.Timedelta(hours=int(rng.integers(2, 24)))
            wait_rows.append(dict(waiting_id=next(waiting_id), transaction_id=tid,
                stage_id=int(stage['stage_id']), visit_number=visit, waiting_type='EXTERNAL_PARTY',
                waiting_reason='THIRD_PARTY_RESPONSE', started_at=ready, ended_at=finish,
                is_excludable=True, reason_verified=True))
            emit(finish, 'JOB_READY', tid, stage_index, visit, root, duration)
        else:
            emit(ready, 'JOB_READY', tid, stage_index, visit, root, duration)

    def finish_stage(job, time):
        tid, idx, visit, root = job['tid'], job['index'], job['visit'], job['root']
        complexity = str(tx.loc[tid, 'complexity_level'])
        a = attrs.loc[tid]
        risk = .015 + {'LOW': 0, 'MEDIUM': .012, 'HIGH': .025}[complexity]
        risk += .012 if bool(a.requires_manual_review) else 0
        if visit == 1 and rng.random() < risk:
            eid = next(quality_id)
            quality_lookup[eid] = len(quality_rows)
            quality_rows.append(dict(event_id=eid, transaction_id=tid,
                stage_id=job['stage_id'], visit_number=visit, event_type='RETURN',
                error_category='DOCUMENT_OR_VALIDATION', detected_at=time, resolved_at=None,
                requires_rework=True, root_event_id=None))
            start_job(tid, idx, 2, eid, time)
        else:
            if root is not None:
                quality_rows[quality_lookup[root]]['resolved_at'] = time
            if idx + 1 < len(stages[tid]):
                start_job(tid, idx + 1, 1, None, time)
            else:
                completion[tid] = time

    def dispatch(team, now):
        """FIFO; capacity assigned only when a worker actually starts work."""
        if now >= CUTOFF:
            return
        stats['dispatches'] += 1
        q = pending[team]
        if not q:
            return
        slot = available_slot(team, now)
        if slot is None:
            wake(team, next_window(team, now + pd.Timedelta(microseconds=1)))
            return
        end, kind, budget, n = slot
        while q and budget > 0:
            occupied = busy[team]
            available = [i for i in range(1, n + 1) if i not in occupied]
            if not available:
                break  # WORK_DONE events will trigger next dispatch
            jid = q.popleft()
            job = jobs[jid]
            preferred = prior_employee.get(job['tid'])
            emp = preferred if preferred in available else available[0]
            minutes = min(job['remaining'], budget, int((end-now).total_seconds() // 60))
            if minutes <= 0:
                q.appendleft(jid)
                break
            if now > job['queued_at']:
                wait_rows.append(dict(waiting_id=next(waiting_id), transaction_id=job['tid'],
                    stage_id=job['stage_id'], visit_number=job['visit'], waiting_type='INTERNAL_QUEUE',
                    waiting_reason='CAPACITY_OR_CALENDAR', started_at=job['queued_at'], ended_at=now,
                    is_excludable=False, reason_verified=True))
            finish = now + pd.Timedelta(minutes=minutes)
            ex_rows.append(dict(execution_id=next(execution_id), transaction_id=job['tid'],
                stage_id=job['stage_id'], team_id=team, visit_number=job['visit'],
                started_at=now, ended_at=finish, active_minutes=minutes,
                execution_status='COMPLETED', is_rework=job['visit'] > 1,
                related_quality_event_id=job['root'], work_type=kind, employee_id=emp))
            occupied[emp] = jid
            used[(team, now.strftime('%Y-%m-%d'), kind)] += minutes
            budget -= minutes
            job['remaining'] -= minutes
            prior_employee[job['tid']] = emp
            emit(finish, 'WORK_DONE', jid, team, emp)
        if q and not [i for i in range(1, n + 1) if i not in busy[team]]:
            return
        if q:
            wake(team, next_window(team, now + pd.Timedelta(minutes=1)))

    for tid, r in tx.iterrows():
        emit(pd.Timestamp(r.opened_at), 'STAGE_READY', int(tid), 0, 1, None)

    while events:
        now, _, kind, args = heapq.heappop(events)
        if now >= CUTOFF:
            break  # As-of snapshot: do not process future events
        if kind == 'STAGE_READY':
            tid, idx, visit, root = args
            start_job(tid, idx, visit, root, now)
        elif kind == 'JOB_READY':
            tid, idx, visit, root, duration = args
            stage = stages[tid][idx]
            jid = next(job_id)
            team = int(stage['team_id'])
            jobs[jid] = dict(tid=tid, index=idx, visit=visit, root=root,
                             stage_id=int(stage['stage_id']), remaining=duration, queued_at=now)
            pending[team].append(jid)
            dispatch(team, now)
        elif kind == 'WORK_DONE':
            jid, team, emp = args
            if busy[team].get(emp) != jid:
                raise AssertionError('Worker/job ownership mismatch')
            del busy[team][emp]
            job = jobs[jid]
            if job['remaining'] == 0:
                finish_stage(job, now)
                del jobs[jid]
            else:
                job['queued_at'] = now
                pending[team].append(jid)
            dispatch(team, now)
        elif kind == 'WAKE':
            (team,) = args
            if wake_scheduled.get(team) != now:
                continue
            del wake_scheduled[team]
            stats['wake_events'] += 1
            dispatch(team, now)
        else:
            raise AssertionError(kind)

    executions = pd.DataFrame(ex_rows)
    waits = pd.DataFrame(wait_rows, columns=['waiting_id','transaction_id','stage_id','visit_number',
        'waiting_type','waiting_reason','started_at','ended_at','is_excludable','reason_verified'])
    quality = pd.DataFrame(quality_rows, columns=['event_id','transaction_id','stage_id','visit_number',
        'event_type','error_category','detected_at','resolved_at','requires_rework','root_event_id'])
    result = d['transactions'].copy()
    result['closed_at'] = result.transaction_id.map(completion)
    result['final_status'] = np.where(result.closed_at <= CUTOFF, 'COMPLETED', 'OPEN')
    result.loc[result.final_status == 'OPEN', 'closed_at'] = pd.NaT
    executions = executions.loc[executions.started_at < CUTOFF].copy()
    mask = executions.ended_at > CUTOFF
    executions.loc[mask, 'ended_at'] = pd.NaT
    executions.loc[mask, 'active_minutes'] = pd.NA
    executions.loc[mask, 'execution_status'] = 'IN_PROGRESS'
    waits = waits.loc[waits.started_at < CUTOFF].copy()
    waits.loc[waits.ended_at > CUTOFF, 'ended_at'] = pd.NaT
    quality = quality.loc[quality.detected_at < CUTOFF].copy()
    quality.loc[quality.resolved_at > CUTOFF, 'resolved_at'] = pd.NaT
    return result, executions, waits, quality, used, stats


def validate(d, tx, ex, waits, quality, used):
    if len(tx) != len(d['transactions']) or not tx.transaction_id.is_unique:
        raise AssertionError('Transaction count / uniqueness')
    for name, frame, id_col in [('executions', ex, 'execution_id'),
                                ('waits', waits, 'waiting_id'), ('quality', quality, 'event_id')]:
        if frame[id_col].duplicated().any() or not frame.transaction_id.isin(tx.transaction_id).all():
            raise AssertionError(f'{name}: duplicate ID or missing transaction')
    if (pd.to_datetime(ex.started_at) < ex.transaction_id.map(
            d['transactions'].set_index('transaction_id').opened_at.pipe(pd.to_datetime))).any():
        raise AssertionError('Execution before transaction opening')
    completed = ex[ex.execution_status == 'COMPLETED'].copy()
    if (pd.to_datetime(completed.ended_at) <= pd.to_datetime(completed.started_at)).any():
        raise AssertionError('Non-positive execution interval')
    if not ((completed.ended_at.pipe(pd.to_datetime) - completed.started_at.pipe(pd.to_datetime))
            .dt.total_seconds().div(60) == completed.active_minutes).all():
        raise AssertionError('Active minute mismatch')
    if ex.duplicated(['transaction_id','stage_id','visit_number','started_at']).any():
        raise AssertionError('Duplicate stage interval')
    # Stable employee IDs across days; verify non-overlap for the full year.
    for _, g in ex.sort_values('started_at').groupby(['team_id', 'employee_id']):
        previous_end = None
        for row in g.itertuples(index=False):
            if previous_end is not None and pd.Timestamp(row.started_at) < previous_end:
                raise AssertionError('Overlapping employee work')
            previous_end = CUTOFF if pd.isna(row.ended_at) else pd.Timestamp(row.ended_at)
    caps = d['team_capacity'].set_index(['team_id', 'capacity_date'])
    for (team, date, kind), minutes in used.items():
        limit = caps.loc[(team,date)].available_minutes if kind == 'NORMAL' else caps.loc[(team,date)].overtime_capacity_minutes
        if minutes > limit:
            raise AssertionError('Team/day capacity exceeded')
    if (pd.to_datetime(ex.started_at) >= CUTOFF).any() or (pd.to_datetime(waits.started_at) >= CUTOFF).any():
        raise AssertionError('Records started at or after reporting cutoff')
    if (pd.to_datetime(quality.detected_at) >= CUTOFF).any():
        raise AssertionError('Future quality event')
    if not tx.final_status.isin(['OPEN', 'COMPLETED']).all():
        raise AssertionError('Invalid final status')
    if tx.loc[tx.final_status == 'COMPLETED','closed_at'].isna().any():
        raise AssertionError('Completed transaction missing closure')
    if tx.loc[tx.final_status == 'OPEN','closed_at'].notna().any():
        raise AssertionError('Open transaction has closure')
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--reference', default='data/reference')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    def resolve(p):
        path = Path(p)
        return path.resolve() if path.is_absolute() else (ROOT / path).resolve()
    input_dir, reference_dir, out = map(resolve, (args.input, args.reference, args.output))
    reference_root = (ROOT / 'data' / 'reference').resolve()

if (
    out == reference_root
    or reference_root in out.parents
    or out == input_dir
    or out == reference_dir
):
    raise ValueError(
        'Output cannot overwrite reference or input data'
    )

    d = load(input_dir, reference_dir)
    tx, ex, w, q, used, stats = simulate(d)
    validate(d, tx, ex, w, q, used)
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in [('transactions',tx), ('stage_executions',ex),
                        ('waiting_intervals',w), ('quality_events',q)]:
        frame.to_csv(out / f'{name}.csv', index=False, encoding='utf-8-sig')
    print('VERIQORA | AS-OF CHRONOLOGICAL SCALE SIMULATION')
    print(f'Transactions: {len(tx)} | Completed: {(tx.final_status == "COMPLETED").sum()} | Open: {(tx.final_status == "OPEN").sum()}')
    print(f'Work intervals: {len(ex)} | Waiting: {len(w)} | Quality events: {len(q)}')
    print(f'Reporting cutoff: {CUTOFF} | Validation: PASS | Output: {out}')

if __name__ == '__main__':
    main()
