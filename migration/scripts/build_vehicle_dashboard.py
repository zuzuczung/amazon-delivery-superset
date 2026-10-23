"""Create Dashboard B using dedicated aggregated datasets and stable UUIDs."""
import argparse
import json
from common import API, MARKER, ROOT, save, uid
from vehicle_spec import KEY, SLUG, TITLE, CHARTS, DATASETS, METRICS, LABELS, FILTER_COLUMNS, form, query


def upsert_dataset(api,key,sql,database_id):
    identity=uid('dataset:'+KEY+':'+key);table='amazon_vehicle_b_'+key
    found=[d for d in api.all('dataset') if d.get('uuid')==identity]
    if found:
        ident=found[0]['id'];old=api.request('GET',f'dataset/{ident}')['result']
        assert (old.get('description') or '').startswith(MARKER)
        api.request('PUT',f'dataset/{ident}',json={'sql':sql})
    else:
        assert not any(d.get('table_name')==table for d in api.all('dataset'))
        ident=api.request('POST','dataset/',json=dict(database=database_id,schema='amazon_bi',
            table_name=table,sql=sql,uuid=identity))['id']
    old=api.request('GET',f'dataset/{ident}')['result'];ids={m['metric_name']:m['id'] for m in old['metrics']}
    metrics=[dict(metric_name=k,verbose_name=label,expression=expr,d3format=fmt,
                  **({'id':ids[k]} if k in ids else {})) for k,(label,expr,fmt) in METRICS[key].items()]
    api.request('PUT',f'dataset/{ident}',json=dict(
        description=MARKER+'; '+KEY+'; grain='+('one condition stratum' if key=='strata' else 'one condition stratum per vehicle'),
        filter_select_enabled=True,metrics=metrics,
        columns=[dict(id=c['id'],column_name=c['column_name'],verbose_name=LABELS.get(c['column_name'],c['column_name'])) for c in old['columns']]))
    return ident


def layout(charts):
    parents=['ROOT_ID','GRID_ID']
    pos={'DASHBOARD_VERSION_KEY':'v2',
         'ROOT_ID':dict(id='ROOT_ID',type='ROOT',children=['GRID_ID']),
         'GRID_ID':dict(id='GRID_ID',type='GRID',children=[],parents=['ROOT_ID'])}
    row='ROW-VEHICLE-B-NOTE';md='MD-VEHICLE-B-NOTE';pos['GRID_ID']['children'].append(row)
    pos[row]=dict(id=row,type='ROW',children=[md],parents=parents,meta={'background':'BACKGROUND_TRANSPARENT'})
    note='''[← Dashboard chính](/superset/dashboard/amazon-delivery-intelligence/) · [Dashboard A](/superset/dashboard/amazon-delivery-giao-keo-dai/)

Snapshot 11/02–06/04/2022; loại Grocery, chỉ so sánh motorcycle và scooter. Mỗi nhóm cùng khu vực, giao thông, thời tiết và khoảng cách 3 km phải có ≥20 đơn cho từng phương tiện. Cả hai được cân bằng theo cùng cơ cấu số đơn gộp của các nhóm đang chọn. Hai cột trước/sau dùng cùng mẫu đủ điều kiện. Chênh lệch dương: motorcycle lâu hơn; đây là liên hệ quan sát, chưa chứng minh tác động của phương tiện.'''
    pos[md]=dict(id=md,type='MARKDOWN',children=[],parents=parents+[row],meta=dict(width=12,height=19,code=note))
    rows=[['gap-kpi','coverage-kpi','sample-kpi'],['comparison','coverage'],['distribution'],['groups']]
    by_key={v['key']:v for v in CHARTS}
    for i,keys in enumerate(rows):
        row=f'ROW-VEHICLE-B-{i}';pos['GRID_ID']['children'].append(row)
        pos[row]=dict(id=row,type='ROW',children=[],parents=parents,meta={'background':'BACKGROUND_TRANSPARENT'})
        for key in keys:
            chart=charts[key];node=f'CHART-{chart}';v=by_key[key]
            pos[row]['children'].append(node)
            pos[node]=dict(id=node,type='CHART',children=[],parents=parents+[row],
                meta=dict(chartId=chart,uuid=uid('chart:'+KEY+':'+key),sliceName=v['title'],
                          width=12//len(keys),height=16 if v['kind']=='kpi' else 60 if v['kind']=='table' else 48))
    return pos


def filters(datasets,charts):
    return [dict(id='NATIVE_FILTER-VEHICLE-B-'+col,type='NATIVE_FILTER',name=LABELS[col],
                 filterType='filter_select',targets=[dict(datasetId=ds,column={'name':col}) for ds in datasets.values()],
                 defaultDataMask=dict(extraFormData={},filterState={},ownState={}),cascadeParentIds=[],
                 controlValues=dict(enableEmptyFilter=False,multiSelect=True,searchAllOptions=True),
                 scope={'rootPath':['ROOT_ID'],'excluded':[]},chartsInScope=list(charts.values()),tabsInScope=[])
            for col in FILTER_COLUMNS]


def navigation(api,main_id,url):
    main=api.request('GET',f'dashboard/{main_id}')['result'];assert main['uuid']==uid('dashboard:main')
    before=ROOT/'migration/evidence/vehicle-b-main-before.json'
    if not before.exists():
        save('migration/evidence/vehicle-b-main-before.json',{k:main[k] for k in ['id','uuid','position_json','json_metadata','css']})
    pos=json.loads(main['position_json']);row='ROW-VEHICLE-B-NAV';md='MD-VEHICLE-B-NAV'
    if row not in pos:
        at=1 if pos['TAB-P1']['children'] and pos['TAB-P1']['children'][0]=='ROW-RISK-A-NAV' else 0
        pos['TAB-P1']['children'].insert(at,row)
    parents=['ROOT_ID','GRID_ID','TABS-AMAZON','TAB-P1']
    pos[row]=dict(id=row,type='ROW',children=[md],parents=parents,meta={'background':'BACKGROUND_TRANSPARENT'})
    pos[md]=dict(id=md,type='MARKDOWN',children=[],parents=parents+[row],meta=dict(width=12,height=8,
        code=f'[Dashboard B: so sánh phương tiện trong điều kiện tương đồng →]({url})'))
    api.request('PUT',f'dashboard/{main_id}',json={'position_json':json.dumps(pos,ensure_ascii=False)})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if not args.apply:
        print(json.dumps(dict(dashboards=1,pages=1,charts=len(CHARTS),datasets=2)));return
    api=API();main_state=json.loads((ROOT/'migration/.state.json').read_text())
    a_state=json.loads((ROOT/'migration/evidence/risk-a-deployment.json').read_text())
    a_before=api.request('GET',f"dashboard/{a_state['dashboard_id']}")['result']
    before_charts={ident:api.request('GET',f'chart/{ident}')['result'] for ident in [*main_state['charts'].values(),*a_state['charts'].values()]}
    datasets={k:upsert_dataset(api,k,sql,main_state['database_id']) for k,sql in DATASETS.items()}
    charts={}
    for v in CHARTS:
        ds=datasets[v['dataset']];f=form(v,ds)
        charts[v['key']]=api.upsert('chart',KEY+':'+v['key'],dict(slice_name=v['title'],description=MARKER+'; '+KEY+'; '+v['key'],
            datasource_id=ds,datasource_type='table',viz_type=f['viz_type'],params=json.dumps(f,ensure_ascii=False),query_context=json.dumps(query(v,ds),ensure_ascii=False)))
    for d in api.all('dashboard'):
        assert d.get('slug')!=SLUG or d.get('uuid')==uid('dashboard:'+KEY)
    colors={'Thô · cùng mẫu':'#287CB0','Đã cân bằng':'#D68124',
            'Đủ mẫu so sánh':'#287CB0','Chưa đủ mẫu':'#B6BEC8',
            'raw_mean':'#287CB0','adjusted_mean':'#D68124'}
    metadata=dict(native_filter_configuration=filters(datasets,charts),filter_bar_orientation='HORIZONTAL',
        cross_filters_enabled=False,chart_configuration={},color_scheme='supersetColors',label_colors=colors,
        refresh_frequency=0,expanded_slices={},timed_refresh_immune_slices=[],map_label_colors={},shared_label_colors=[],color_scheme_domain=[])
    body=dict(dashboard_title=TITLE,slug=SLUG,published=True,position_json=json.dumps(layout(charts),ensure_ascii=False),
              json_metadata=json.dumps(metadata,ensure_ascii=False),css='.dashboard-content{background:#f7f8fa}.header-title a{font-size:14px;line-height:19px}')
    light=[t for t in api.all('theme') if t.get('is_system') and t.get('theme_name')=='THEME_DEFAULT']
    if light:body['theme_id']=light[0]['id']
    ident=api.upsert('dashboard',KEY,body)
    for v in CHARTS:
        ds=datasets[v['dataset']];chart=charts[v['key']];f=form(v,ds);f.update(slice_id=chart,dashboards=[ident]);q=query(v,ds);q['form_data']=f
        api.request('PUT',f'chart/{chart}',json=dict(dashboards=[ident],params=json.dumps(f,ensure_ascii=False),query_context=json.dumps(q,ensure_ascii=False)))
    url=api.base+'/superset/dashboard/'+SLUG+'/'
    navigation(api,main_state['dashboard_id'],url)
    a_after=api.request('GET',f"dashboard/{a_state['dashboard_id']}")['result']
    for field in ['position_json','json_metadata','css','uuid']:assert a_after[field]==a_before[field]
    for chart,old in before_charts.items():
        current=api.request('GET',f'chart/{chart}')['result']
        for field in ['params','query_context','slice_name','datasource_id','uuid']:
            assert current[field]==old[field],(chart,field)
    result=dict(dashboard_id=ident,datasets=datasets,charts=charts,dashboard_url=url,pages=1,
                uuid=uid('dashboard:'+KEY),main_and_a_charts_unchanged=len(before_charts),dashboard_a_unchanged=True)
    save('migration/evidence/vehicle-b-deployment.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
