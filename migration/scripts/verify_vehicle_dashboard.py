"""Independent CSV direct-standardization checks for Dashboard B."""
import csv
import json
import math
from collections import defaultdict
from common import API,ROOT,save,sql_json
from vehicle_spec import CHARTS,STRATA_SQL,query


def csv_strata():
    groups=defaultdict(lambda:dict(n_motor=0,n_scooter=0,time_motor=0,time_scooter=0))
    ids=set();source_n=0
    for r in csv.DictReader((ROOT/'data/amazon_delivery_cleaned.csv').open()):
        assert r['Order_ID'] not in ids;ids.add(r['Order_ID'])
        if r['Category']=='Grocery' or r['Vehicle'] not in ['motorcycle','scooter']:continue
        assert '2022-02-11'<=r['Order_Date']<'2022-04-07'
        source_n+=1;low=int(float(r['Distance_Km'])//3)*3
        key=(r['Area'],r['Traffic'],r['Weather'],low)
        vehicle='motor' if r['Vehicle']=='motorcycle' else 'scooter'
        groups[key]['n_'+vehicle]+=1;groups[key]['time_'+vehicle]+=float(r['Delivery_Time'])
    result=[]
    for (area,traffic,weather,low),stats in groups.items():
        band=f'{low:02}–{low+3:02} km'
        n1,n2=stats['n_motor'],stats['n_scooter']
        m1=stats['time_motor']/n1 if n1 else None;m2=stats['time_scooter']/n2 if n2 else None
        gap=m1-m2 if m1 is not None and m2 is not None else None
        result.append(dict(**stats,area=area,traffic=traffic,weather=weather,distance_band=band,
            group_label=' · '.join([area,traffic,weather,band]),
            eligible=n1>=20 and n2>=20,pooled_n=n1+n2,mean_motor=m1,mean_scooter=m2,
            gap=gap,gap_bin=math.floor(gap/5)*5 if gap is not None else None,
            support_status='Đủ mẫu so sánh' if n1>=20 and n2>=20 else 'Chưa đủ mẫu'))
    assert sum(r['pooled_n'] for r in result)==source_n
    return result


def vehicle_rows(strata):
    result=[]
    for r in strata:
        for name,key in [('motorcycle','motor'),('scooter','scooter')]:
            if r['n_'+key]:result.append(dict(**r,vehicle=name,vehicle_orders=r['n_'+key],
                vehicle_time=r['time_'+key],vehicle_mean=r['mean_'+key]))
    return result


def measures(rows,dataset):
    if dataset=='vehicles':
        orders=sum(r['vehicle_orders'] for r in rows)
        pool=sum(r['pooled_n'] for r in rows)
        return dict(vehicle_orders=orders if rows else None,
            raw_mean=sum(r['vehicle_time'] for r in rows)/orders if orders else None,
            adjusted_mean=sum(r['vehicle_mean']*r['pooled_n'] for r in rows)/pool if pool else None)
    eligible=[r for r in rows if r['eligible']];common=sum(r['pooled_n'] for r in eligible)
    total=sum(r['pooled_n'] for r in rows)
    n1=sum(r['n_motor'] for r in rows);n2=sum(r['n_scooter'] for r in rows)
    gaps=[r['gap'] for r in rows if r['gap'] is not None]
    return dict(adjusted_gap=sum(r['gap']*r['pooled_n'] for r in eligible)/common if common else None,
                coverage=common/total if total else None,common_orders=common,group_count=len(rows),
                n_motor=n1 if rows else None,n_scooter=n2 if rows else None,
                mean_motor=sum(r['time_motor'] for r in rows)/n1 if n1 else None,
                mean_scooter=sum(r['time_scooter'] for r in rows)/n2 if n2 else None,
                group_gap=max(gaps) if gaps else None)


def same(a,b):
    if a is None or b is None:return a is b
    return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8)


def main():
    api=API();state=json.loads((ROOT/'migration/evidence/vehicle-b-deployment.json').read_text())
    strata=csv_strata();results=[];failures=[]
    scenarios=[('all',{}),('metropolitan',{'area':'Metropolitan'}),
               ('jam-fog',{'traffic':'Jam','weather':'Fog'}),
               ('long-distance',{'distance_band':'18–21 km'}),
               ('no-common-support',{'area':'Semi-Urban'}),('empty',{'area':'__missing__'})]
    summaries=[]
    for name,filters in scenarios:
        selected=[r for r in strata if all(r[k]==v for k,v in filters.items())]
        summaries.append(dict(scenario=name,**measures(selected,'strata')))
        for v in CHARTS:
            rows=vehicle_rows(selected) if v['dataset']=='vehicles' else selected
            if v.get('eligible_only'):rows=[r for r in rows if r['eligible']]
            dims=([v['dimension']] if v.get('dimension') else [])+([v['series']] if v.get('series') else [])
            groups=defaultdict(list)
            for r in rows:groups[tuple(r[k] for k in dims)].append(r)
            if not dims and not groups:groups[()]=[]
            exp={k:measures(items,v['dataset']) for k,items in groups.items()}
            response=api.request('POST','chart/data',json=query(v,state['datasets'][v['dataset']],
                [dict(col=k,op='IN',val=[val]) for k,val in filters.items()]))['result'][0]
            errors=[]
            if response.get('status')!='success' or response.get('error'):errors.append('query status')
            actual={tuple(r[d] for d in dims):r for r in response.get('data',[])}
            if actual.keys()!=exp.keys():errors.append('group membership')
            for k in actual.keys() & exp.keys():
                for metric in v['metrics']:
                    if not same(actual[k][metric],exp[k][metric]):errors.append(str(k)+':'+metric)
            results.append(dict(scenario=name,chart=v['key'],passed=not errors,groups=len(actual)))
            if errors:failures.append([name,v['key'],errors[:4]])
        print(name+': '+str(len(selected))+' strata checked')
    sql=sql_json('SELECT count(*) strata,count(DISTINCT group_label) distinct_strata,sum(pooled_n) orders,sum(pooled_n) FILTER (WHERE eligible) common_orders,count(*) FILTER (WHERE eligible) common_strata FROM ('+STRATA_SQL+') s')[0]
    expected=dict(strata=len(strata),distinct_strata=len(strata),orders=sum(r['pooled_n'] for r in strata),
                  common_orders=sum(r['pooled_n'] for r in strata if r['eligible']),
                  common_strata=sum(r['eligible'] for r in strata))
    assert sql==expected,(sql,expected)
    baseline=summaries[0]
    assert baseline['common_orders']==34281 and same(baseline['coverage'],34281/37658)
    assert same(baseline['adjusted_gap'],137.9436869922209-122.343030412679)
    dash=api.request('GET',f"dashboard/{state['dashboard_id']}")['result'];assert dash['uuid']==state['uuid']
    linked=api.request('GET',f"dashboard/{state['dashboard_id']}/charts")['result']
    assert {c['id'] for c in linked}==set(state['charts'].values())
    md=json.loads(dash['json_metadata'])
    assert len(md['native_filter_configuration'])==4
    for f in md['native_filter_configuration']:
        assert {t['datasetId'] for t in f['targets']}==set(state['datasets'].values())
        assert set(f['chartsInScope'])==set(state['charts'].values())
    save('migration/evidence/vehicle-b-verification.json',dict(checks=results,failures=failures,
         summaries=summaries,sql_grain_check=sql,method='Independent CSV stratum counts, means and direct standardization vs PostgreSQL and Superset',
         population='Fixed snapshot 11/02–06/04/2022; non-Grocery motorcycle/scooter; >=20 per vehicle per common stratum'))
    if failures:raise SystemExit('FAILED '+str(failures))
    print('PASS: '+str(len(results))+' chart/filter checks; common sample '+str(sql['common_orders']))


if __name__=='__main__':main()
