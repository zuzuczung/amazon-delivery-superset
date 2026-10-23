"""Dashboard B: direct standardization on common condition strata."""
import copy
from common import ROOT

KEY='vehicle-b-v1'
SLUG='amazon-delivery-so-sanh-phuong-tien'
TITLE='Amazon Delivery · So sánh phương tiện cùng điều kiện'
STRATA_SQL=(ROOT/'migration/sql/003_vehicle_strata.sql').read_text().strip()
VEHICLE_SQL='''WITH strata AS ('''+STRATA_SQL+''')
SELECT s.area,s.traffic,s.weather,s.distance_band,s.group_label,s.eligible,
       s.support_status,s.pooled_n,v.vehicle,v.vehicle_orders,v.vehicle_time,v.vehicle_mean
FROM strata s CROSS JOIN LATERAL (VALUES
 ('motorcycle',s.n_motor,s.time_motor,s.mean_motor),
 ('scooter',s.n_scooter,s.time_scooter,s.mean_scooter)
) AS v(vehicle,vehicle_orders,vehicle_time,vehicle_mean)
WHERE v.vehicle_orders>0'''
DATASETS={'strata':STRATA_SQL,'vehicles':VEHICLE_SQL}
COMMON='SUM(pooled_n) FILTER (WHERE eligible)'
METRICS={
 'strata':{
  'adjusted_gap':('Chênh lệch sau cân bằng (phút)',f'SUM(gap*pooled_n) FILTER (WHERE eligible)/NULLIF({COMMON},0)','+,.2f'),
  'coverage':('Độ bao phủ mẫu so sánh',f'COALESCE({COMMON},0)::double precision/NULLIF(SUM(pooled_n),0)','.1%'),
  'common_orders':('Số đơn trong mẫu so sánh',f'COALESCE({COMMON},0)',',d'),
  'group_count':('Số nhóm điều kiện','COUNT(*)',',d'),
  'n_motor':('Số đơn motorcycle','SUM(n_motor)',',d'),
  'n_scooter':('Số đơn scooter','SUM(n_scooter)',',d'),
  'mean_motor':('Motorcycle (phút)','SUM(time_motor)::double precision/NULLIF(SUM(n_motor),0)',',.2f'),
  'mean_scooter':('Scooter (phút)','SUM(time_scooter)::double precision/NULLIF(SUM(n_scooter),0)',',.2f'),
  'group_gap':('Motorcycle − scooter (phút)','MAX(gap)','+,.2f'),
 },
 'vehicles':{
  'raw_mean':('Thô · cùng mẫu','SUM(vehicle_time)::double precision/NULLIF(SUM(vehicle_orders),0)',',.2f'),
  'adjusted_mean':('Đã cân bằng','SUM(vehicle_mean*pooled_n)/NULLIF(SUM(pooled_n),0)',',.2f'),
  'vehicle_orders':('Số đơn','SUM(vehicle_orders)',',d'),
 }
}
LABELS={'area':'Khu vực','traffic':'Giao thông','weather':'Thời tiết',
        'distance_band':'Nhóm khoảng cách','group_label':'Nhóm điều kiện',
        'vehicle':'Phương tiện','eligible':'Đủ mẫu','support_status':'Điều kiện mẫu',
        'gap_bin':'Mốc dưới khoảng 5 phút','gap':'Chênh lệch (phút)'}
FILTER_COLUMNS=['area','traffic','weather','distance_band']
CHARTS=[
 dict(key='gap-kpi',kind='kpi',dataset='strata',metrics=['adjusted_gap'],title='Motorcycle − scooter sau cân bằng (phút)'),
 dict(key='coverage-kpi',kind='kpi',dataset='strata',metrics=['coverage'],title='Độ bao phủ mẫu so sánh'),
 dict(key='sample-kpi',kind='kpi',dataset='strata',metrics=['common_orders'],title='Số đơn trong mẫu so sánh'),
 dict(key='comparison',kind='bar',dataset='vehicles',dimension='vehicle',metrics=['raw_mean','adjusted_mean'],eligible_only=True,
      title='Thời gian giao trước và sau cân bằng · cùng mẫu'),
 dict(key='coverage',kind='bar',dataset='vehicles',dimension='vehicle',series='support_status',metrics=['vehicle_orders'],stack=True,
      title='Đơn đủ mẫu và chưa đủ mẫu theo phương tiện'),
 dict(key='distribution',kind='bar',dataset='strata',dimension='gap_bin',metrics=['group_count'],eligible_only=True,ascending=True,
      title='Phân bố chênh lệch giữa các nhóm · mỗi cột rộng 5 phút'),
 dict(key='groups',kind='table',dataset='strata',dimension='group_label',eligible_only=True,
      metrics=['n_motor','n_scooter','mean_motor','mean_scooter','group_gap'],
      title='Chi tiết các nhóm đủ mẫu · sắp xếp theo mức chênh lệch')
]


def form(v,dataset_id):
    definitions=METRICS[v['dataset']];first=v['metrics'][0]
    f=dict(datasource=f'{dataset_id}__table',viz_type=dict(kpi='big_number_total',bar='echarts_timeseries_bar',table='table')[v['kind']],
           time_range='No filter',adhoc_filters=[],extra_form_data={},metrics=v['metrics'],groupby=[],
           row_limit=1000,order_desc=True,color_scheme='supersetColors',annotation_layers=[],
           show_legend=True,legendType='scroll',legendOrientation='top',rich_tooltip=True,
           show_empty_columns=True,y_axis_format=definitions[first][2],number_format=definitions[first][2])
    if v.get('eligible_only'):
        f['adhoc_filters']=[dict(expressionType='SIMPLE',clause='WHERE',subject='eligible',operator='==',comparator=True)]
    if v['kind']=='kpi':
        f.update(metric=first,subheader='',header_font_size=.6,show_legend=False)
    elif v['kind']=='bar':
        f.update(x_axis=v['dimension'],groupby=[v['series']] if v.get('series') else [],
                 xAxisForceCategorical=not v.get('ascending',False),xAxisLabelInterval=0,x_axis_sort='name',
                 x_axis_sort_asc=True,x_axis_title=LABELS[v['dimension']] if v.get('ascending') else '',
                 y_axis_title='Số nhóm điều kiện' if v.get('ascending') else 'Số đơn' if v.get('stack') else 'Phút',
                 x_axis_title_margin=30,y_axis_title_margin=40,
                 stack='Stack' if v.get('stack') else None,show_value=not v.get('ascending'),
                 show_legend=bool(v.get('series') or len(v['metrics'])>1),
                 truncateYAxis=False,y_axis_bounds=[0,None],zoomable=False,
                 orderby=[[v['dimension'],True]])
    else:
        f.update(query_mode='aggregate',groupby=[v['dimension']],all_columns=[],
                 percent_metrics=[],include_search=True,page_length=15,show_cell_bars=True,
                 show_totals=False,order_by_cols=[],orderby=[['group_gap',False]],
                 timeseries_limit_metric='group_gap',
                 column_config={k:{'d3NumberFormat':definitions[k][2]} for k in v['metrics']})
    return f


def query(v,dataset_id,filters=None):
    f=form(v,dataset_id)
    fs=[dict(col='eligible',op='==',val=True)] if v.get('eligible_only') else []
    fs+=filters or []
    columns=([v['dimension']] if v.get('dimension') else [])+([v['series']] if v.get('series') else [])
    orderby=[['group_gap',False]] if v['kind']=='table' else [[v['dimension'],True]] if v.get('dimension') else []
    q=dict(columns=columns,metrics=v['metrics'],filters=fs,time_range='No filter',
           extras={'where':'','having':''},row_limit=1000,orderby=orderby,order_desc=True)
    return dict(datasource={'id':dataset_id,'type':'table'},force=False,queries=[q],
                form_data=f,result_format='json',result_type='full')
