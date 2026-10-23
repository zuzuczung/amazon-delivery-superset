# Dashboard A · Giao kéo dài và đơn cần kiểm tra

Dashboard: http://localhost:8088/superset/dashboard/amazon-delivery-giao-keo-dai/

ID 23, dataset 42, chart 258–269. Nguồn snapshot: 43.648 đơn từ 11/02–06/04/2022. Các bộ lọc ngày, nhóm điều kiện, khu vực, giao thông, thời tiết, phương tiện và danh mục áp dụng cho cả hai trang.

## 1. Xác định vấn đề

Đã thực hiện: tập trung vào mức độ nghiêm trọng, sự tập trung của các đơn giao kéo dài và đơn có quãng đường ngắn nhưng thời gian giao lớn. Không sao chép các chart trung bình theo một chiều đã có ở dashboard chính.

Kết quả: 1 dashboard, 2 trang, 8 biểu đồ/bảng và 4 KPI mới. [Dashboard B](dashboard-b.md) bổ sung so sánh phương tiện trong điều kiện tương đồng.

## 2. Thu thập dữ liệu

Dataset ảo `amazon_delivery_risk_a` đọc `amazon_bi.delivery_orders`, giữ một dòng/đơn, bổ sung số phút vượt mốc 160, mức thời gian giao, ô mật độ và nhóm tham chiếu. Không tạo hoặc sửa bảng nguồn PostgreSQL.

## 3. Làm sạch và phạm vi

Trang 1 giữ toàn bộ snapshot. Trang 2 chỉ dùng các đơn có bốn thành phần tọa độ khác 0; không tuyên bố đây là kiểm chứng độ chính xác địa lý. Bộ lọc áp dụng cho đơn đang xem; nhóm tham chiếu được tính từ snapshot đầy đủ, không đổi theo bộ lọc.

Tham chiếu gồm các đơn có tọa độ khác 0, cùng khu vực, giao thông, thời tiết và khoảng cách chia nhóm 3 km. Dùng trung vị khi có ít nhất 30 đơn. Có 873 đơn dưới 5 km và trên 160 phút; trong đó 36 đơn chưa đủ mẫu tham chiếu. Các đơn này vẫn ở bảng với mức lệch NULL, không bị loại khỏi KPI đếm đơn cần xem.

## 4. Phân tích và bố cục

### Trang Mức độ tập trung

- KPI tổng phút vượt mốc 160: 366.375 phút.
- KPI số đơn trên 200 phút: 3.608.
- KPI phút vượt trung bình trên mỗi đơn kéo dài: 36,4 phút.
- Pareto: 15 tổ hợp khu vực × giao thông × thời tiết đứng đầu theo tổng phút vượt. Trình bày bằng thanh trong bảng và cột tỷ trọng tích lũy để bảo toàn thứ tự giảm dần. Tích lũy dùng mẫu số mọi tổ hợp sau lọc, không chỉ 15 tổ hợp hiển thị.
- Bong bóng ưu tiên: X số đơn trên 160 phút, Y phút vượt trung bình của những đơn này, kích thước tổng đơn của nhóm. Chỉ hiện nhóm có đơn kéo dài.
- Cột chồng: số đơn theo các mức (160,180], (180,200] và >200 phút, chia theo khu vực.
- Cột ngang: tỷ trọng đơn so với tỷ trọng phút vượt, 12 tổ hợp đứng đầu theo tỷ trọng phút vượt. Hai mẫu số gồm mọi tổ hợp sau lọc, không chỉ Top 12.

### Trang Đơn cần kiểm tra

- KPI số đơn dưới 5 km, trên 160 phút, tọa độ khác 0: 873.
- Mật độ: khoảng cách theo ô [k,k+1) km × thời gian theo ô [t,t+20) phút. Tập hiển thị là toàn bộ đơn có tọa độ khác 0. Ô trống là tổ hợp không có đơn quan sát.
- Ma trận: số đơn dưới 5 km và trên 160 phút theo giao thông × thời tiết.
- Biểu đồ 20 đơn quãng đường ngắn có mức lệch trung vị lớn nhất. Chỉ dùng nhóm tham chiếu có ít nhất 30 đơn.
- Bảng chi tiết: tối đa 200 đơn dưới 5 km và trên 160 phút, ưu tiên số phút vượt lớn nhất; có phân trang, tìm kiếm trong 200 dòng đã tải. Lọc nhóm để thu hẹp tập; không tuyên bố bảng hiển thị tất cả 873 đơn. Mức lệch NULL hiện N/A.

## 5. Diễn giải và kiểm chứng

Mốc 160 phút là định nghĩa phân tích có sẵn; 200 phút là ngưỡng khám phá mới. Không coi đây là SLA cam kết. Tổng phút vượt mô tả mức độ kéo dài, không phải khoản tiết kiệm dự báo. Trung vị nhóm là tham chiếu mô tả, gồm cả đơn đang xét; mức lệch lớn không chứng minh lỗi, nguyên nhân hoặc hiệu quả can thiệp.

48 lượt chart/filter được tính lại độc lập từ CSV và đối chiếu Superset: toàn bộ dữ liệu, Grocery, tháng 3 + Jam, khoảng ngày không dữ liệu. Đã kiểm tra grain và tổng phút vượt trong PostgreSQL. Xem `migration/evidence/risk-a-verification.json`.

Kiểm tra trình duyệt gồm hai trang, sửa lỗi legend của heatmap, số liệu nhóm Metropolitan · Jam · Fog, giữ nhóm khi chuyển trang và reset. Với nhóm này trang 1 có 57.270 phút vượt, 643 đơn trên 200 phút; trang 2 có 44 đơn cần xem.

## Tái tạo

Với credential Superset đã cấu hình trong environment:

```bash
python migration/scripts/build_risk_dashboard.py --apply
python migration/scripts/verify_risk_dashboard.py
```

Runner chung đã gồm hai bước này sau migration dashboard chính. UUID riêng giữ ID ổn định khi chạy lại. Bộ 5 dashboard con cũ đã gỡ không được tạo lại. Dashboard chính có các khối liên kết sang A và B.

ZIP `amazon_delivery_superset_6.zip` hiện chỉ chứa dashboard chính; tái tạo Dashboard A bằng script riêng ở trên. Các ảnh trang A nằm trong `migration/evidence/screenshots/risk-a-page-1.png` và `risk-a-page-2.png`.
