# Amazon Delivery: Power BI → Apache Superset

Ngày thực hiện: 21/10/2026, Asia/Ho_Chi_Minh. Phạm vi được người dùng sửa từ 4 thành **5 trang**. Nguồn duy nhất để dựng dashboard là `reports/amazon_delivery_dashboard.pdf` và `data/amazon_delivery_cleaned.csv`.

Dashboard thực tế: http://localhost:8088/superset/dashboard/amazon-delivery-intelligence/

Cập nhật ngày 23/10/2026: đã Việt hóa đủ 28 tên biểu đồ cùng nhãn metric/trục/bộ lọc. Ba bảng/ma trận không có tiêu đề trong PDF được đặt tên mô tả nội dung. Mapping giữ tiêu đề Power BI gốc riêng với tên Superset; SQL, filter scope, grain và format giữ nguyên. Xem `localization.json` và `localization-browser.json` trong thư mục bằng chứng.

Cùng ngày, bộ 5 dashboard con thử nghiệm (11 trang, 55 chart) đã được gỡ theo yêu cầu người dùng vì trùng nội dung với dashboard chính. Đã xóa dashboard ID 18–22, chart ID 203–257, dataset ảo riêng ID 41 và khối điều hướng sang bộ này. Dashboard chính vẫn giữ 5 trang, 28 chart, 4 dataset và bộ lọc cũ. Không thay đổi bảng nguồn PostgreSQL. Script tạo bộ cũ đã được lưu trong thư mục bản sao và gỡ khỏi migration đang dùng để tránh tự tạo lại. Bằng chứng: `migration/evidence/redundant-children-removal.json`; ZIP khôi phục đã loại credential: `migration/retired/redundant-children-2026-10-23/superset-children-backup.zip`.

## 1. Xác định vấn đề

**Đã thực hiện:** chuyển 5 trang theo thứ tự PDF thành một dashboard có 5 tab. Thống kê 28 visual số liệu và một khối kết luận, không trộn bản report 6 trang. Bài toán là bảo toàn nội dung, phép tổng hợp và phạm vi bộ lọc khi thay Power BI bằng Superset.

**Bằng chứng:** `visual-mapping.csv`, `visual-mapping.md`, `migration/evidence/visual-inventory.json`, ảnh PDF gốc trong `migration/evidence/source/`. Trang 1 có 11 visual, các trang 2–4 mỗi trang 4 visual; trang 5 có 5 visual và văn bản kết luận.

**Hạn chế:** không có tên tab trong PDF; nhãn “Trang 1…5” là điều hướng theo số trang. Không có `.pbix`, `.pbip`, `.pbir`, DAX, semantic-model export hoặc Power Query. Chưa xác minh các trạng thái Power BI sau khi lọc.

**Đề xuất bổ sung:** khi có DAX/export semantic model và ảnh Power BI đã lọc, cập nhật mapping rồi kiểm chứng lại những logic có filter context đặc biệt. Không cần đợi các tài liệu này để dùng bản Superset đã đối chiếu snapshot.

## 2. Thu thập dữ liệu và khảo sát môi trường

**Đã thực hiện:** tìm đúng bản Amazon ở `/Users/zuzuczung/Desktop/sql-bi-project/amazon-delivery-intelligence`. Thư mục này không phải checkout độc lập: Git root là dự án Inventory với remote khác. GitHub repository do người dùng cung cấp trả 404 với connector hiện tại; Git HTTPS không có credential phù hợp. Vì vậy tạo bản làm việc độc lập từ đúng tệp Amazon, không tuyên bố đã clone hoặc đồng bộ commit GitHub.

Bản làm việc: `/Users/zuzuczung/Documents/ChatGPT/DA/amazon-delivery-intelligence`. Theo yêu cầu tiếp theo của người dùng, dự án được xuất bản thành repo Public mới: https://github.com/zuzuczung/amazon-delivery-superset, nhánh chính `main`. Đây là lịch sử mới độc lập; không ghép vào repo Power BI cũ. Giữ nguyên các thay đổi chưa commit trong cả workspace DA và Git root Inventory.

**Đã tái sử dụng:** Docker stack sẵn có tại `/Users/zuzuczung/superset/docker-compose-image-tag.yml`, Superset **6.0.0**, PostgreSQL dữ liệu **17.10**, container `postgres-local`; kết nối BI hiện có **PostgreSQL**, ID 2, database **tunglocaldb**, bảng **public.amazon_delivery**. Các bảng `postgres.amz_lgt.amazon_delivery*` cũng tồn tại nhưng không phải nguồn được kết nối BI này; bản REAL của chúng có độ chính xác float thấp hơn bản NUMERIC/double đang dùng.

Docker Desktop ban đầu chưa chạy, đã mở lại ứng dụng để stack hiện có tự khởi động. Không reset volume, không xóa database, không tạo stack thay thế. PostgreSQL 15 trong `superset_db` là metadata database, không dùng làm dữ liệu Amazon và không chỉnh trực tiếp.

**Bằng chứng:** source hash, schema và profile trong `migration/evidence/data-profile.json`; ID/URL tài nguyên trong `migration/evidence/deployment.json`. REST API được đối chiếu với runtime OpenAPI và source Superset; tài liệu chính thức: https://superset.apache.org/docs/api/.

**Hạn chế:** nguồn raw 43.739 dòng và curated 43.648 dòng chỉ là snapshot 2022, không phải dữ liệu Amazon vận hành trực tiếp. Pipeline làm sạch gốc không nằm trong project. Bản `amazon_delivery_report.pdf` có 6 trang, 43.594 đơn và khoảng cách 26,76 km; không trộn KPI của bản đó vào dashboard này.

**Đề xuất bổ sung:** nếu cần ghép với lịch sử repo Power BI cũ, khôi phục quyền truy cập và đối chiếu trước. Repo Superset mới không yêu cầu bước này. Không đổi remote của dự án Inventory hoặc ghi đè checkout của người dùng.

## 3. Làm sạch dữ liệu và bảo toàn grain

**Đã thực hiện:** kiểm tra khóa, duplicate, NULL, kiểu dữ liệu, khoảng ngày, cờ long, tọa độ, whitespace raw, so sánh raw–clean và CSV–DB. Bảng nguồn khớp **toàn bộ 43.648 dòng và mọi trường** với CSV sau chuẩn hóa biểu diễn số. Không có khóa thiếu hoặc trùng, không có bản ghi trùng hoàn toàn. Ngày từ 11/02 đến 06/04/2022. Có 54 đơn thiếu Agent_Rating/Rating_Group; vẫn giữ các đơn này trong tổng đơn.

Raw có 91 ID không còn trong CSV sạch, đồng thời raw có 91 Order_Time và 91 Weather/Traffic thiếu. Đây là quan sát, không khẳng định biết chính xác code hoặc quy tắc ETL đã loại các dòng. Whitespace ở raw được ghi nhận; CSV sạch đã chuẩn hóa danh mục.

View mới **amazon_bi.delivery_orders** chỉ chọn dữ liệu nguồn, đổi chuỗi rating_group rỗng thành NULL, thêm khóa hiển thị ngày tuần và band khoảng cách. Không JOIN dữ liệu, không tự loại outlier/NULL, không tính lại khoảng cách. Có 828 lần pickup qua nửa đêm; pickup_delay_min khớp chênh lệch phút modulo 24h trên toàn bộ dữ liệu. Thời điểm trong dữ liệu không có timezone; không tự gán timezone hoặc đổi giờ.

**Bằng chứng:** `profile.py`, `001_delivery_orders.sql`, `data-profile.json`. SQL tạo schema/view trong transaction và kiểm tra ownership comment trước khi thay view, không thay bảng nguồn.

**Hạn chế:** 3.495 đơn có ít nhất một tọa độ bằng 0. Distance_Km được giữ nguyên để khớp nguồn; chưa thể xác minh ý nghĩa địa lý của các dòng này. Chưa biết chính xác Power Query đã sửa định dạng tọa độ raw như thế nào. Band khoảng cách [0,3), [3,6), … được suy luận từ ảnh, chưa có DAX xác nhận biên.

**Đề xuất bổ sung:** bổ sung ETL gốc và quy tắc chất lượng tọa độ; đánh giá ảnh hưởng trước khi sửa dữ liệu, vì sửa distance có thể làm thay toàn bộ so sánh với Power BI.

## 4. Phân tích dữ liệu và chuyển logic BI

**Đã thực hiện:** 8 metric nghiệp vụ, kèm 3 alias trình bày dùng cùng SQL để giữ màu từng chart; 28 chart; 5 tab; 6 native filter với scope theo PDF. SQL không mặc định SUM/AVG theo tên: từng metric có định nghĩa trong mapping. Total Orders dùng COUNT(order_id); DISTINCTCOUNT chỉ được ghi là tương đương trên snapshot có khóa duy nhất, chưa biết DAX gốc dùng cách nào.

Tỷ lệ long tính SUM(cờ)/COUNT(đơn), giữ mẫu số sau lọc; cờ >160 khớp 100% CSV nhưng không tuyên bố đã đọc DAX. AVG bỏ NULL rating; median/P90 dùng PERCENTILE_CONT. Chia 0 trả NULL. Tất cả được tính từ từng dòng, không lấy trung bình của các trung bình.

Hai ma trận có dataset riêng tạo ô chi tiết và ô Total. Grain ở đây là **đơn × ô chi tiết/tổng**, không được coi là bảng fact một dòng/đơn. Trong từng ô chỉ có một bản của mỗi đơn thuộc ô, nên tỷ lệ/trung bình vẫn có trọng số đúng. Tắt tổng mặc định của pivot frontend để tránh cộng các tỷ lệ. Dataset `area_totals` có một dòng/đơn/nhãn khu vực hoặc Total; bảng trang 5 group đúng nhãn nên tổng đơn và percentile đúng. Không dùng các dataset này để lấy COUNT toàn tập không group.

**Bằng chứng kiểm chứng số liệu:** `migration/evidence/verification.json`. Bộ kiểm chứng gồm 6 trạng thái: toàn bộ 43.648 đơn; tháng 03/2022 với 30.588 đơn; Grocery 2.688 đơn; tổ hợp Grocery + motorcycle + Jam + Metropolitan trong tháng 03 với 305 đơn; khoảng không có dữ liệu; reset về toàn bộ. CSV tính bằng Python độc lập → PostgreSQL tổng hợp → Superset API.

| Trang | Visual số liệu | Tình trạng số liệu |
|---|---:|---|
| 1 | 11 | Kiểm chứng trong ma trận 6 trạng thái |
| 2 | 4 | Kiểm chứng cả ô tổng có trọng số |
| 3 | 4 | Giữ đơn thiếu rating; loại nhóm rating NULL riêng ở chart phân nhóm rating theo ảnh |
| 4 | 4 | Kiểm chứng theo weather và order_hour |
| 5 | 5 | Kiểm chứng bảng Area + Total và các KPI; kết luận tĩnh chép từ PDF |

Trên snapshot ban đầu, 168/168 trường hợp chart/filter và 30 giá trị PDF in ra đạt kiểm tra. Luôn đọc file verification mới nhất sau khi chạy lại; script dừng với exit code khác 0 nếu sai. Counts yêu cầu khớp chính xác; các metric khác abs 1e-8 / rel 1e-10; baseline PDF so ở precision hiển thị.

KPI không lọc: **43.648** đơn; thời gian giao trung bình **124,91 phút**; median **125**; P90 **195**; khoảng cách trung bình **9,73 km**; long delivery rate **23,1%**. Không hardcode các số này vào chart.

**Hạn chế:** kiểm chứng lọc trên CSV/SQL/API không chứng minh filter context DAX gốc. Kiểm tra trình duyệt được ghi riêng trong `browser-QA.md`. Tooltip dùng bản chuẩn Superset; không thể phục hồi tooltip/bookmark/drill-through hoặc cross-filter từ PDF. Không bật tương tác chéo khi không có bằng chứng cấu hình Power BI.

**Đề xuất bổ sung:** đối chiếu export Power BI cho từng trạng thái lọc và kiểm tra lại cách tính percentile, ngưỡng long, band khoảng cách khi có DAX.

## 5. Diễn giải kết quả và bàn giao

**Đã thực hiện:** giữ đủ nội dung số liệu của 5 trang và văn bản kết luận; đánh dấu khác biệt tính năng trong mapping. Có script chạy lại theo UUID ổn định; không nhận diện tài nguyên bằng tiêu đề đơn thuần. Các tài nguyên project dùng namespace UUID riêng. Có guard chống thay view/dataset/dashboard không thuộc migration; chạy lại không tạo bản sao. Mọi thay đổi Superset đi qua REST API, kể cả liên kết chart với dashboard; không ghi trực tiếp metadata DB.

**Bằng chứng:** SQL, source scripts, mapping, JSON kiểm chứng, ảnh trình duyệt và export ZIP. Export chính thức được tải cho duy nhất dashboard project, gồm 1 dashboard, 28 chart, 4 dataset và 1 database liên quan. URI username/password được thay placeholder và extras có thể chứa bí mật bị bỏ; không có credential thật trong export. ZIP dùng định dạng 1.0.0 của Superset 6.0.0. Không reimport ZIP vào instance đang chạy để tránh tác động cấu hình database dùng chung.

**Hạn chế:** dữ liệu mang tính portfolio; không diễn giải thành hiệu suất Amazon hiện tại. Kết luận trang 5 là văn bản tĩnh từ nguồn, không tự cập nhật theo filter. Màu/typography/spacing và cách hiển thị scroll của Superset có thể khác Power BI, không tuyên bố pixel-perfect hay giống 100%.

**Đề xuất bổ sung:** chỉ dùng kết luận định lượng cho snapshot và cohort đã lọc; khi thay dữ liệu cần kiểm chứng lại. Đặc biệt, tỷ lệ cao ở Semi-Urban dựa trên 152 đơn, nhỏ hơn nhiều nhóm Metropolitan, nên cần xét độ bất định trước quyết định vận hành.

## Chạy lại chính xác

Yêu cầu: Python 3.11+, Docker stack hiện có đang chạy, quyền đọc bảng nguồn và tạo/cập nhật view trong schema amazon_bi; tài khoản Superset có quyền quản lý dataset/chart/dashboard. Không cần cài lại Superset/PostgreSQL.

```bash
git clone https://github.com/zuzuczung/amazon-delivery-superset.git
cd amazon-delivery-superset
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-superset.txt
python migration/scripts/run_migration.py
```

Runner hỏi username/password với password không echo, chỉ truyền qua environment của process con, không ghi lại. Hoặc đặt credential trong biến môi trường shell/secret manager trước khi chạy. `.env.example` chỉ là mẫu, script không tự nạp `.env`. Không đưa mật khẩu/token vào lệnh, Git hoặc log.

Mặc định khớp môi trường đã xác minh: AMAZON_PG_CONTAINER=postgres-local, AMAZON_DATABASE=tunglocaldb, SUPERSET_URL=http://localhost:8088, SUPERSET_DATABASE_ID=2. Nếu dùng môi trường khác, đặt các biến này và xác minh bảng public.amazon_delivery trước; script từ chối database BI không trùng database đã profile. Source SQL không tự đoán schema/bảng.

Chạy từng bước, với credential Superset đã có trong environment:

```bash
python migration/scripts/profile.py
python migration/scripts/migrate.py --apply-sql
python migration/scripts/verify.py
python -m unittest discover -s migration/tests -v
python migration/scripts/export_dashboard.py
python migration/scripts/document.py
```

## Cập nhật dữ liệu

View đọc trực tiếp bảng nguồn nên tự phản ánh thay đổi ở `public.amazon_delivery`; không cần reload bản sao hay reset database. Pipeline gốc không có trong repo: không giả định biết lệnh ETL của người dùng. Khi upstream cập nhật, xuất snapshot tương ứng vào `data/amazon_delivery_cleaned.csv` rồi chạy profile/verify; script kiểm tra mọi trường và từ chối khi CSV–DB lệch nhau.

`profile.py` ghi nhận chất lượng hiện tại; `verify.py` vẫn so với PDF snapshot 2022 và sẽ báo baseline lệch nếu thay dữ liệu. Đây là hành vi có chủ đích: cần thêm baseline mới có nguồn, không sửa chart để ép khớp số cũ. Refresh chart bằng nút refresh/menu Superset sau khi upstream đổi dữ liệu; không xóa toàn bộ cache hoặc tác động dashboard khác.

## Export/import và hoàn tác

Ưu tiên chạy REST migration để tái tạo trên cùng kết nối đã cấu hình. ZIP export phục vụ chuyển môi trường/backup cấu trúc; cấu hình database đích/credential qua UI import theo Superset, giữ UUID database nếu tái dùng connection có sẵn. Không nhập placeholder vào database dùng chung và không bật overwrite toàn bộ tài nguyên một cách mù quáng. Cần PostgreSQL view trước khi chart chạy.

Có thể hoàn tác tài nguyên BI qua UI/API với các ID trong deployment.json, sau khi kiểm tra UUID; chỉ xóa chart/dashboard/dataset của project. Không chạy rollback tự động. View chỉ là phép đọc; nếu muốn gỡ thì kiểm tra dependency trước khi DROP VIEW, không dùng CASCADE và không xóa bảng public.amazon_delivery. Giữ stack/volume hiện có.

## Tệp bàn giao

- `migration/sql/001_delivery_orders.sql`: additive BI view và guard ownership.
- `migration/scripts/{common,spec,profile,migrate,verify,export_dashboard,document,run_migration}.py`: quy trình tái chạy dashboard chính.
- `migration/tests/test_metric_semantics.py`: nội suy percentile, NULL, empty cohort và weighted totals.
- `migration/exports/amazon_delivery_superset_6.zip`: export đã bỏ credential thật.
- `.env.example`, `requirements-superset.txt`: cấu hình mẫu và dependency.
- `docs/visual-mapping.{csv,md}`, `docs/browser-QA.md`: mapping và khác biệt/kiểm tra giao diện.
- `migration/evidence/*.json`, `migration/evidence/screenshots/`: bằng chứng và ảnh.

Mọi mục **đề xuất bổ sung** ở trên là việc chưa thực hiện, không được hiểu là kết quả đã hoàn thành.
