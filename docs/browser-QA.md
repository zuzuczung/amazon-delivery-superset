# Kiểm tra trình duyệt — 21/10/2026

Dashboard: http://localhost:8088/superset/dashboard/amazon-delivery-intelligence/

Kiểm tra trên trình duyệt trong Codex, các kích thước vùng xem mặc định quan sát được khoảng 916–1384px. Ảnh là ảnh chụp dashboard chạy thật, không phải mockup. Ảnh dài chụp toàn trang sau khi chart hoàn tất chuyển động; ma trận có thể cần cuộn ngang để xem mọi cột.

## Phạm vi đã kiểm tra

| Trang | Nội dung | Bằng chứng |
|---|---|---|
| 1 | 6 KPI, 5 chart; 43.648 đơn, 124,91 phút, median 125, P90 195, distance 9,73, long 23,1% | `migration/evidence/screenshots/page-1.png` |
| 2 | Line distance × traffic; ma trận Area × Traffic; pickup × traffic; ma trận weekday × hour và Total | `migration/evidence/screenshots/page-2.png` |
| 3 | Rating group, age group, long rate × category, rating × category | `migration/evidence/screenshots/page-3.png` |
| 4 | Weather, long rate × weather, pickup × hour, orders × hour | `migration/evidence/screenshots/page-4.png` |
| 5 | KPI, hai chart tỷ lệ, bảng Area + Total, kết luận tĩnh | `migration/evidence/screenshots/page-5.png` |

Đã kiểm tra chart có dữ liệu, không còn thông báo thiếu chart definition hoặc lỗi SQL. No-data là trạng thái có chủ đích khi lọc ngoài khoảng snapshot.

## Thử filter thực tế

- Grocery: UI hiển thị **2.688** đơn, avg delivery **26,54**, long rate **0%**; khớp CSV/SQL. Ảnh `filter-category-grocery.png`.
- Grocery + Jam: UI hiển thị **876** đơn, avg delivery **31,20**; SQL cho 31,19520547945. Ảnh `filter-grocery-jam.png`.
- Chuyển trang 1 → 3 → 1: Category không lọc nhầm trang 3; khi quay lại trang 1 lựa chọn được giữ. Ảnh `scope-category-excluded-page3.png` ghi nhận chart rating vẫn gồm dữ liệu đầy đủ theo scope.
- Khoảng ngày **2022-03-01 : 2022-04-01**: UI hiển thị **30.588** đơn, avg delivery **124,76**, long **23,0%**. Đã xem trực tiếp trong accessibility tree; một lần chụp toàn trang ở trạng thái này timeout, không dùng ảnh lỗi làm bằng chứng.
- Khoảng ngày **2023-01-01 : 2023-02-01**: UI hiển thị **0** đơn; các KPI AVG/percentile/rate hiển thị **No data**; chart có thông báo không có kết quả, không phải lỗi truy vấn. Ảnh `filter-no-data.png`.
- **Clear all → Apply**: xóa điều kiện và trả về **43.648** đơn, avg **124,91**, long **23,1%**. Clear all đặt native date thành No filter; tải lại URL dashboard không có query string phục hồi khoảng ngày mặc định theo PDF.

Các thử nghiệm category/tổ hợp/scope được thực hiện trong quá trình kiểm tra cả thanh ngang và thanh dọc. Bản cuối dùng thanh ngang, sau khi bổ sung type NATIVE_FILTER; date/no-data/Clear all đã được thử lại trên cấu hình cuối. Không tuyên bố đã tự động kiểm thử mọi tổ hợp click trên mọi tab. API kiểm tra độc lập 28 visual × 6 trạng thái trong verification.json.

## Lỗi phát hiện và đã sửa

1. Chỉ ghi layout chưa gắn chart vào dashboard: sửa bằng Chart REST API `dashboards: [id]`; layout đơn thuần không đủ trong Superset 6.
2. Native time filter gắn dataset khiến truy vấn metric mặc định `count` không tồn tại: dùng `targets: [{}]` cho filter_time, các chart có main_dttm_col=order_date.
3. Reset/nhận diện applied filter không hoạt động, các filter overflow mất trạng thái khi đổi tab: migration thiếu `type: NATIVE_FILTER`. Đã bổ sung, kiểm tra metadata và thử lại Clear all. Đây là lỗi cấu hình migration đã sửa, không kết luận là lỗi sản phẩm Superset.
4. Màn hình nhỏ làm header KPI xuống nhiều dòng: ẩn header trùng với subheader, giữ 6 KPI theo thứ tự; dùng thanh filter ngang. Axis count dùng SMART_NUMBER, line dùng trục tự co theo dữ liệu, không cắt giá trị bằng bounds cố định.
5. Ma trận lặp tên metric trên mọi cột: ẩn hàng header metric lặp; giá trị và ô Total vẫn đủ. Tổng tỷ lệ do SQL tính, không cộng các tỷ lệ frontend.

## Khác biệt còn lại so với Power BI

| Hạng mục | Bản chuyển đổi / giới hạn |
|---|---|
| Tên tab | “Trang 1…5” là nhãn vị trí; tên tab gốc chưa có bằng chứng. |
| Màu | Nền KPI vàng và khung xanh được giữ; palette chart, gradient/cell bars và một số màu series còn khác ảnh Power BI. Metadata có mapping màu và alias trình bày; không tuyên bố khớp màu tuyệt đối. |
| Bố cục | Giữ nhóm và thứ tự; trang 2 có line trái, matrix/pickup xếp phải, weekday bên dưới. Superset thay đổi kích thước và spacing theo vùng xem. |
| Ma trận | Cột traffic sắp theo khóa native, khác thứ tự Jam–Low–Medium–High của PDF. Ô Total được tính đúng nhưng vị trí dòng Total theo sort có thể khác; không phải footer cộng tỷ lệ. Ngày tuần có prefix số để giữ Monday→Sunday. |
| Chart category | Giữ đủ 16 category và zoom/scroll; PDF chỉ hiển thị một phần viewport, không có bằng chứng Top N/filter ẩn. Trang 5 không ép chỉ giữ 5 category nhìn thấy trong ảnh. |
| Nhãn trên vùng xem nhỏ | Chart nhiều category có nhãn thưa/dày và có cuộn ngang/zoom; cần xem tooltip hoặc mở vùng dashboard rộng hơn. Không bảo đảm mọi nhãn cùng hiện đầy đủ ở viewport 916px. |
| Tooltip và tương tác | Tooltip chuẩn Superset; cross-filter mặc định tắt vì chưa có bằng chứng cấu hình gốc. Không phục hồi bookmark/drill-through từ PDF. |
| Kết luận | Văn bản tĩnh từ trang 5, có chú thích không tự cập nhật theo filter. |

Không khẳng định pixel-perfect hoặc tương đương 100% DAX. Muốn xác minh filter context Power BI cần thêm semantic model/DAX và số liệu Power BI ở cùng trạng thái lọc.
