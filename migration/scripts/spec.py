"""Inventory transcribed from the five-page dashboard PDF (not the six-page report).

Page labels are positional: original tab names and all DAX are unavailable.
SQL metric definitions below are proposed equivalents, verified against CSV/PDF.
"""
METRICS = {
    'orders': ('Tổng số đơn hàng', 'COUNT(order_id)', ',d'),
    'avg_time': ('Thời gian giao hàng trung bình', 'AVG(delivery_time)', ',.2f'),
    'median': ('Trung vị thời gian giao hàng', 'PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_time)', ',.2f'),
    'p90': ('Thời gian giao hàng P90', 'PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_time)', ',.2f'),
    'distance': ('Khoảng cách giao hàng trung bình', 'AVG(distance_km)', ',.2f'),
    'long_rate': ('Tỷ lệ giao hàng kéo dài', 'SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0)', '.1%'),
    'pickup': ('Thời gian chờ lấy hàng trung bình', 'AVG(pickup_delay_min)', ',.2f'),
    'rating': ('Điểm đánh giá tài xế trung bình', 'AVG(agent_rating)', ',.1f'),
}
# Presentation aliases keep the same SQL/label while allowing the PDF's
# yellow/red/blue single-series colors to coexist in Superset's shared palette.
for alias,base in [('avg_time_yellow','avg_time'),('avg_time_red','avg_time'),('pickup_yellow','pickup')]:
    METRICS[alias]=METRICS[base]


def visual(key, title, kind, metric, dimension=None, **extra):
    return dict(key=key, title=title, kind=kind, metric=metric, dimension=dimension, **extra)


PAGES = [
    dict(number=1, filters=['order_date','traffic','weather','vehicle','area','category'], rows=[
        [visual('p1-01','Total Orders','kpi','orders'),
         visual('p1-02','Average Delivery Time','kpi','avg_time'),
         visual('p1-03','Median Delivery Time','kpi','median'),
         visual('p1-04','P90 Delivery Time','kpi','p90'),
         visual('p1-05','Average Distance','kpi','distance'),
         visual('p1-06','Long Delivery Rate','kpi','long_rate')],
        [visual('p1-07','Average Delivery Time by Traffic','bar','avg_time_yellow','traffic',horizontal=True,yellow=True),
         visual('p1-08','Total Orders by Vehicle','pie','orders','vehicle'),
         visual('p1-09','Average Delivery Time by Order_Date','line','avg_time_red','order_date',ascending=True)],
        [visual('p1-10','Average Delivery Time by Area','bar','avg_time','area'),
         visual('p1-11','Total Orders by Category','bar','orders','category',horizontal=True)],
    ]),
    dict(number=2, filters=['order_date','vehicle','category'], rows=[
        [visual('p2-01','Average Delivery Time by Distance Band and Traffic','line','avg_time','distance_band',series='traffic',ascending=True),
         visual('p2-02',None,'pivot','long_rate','matrix_area',columns='matrix_traffic',dataset='area_matrix')],
        [visual('p2-03','Average Pickup Delay by Traffic','bar','pickup_yellow','traffic',horizontal=True,yellow=True)],
        [visual('p2-04',None,'pivot','avg_time','matrix_day',columns='matrix_hour',dataset='hour_matrix')],
    ]),
    dict(number=3, filters=['order_date','traffic','area'], rows=[
        [visual('p3-01','Average Delivery Time by Agent Rating','bar','avg_time','rating_group',exclude_null=True,number_format=',.0f',labels=True),
         visual('p3-02','Average Delivery Time by Agent Age Group','bar','avg_time','age_group',horizontal=True)],
        [visual('p3-03','Long Delivery Rate by Category','bar','long_rate','category',horizontal=True,labels=True),
         visual('p3-04','Average Agent Rating by Category','bar','rating','category',labels=True)],
    ]),
    dict(number=4, filters=['order_date','area','vehicle','traffic'], rows=[
        [visual('p4-01','Average Delivery Time by Weather','bar','avg_time','weather',horizontal=True),
         visual('p4-02','Long Delivery Rate by Weather','bar','long_rate','weather')],
        [visual('p4-03','Average Pickup Delay by Order_Hour','line','pickup','order_hour',ascending=True),
         visual('p4-04','Total Orders by Order_Hour','bar','orders','order_hour',ascending=True)],
    ]),
    dict(number=5, filters=['order_date','traffic','weather','vehicle','area'], rows=[
        [visual('p5-01','Average Delivery Time','kpi','avg_time'),
         visual('p5-02','Long Delivery Rate','kpi','long_rate')],
        [visual('p5-03','Long Delivery Rate by Traffic','bar','long_rate','traffic',fixed_traffic_order=True,horizontal=True),
         visual('p5-04','Long Delivery Rate by Category','bar','long_rate','category',source_subset_unknown=True)],
        [visual('p5-05',None,'table','long_rate','matrix_area',dataset='area_totals',metrics=['p90','pickup','long_rate','distance','avg_time','orders'])],
    ]),
]

CONCLUSION = '''Giao thông ùn tắc có tỷ lệ giao hàng kéo dài và thời gian giao hàng trung bình cao nhất.

* Khu vực Semi-Urban có tỷ lệ giao hàng kéo dài rất cao, nhưng số lượng đơn hàng ít nên cần xem đây là một điểm bất thường cần phân tích thêm.
* Thời gian giao hàng có xu hướng tăng khi khoảng cách giao hàng tăng; thời gian chờ lấy hàng cũng là một yếu tố vận hành cần theo dõi.

**Kết luận**

Cần ưu tiên tối ưu giao hàng trong các khung giờ ùn tắc, giảm thời gian chờ lấy hàng và tập trung phân tích các khu vực hoặc nhóm đơn hàng có rủi ro giao chậm cao.

_Nội dung tĩnh chép từ PDF trang 5; không tự cập nhật theo bộ lọc._'''

# Base grain: order. Matrix dataset grains deliberately replicate each order for
# explicit total cells. They NEVER expose COUNT metrics across those copies.
# Every filter is applied to the retained original columns before aggregation.
DATASET_SQL = {
    'base': None,
    'area_matrix': '''SELECT b.*, v.matrix_area, v.matrix_traffic
        FROM amazon_bi.delivery_orders b CROSS JOIN LATERAL (VALUES
        (b.area,b.traffic),(b.area,'Total'),('Total',b.traffic),('Total','Total'))
        AS v(matrix_area,matrix_traffic)''',
    'hour_matrix': '''SELECT b.*, v.matrix_day, v.matrix_hour
        FROM amazon_bi.delivery_orders b CROSS JOIN LATERAL (VALUES
        (b.weekday_sorted,lpad(b.order_hour::text,2,'0')),(b.weekday_sorted,'Total'),
        ('Total',lpad(b.order_hour::text,2,'0')),('Total','Total'))
        AS v(matrix_day,matrix_hour)''',
    'area_totals': '''SELECT b.*, v.matrix_area FROM amazon_bi.delivery_orders b
        CROSS JOIN LATERAL (VALUES (b.area),('Total')) AS v(matrix_area)''',
}


def title(v):
    # Keep v['title'] as the original PDF title for provenance and crosswalks.
    return CHART_TITLES[v['key']]


CHART_TITLES = {
    'p1-01': 'Tổng số đơn hàng',
    'p1-02': 'Thời gian giao hàng trung bình',
    'p1-03': 'Trung vị thời gian giao hàng',
    'p1-04': 'Thời gian giao hàng P90',
    'p1-05': 'Khoảng cách giao hàng trung bình',
    'p1-06': 'Tỷ lệ giao hàng kéo dài',
    'p1-07': 'Thời gian giao hàng trung bình theo giao thông',
    'p1-08': 'Tổng số đơn hàng theo phương tiện',
    'p1-09': 'Thời gian giao hàng trung bình theo ngày đặt hàng',
    'p1-10': 'Thời gian giao hàng trung bình theo khu vực',
    'p1-11': 'Tổng số đơn hàng theo danh mục sản phẩm',
    'p2-01': 'Thời gian giao hàng trung bình theo nhóm khoảng cách và giao thông',
    'p2-02': 'Tỷ lệ giao hàng kéo dài theo khu vực và giao thông',
    'p2-03': 'Thời gian chờ lấy hàng trung bình theo giao thông',
    'p2-04': 'Thời gian giao hàng trung bình theo thứ và giờ đặt hàng',
    'p3-01': 'Thời gian giao hàng trung bình theo điểm đánh giá tài xế',
    'p3-02': 'Thời gian giao hàng trung bình theo nhóm tuổi tài xế',
    'p3-03': 'Tỷ lệ giao hàng kéo dài theo danh mục sản phẩm',
    'p3-04': 'Điểm đánh giá tài xế trung bình theo danh mục sản phẩm',
    'p4-01': 'Thời gian giao hàng trung bình theo thời tiết',
    'p4-02': 'Tỷ lệ giao hàng kéo dài theo thời tiết',
    'p4-03': 'Thời gian chờ lấy hàng trung bình theo giờ đặt hàng',
    'p4-04': 'Tổng số đơn hàng theo giờ đặt hàng',
    'p5-01': 'Thời gian giao hàng trung bình',
    'p5-02': 'Tỷ lệ giao hàng kéo dài',
    'p5-03': 'Tỷ lệ giao hàng kéo dài theo giao thông',
    'p5-04': 'Tỷ lệ giao hàng kéo dài theo danh mục sản phẩm',
    'p5-05': 'Tổng hợp hiệu suất giao hàng theo khu vực',
}

COLUMN_LABELS = {
    'order_date': 'Ngày đặt hàng', 'order_hour': 'Giờ đặt hàng',
    'distance_band': 'Nhóm khoảng cách', 'traffic': 'Giao thông',
    'weather': 'Thời tiết', 'vehicle': 'Phương tiện', 'area': 'Khu vực',
    'category': 'Danh mục sản phẩm', 'age_group': 'Nhóm tuổi tài xế',
    'rating_group': 'Nhóm điểm đánh giá tài xế', 'matrix_area': 'Khu vực',
    'matrix_traffic': 'Giao thông', 'matrix_day': 'Thứ trong tuần',
    'matrix_hour': 'Giờ đặt hàng', 'weekday_sorted': 'Thứ trong tuần',
    'delivery_band': 'Nhóm thời gian giao hàng',
    'pickup_delay_band': 'Nhóm thời gian chờ lấy hàng',
}

METRIC_ALIAS_LABELS = {
    'avg_time_yellow': CHART_TITLES['p1-07'],
    'avg_time_red': CHART_TITLES['p1-09'],
    'pickup_yellow': CHART_TITLES['p2-03'],
}


def visuals():
    return [v for p in PAGES for row in p['rows'] for v in row]


def metric_keys(dataset):
    # These rollup queries are restricted to grouping by their display dimensions.
    return ['long_rate'] if dataset == 'area_matrix' else ['avg_time'] if dataset == 'hour_matrix' else list(METRICS)
