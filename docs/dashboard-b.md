# Dashboard B · So sánh phương tiện cùng điều kiện

[Mở trên Superset local](http://localhost:8088/superset/dashboard/amazon-delivery-so-sanh-phuong-tien/). Dashboard 24, dataset 43–44, chart 270–276. Một trang gồm 4 biểu đồ/bảng và 3 KPI; không sao chép các chart trung bình theo phương tiện của dashboard chính.

## 1. Xác định vấn đề

Đã thực hiện: so sánh thời gian giao của motorcycle và scooter sau khi đưa về cùng cơ cấu khu vực, giao thông, thời tiết và khoảng cách. Câu hỏi là chênh lệch mô tả còn bao nhiêu khi cơ cấu các điều kiện đo được giống nhau, đồng thời chỉ rõ phần dữ liệu có thể so sánh.

Hạn chế: dữ liệu quan sát không xác định hiệu quả nhân quả của phương tiện. Đề xuất tiếp theo, chưa thực hiện: bổ sung người giao, tải đơn, giờ nhận đơn và thiết kế đánh giá can thiệp nếu cần quyết định đổi phương tiện.

## 2. Thu thập dữ liệu

Đã thực hiện: đọc snapshot 43.648 đơn ngày 11/02–06/04/2022 từ `amazon_bi.delivery_orders`, đối chiếu độc lập CSV sạch. Loại Grocery, chỉ giữ motorcycle và scooter: 37.658 đơn, gồm 23.936 motorcycle và 13.722 scooter. Không tạo hay sửa bảng nguồn PostgreSQL.

Hai dataset ảo có grain khác nhau: `amazon_vehicle_b_strata` một dòng mỗi nhóm điều kiện; `amazon_vehicle_b_vehicles` một dòng mỗi nhóm và phương tiện có đơn. `pooled_n` lặp ở hai phương tiện trong dataset thứ hai, vì vậy chỉ dùng tính trung bình chuẩn hóa theo từng phương tiện, không cộng thành tổng đơn toàn mẫu.

## 3. Làm sạch và phạm vi

Nhóm điều kiện = khu vực × giao thông × thời tiết × khoảng cách chia dải 3 km `[3k,3k+3)`. Một nhóm đủ mẫu khi có ít nhất 20 đơn motorcycle **và** 20 đơn scooter. Có 432 nhóm quan sát, 207 nhóm đủ mẫu. Mẫu chung gồm 34.281 đơn; 3.377 đơn còn lại vẫn được thể hiện trong biểu đồ độ bao phủ.

Khoảng cách giữ giá trị nguồn, không tái tính hay khẳng định tọa độ chính xác. Nguồn có 3.495 đơn chứa thành phần tọa độ bằng 0 trong toàn snapshot; B không bổ sung quy tắc loại những đơn này. Ngưỡng 20 là lựa chọn phân tích về độ hỗ trợ mẫu, không phải kiểm định ý nghĩa thống kê.

Chỉ có bốn bộ lọc khu vực, giao thông, thời tiết và dải khoảng cách. Chúng chọn toàn bộ nhóm nên điều kiện đủ mẫu giữ đúng. Không thêm bộ lọc ngày, phương tiện hoặc danh mục trên các tổng hợp đã tính sẵn: nếu cần các bộ lọc đó phải tính lại nhóm và ngưỡng từ cấp đơn hàng. Trọng số được tính lại trong các nhóm đang chọn.

## 4. Phân tích và bố cục

Với mỗi nhóm đủ mẫu s, lấy `n_s = n_motor,s + n_scooter,s`, trọng số `w_s = n_s / Σn_s`. Thời gian chuẩn hóa của mỗi phương tiện là `Σw_s × mean_vehicle,s`; chênh lệch là motorcycle trừ scooter. Cả hai dùng cùng trọng số. Trung bình thô và đã cân bằng đều tính trên cùng mẫu đủ điều kiện để tránh đổi quần thể khi so sánh trước/sau.

| Chỉ tiêu mặc định | Kết quả |
|---|---:|
| Trung bình thô motorcycle / scooter trên mẫu chung | 137,88 / 122,59 phút |
| Trung bình đã cân bằng motorcycle / scooter | 137,94 / 122,34 phút |
| Chênh lệch đã cân bằng | +15,60 phút |
| Độ bao phủ = số đơn đủ mẫu / tổng đơn thuộc phạm vi B | 91,0% |
| Số đơn đủ mẫu | 34.281 |
| Nhóm đủ mẫu | 207 |

Ba KPI: chênh lệch đã cân bằng, độ bao phủ và số đơn đủ mẫu.

Bốn biểu đồ/bảng:

- Cột ghép trung bình thô và đã cân bằng theo phương tiện trên cùng mẫu.
- Cột chồng số đơn đủ/chưa đủ mẫu theo phương tiện: motorcycle 21.788/2.148, scooter 12.493/1.229.
- Phân bố chênh lệch của 207 nhóm, mỗi cột đếm số nhóm trong khoảng 5 phút `[k,k+5)`. Trục X dạng số giữ đúng khoảng cách cả khi không có nhóm ở một khoảng. Mỗi nhóm có trọng số bằng nhau trong biểu đồ phân bố; KPI dùng trọng số theo đơn.
- Bảng toàn bộ nhóm đủ mẫu: tên nhóm, số đơn mỗi phương tiện, trung bình từng phương tiện và chênh lệch. Mặc định sắp xếp chênh lệch giảm dần, 15 dòng/trang; tìm kiếm trong toàn bộ nhóm đã tải (giới hạn 1.000, cao hơn 207 nhóm của snapshot).

## 5. Diễn giải và kiểm chứng

Motorcycle có thời gian giao dài hơn scooter khoảng 15,60 phút sau cân bằng bốn điều kiện trên mẫu chung. Kết quả này không chứng minh thay phương tiện sẽ giảm tương ứng 15,60 phút; các yếu tố chưa đo và độ chính xác khoảng cách vẫn có thể ảnh hưởng. Những nhóm chưa đủ mẫu không đóng góp vào chênh lệch; không ngoại suy sang phần này.

42 đối chiếu CSV → Superset cho 7 chart × 6 trường hợp: mặc định, Metropolitan, Jam + Fog, 18–21 km, Semi-Urban không có nhóm đủ mẫu và tập rỗng. Khi có đơn nhưng không có nhóm đủ mẫu, độ bao phủ và số đơn so sánh bằng 0; chênh lệch là NULL/N/A. Với tập hoàn toàn rỗng, độ bao phủ cũng là NULL. Xem `migration/evidence/vehicle-b-verification.json`.

Chạy lại builder giữ nguyên dashboard 24, dataset 43–44, chart 270–276. Builder kiểm tra toàn bộ 40 chart của main/A và cấu hình dashboard A không đổi; main chỉ thêm liên kết tới B. Kiểm tra trình duyệt và ảnh chụp lưu trong `migration/evidence/vehicle-b-browser.json` và `migration/evidence/screenshots/vehicle-b.png`.

## Tái tạo

Sau khi cấu hình credential Superset trong environment và đã tạo dashboard chính/A:

```bash
python3 migration/scripts/build_vehicle_dashboard.py --apply
python3 migration/scripts/verify_vehicle_dashboard.py
```

Runner chung gồm cả hai bước này sau A. UUID ổn định giúp chạy lại không tạo bản sao. SQL nhóm nằm trong `migration/sql/003_vehicle_strata.sql` và chỉ được dùng như truy vấn dataset ảo. ZIP `amazon_delivery_superset_6.zip` hiện chỉ chứa dashboard chính; tái tạo A/B bằng các script tương ứng.
