"""Five drill-down dashboards derived from the five-page main dashboard.

These views use only fields supported by the curated delivery-order dataset.
They add segment comparisons and distributions without claiming individual
driver performance, revenue, cost, or contractual SLA measurements.
"""


def visual(key, title, kind, metric, dimension=None, **extra):
    return dict(key=key, title=title, kind=kind, metric=metric,
                dimension=dimension, **extra)


def page(name, key, rows):
    return dict(name=name, key=key, rows=rows)


DASHBOARDS = [
    dict(
        key='child-area', slug='amazon-delivery-khu-vuc',
        title='Amazon Delivery · Phân tích khu vực',
        pages=[
            page('So sánh khu vực', 'overview', [
                [visual('orders', 'Tổng số đơn hàng', 'kpi', 'orders'),
                 visual('avg-time', 'Thời gian giao hàng trung bình', 'kpi', 'avg_time')],
                [visual('avg-area', 'Thời gian giao hàng trung bình theo khu vực', 'bar', 'avg_time', 'area'),
                 visual('long-area', 'Tỷ lệ giao hàng kéo dài theo khu vực', 'bar', 'long_rate', 'area', labels=True)],
                [visual('area-table', 'Bảng tổng hợp hiệu suất theo khu vực', 'table', 'orders', 'area',
                        metrics=['orders', 'avg_time', 'p90', 'long_rate', 'distance', 'pickup'])],
            ]),
            page('Chi tiết khu vực', 'detail', [
                [visual('p90', 'Thời gian giao hàng P90', 'kpi', 'p90'),
                 visual('long-rate', 'Tỷ lệ giao hàng kéo dài', 'kpi', 'long_rate')],
                [visual('daily', 'Xu hướng thời gian giao hàng theo ngày', 'line', 'avg_time', 'order_date', ascending=True),
                 visual('traffic-area', 'Thời gian giao hàng theo khu vực và giao thông', 'pivot', 'avg_time', 'area', columns='traffic')],
                [visual('weather-area', 'Tỷ lệ giao hàng kéo dài theo khu vực và thời tiết', 'pivot', 'long_rate', 'area', columns='weather')],
            ]),
        ],
    ),
    dict(
        key='child-conditions', slug='amazon-delivery-dieu-kien-thoi-diem',
        title='Amazon Delivery · Điều kiện và thời điểm giao',
        pages=[
            page('Giao thông', 'traffic', [
                [visual('avg-time', 'Thời gian giao hàng trung bình', 'kpi', 'avg_time'),
                 visual('p90', 'Thời gian giao hàng P90', 'kpi', 'p90')],
                [visual('avg-traffic', 'Thời gian giao hàng trung bình theo giao thông', 'bar', 'avg_time', 'traffic'),
                 visual('long-traffic', 'Tỷ lệ giao hàng kéo dài theo giao thông', 'bar', 'long_rate', 'traffic', labels=True)],
                [visual('traffic-area', 'Thời gian giao hàng theo giao thông và khu vực', 'pivot', 'avg_time', 'traffic', columns='area')],
            ]),
            page('Thời tiết', 'weather', [
                [visual('orders', 'Tổng số đơn hàng', 'kpi', 'orders'),
                 visual('long-rate', 'Tỷ lệ giao hàng kéo dài', 'kpi', 'long_rate')],
                [visual('avg-weather', 'Thời gian giao hàng trung bình theo thời tiết', 'bar', 'avg_time', 'weather'),
                 visual('long-weather', 'Tỷ lệ giao hàng kéo dài theo thời tiết', 'bar', 'long_rate', 'weather', labels=True)],
                [visual('weather-traffic', 'Thời gian giao hàng theo thời tiết và giao thông', 'pivot', 'avg_time', 'weather', columns='traffic')],
            ]),
            page('Ngày và khung giờ', 'time', [
                [visual('avg-time', 'Thời gian giao hàng trung bình', 'kpi', 'avg_time'),
                 visual('pickup', 'Thời gian chờ lấy hàng trung bình', 'kpi', 'pickup')],
                [visual('weekday-hour', 'Thời gian giao hàng theo thứ và giờ đặt hàng', 'pivot', 'avg_time', 'weekday_sorted', columns='order_hour'),
                 visual('avg-hour', 'Thời gian giao hàng trung bình theo giờ đặt hàng', 'line', 'avg_time', 'order_hour', ascending=True)],
                [visual('long-hour', 'Tỷ lệ giao hàng kéo dài theo giờ đặt hàng', 'bar', 'long_rate', 'order_hour', ascending=True, labels=True)],
            ]),
        ],
    ),
    dict(
        key='child-distance', slug='amazon-delivery-khoang-cach-cho-lay-hang',
        title='Amazon Delivery · Khoảng cách và chờ lấy hàng',
        pages=[
            page('Khoảng cách', 'distance', [
                [visual('distance', 'Khoảng cách giao hàng trung bình', 'kpi', 'distance'),
                 visual('p90', 'Thời gian giao hàng P90', 'kpi', 'p90')],
                [visual('avg-distance', 'Thời gian giao hàng theo nhóm khoảng cách và giao thông', 'line', 'avg_time', 'distance_band', series='traffic', ascending=True),
                 visual('long-distance', 'Tỷ lệ giao hàng kéo dài theo nhóm khoảng cách', 'bar', 'long_rate', 'distance_band', ascending=True, labels=True)],
                [visual('orders-distance', 'Phân bố đơn hàng theo nhóm khoảng cách', 'bar', 'orders', 'distance_band', ascending=True)],
            ]),
            page('Chờ lấy hàng', 'pickup', [
                [visual('pickup', 'Thời gian chờ lấy hàng trung bình', 'kpi', 'pickup'),
                 visual('long-rate', 'Tỷ lệ giao hàng kéo dài', 'kpi', 'long_rate')],
                [visual('avg-pickup-band', 'Thời gian giao hàng theo nhóm thời gian chờ lấy hàng', 'bar', 'avg_time', 'pickup_delay_band', ascending=True),
                 visual('pickup-hour', 'Thời gian chờ lấy hàng theo giờ đặt hàng', 'line', 'pickup', 'order_hour', ascending=True)],
                [visual('pickup-traffic', 'Thời gian chờ lấy hàng theo giao thông', 'bar', 'pickup', 'traffic')],
            ]),
        ],
    ),
    dict(
        key='child-vehicle-product', slug='amazon-delivery-phuong-tien-san-pham',
        title='Amazon Delivery · Phương tiện và sản phẩm',
        pages=[
            page('Phương tiện', 'vehicle', [
                [visual('orders', 'Tổng số đơn hàng', 'kpi', 'orders'),
                 visual('avg-time', 'Thời gian giao hàng trung bình', 'kpi', 'avg_time')],
                [visual('orders-vehicle', 'Tổng số đơn hàng theo phương tiện', 'pie', 'orders', 'vehicle'),
                 visual('avg-vehicle', 'Thời gian giao hàng trung bình theo phương tiện', 'bar', 'avg_time', 'vehicle')],
                [visual('vehicle-traffic', 'Tỷ lệ giao hàng kéo dài theo phương tiện và giao thông', 'pivot', 'long_rate', 'vehicle', columns='traffic')],
            ]),
            page('Danh mục sản phẩm', 'category', [
                [visual('orders', 'Tổng số đơn hàng', 'kpi', 'orders'),
                 visual('long-rate', 'Tỷ lệ giao hàng kéo dài', 'kpi', 'long_rate')],
                [visual('orders-category', 'Tổng số đơn hàng theo danh mục sản phẩm', 'bar', 'orders', 'category', horizontal=True),
                 visual('avg-category', 'Thời gian giao hàng trung bình theo danh mục sản phẩm', 'bar', 'avg_time', 'category', horizontal=True)],
                [visual('category-traffic', 'Tỷ lệ giao hàng kéo dài theo danh mục và giao thông', 'pivot', 'long_rate', 'category', columns='traffic')],
            ]),
        ],
    ),
    dict(
        key='child-driver', slug='amazon-delivery-ho-so-tai-xe',
        title='Amazon Delivery · Hồ sơ tài xế',
        pages=[
            page('Điểm đánh giá', 'rating', [
                [visual('rating', 'Điểm đánh giá tài xế trung bình', 'kpi', 'rating'),
                 visual('avg-time', 'Thời gian giao hàng trung bình', 'kpi', 'avg_time')],
                [visual('avg-rating', 'Thời gian giao hàng theo nhóm điểm đánh giá', 'bar', 'avg_time', 'rating_group', exclude_null=True),
                 visual('long-rating', 'Tỷ lệ giao hàng kéo dài theo nhóm điểm đánh giá', 'bar', 'long_rate', 'rating_group', exclude_null=True, labels=True)],
                [visual('orders-rating', 'Phân bố đơn hàng theo nhóm điểm đánh giá', 'bar', 'orders', 'rating_group', exclude_null=True)],
            ]),
            page('Độ tuổi', 'age', [
                [visual('orders', 'Tổng số đơn hàng', 'kpi', 'orders'),
                 visual('long-rate', 'Tỷ lệ giao hàng kéo dài', 'kpi', 'long_rate')],
                [visual('avg-age', 'Thời gian giao hàng trung bình theo nhóm tuổi', 'bar', 'avg_time', 'age_group'),
                 visual('p90-age', 'Thời gian giao hàng P90 theo nhóm tuổi', 'bar', 'p90', 'age_group')],
                [visual('age-traffic', 'Tỷ lệ giao hàng kéo dài theo nhóm tuổi và giao thông', 'pivot', 'long_rate', 'age_group', columns='traffic')],
            ]),
        ],
    ),
]


FILTERS = ['order_date', 'area', 'traffic', 'weather', 'vehicle', 'category']


def visuals(dashboard):
    return [v for p in dashboard['pages'] for row in p['rows'] for v in row]
