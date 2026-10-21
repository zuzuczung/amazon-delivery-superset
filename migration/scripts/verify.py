"""CSV -> PostgreSQL -> Superset, for every visual and six filter states.

Power BI is only verified at the precision visibly printed in the PDF. Other
filter states have no Power BI baseline and are explicitly 'chưa xác minh'.
"""
import csv
import datetime as dt
import json
import math
from collections import defaultdict
from statistics import mean
from common import API, ROOT, save, sql_json
from migrate import query
from spec import DATASET_SQL, METRICS, PAGES, visuals

SCENARIOS = [
    ('all',{},'2022-02-11 : 2022-04-07'),
    ('date',{},'2022-03-01 : 2022-04-01'),
    ('category',{'category':'Grocery'},'2022-02-11 : 2022-04-07'),
    ('combined',{'category':'Grocery','vehicle':'motorcycle','traffic':'Jam','area':'Metropolitan'},'2022-03-01 : 2022-04-01'),
    ('no_data',{},'2023-01-01 : 2023-02-01'),
    ('reset',{},'2022-02-11 : 2022-04-07'),
]


def quantile(values, p):
    if not values: return None
    v=sorted(values); pos=(len(v)-1)*p; lo=math.floor(pos); hi=math.ceil(pos)
    return v[lo]+(v[hi]-v[lo])*(pos-lo)


def measures(rows):
    def avg(col):
        vals=[float(r[col]) for r in rows if r[col] not in (None,'')]
        return mean(vals) if vals else None
    times=[float(r['delivery_time']) for r in rows if r['delivery_time'] not in (None,'')]
    result=dict(orders=sum(r['order_id'] not in (None,'') for r in rows),avg_time=avg('delivery_time'),
        median=quantile(times,.5),p90=quantile(times,.9),distance=avg('distance_km'),
        long_rate=sum(int(r['long_delivery_flag']) for r in rows)/len(rows) if rows else None,
        pickup=avg('pickup_delay_min'),rating=avg('agent_rating'))
    result.update(avg_time_yellow=result['avg_time'],avg_time_red=result['avg_time'],pickup_yellow=result['pickup'])
    return result


def read_rows():
    result=[]
    for r in csv.DictReader((ROOT/'data/amazon_delivery_cleaned.csv').open()):
        r={k.lower():v if v!='' else None for k,v in r.items()}
        low=math.floor(float(r['distance_km'])/3)*3
        r['distance_band']=f'{low:02}–{low+3:02} km'
        r['weekday_sorted']=r['day_number']+' · '+r['day_name']
        result.append(r)
    return result


def same(a,b,metric):
    if a is None or b is None: return a is b
    if metric=='orders': return a==b
    return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8)


def expected(rows,v):
    groups=defaultdict(list)
    dataset=v.get('dataset','base')
    dims=[v['dimension']] if v.get('dimension') else []
    if v.get('series'):dims.append(v['series'])
    if v.get('columns'):dims.append(v['columns'])
    for r in rows:
        if v.get('exclude_null') and r[v['dimension']] is None: continue
        combos=[{}]
        if dataset=='area_matrix':
            combos=[dict(matrix_area=a,matrix_traffic=t) for a in [r['area'],'Total'] for t in [r['traffic'],'Total']]
        elif dataset=='hour_matrix':
            combos=[dict(matrix_day=d,matrix_hour=h) for d in [r['weekday_sorted'],'Total'] for h in [r['order_hour'].zfill(2),'Total']]
        elif dataset=='area_totals':combos=[dict(matrix_area=a) for a in [r['area'],'Total']]
        for extra in combos:
            groups[tuple(extra[d] if d in extra else r[d] for d in dims)].append(r)
    if not dims and not groups:groups[()]=[]
    return dims,{key:measures(items) for key,items in groups.items()}


def main():
    state=json.loads((ROOT/'migration/.state.json').read_text());api=API();rows=read_rows()
    results=[];failures=[]
    for scenario,filters,tr in SCENARIOS:
        start,end=tr.split(' : ')
        subset=[r for r in rows if start<=r['order_date']<end and all(r[k]==val for k,val in filters.items())]
        # Exact SQL checks use their own aggregate execution, independently of Superset.
        wheres=[f"order_date >= DATE '{start}'",f"order_date < DATE '{end}'"]
        wheres += [f"{k} = '{val}'" for k,val in filters.items()]
        sqlrow=sql_json('SELECT '+','.join(f'{m[1]} AS {k}' for k,m in METRICS.items())+
                        ' FROM amazon_bi.delivery_orders WHERE '+' AND '.join(wheres))[0]
        pythonrow=measures(subset)
        for metric in METRICS:
            if not same(sqlrow[metric],pythonrow[metric],metric):failures.append([scenario,'CSV/SQL',metric])
        for v in visuals():
            ds=state['datasets'][v.get('dataset','base')]
            fs=[dict(col=k,op='IN',val=[val]) for k,val in filters.items()]
            d=api.request('POST','chart/data',json=query(v,ds,fs,tr))
            result=d['result'][0]
            if result.get('status')!='success' or result.get('error'):
                failures.append([scenario,v['key'],'chart query failed']);continue
            dims,exp=expected(subset,v)
            def dimvalue(r,k):
                if r[k] is None:return None
                if k=='order_date' and isinstance(r[k],(int,float)):
                    return dt.datetime.fromtimestamp(r[k]/1000,dt.timezone.utc).date().isoformat()
                return str(r[k])
            actual={tuple(dimvalue(r,k) for k in dims):r for r in result['data']}
            errors=[]
            if actual.keys()!=exp.keys():errors.append('group keys differ')
            for key in actual.keys() & exp.keys():
                for metric in v.get('metrics',[v['metric']]):
                    if not same(actual[key][metric],exp[key][metric],metric):errors.append(f'{key}:{metric}')
            if errors:failures.append([scenario,v['key'],errors[:5]])
            results.append(dict(scenario=scenario,visual=v['key'],groups=len(actual),passed=not errors))
        print(f'{scenario}: {len(subset)} orders; {sum(x["passed"] for x in results if x["scenario"]==scenario)}/28 charts matched CSV')
    # Baselines transcribed only from printed numbers, never used as query data.
    global_values=measures(rows)
    printed={'avg_time':(124.91,2),'median':(125.00,2),'p90':(195.00,2),'distance':(9.73,2)}
    pdf_checks=[dict(metric=k,PDF=value,SQL=global_values[k],passed=round(global_values[k],digits)==value,
                     scope='dashboard PDF page 1; all filters shown as All; displayed precision only')
                for k,(value,digits) in printed.items()]
    pdf_checks.append(dict(metric='long_rate',PDF='23.1%',SQL=global_values['long_rate'],
                           passed=round(global_values['long_rate']*100,1)==23.1))
    pdf_checks.append(dict(metric='orders',PDF=43648,SQL=global_values['orders'],
                           passed=global_values['orders']==43648,source='PDF page 5 total row; page 1 only shows 44K'))
    # Page 5 table provides actual exact counts, and printed decimal baselines by area.
    areas={'Semi-Urban':(152,269.50,10.07,94.7,12.87,238.55),
           'Metropolitan':(32634,200,9.98,25.9,9.93,129.71),
           'Urban':(9726,175,10.03,13.9,9.09,109.44),
           'Other':(1136,165,10.11,11.4,9.19,104.50)}
    for area,vals in areas.items():
        got=measures([r for r in rows if r['area']==area])
        for metric,value,digits,scale in [('orders',vals[0],0,1),('p90',vals[1],2,1),
            ('pickup',vals[2],2,1),('long_rate',vals[3],1,100),('distance',vals[4],2,1),('avg_time',vals[5],2,1)]:
            pdf_checks.append(dict(area=area,metric=metric,PDF=value,SQL=got[metric],
                passed=round(got[metric]*scale,digits)==value,source='PDF page 5 table; displayed precision'))
    if any(not c['passed'] for c in pdf_checks):failures.append(['PDF','baseline mismatch'])
    # Compare persisted dashboard and all linked chart identities, not just script output.
    dash=api.request('GET',f'dashboard/{state["dashboard_id"]}')['result']
    positions=json.loads(dash['position_json']); md=json.loads(dash['json_metadata'])
    chartids={n['meta']['chartId'] for n in positions.values() if isinstance(n,dict) and n.get('type')=='CHART'}
    if chartids!=set(state['charts'].values()):failures.append(['layout','chart inventory differs'])
    if len([n for n in positions.values() if isinstance(n,dict) and n.get('type')=='TAB'])!=5:failures.append(['layout','tab count'])
    # Verify native filter exclusions exactly match the PDF page scope.
    for cfg in md['native_filter_configuration']:
        if cfg.get('type')!='NATIVE_FILTER':failures.append(['native_filter_type',cfg['id']])
        col='order_date' if cfg['filterType']=='filter_time' else cfg['targets'][0]['column']['name']
        included={state['charts'][v['key']] for p in PAGES if col in p['filters'] for row in p['rows'] for v in row}
        if set(state['charts'].values())-set(cfg['scope']['excluded'])!=included:
            failures.append(['native_filter_scope',col])
    save('migration/evidence/verification.json',dict(
        scenarios=results,PDF_baselines=pdf_checks,failures=failures,
        numerical_tolerance={'counts':'exact','other':'abs 1e-8 / rel 1e-10'},
        Power_BI_filtered_states='chưa xác minh: no filtered Power BI exports supplied',
        Power_BI_DAX='chưa xác minh: no PBIX, PBIP, semantic model or DAX supplied',
        query_tests='168 chart requests plus 6 SQL comparisons against independently calculated CSV aggregates',
        native_UI='see browser-QA.md; API requests alone do not prove browser filter behavior'))
    if failures:raise SystemExit(f'FAILED: {len(failures)} checks; see evidence/verification.json')
    print(f'PASS: {len(results)} chart/filter checks; {len(pdf_checks)} printed PDF baselines')


if __name__=='__main__':main()
