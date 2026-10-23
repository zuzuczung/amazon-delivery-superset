"""Independent CSV checks for all Dashboard A charts and filter edge cases."""
import csv
import json
import math
from collections import defaultdict
from statistics import median
from common import API, ROOT, save, sql_json, uid
from risk_spec import CHARTS, DATASET_SQL, TIME_RANGE, query


def csv_rows():
    rows=[]
    for raw in csv.DictReader((ROOT/'data/amazon_delivery_cleaned.csv').open()):
        r={k.lower():v for k,v in raw.items()}
        for k in ['delivery_time','distance_km','store_latitude','store_longitude','drop_latitude','drop_longitude']:
            r[k]=float(r[k])
        r['coordinates_nonzero']=all(r[k]!=0 for k in ['store_latitude','store_longitude','drop_latitude','drop_longitude'])
        r['peer_distance_band']=int(r['distance_km']//3)
        r['risk_group']=' · '.join(r[k] for k in ['area','traffic','weather'])
        r['excess_minutes']=max(r['delivery_time']-160,0)
        t=r['delivery_time']
        r['severity_band']='00 · Không quá 160' if t<=160 else '01 · Trên 160–180' if t<=180 else '02 · Trên 180–200' if t<=200 else '03 · Trên 200'
        low=int(r['distance_km']);r['distance_cell']=f'{low:02}–{low+1:02}'
        low=int(t//20)*20;r['time_cell']=f'{low:03}–{low+20:03}'
        rows.append(r)
    peers=defaultdict(list)
    def key(r):return tuple(r[k] for k in ['area','traffic','weather','peer_distance_band'])
    for r in rows:
        if r['coordinates_nonzero']:peers[key(r)].append(r['delivery_time'])
    for r in rows:
        cohort=peers[key(r)];r['peer_n']=len(cohort)
        r['peer_median']=median(cohort) if cohort else None
        r['peer_delta']=r['delivery_time']-r['peer_median'] if r['coordinates_nonzero'] and len(cohort)>=30 else None
    return rows


def measures(rows):
    count=len(rows);long=sum(r['delivery_time']>160 for r in rows)
    excess=sum(r['excess_minutes'] for r in rows) if rows else None
    delta=[r['peer_delta'] for r in rows if r['peer_delta'] is not None]
    return dict(orders=count,long_orders=long,severe_orders=sum(r['delivery_time']>200 for r in rows),
                excess=excess,excess_per_long=excess/long if long else None,
                peer_delta=max(delta) if delta else None)


def compare(a,b):
    return a is b if a is None or b is None else math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8)


def accepts(r,filters):
    for f in filters:
        value=r[f['subject']];test=f['comparator'];op=f['operator']
        if not {'==':lambda:value==test,'<':lambda:value<test,'>':lambda:value>test,'>=':lambda:value>=test}[op]():return False
    return True


def main():
    api=API();state=json.loads((ROOT/'migration/evidence/risk-a-deployment.json').read_text())
    rows=csv_rows();results=[];failures=[]
    scenarios=[('all',{},TIME_RANGE),('grocery',{'category':'Grocery'},TIME_RANGE),
               ('march-jam',{'traffic':'Jam'},'2022-03-01 : 2022-04-01'),
               ('empty',{},'2023-01-01 : 2023-02-01')]
    for name,filters,tr in scenarios:
        start,end=tr.split(' : ')
        selected=[r for r in rows if start<=r['order_date']<end and all(r[k]==v for k,v in filters.items())]
        for v in CHARTS:
            subset=[r for r in selected if accepts(r,v.get('filters',[]))]
            response=api.request('POST','chart/data',json=query(v,state['dataset_id'],[
                dict(col=k,op='IN',val=[val]) for k,val in filters.items()],tr))['result']
            errors=[]
            for batch in response:
                if batch.get('status')!='success' or batch.get('error'):errors.append('query failed')
            if errors:
                failures.append([name,v['key'],errors]);continue
            if v['kind']=='records':
                by_id={r['order_id']:r for r in subset};actual=response[0]['data']
                if len(actual)!=min(v['limit'],len(subset)):errors.append('record count')
                boundary=sorted((r['excess_minutes'] for r in subset),reverse=True)[min(v['limit'],len(subset))-1] if subset else None
                for got in actual:
                    if got['order_id'] not in by_id:errors.append('record membership');continue
                    ref=by_id[got['order_id']]
                    for col in ['distance_km','delivery_time','excess_minutes','peer_n','peer_median','peer_delta']:
                        if not compare(got[col],ref[col]):errors.append('record '+col)
                    if boundary is not None and got['excess_minutes']<boundary:errors.append('record rank')
            else:
                dims=([v['dimension']] if v.get('dimension') else [])+([v['series']] if v.get('series') else [])
                groups=defaultdict(list)
                for r in subset:groups[tuple(r[k] for k in dims)].append(r)
                if not dims and not groups:groups[()]=[]
                calculated={k:measures(items) for k,items in groups.items()}
                if v['kind']=='bubble':calculated={k:m for k,m in calculated.items() if m['long_orders']>0}
                total_n=len(subset);total_excess=sum(r['excess_minutes'] for r in subset)
                cumul=0
                for k in sorted(calculated,key=lambda k:(-(calculated[k]['excess'] or 0),k)):
                    m=calculated[k];cumul+=m['excess'] or 0
                    m['order_share']=m['orders']/total_n if total_n else None
                    m['excess_share']=m['excess']/total_excess if total_excess else None
                    m['cumulative_share']=cumul/total_excess if total_excess else None
                for i,batch in enumerate(response):
                    metric_keys=v['metrics_b'] if i else v['metrics']
                    for got in batch['data']:
                        k=tuple(got[col] for col in dims)
                        if k not in calculated:errors.append('group missing');continue
                        for metric in metric_keys:
                            if not compare(got[metric],calculated[k][metric]):errors.append(str(k)+':'+metric)
                    if len(batch['data'])!=min(len(calculated),v.get('limit',1000)):errors.append('group count')
                if v['kind']=='pareto' and total_excess:
                    values=[r['excess'] for r in response[0]['data']]
                    if values!=sorted(values,reverse=True):errors.append('Pareto order')
            if errors:failures.append([name,v['key'],errors[:4]])
            results.append(dict(scenario=name,chart=v['key'],passed=not errors))
        print(name+': '+str(len(selected))+' orders checked')
    sql=sql_json('SELECT COUNT(*) n,COUNT(DISTINCT order_id) distinct_n,SUM(excess_minutes) excess,COUNT(*) FILTER (WHERE distance_km<5 AND delivery_time>160 AND coordinates_nonzero) short_n FROM ('+DATASET_SQL+') r')[0]
    assert sql==dict(n=len(rows),distinct_n=len(rows),excess=measures(rows)['excess'],short_n=sum(r['distance_km']<5 and r['delivery_time']>160 and r['coordinates_nonzero'] for r in rows))
    dash=api.request('GET',f"dashboard/{state['dashboard_id']}")['result']
    assert dash['uuid']==state['uuid'];pos=json.loads(dash['position_json'])
    assert sum(isinstance(n,dict) and n.get('type')=='TAB' for n in pos.values())==2
    linked=api.request('GET',f"dashboard/{state['dashboard_id']}/charts")['result']
    assert {c['id'] for c in linked}==set(state['charts'].values())
    for f in json.loads(dash['json_metadata'])['native_filter_configuration']:
        assert set(f['chartsInScope'])==set(state['charts'].values()) and not f['scope']['excluded']
    save('migration/evidence/risk-a-verification.json',dict(checks=results,failures=failures,sql_grain_check=sql,
        baseline='Independent CSV grouping and median, compared with Superset REST; no raw rows retained',
        reference='Fixed full-snapshot peer median, n>=30; filter selects orders, not the reference cohort'))
    if failures:raise SystemExit('FAILED: '+str(failures))
    print('PASS: '+str(len(results))+' chart/filter checks and SQL grain validation')


if __name__=='__main__':main()
