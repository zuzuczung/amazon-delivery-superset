"""Dashboard A: severity concentration and order-level exceptions."""
import copy

TIME_RANGE = '2022-02-11 : 2022-04-07'
DATASET_SQL = """WITH b AS (
 SELECT d.*, floor(distance_km/3)::int AS peer_distance_band,
        (store_latitude<>0 AND store_longitude<>0 AND drop_latitude<>0 AND drop_longitude<>0) AS coordinates_nonzero
 FROM amazon_bi.delivery_orders d
 WHERE order_date >= DATE '2022-02-11' AND order_date < DATE '2022-04-07'
), peers AS (
 SELECT area,traffic,weather,peer_distance_band,count(*) AS peer_n,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY delivery_time) AS peer_median
 FROM b WHERE coordinates_nonzero GROUP BY area,traffic,weather,peer_distance_band
)
SELECT b.*, greatest(delivery_time-160,0) AS excess_minutes,
       area || ' · ' || traffic || ' · ' || weather AS risk_group,
       CASE WHEN delivery_time<=160 THEN '00 · Không quá 160'
            WHEN delivery_time<=180 THEN '01 · Trên 160–180'
            WHEN delivery_time<=200 THEN '02 · Trên 180–200'
            ELSE '03 · Trên 200' END AS severity_band,
       lpad(floor(distance_km)::int::text,2,'0') || '–' ||
       lpad((floor(distance_km)::int+1)::text,2,'0') AS distance_cell,
       lpad((floor(delivery_time/20)::int*20)::text,3,'0') || '–' ||
       lpad((floor(delivery_time/20)::int*20+20)::text,3,'0') AS time_cell,
       p.peer_n, p.peer_median,
       CASE WHEN b.coordinates_nonzero AND p.peer_n>=30 THEN delivery_time-p.peer_median END AS peer_delta
FROM b LEFT JOIN peers p USING(area,traffic,weather,peer_distance_band)"""

METRICS = {
 'orders': ('Số đơn', 'COUNT(order_id)', ',d'),
 'long_orders': ('Số đơn trên 160 phút', 'COUNT(*) FILTER (WHERE delivery_time>160)', ',d'),
 'severe_orders': ('Số đơn trên 200 phút', 'COUNT(*) FILTER (WHERE delivery_time>200)', ',d'),
 'excess': ('Tổng phút vượt mốc 160', 'SUM(excess_minutes)', ',.0f'),
 'excess_per_long': ('Phút vượt trên mỗi đơn kéo dài', 'SUM(excess_minutes)::numeric/NULLIF(COUNT(*) FILTER (WHERE delivery_time>160),0)', ',.1f'),
 'cumulative_share': ('Tỷ trọng phút vượt tích lũy', 'SUM(SUM(excess_minutes)) OVER (ORDER BY SUM(excess_minutes) DESC,risk_group ROWS UNBOUNDED PRECEDING)::numeric/NULLIF(SUM(SUM(excess_minutes)) OVER(),0)', '.1%'),
 'order_share': ('Tỷ trọng số đơn', 'COUNT(order_id)::numeric/NULLIF(SUM(COUNT(order_id)) OVER(),0)', '.1%'),
 'excess_share': ('Tỷ trọng phút vượt', 'SUM(excess_minutes)::numeric/NULLIF(SUM(SUM(excess_minutes)) OVER(),0)', '.1%'),
 'peer_delta': ('Lệch trung vị nhóm (phút)', 'MAX(peer_delta)', '+,.0f'),
}
LABELS = {
 'order_id':'Mã đơn', 'order_date':'Ngày đặt hàng', 'area':'Khu vực',
 'traffic':'Giao thông', 'weather':'Thời tiết', 'vehicle':'Phương tiện',
 'category':'Danh mục sản phẩm', 'risk_group':'Khu vực · giao thông · thời tiết',
 'severity_band':'Mức thời gian giao (phút)', 'distance_cell':'Khoảng cách (km)',
 'time_cell':'Thời gian giao (phút)', 'distance_km':'Khoảng cách (km)',
 'delivery_time':'Thời gian giao (phút)', 'excess_minutes':'Phút vượt mốc 160',
 'peer_n':'Số đơn nhóm tham chiếu', 'peer_median':'Trung vị nhóm (phút)',
 'peer_delta':'Lệch trung vị nhóm (phút)', 'coordinates_nonzero':'Tọa độ khác 0',
}


def filt(subject, op, value=None):
    return dict(expressionType='SIMPLE',clause='WHERE',subject=subject,operator=op,comparator=value)


VALID = [filt('coordinates_nonzero','==',True)]
SHORT_LONG = VALID+[filt('distance_km','<',5),filt('delivery_time','>',160)]


CHARTS = [
 dict(key='severity-excess-kpi', title='Tổng phút vượt mốc 160',kind='kpi',metrics=['excess'],page=1),
 dict(key='severity-severe-kpi', title='Số đơn trên 200 phút',kind='kpi',metrics=['severe_orders'],page=1),
 dict(key='severity-mean-excess-kpi',title='Phút vượt trên mỗi đơn kéo dài',kind='kpi',metrics=['excess_per_long'],page=1),
 dict(key='severity-pareto',title='Pareto phút vượt mốc 160 · 15 nhóm đứng đầu',kind='pareto',dimension='risk_group',metrics=['excess','cumulative_share'],limit=15,page=1),
 dict(key='severity-priority',title='Số đơn kéo dài × mức vượt trung bình · kích thước = số đơn',kind='bubble',dimension='risk_group',series='area',metrics=['long_orders','excess_per_long','orders'],page=1,
      having='COUNT(*) FILTER (WHERE delivery_time>160)>0'),
 dict(key='severity-levels',title='Phân bố mức độ kéo dài theo khu vực',kind='bar',dimension='area',series='severity_band',metrics=['orders'],stack=True,page=1,filters=[filt('delivery_time','>',160)]),
 dict(key='severity-contribution',title='Tỷ trọng đơn so với tỷ trọng phút vượt · 12 nhóm đứng đầu',kind='bar',dimension='risk_group',metrics=['order_share','excess_share'],sort_metric='excess_share',horizontal=True,limit=12,page=1),
 dict(key='exceptions-short-kpi',title='Đơn dưới 5 km nhưng trên 160 phút',kind='kpi',metrics=['orders'],filters=SHORT_LONG,page=2),
 dict(key='exceptions-density',title='Mật độ đơn theo khoảng cách và thời gian giao',kind='heatmap',dimension='distance_cell',series='time_cell',metrics=['orders'],filters=VALID,page=2),
 dict(key='exceptions-conditions',title='Đơn dưới 5 km và trên 160 phút · giao thông × thời tiết',kind='heatmap',dimension='traffic',series='weather',metrics=['orders'],filters=SHORT_LONG,page=2),
 dict(key='exceptions-deviation',title='20 đơn quãng đường ngắn lệch trung vị nhóm nhiều nhất',kind='bar',dimension='order_id',metrics=['peer_delta'],horizontal=True,limit=20,page=2,
      filters=SHORT_LONG+[filt('peer_n','>=',30)]),
 dict(key='exceptions-records',title='Đơn dưới 5 km và trên 160 phút · tối đa 200 đơn',kind='records',metrics=[],limit=200,filters=SHORT_LONG,page=2),
]


def form(v,dataset_id):
    kinds=dict(kpi='big_number_total',bar='echarts_timeseries_bar',pareto='table',
               bubble='bubble_v2',heatmap='heatmap_v2',records='table')
    f=dict(datasource=f'{dataset_id}__table',viz_type=kinds[v['kind']],
           time_range=TIME_RANGE,granularity_sqla='order_date',
           adhoc_filters=copy.deepcopy(v.get('filters',[])),extra_form_data={},
           metrics=v['metrics'],groupby=[],row_limit=v.get('limit',1000),
           order_desc=True,color_scheme='supersetColors',annotation_layers=[],
           show_legend=True,legendType='scroll',legendOrientation='top',
           rich_tooltip=True,xAxisForceCategorical=True,truncateYAxis=False,
           y_axis_bounds=[0,None],x_axis_title_margin=30,y_axis_title_margin=40,
           label_colors={},show_empty_columns=True)
    if v.get('having'):
        f['adhoc_filters'].append(dict(expressionType='SQL',clause='HAVING',sqlExpression=v['having']))
    metric=v['metrics'][0] if v['metrics'] else None
    if metric:
        f.update(number_format=METRICS[metric][2],y_axis_format=METRICS[metric][2])
    if v['kind']=='kpi':
        f.update(metric=metric,subheader='',header_font_size=.6,
                 subheader_font_size=.13,show_legend=False)
    elif v['kind']=='pareto':
        f.update(query_mode='aggregate',groupby=[v['dimension']],all_columns=[],
          orderby=[['excess',False]],order_by_cols=[],percent_metrics=[],
          include_search=False,page_length=0,show_cell_bars=True,show_totals=False,
          column_config={k:{'d3NumberFormat':METRICS[k][2]} for k in v['metrics']})
    elif v['kind']=='bar':
        f.update(x_axis=v['dimension'],groupby=[v['series']] if v.get('series') else [],
                 orderby=[[v.get('sort_metric',metric),False]],
                 x_axis_sort='sum',x_axis_sort_asc=False,
                 orientation='horizontal' if v.get('horizontal') else 'vertical',
                 x_axis_title='',y_axis_title='',xAxisLabelRotation=45 if v['dimension']=='risk_group' and not v.get('horizontal') else 0,
                 truncateXAxis=True,show_value=False,zoomable=False,
                 show_legend=bool(v.get('series') or len(v['metrics'])>1),
                 stack='Stack' if v.get('stack') else None)
    elif v['kind']=='bubble':
        f.update(entity=v['dimension'],series=v['series'],x='long_orders',y='excess_per_long',size='orders',
                 x_axis_label='Số đơn trên 160 phút',y_axis_label='Phút vượt / đơn kéo dài',
                 xAxisFormat=',d',y_axis_format=',.1f',tooltipSizeFormat=',d',
                 max_bubble_size='30',opacity=.65,x_axis_bounds=[0,None],
                 truncateYAxis=False,truncateXAxis=False)
    elif v['kind']=='heatmap':
        f.update(x_axis=v['dimension'],groupby=v['series'],metric=metric,
                 linear_color_scheme='schemeYlOrRd',normalize_across='heatmap',
                 sort_x_axis='alpha_asc',sort_y_axis='alpha_asc',
                 show_legend=True,legend_type='continuous',show_values=v['key']=='exceptions-conditions',
                 legendType='continuous',
                 left_margin=70,bottom_margin=55,xAxisLabelRotation=0,
                 value_format=',d',y_axis_format=',d',xscale_interval=1,yscale_interval=1,
                 x_axis_label=LABELS[v['dimension']],y_axis_label=LABELS[v['series']],
                 border_width=.5)
    elif v['kind']=='records':
        cols=['order_id','order_date','area','traffic','weather','distance_km','delivery_time',
              'excess_minutes','peer_n','peer_median','peer_delta']
        f.update(query_mode='raw',all_columns=cols,groupby=[],metrics=[],
                 include_search=True,page_length=20,show_cell_bars=False,
                 order_by_cols=['["excess_minutes", false]','["order_id", true]'],
                 table_timestamp_format='%Y-%m-%d',column_config={
                     'distance_km':{'d3NumberFormat':',.2f'},
                     'peer_median':{'d3NumberFormat':',.1f'},
                     'peer_delta':{'d3NumberFormat':'+,.0f'}},show_totals=False)
    return f


def query(v,dataset_id,extra_filters=None,time_range=None):
    f=form(v,dataset_id)
    filters=[dict(col=x['subject'],op=x['operator'],val=x['comparator']) for x in f['adhoc_filters'] if x['expressionType']=='SIMPLE']
    filters+=extra_filters or []
    columns=([v['dimension']] if v.get('dimension') else [])+([v['series']] if v.get('series') else [])
    if v['kind']=='records':
        columns=f['all_columns']
    sort=v.get('sort_metric',v['metrics'][0] if v['metrics'] else 'excess_minutes')
    q=dict(columns=columns,metrics=v['metrics'],filters=filters,
           time_range=time_range or TIME_RANGE,granularity='order_date',
           extras={'where':'','having':v.get('having','')},row_limit=f['row_limit'],
           orderby=[[sort,False]],order_desc=True)
    queries=[q]
    return dict(datasource={'id':dataset_id,'type':'table'},force=False,queries=queries,
                form_data=f,result_format='json',result_type='full')


PAGES = [dict(name='Mức độ tập trung',rows=[
    ['severity-excess-kpi','severity-severe-kpi','severity-mean-excess-kpi'],
    ['severity-pareto'],['severity-priority','severity-levels'],['severity-contribution']]),
 dict(name='Đơn cần kiểm tra',rows=[['exceptions-short-kpi'],
    ['exceptions-density'],['exceptions-conditions'],['exceptions-deviation'],['exceptions-records']])]
