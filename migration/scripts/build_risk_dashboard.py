"""Build Dashboard A through public Superset REST APIs, preserving main charts."""
import argparse
import json
from common import API, MARKER, ROOT, save, uid
from risk_spec import CHARTS, DATASET_SQL, LABELS, METRICS, PAGES, TIME_RANGE, form, query

KEY='risk-a-v1'
SLUG='amazon-delivery-giao-keo-dai'
TITLE='Amazon Delivery · Giao kéo dài và đơn cần kiểm tra'


def dataset(api,dbid):
    identity=uid('dataset:'+KEY)
    found=[d for d in api.all('dataset') if d.get('uuid')==identity]
    if found:
        ident=found[0]['id']
        old=api.request('GET',f'dataset/{ident}')['result']
        assert (old.get('description') or '').startswith(MARKER)
        api.request('PUT',f'dataset/{ident}',json={'sql':DATASET_SQL})
    else:
        assert not any(d.get('table_name')=='amazon_delivery_risk_a' for d in api.all('dataset'))
        ident=api.request('POST','dataset/',json=dict(database=dbid,schema='amazon_bi',
            table_name='amazon_delivery_risk_a',sql=DATASET_SQL,uuid=identity))['id']
    old=api.request('GET',f'dataset/{ident}')['result']
    metric_ids={m['metric_name']:m['id'] for m in old['metrics']}
    metrics=[dict(metric_name=k,verbose_name=label,expression=expr,d3format=fmt,
                  **({'id':metric_ids[k]} if k in metric_ids else {}))
             for k,(label,expr,fmt) in METRICS.items()]
    api.request('PUT',f'dataset/{ident}',json=dict(description=MARKER+'; '+KEY+'; one order; fixed snapshot peer baseline',
        main_dttm_col='order_date',filter_select_enabled=True,metrics=metrics,
        columns=[dict(id=c['id'],column_name=c['column_name'],verbose_name=LABELS.get(c['column_name'],c['column_name'])) for c in old['columns']]))
    return ident


def layout(chart_ids):
    pos={'DASHBOARD_VERSION_KEY':'v2',
      'ROOT_ID':dict(id='ROOT_ID',type='ROOT',children=['GRID_ID']),
      'GRID_ID':dict(id='GRID_ID',type='GRID',children=['TABS-RISK-A'],parents=['ROOT_ID']),
      'TABS-RISK-A':dict(id='TABS-RISK-A',type='TABS',children=[],parents=['ROOT_ID','GRID_ID'],meta={}),
      'ROW-RISK-BACK':dict(id='ROW-RISK-BACK',type='ROW',children=['MD-RISK-BACK'],parents=['ROOT_ID','GRID_ID'],meta={'background':'BACKGROUND_TRANSPARENT'}),
      'MD-RISK-BACK':dict(id='MD-RISK-BACK',type='MARKDOWN',children=[],parents=['ROOT_ID','GRID_ID','ROW-RISK-BACK'],
        meta=dict(width=12,height=8,code='[← Dashboard chính](/superset/dashboard/amazon-delivery-intelligence/)'))}
    by_key={v['key']:v for v in CHARTS}
    notes=[
      'Phút vượt mốc 160 = max(thời gian giao − 160, 0), không phải SLA hoặc số phút có thể tiết kiệm. Pareto dùng thanh trong bảng và cột tích lũy, hiển thị 15 nhóm. Các tỷ trọng dùng mẫu số toàn bộ nhóm sau lọc. Bộ lọc Khu vực · giao thông · thời tiết giữ nhóm đã chọn khi chuyển trang.',
      'Trang này chỉ dùng đơn có các thành phần tọa độ khác 0; điều kiện này chưa xác nhận khoảng cách chính xác. Mức lệch = thời gian giao − trung vị nhóm cùng khu vực, giao thông, thời tiết và khoảng cách 3 km; nhóm phải có ≥30 đơn. Tham chiếu cố định theo toàn bộ snapshot 11/02–06/04/2022, gồm cả đơn đang xét; bộ lọc chỉ chọn đơn cần xem. Ô mức lệch trống nghĩa là chưa đủ mẫu.']
    for i,p in enumerate(PAGES,1):
        tab=f'TAB-RISK-A-{i}';parents=['ROOT_ID','GRID_ID','TABS-RISK-A']
        pos['TABS-RISK-A']['children'].append(tab)
        pos[tab]=dict(id=tab,type='TAB',children=[],parents=parents,meta={'text':p['name']})
        row=f'ROW-RISK-NOTE-{i}';md=f'MD-RISK-NOTE-{i}'
        pos[tab]['children'].append(row)
        pos[row]=dict(id=row,type='ROW',children=[md],parents=parents+[tab],meta={'background':'BACKGROUND_TRANSPARENT'})
        pos[md]=dict(id=md,type='MARKDOWN',children=[],parents=parents+[tab,row],meta=dict(width=12,height=16 if i==1 else 19,
            code='[← Dashboard chính](/superset/dashboard/amazon-delivery-intelligence/)\n\n'+notes[i-1]))
        for j,keys in enumerate(p['rows']):
            row=f'ROW-RISK-{i}-{j}';pos[tab]['children'].append(row)
            pos[row]=dict(id=row,type='ROW',children=[],parents=parents+[tab],meta={'background':'BACKGROUND_TRANSPARENT'})
            for key in keys:
                ident=chart_ids[key];v=by_key[key];node=f'CHART-{ident}'
                pos[row]['children'].append(node)
                height=14 if v['kind']=='kpi' else 70 if key in ['severity-pareto','severity-contribution','exceptions-deviation'] else 64 if v['kind']=='records' else 56
                pos[node]=dict(id=node,type='CHART',children=[],parents=parents+[tab,row],
                    meta=dict(chartId=ident,uuid=uid('chart:'+KEY+':'+key),width=12//len(keys),height=height,sliceName=v['title']))
    return pos


def filters(ds,charts):
    configs=[]
    for col in ['order_date','risk_group','area','traffic','weather','vehicle','category']:
        time=col=='order_date'
        default=dict(extraFormData={'time_range':TIME_RANGE},filterState={'value':TIME_RANGE},ownState={}) if time else dict(extraFormData={},filterState={},ownState={})
        configs.append(dict(id='NATIVE_FILTER-RISK-A-'+col,type='NATIVE_FILTER',name=LABELS[col],
            filterType='filter_time' if time else 'filter_select',targets=[{}] if time else [{'datasetId':ds,'column':{'name':col}}],
            defaultDataMask=default,cascadeParentIds=[],controlValues=dict(enableEmptyFilter=False,multiSelect=True,searchAllOptions=True),
            scope={'rootPath':['ROOT_ID'],'excluded':[]},chartsInScope=list(charts.values()),tabsInScope=['TAB-RISK-A-1','TAB-RISK-A-2']))
    return configs


def navigation(api,main_id,url):
    main=api.request('GET',f'dashboard/{main_id}')['result'];assert main['uuid']==uid('dashboard:main')
    pos=json.loads(main['position_json']);row='ROW-RISK-A-NAV';md='MD-RISK-A-NAV'
    if row not in pos:
        backup=ROOT/'migration/evidence/risk-a-main-before.json'
        if not backup.exists():
            save('migration/evidence/risk-a-main-before.json',{'position_json':main['position_json'],'json_metadata':main['json_metadata']})
        pos['TAB-P1']['children'].insert(0,row)
    parents=['ROOT_ID','GRID_ID','TABS-AMAZON','TAB-P1']
    pos[row]=dict(id=row,type='ROW',children=[md],parents=parents,meta={'background':'BACKGROUND_TRANSPARENT'})
    pos[md]=dict(id=md,type='MARKDOWN',children=[],parents=parents+[row],
        meta=dict(width=12,height=10,code=f'[Phân tích chuyên sâu: mức độ giao kéo dài và đơn cần kiểm tra →]({url})'))
    api.request('PUT',f'dashboard/{main_id}',json={'position_json':json.dumps(pos,ensure_ascii=False)})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if not args.apply:
        print(json.dumps(dict(dashboards=1,pages=2,charts=len(CHARTS),slug=SLUG)));return
    api=API();state=json.loads((ROOT/'migration/.state.json').read_text())
    ds=dataset(api,state['database_id']);charts={}
    for v in CHARTS:
        f=form(v,ds)
        charts[v['key']]=api.upsert('chart',KEY+':'+v['key'],dict(slice_name=v['title'],
            description=MARKER+'; '+KEY+'; '+v['key'],datasource_id=ds,datasource_type='table',
            viz_type=f['viz_type'],params=json.dumps(f,ensure_ascii=False),query_context=json.dumps(query(v,ds),ensure_ascii=False)))
    for existing in api.all('dashboard'):
        assert existing.get('slug')!=SLUG or existing.get('uuid')==uid('dashboard:'+KEY),'Slug ownership mismatch'
    labels={'01 · Trên 160–180':'#E7B84B','02 · Trên 180–200':'#E77832','03 · Trên 200':'#BE3548',
            METRICS['excess'][0]:'#287CB0',METRICS['cumulative_share'][0]:'#D68124',
            METRICS['order_share'][0]:'#287CB0',METRICS['excess_share'][0]:'#D68124'}
    metadata=dict(native_filter_configuration=filters(ds,charts),filter_bar_orientation='HORIZONTAL',
        cross_filters_enabled=False,chart_configuration={},color_scheme='supersetColors',label_colors=labels,
        refresh_frequency=0,expanded_slices={},timed_refresh_immune_slices=[],map_label_colors={},shared_label_colors=[],color_scheme_domain=[])
    body=dict(dashboard_title=TITLE,slug=SLUG,published=True,position_json=json.dumps(layout(charts),ensure_ascii=False),
              json_metadata=json.dumps(metadata,ensure_ascii=False),css='.dashboard-content{background:#f7f8fa}.dashboard-component-tabs-content{background:white}.header-title a{font-size:14px;line-height:19px}')
    themes=api.all('theme');light=[t for t in themes if t.get('is_system') and t.get('theme_name')=='THEME_DEFAULT']
    if light:body['theme_id']=light[0]['id']
    ident=api.upsert('dashboard',KEY,body)
    for v in CHARTS:
        chart=charts[v['key']];f=form(v,ds);f.update(slice_id=chart,dashboards=[ident]);q=query(v,ds);q['form_data']=f
        api.request('PUT',f'chart/{chart}',json={'dashboards':[ident],'params':json.dumps(f,ensure_ascii=False),'query_context':json.dumps(q,ensure_ascii=False)})
    url=api.base+'/superset/dashboard/'+SLUG+'/'
    navigation(api,state['dashboard_id'],url)
    result=dict(dashboard_id=ident,dataset_id=ds,charts=charts,pages=2,dashboard_url=url,uuid=uid('dashboard:'+KEY))
    save('migration/evidence/risk-a-deployment.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
