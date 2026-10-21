"""Idempotent migration through Superset 6 REST API; no metadata DB writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from common import API, MARKER, ROOT, save, sql, sql_json, uid
from spec import DATASET_SQL, METRICS, PAGES, CONCLUSION, metric_keys, title, visuals


def dataset_metrics(key):
    names={'avg_time_yellow':'Average Delivery Time by Traffic',
           'avg_time_red':'Average Delivery Time by Order_Date',
           'pickup_yellow':'Average Pickup Delay by Traffic'}
    return [dict(metric_name=k, verbose_name=names.get(k,METRICS[k][0]), expression=METRICS[k][1],
                 d3format=METRICS[k][2], description='SQL equivalent proposed from CSV/PDF; original DAX unavailable')
            for k in metric_keys(key)]


def form(v, dataset_id):
    metric = v['metric']; fmt = v.get('number_format', METRICS[metric][2])
    types = {'kpi':'big_number_total','bar':'echarts_timeseries_bar',
             'line':'echarts_timeseries_line','pie':'pie','pivot':'pivot_table_v2','table':'table'}
    f = dict(datasource=f'{dataset_id}__table', viz_type=types[v['kind']],
             metrics=v.get('metrics', [metric]), granularity_sqla='order_date',
             time_range='2022-02-11 : 2022-04-07',
             adhoc_filters=[], row_limit=10000, order_desc=True, extra_form_data={},
             color_scheme='supersetColors', label_colors={},
             number_format=fmt, y_axis_format=fmt, show_legend=bool(v.get('series')),
             legendType='scroll',legendOrientation='top',rich_tooltip=True,
             showTooltipTotal=False, annotation_layers=[], show_empty_columns=True)
    if v.get('exclude_null'):
        f['adhoc_filters'].append(dict(expressionType='SIMPLE',clause='WHERE',subject=v['dimension'],operator='IS NOT NULL',comparator=None))
    if v['kind']=='kpi':
        f.update(metric=metric, header_font_size=0.35, subheader_font_size=0.12,
                 subheader=METRICS[metric][0], y_axis_format=fmt)
    elif v['kind']=='pie':
        f.update(metric=metric, groupby=[v['dimension']], donut=True, show_labels=True,
                 show_legend=True, label_type='key_percent', labels_outside=True,
                 show_total=True, innerRadius=60, outerRadius=90, sort_by_metric=True)
    elif v['kind']=='pivot':
        f.update(groupbyRows=[v['dimension']], groupbyColumns=[v['columns']],
                 metricsLayout='COLUMNS', aggregateFunction='Sum',
                 rowTotals=False,colTotals=False,rowSubTotals=False,colSubTotals=False,
                 valueFormat=fmt,rowOrder='key_a_to_z',colOrder='key_a_to_z',
                 transposePivot=False, combineMetric=True)
        f['conditional_formatting']=[dict(column=metric,operator='None',colorScheme='#118DFF')]
    elif v['kind']=='table':
        f.update(query_mode='aggregate',groupby=[v['dimension']],
                 all_columns=[],percent_metrics=[],include_search=True,
                 show_cell_bars=True,table_timestamp_format='smart_date',
                 page_length=0,show_totals=False,
                 column_config={k:{'d3NumberFormat':METRICS[k][2]} for k in f['metrics']},
                 order_by_cols=[],order_desc=True)
        f['conditional_formatting']=[dict(column=k,operator='None',colorScheme='#118DFF') for k in f['metrics']]
    else:
        f.update(x_axis=v['dimension'],groupby=[v['series']] if v.get('series') else [],
                 xAxisForceCategorical=v['dimension']!='order_date',
                 x_axis_sort=v['dimension'] if v.get('ascending') else metric,
                 x_axis_sort_asc=bool(v.get('ascending') or v.get('horizontal')),orientation='horizontal' if v.get('horizontal') else 'vertical',
                 x_axis_title=v['dimension'],y_axis_title=METRICS[metric][0],
                 x_axis_title_margin=20,y_axis_title_margin=35,
                 x_axis_time_format='%b %d',xAxisLabelRotation=45 if v['dimension']=='category' and not v.get('horizontal') else 0,
                 truncateXAxis=True,truncate_metric=True,show_value=bool(v.get('labels')),
                 zoomable=v['dimension']=='category')
        f['y_axis_format']=fmt if metric=='long_rate' else 'SMART_NUMBER' if metric=='orders' else '.1f' if metric.startswith('pickup') or metric=='rating' else ',.0f'
        if v['kind']=='line':f['truncateYAxis']=True
        if v.get('horizontal'):f['x_axis_title']=''
        if v.get('horizontal'):f['x_axis_title_margin']=60
        if v.get('fixed_traffic_order'):
            f.update(x_axis_sort='traffic',x_axis_sort_asc=True)  # PDF order explicitly differs; documented.
    return f


def query(v, dataset_id, filters=None, time_range=None):
    f = form(v,dataset_id)
    columns = []
    if v.get('dimension'): columns.append(v['dimension'])
    if v.get('series'): columns.append(v['series'])
    if v.get('columns'): columns.append(v['columns'])
    fs = list(filters or [])
    if v.get('exclude_null'): fs.append({'col':v['dimension'],'op':'IS NOT NULL'})
    q = dict(columns=columns, metrics=v.get('metrics',[v['metric']]),
             filters=fs, time_range=time_range or f['time_range'],
             granularity='order_date', extras={'having':'','where':''},
             row_limit=10000, orderby=[], order_desc=True, applied_time_extras={})
    # Dashboard/Explore rebuilds plugin queries from form_data. This context also
    # makes REST validation/export independently executable.
    return dict(datasource={'id':dataset_id,'type':'table'},force=False,
                queries=[q],form_data=f,result_format='json',result_type='full')


def layout(ids):
    pos={'DASHBOARD_VERSION_KEY':'v2',
         'ROOT_ID':dict(type='ROOT',id='ROOT_ID',children=['GRID_ID']),
         'GRID_ID':dict(type='GRID',id='GRID_ID',children=['TABS-AMAZON'],parents=['ROOT_ID']),
         'TABS-AMAZON':dict(type='TABS',id='TABS-AMAZON',children=[],parents=['ROOT_ID','GRID_ID'],meta={})}
    for p in PAGES:
        t=f"TAB-P{p['number']}"; pos['TABS-AMAZON']['children'].append(t)
        parents=['ROOT_ID','GRID_ID','TABS-AMAZON']
        pos[t]=dict(id=t,type='TAB',children=[],parents=parents,meta={'text':f"Trang {p['number']}"})
        for i,row in enumerate(p['rows']):
            r=f"ROW-P{p['number']}-{i}";pos[t]['children'].append(r)
            pos[r]=dict(id=r,type='ROW',parents=parents+[t],children=[],meta={'background':'BACKGROUND_TRANSPARENT'})
            for v in row:
                ident=ids[v['key']];n=f'CHART-{ident}';pos[r]['children'].append(n)
                width=12//len(row)
                height=22 if v['kind']=='kpi' else 56 if v['kind']=='pivot' else 54
                pos[n]=dict(id=n,type='CHART',parents=parents+[t,r],children=[],
                            meta=dict(chartId=ident,uuid=uid('chart:'+v['key']),width=width,height=height,sliceName=title(v)))
        if p['number']==5:
            r='ROW-CONCLUSION';n='MARKDOWN-CONCLUSION';pos[t]['children'].append(r)
            pos[r]=dict(id=r,type='ROW',parents=parents+[t],children=[n],meta={'background':'BACKGROUND_TRANSPARENT'})
            pos[n]=dict(id=n,type='MARKDOWN',parents=parents+[t,r],children=[],meta=dict(code=CONCLUSION,width=12,height=45))
    # PDF page 2: large line chart left, matrix and pickup chart stacked right.
    parents=['ROOT_ID','GRID_ID','TABS-AMAZON','TAB-P2']
    top='ROW-P2-TOP';left='COLUMN-P2-LEFT';right='COLUMN-P2-RIGHT'
    pos['TAB-P2']['children']=[top,'ROW-P2-2']
    pos[top]=dict(id=top,type='ROW',parents=parents,children=[left,right],meta={'background':'BACKGROUND_TRANSPARENT'})
    for name,width,keys in [(left,7,['p2-01']),(right,5,['p2-02','p2-03'])]:
        pos[name]=dict(id=name,type='COLUMN',parents=parents+[top],children=[],meta={'width':width,'background':'BACKGROUND_TRANSPARENT'})
        for key in keys:
            n=f'CHART-{ids[key]}';pos[name]['children'].append(n)
            pos[n]['parents']=parents+[top,name]
            pos[n]['meta'].update(width=width,height=76 if name==left else 38)
    pos[f'CHART-{ids["p2-04"]}']['meta']['height']=50
    del pos['ROW-P2-0'];del pos['ROW-P2-1']
    return pos


def filters(datasets, chartids):
    configs=[]
    for col in ['order_date','traffic','weather','vehicle','area','category']:
        included=[chartids[v['key']] for p in PAGES if col in p['filters'] for row in p['rows'] for v in row]
        excluded=[x for x in chartids.values() if x not in included]
        time=col=='order_date'
        default={'extraFormData':{'time_range':'2022-02-11 : 2022-04-07'},
                 'filterState':{'value':'2022-02-11 : 2022-04-07'},'ownState':{}} if time else {
                     'extraFormData':{},'filterState':{},'ownState':{}}
        configs.append(dict(id='NATIVE_FILTER-AMAZON-'+col,type='NATIVE_FILTER',name='Order_Date' if time else col.title(),
            filterType='filter_time' if time else 'filter_select',
            targets=[{}] if time else [{'datasetId':i,'column':{'name':col}} for i in datasets.values()],
            defaultDataMask=default,cascadeParentIds=[],
            controlValues={'enableEmptyFilter':False,'multiSelect':True,'searchAllOptions':True},
            scope={'rootPath':['ROOT_ID'],'excluded':excluded},
            chartsInScope=included,tabsInScope=[f"TAB-P{p['number']}" for p in PAGES if col in p['filters']]))
    return configs


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply-sql',action='store_true')
    args=parser.parse_args()
    profile=json.loads((ROOT/'migration/evidence/data-profile.json').read_text())
    if any(profile['database_csv_comparison'].values()):
        raise RuntimeError('Source DB/CSV differs; profile and review before migrating')
    digest=sql_json("SELECT md5(string_agg(row_to_json(b)::text, E'\\n' ORDER BY order_id)) AS digest FROM public.amazon_delivery b")[0]['digest']
    if digest!=profile.get('database_fingerprint') or hashlib.sha256((ROOT/'data/amazon_delivery_cleaned.csv').read_bytes()).hexdigest()!=profile['sha256']['data/amazon_delivery_cleaned.csv']:
        raise RuntimeError('Profile is stale; rerun profile.py before applying this migration')
    if args.apply_sql: print(sql((ROOT/'migration/sql/001_delivery_orders.sql').read_text()))
    api=API(); dbid=int(os.environ.get('SUPERSET_DATABASE_ID','2'))
    # Validate existing Superset connection against the discovered database, without logging URI.
    import urllib.parse
    db=api.request('GET',f'database/{dbid}/connection')['result']
    u=urllib.parse.urlparse(db['sqlalchemy_uri'])
    if u.path.lstrip('/')!=os.environ.get('AMAZON_DATABASE','tunglocaldb'):
        raise RuntimeError('Superset database target differs from the profiled PostgreSQL target')
    datasets={}
    for key, statement in DATASET_SQL.items():
        table='delivery_orders' if key=='base' else 'amazon_delivery_'+key
        body=dict(database=dbid,schema='amazon_bi',table_name=table,sql=statement)
        existing=[x for x in api.all('dataset') if x.get('uuid')==uid('dataset:'+key)]
        if existing:
            ident=existing[0]['id']
            d=api.request('GET',f'dataset/{ident}')['result']
            if not (d.get('description') or '').startswith(MARKER):raise RuntimeError('Dataset ownership mismatch')
            api.request('PUT',f'dataset/{ident}',json={'sql':statement})
        else:
            # Do not adopt another dataset merely because its table name matches.
            collision=[x for x in api.all('dataset') if x.get('table_name')==table and x.get('schema')=='amazon_bi']
            if collision:raise RuntimeError('Unowned dataset name collision')
            ident=api.request('POST','dataset/',json={**body,'uuid':uid('dataset:'+key)})['id']
        current=api.request('GET',f'dataset/{ident}')['result']
        metric_ids={m['metric_name']:m['id'] for m in current['metrics']}
        metrics=[{**m,**({'id':metric_ids[m['metric_name']]} if m['metric_name'] in metric_ids else {})}
                 for m in dataset_metrics(key)]
        labels={'order_date':'Order_Date','order_hour':'Order_Hour','distance_band':'Distance Band',
                'traffic':'Traffic','weather':'Weather','vehicle':'Vehicle','area':'Area','category':'Category',
                'age_group':'Age_Group','rating_group':'Rating_Group',
                'matrix_area':'Area','matrix_traffic':'Traffic','matrix_day':'Day_Name','matrix_hour':'Order_Hour'}
        columns=[dict(id=c['id'],column_name=c['column_name'],verbose_name=labels.get(c['column_name'],c.get('verbose_name')))
                 for c in current['columns']]
        api.request('PUT',f'dataset/{ident}',json=dict(description=MARKER+'; grain='+(
            'one order' if key=='base' else 'order × explicit total cells; group by matrix dimensions only'),
            main_dttm_col='order_date',filter_select_enabled=True,metrics=metrics,columns=columns))
        datasets[key]=ident
    charts={}
    for v in visuals():
        ds=datasets[v.get('dataset','base')]; f=form(v,ds)
        charts[v['key']]=api.upsert('chart',v['key'],dict(slice_name=title(v),
            description=MARKER+'; PDF '+v['key']+'; original DAX unavailable',
            datasource_id=ds,datasource_type='table',viz_type=f['viz_type'],
            params=json.dumps(f),query_context=json.dumps(query(v,ds))))
    metadata=dict(native_filter_configuration=filters(datasets,charts),filter_bar_orientation='HORIZONTAL',
        cross_filters_enabled=False,chart_configuration={},
        color_scheme='supersetColors',label_colors={'motorcycle':'#118DFF','scooter':'#161BA2','van':'#E66C37',
        'Jam':'#118DFF','Low':'#161BA2','Medium':'#E66C37','High':'#6B007B'},
        refresh_frequency=0,expanded_slices={},timed_refresh_immune_slices=[],
        map_label_colors={},shared_label_colors=[],color_scheme_domain=[])
    metadata['label_colors'].update({'avg_time':'#118DFF','avg_time_yellow':'#FBE34D',
        'avg_time_red':'#D64550','pickup':'#118DFF','pickup_yellow':'#FBE34D',
        'orders':'#118DFF','long_rate':'#118DFF','rating':'#118DFF'})
    metadata['label_colors'].update({'Average Delivery Time':'#118DFF',
        'Average Delivery Time by Traffic':'#FBE34D','Average Delivery Time by Order_Date':'#D64550',
        'Average Pickup Delay':'#118DFF','Average Pickup Delay by Traffic':'#FBE34D',
        'Total Orders':'#118DFF','Long Delivery Rate':'#118DFF','Average Agent Rating':'#118DFF'})
    # Single-series colors must be local; average metric appears in both yellow and blue visuals.
    css='''.dashboard-content {background:#fff;} .dashboard-chart {border:1px solid #118DFF; border-radius:2px;}
    .dashboard-component-tabs-content {background:#fff;} .header-title a {font-size:14px;line-height:18px;}'''
    for v in visuals():
        if v['kind']=='kpi' and v['key'].startswith('p1-'):
            css+=f' .dashboard-chart-id-{charts[v["key"]]} .chart-slice {{background:#FBE34D; border:1px solid #118DFF;border-radius:6px;}}'
        if v['kind']=='kpi':
            css+=f' .dashboard-chart-id-{charts[v["key"]]} .chart-slice > div:first-child {{display:none;}}'
        if v['kind']=='pivot':
            css+=f' .dashboard-chart-id-{charts[v["key"]]} table thead tr:nth-child(2) {{display:none;}}'
            css+=f' .dashboard-chart-id-{charts[v["key"]]} table td, .dashboard-chart-id-{charts[v["key"]]} table td a {{color:#222!important;}}'
    themes=api.all('theme')
    light=[t for t in themes if t.get('is_system') and t.get('theme_name')=='THEME_DEFAULT']
    dashbody=dict(dashboard_title='Amazon Delivery · 5 trang PDF',slug='amazon-delivery-intelligence',
        published=True,position_json=json.dumps(layout(charts)),json_metadata=json.dumps(metadata),css=css)
    if light:dashbody['theme_id']=light[0]['id']
    # UUID identity plus slug collision protection; no adoption by title.
    for d in api.all('dashboard'):
        if d.get('slug')==dashbody['slug'] and d.get('uuid')!=uid('dashboard:main'):
            raise RuntimeError('Dashboard slug belongs to another resource')
    dashboard=api.upsert('dashboard','main',dashbody)
    # Layout JSON alone does not populate Dashboard.slices in Superset 6.
    # Link through the chart API so /dashboard/{id}/charts returns every visual.
    for v in visuals():
        ident=charts[v['key']];ds=datasets[v.get('dataset','base')]
        f=form(v,ds);f.update(slice_id=ident,dashboards=[dashboard])
        context=query(v,ds);context['form_data']=f
        api.request('PUT',f'chart/{ident}',json={'dashboards':[dashboard],
            'params':json.dumps(f),'query_context':json.dumps(context)})
    state=dict(database_id=dbid,datasets=datasets,charts=charts,dashboard_id=dashboard,
        dashboard_url=api.base+'/superset/dashboard/amazon-delivery-intelligence/',
        source='reports/amazon_delivery_dashboard.pdf',pages=5,
        scope_confirmation='User corrected 4 pages to 5 on 2026-10-21',
        source_tab_names='unavailable; Trang 1..5 are positional navigation labels')
    save('migration/.state.json',state)
    save('migration/evidence/deployment.json',state)
    print(json.dumps({'dashboard':state['dashboard_url'],'charts':len(charts),'pages':5,'datasets':datasets},ensure_ascii=False))


if __name__=='__main__': main()
