# Bản đồ Power BI → Apache Superset

Nguồn quyết định: `reports/amazon_delivery_dashboard.pdf`, 5 trang. Người dùng sửa phạm vi từ 4 thành 5 trang ngày 21/10/2026.
Tên tab không nằm trong PDF; Trang 1–5 là nhãn vị trí, không được tuyên bố là tên gốc. `amazon_delivery_report.pdf` là bản 6 trang khác KPI và không dùng để tính toán.
Tên biểu đồ Superset được Việt hóa; tiêu đề Power BI gốc được giữ riêng để đối chiếu. Ba bảng/ma trận không có tiêu đề trong PDF được đặt tên tiếng Việt mô tả nội dung.

| Trang | Visual Power BI | Tên biểu đồ Superset | Field | DAX/công thức | Bộ lọc | Dataset/metric | Chart | Thông tin còn thiếu |
|---|---|---|---|---|---|---|---|---|
| 1 | Total Orders | Tổng số đơn hàng |  | DAX chưa xác minh; SQL: orders: COUNT(order_id) | order_date, traffic, weather, vehicle, area, category | base | 175 · kpi | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Average Delivery Time | Thời gian giao hàng trung bình |  | DAX chưa xác minh; SQL: avg_time: AVG(delivery_time) | order_date, traffic, weather, vehicle, area, category | base | 176 · kpi | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Median Delivery Time | Trung vị thời gian giao hàng |  | DAX chưa xác minh; SQL: median: PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_time) | order_date, traffic, weather, vehicle, area, category | base | 177 · kpi | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | P90 Delivery Time | Thời gian giao hàng P90 |  | DAX chưa xác minh; SQL: p90: PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_time) | order_date, traffic, weather, vehicle, area, category | base | 178 · kpi | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Average Distance | Khoảng cách giao hàng trung bình |  | DAX chưa xác minh; SQL: distance: AVG(distance_km) | order_date, traffic, weather, vehicle, area, category | base | 179 · kpi | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Long Delivery Rate | Tỷ lệ giao hàng kéo dài |  | DAX chưa xác minh; SQL: long_rate: SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0) | order_date, traffic, weather, vehicle, area, category | base | 180 · kpi | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Average Delivery Time by Traffic | Thời gian giao hàng trung bình theo giao thông | traffic | DAX chưa xác minh; SQL: avg_time_yellow: AVG(delivery_time) | order_date, traffic, weather, vehicle, area, category | base | 181 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Total Orders by Vehicle | Tổng số đơn hàng theo phương tiện | vehicle | DAX chưa xác minh; SQL: orders: COUNT(order_id) | order_date, traffic, weather, vehicle, area, category | base | 182 · pie | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Average Delivery Time by Order_Date | Thời gian giao hàng trung bình theo ngày đặt hàng | order_date | DAX chưa xác minh; SQL: avg_time_red: AVG(delivery_time) | order_date, traffic, weather, vehicle, area, category | base | 183 · line | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Average Delivery Time by Area | Thời gian giao hàng trung bình theo khu vực | area | DAX chưa xác minh; SQL: avg_time: AVG(delivery_time) | order_date, traffic, weather, vehicle, area, category | base | 184 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 1 | Total Orders by Category | Tổng số đơn hàng theo danh mục sản phẩm | category | DAX chưa xác minh; SQL: orders: COUNT(order_id) | order_date, traffic, weather, vehicle, area, category | base | 185 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 2 | Average Delivery Time by Distance Band and Traffic | Thời gian giao hàng trung bình theo nhóm khoảng cách và giao thông | distance_band, traffic | DAX chưa xác minh; SQL: avg_time: AVG(delivery_time) | order_date, vehicle, category | base | 186 · line | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn; Distance Band suy luận từ ảnh: [0,3), [3,6), …, [18,21); chưa có DAX xác nhận biên |
| 2 | (không có tiêu đề) | Tỷ lệ giao hàng kéo dài theo khu vực và giao thông | matrix_area, matrix_traffic | DAX chưa xác minh; SQL: long_rate: SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0) | order_date, vehicle, category | area_matrix | 187 · pivot | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn; Visual không có tiêu đề trong PDF; tên hiển thị chỉ là nhãn quản trị; Total là ô tổng SQL theo từng đơn; tắt tính tổng các tỷ lệ ở frontend |
| 2 | Average Pickup Delay by Traffic | Thời gian chờ lấy hàng trung bình theo giao thông | traffic | DAX chưa xác minh; SQL: pickup_yellow: AVG(pickup_delay_min) | order_date, vehicle, category | base | 188 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 2 | (không có tiêu đề) | Thời gian giao hàng trung bình theo thứ và giờ đặt hàng | matrix_day, matrix_hour | DAX chưa xác minh; SQL: avg_time: AVG(delivery_time) | order_date, vehicle, category | hour_matrix | 189 · pivot | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn; Visual không có tiêu đề trong PDF; tên hiển thị chỉ là nhãn quản trị; Total là ô tổng SQL theo từng đơn; tắt tính tổng các tỷ lệ ở frontend |
| 3 | Average Delivery Time by Agent Rating | Thời gian giao hàng trung bình theo điểm đánh giá tài xế | rating_group | DAX chưa xác minh; SQL: avg_time: AVG(delivery_time) | order_date, traffic, area | base | 190 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn; PDF không hiển thị nhóm rating BLANK; loại nhóm NULL chỉ ở visual này |
| 3 | Average Delivery Time by Agent Age Group | Thời gian giao hàng trung bình theo nhóm tuổi tài xế | age_group | DAX chưa xác minh; SQL: avg_time: AVG(delivery_time) | order_date, traffic, area | base | 191 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 3 | Long Delivery Rate by Category | Tỷ lệ giao hàng kéo dài theo danh mục sản phẩm | category | DAX chưa xác minh; SQL: long_rate: SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0) | order_date, traffic, area | base | 192 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 3 | Average Agent Rating by Category | Điểm đánh giá tài xế trung bình theo danh mục sản phẩm | category | DAX chưa xác minh; SQL: rating: AVG(agent_rating) | order_date, traffic, area | base | 193 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 4 | Average Delivery Time by Weather | Thời gian giao hàng trung bình theo thời tiết | weather | DAX chưa xác minh; SQL: avg_time: AVG(delivery_time) | order_date, area, vehicle, traffic | base | 194 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 4 | Long Delivery Rate by Weather | Tỷ lệ giao hàng kéo dài theo thời tiết | weather | DAX chưa xác minh; SQL: long_rate: SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0) | order_date, area, vehicle, traffic | base | 195 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 4 | Average Pickup Delay by Order_Hour | Thời gian chờ lấy hàng trung bình theo giờ đặt hàng | order_hour | DAX chưa xác minh; SQL: pickup: AVG(pickup_delay_min) | order_date, area, vehicle, traffic | base | 196 · line | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 4 | Total Orders by Order_Hour | Tổng số đơn hàng theo giờ đặt hàng | order_hour | DAX chưa xác minh; SQL: orders: COUNT(order_id) | order_date, area, vehicle, traffic | base | 197 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 5 | Average Delivery Time | Thời gian giao hàng trung bình |  | DAX chưa xác minh; SQL: avg_time: AVG(delivery_time) | order_date, traffic, weather, vehicle, area | base | 198 · kpi | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 5 | Long Delivery Rate | Tỷ lệ giao hàng kéo dài |  | DAX chưa xác minh; SQL: long_rate: SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0) | order_date, traffic, weather, vehicle, area | base | 199 · kpi | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 5 | Long Delivery Rate by Traffic | Tỷ lệ giao hàng kéo dài theo giao thông | traffic | DAX chưa xác minh; SQL: long_rate: SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0) | order_date, traffic, weather, vehicle, area | base | 200 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn |
| 5 | Long Delivery Rate by Category | Tỷ lệ giao hàng kéo dài theo danh mục sản phẩm | category | DAX chưa xác minh; SQL: long_rate: SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0) | order_date, traffic, weather, vehicle, area | base | 201 · bar | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn; PDF thấy Sports/Skincare/Snacks/Shoes/Toys; không có bằng chứng filter/Top N/viewport, nên bản chuyển đổi giữ đủ 16 category |
| 5 | (không có tiêu đề) | Tổng hợp hiệu suất giao hàng theo khu vực | matrix_area | DAX chưa xác minh; SQL: p90: PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_time); pickup: AVG(pickup_delay_min); long_rate: SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0); distance: AVG(distance_km); avg_time: AVG(delivery_time); orders: COUNT(order_id) | order_date, traffic, weather, vehicle, area | area_totals | 202 · table | DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn; Visual không có tiêu đề trong PDF; tên hiển thị chỉ là nhãn quản trị |

## Mức bằng chứng

- **Đã xác nhận từ tệp:** thứ tự 5 trang; 28 visual số liệu và 1 khối kết luận; field, tiêu đề hiển thị, slicer, giá trị in trên PDF. CSV sạch khớp từng dòng với bảng nguồn.
- **Suy luận từ ảnh:** kiểu chart, màu gần mẫu Power BI (#118DFF, #FBE34D, #D64550), vị trí tương đối, sắp xếp, format và band khoảng cách. CSV xác nhận cờ long tương ứng delivery_time >160; chưa xác nhận công thức DAX.
- **Chưa có bằng chứng:** tên tab gốc, DAX, Power Query/ETL nguồn, bookmark, hidden filters, drill-through, tooltip tùy chỉnh, Top N và tương tác chéo. Không tự áp dụng Top N khi PDF chỉ có thanh cuộn/viewport.

## Metric và NULL / filter context

| Metric | SQL tương đương đề xuất | Format |
|---|---|---|
| Tổng số đơn hàng (`orders`) | `COUNT(order_id)` | `,d` |
| Thời gian giao hàng trung bình (`avg_time`) | `AVG(delivery_time)` | `,.2f` |
| Trung vị thời gian giao hàng (`median`) | `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_time)` | `,.2f` |
| Thời gian giao hàng P90 (`p90`) | `PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_time)` | `,.2f` |
| Khoảng cách giao hàng trung bình (`distance`) | `AVG(distance_km)` | `,.2f` |
| Tỷ lệ giao hàng kéo dài (`long_rate`) | `SUM(long_delivery_flag)::numeric / NULLIF(COUNT(order_id), 0)` | `.1%` |
| Thời gian chờ lấy hàng trung bình (`pickup`) | `AVG(pickup_delay_min)` | `,.2f` |
| Điểm đánh giá tài xế trung bình (`rating`) | `AVG(agent_rating)` | `,.1f` |
| Thời gian giao hàng trung bình (`avg_time_yellow`) | `AVG(delivery_time)` | `,.2f` |
| Thời gian giao hàng trung bình (`avg_time_red`) | `AVG(delivery_time)` | `,.2f` |
| Thời gian chờ lấy hàng trung bình (`pickup_yellow`) | `AVG(pickup_delay_min)` | `,.2f` |

`COUNT(order_id)` đếm giá trị không NULL; `COUNT(DISTINCT order_id)` khác về nghĩa. Hai cách trùng kết quả trên snapshot này vì khóa không thiếu và không trùng. Không có DAX nên chưa biết Power BI dùng cách nào.
`AVG` bỏ NULL rating; giữ đủ 54 đơn thiếu rating trong tổng đơn. Tỷ lệ long dùng cờ đã tồn tại, chia `NULLIF(COUNT(order_id),0)` và trả NULL khi không có đơn. Median/P90 dùng nội suy liên tục; khớp số PDF hiển thị, chưa chứng minh DAX gốc.
Không dùng trung bình các trung bình nhóm. Các dataset ma trận tạo ô tổng riêng ở grain order × ô chi tiết/tổng; mỗi ô chỉ có đúng một bản của mỗi đơn thuộc ô. Không dùng SUM/COUNT trên toàn bộ tập sao chép này. Dataset `base` luôn giữ một dòng/đơn.
Ngày là DATE không timezone, khoảng lọc dùng đầu bao gồm/cuối loại trừ. 11/02–06/04/2022 được biểu diễn `2022-02-11 : 2022-04-07`. Không tự đổi timezone. Giữ pickup_delay_min từ nguồn; đối chiếu phép modulo 24 giờ cho thấy 828 đơn qua nửa đêm và 0 sai lệch.

## Bộ lọc và khác biệt tính năng

| Filter | Phạm vi trang theo PDF | Mặc định |
|---|---|---|
| Order_Date | 1,2,3,4,5 | 11/02/2022 đến hết 06/04/2022 |
| Traffic | 1,3,4,5 | All |
| Weather | 1,5 | All |
| Vehicle | 1,2,4,5 | All |
| Area | 1,3,4,5 | All |
| Category | 1,2 | All |

Superset dùng filter chung và exclusions theo chart/tab. Chọn một giá trị sẽ đi cùng khi chuyển sang tab có cùng filter; Power BI PDF không thể chứng minh slicer đã đồng bộ giữa các trang. Filter ngoài phạm vi bị ẩn/đánh dấu out of scope. Không bật cross-filter mặc định vì PDF không chứng minh cấu hình tương tác gốc.
Native date filter không gắn dataset (`targets: [{}]`), đúng cơ chế Superset 6; mọi chart có main_dttm_col=order_date. Select filter trỏ cả bốn dataset để lọc đồng nhất các ô tổng.
PDF có scroll/viewport ở chart category. Bản chuyển đổi giữ mọi category và dùng zoom/scroll khi cần; không cố định số liệu/giá trị từ ảnh. Khối kết luận trang 5 là văn bản tĩnh, được ghi nhãn rõ không cập nhật theo bộ lọc.
Bố cục giữ thứ tự KPI và nhóm chart; Superset chuyển vùng lọc sang thanh ngang. Kích thước và tooltip là bản tương đương, không pixel-perfect. Kiểm tra ảnh trong `migration/evidence/screenshots/` và ghi nhận giới hạn ở `docs/browser-QA.md`.
