"""Generate the inventory and metric crosswalk from the deployed source spec."""
import csv
import json
from common import ROOT, save
from spec import METRICS, PAGES, DATASET_SQL, title, visuals


def main():
    state=json.loads((ROOT/'migration/evidence/deployment.json').read_text())
    mapping=[]
    for p in PAGES:
        for rowindex,row in enumerate(p['rows']):
            for colindex,v in enumerate(row):
                metrics=v.get('metrics',[v['metric']]);fields=[v.get('dimension'),v.get('series'),v.get('columns')]
                gaps=['DAX gốc, tooltip tùy chỉnh và tương tác không có trong tệp nguồn']
                if not v['title']:gaps.append('Visual không có tiêu đề trong PDF; tên hiển thị chỉ là nhãn quản trị')
                if v.get('source_subset_unknown'):gaps.append('PDF thấy Sports/Skincare/Snacks/Shoes/Toys; không có bằng chứng filter/Top N/viewport, nên bản chuyển đổi giữ đủ 16 category')
                if v['key']=='p2-01':gaps.append('Distance Band suy luận từ ảnh: [0,3), [3,6), …, [18,21); chưa có DAX xác nhận biên')
                if v.get('exclude_null'):gaps.append('PDF không hiển thị nhóm rating BLANK; loại nhóm NULL chỉ ở visual này')
                if v['kind']=='pivot':gaps.append('Total là ô tổng SQL theo từng đơn; tắt tính tổng các tỷ lệ ở frontend')
                mapping.append(dict(page=p['number'],visual_id=v['key'],source_title=v['title'] or '(không có tiêu đề)',
                    source_kind=v['kind'],fields=', '.join(x for x in fields if x),
                    DAX='chưa xác minh: không có PBIX/PBIP/DAX',
                    SQL='; '.join(f'{k}: {METRICS[k][1]}' for k in metrics),
                    filters=', '.join(p['filters']),dataset=v.get('dataset','base'),
                    chart_id=state['charts'][v['key']],superset_chart=title(v),
                    layout=f'hàng {rowindex+1}, cột {colindex+1}',
                    format='; '.join(METRICS[k][2] for k in metrics),
                    sort='trục tăng dần' if v.get('ascending') else 'theo metric giảm dần; matrix theo khóa',
                    evidence='Đã xác nhận visual/field từ PDF; SQL là suy luận được kiểm tra CSV/SQL/PDF, không phải DAX trích xuất',
                    missing='; '.join(gaps)))
    with (ROOT/'docs/visual-mapping.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(mapping[0]));w.writeheader();w.writerows(mapping)
    lines=['# Bản đồ Power BI → Apache Superset','',
        'Nguồn quyết định: `reports/amazon_delivery_dashboard.pdf`, 5 trang. Người dùng sửa phạm vi từ 4 thành 5 trang ngày 21/10/2026.',
        'Tên tab không nằm trong PDF; Trang 1–5 là nhãn vị trí, không được tuyên bố là tên gốc. `amazon_delivery_report.pdf` là bản 6 trang khác KPI và không dùng để tính toán.',
        'Tên biểu đồ Superset được Việt hóa; tiêu đề Power BI gốc được giữ riêng để đối chiếu. Ba bảng/ma trận không có tiêu đề trong PDF được đặt tên tiếng Việt mô tả nội dung.',
        '', '| Trang | Visual Power BI | Tên biểu đồ Superset | Field | DAX/công thức | Bộ lọc | Dataset/metric | Chart | Thông tin còn thiếu |',
        '|---|---|---|---|---|---|---|---|---|']
    for r in mapping:
        values=[str(r['page']),r['source_title'],r['superset_chart'],r['fields'],'DAX chưa xác minh; SQL: '+r['SQL'],r['filters'],r['dataset'],str(r['chart_id'])+' · '+r['source_kind'],r['missing']]
        lines.append('| '+' | '.join(x.replace('|','\\|') for x in values)+' |')
    lines+=['','## Mức bằng chứng','',
        '- **Đã xác nhận từ tệp:** thứ tự 5 trang; 28 visual số liệu và 1 khối kết luận; field, tiêu đề hiển thị, slicer, giá trị in trên PDF. CSV sạch khớp từng dòng với bảng nguồn.',
        '- **Suy luận từ ảnh:** kiểu chart, màu gần mẫu Power BI (#118DFF, #FBE34D, #D64550), vị trí tương đối, sắp xếp, format và band khoảng cách. CSV xác nhận cờ long tương ứng delivery_time >160; chưa xác nhận công thức DAX.',
        '- **Chưa có bằng chứng:** tên tab gốc, DAX, Power Query/ETL nguồn, bookmark, hidden filters, drill-through, tooltip tùy chỉnh, Top N và tương tác chéo. Không tự áp dụng Top N khi PDF chỉ có thanh cuộn/viewport.',
        '', '## Metric và NULL / filter context','',
        '| Metric | SQL tương đương đề xuất | Format |','|---|---|---|']
    for k,(name,expression,fmt) in METRICS.items():lines.append(f'| {name} (`{k}`) | `{expression}` | `{fmt}` |')
    lines+=['',
        '`COUNT(order_id)` đếm giá trị không NULL; `COUNT(DISTINCT order_id)` khác về nghĩa. Hai cách trùng kết quả trên snapshot này vì khóa không thiếu và không trùng. Không có DAX nên chưa biết Power BI dùng cách nào.',
        '`AVG` bỏ NULL rating; giữ đủ 54 đơn thiếu rating trong tổng đơn. Tỷ lệ long dùng cờ đã tồn tại, chia `NULLIF(COUNT(order_id),0)` và trả NULL khi không có đơn. Median/P90 dùng nội suy liên tục; khớp số PDF hiển thị, chưa chứng minh DAX gốc.',
        'Không dùng trung bình các trung bình nhóm. Các dataset ma trận tạo ô tổng riêng ở grain order × ô chi tiết/tổng; mỗi ô chỉ có đúng một bản của mỗi đơn thuộc ô. Không dùng SUM/COUNT trên toàn bộ tập sao chép này. Dataset `base` luôn giữ một dòng/đơn.',
        'Ngày là DATE không timezone, khoảng lọc dùng đầu bao gồm/cuối loại trừ. 11/02–06/04/2022 được biểu diễn `2022-02-11 : 2022-04-07`. Không tự đổi timezone. Giữ pickup_delay_min từ nguồn; đối chiếu phép modulo 24 giờ cho thấy 828 đơn qua nửa đêm và 0 sai lệch.',
        '', '## Bộ lọc và khác biệt tính năng','',
        '| Filter | Phạm vi trang theo PDF | Mặc định |','|---|---|---|',
        '| Order_Date | 1,2,3,4,5 | 11/02/2022 đến hết 06/04/2022 |',
        '| Traffic | 1,3,4,5 | All |','| Weather | 1,5 | All |',
        '| Vehicle | 1,2,4,5 | All |','| Area | 1,3,4,5 | All |','| Category | 1,2 | All |',
        '',
        'Superset dùng filter chung và exclusions theo chart/tab. Chọn một giá trị sẽ đi cùng khi chuyển sang tab có cùng filter; Power BI PDF không thể chứng minh slicer đã đồng bộ giữa các trang. Filter ngoài phạm vi bị ẩn/đánh dấu out of scope. Không bật cross-filter mặc định vì PDF không chứng minh cấu hình tương tác gốc.',
        'Native date filter không gắn dataset (`targets: [{}]`), đúng cơ chế Superset 6; mọi chart có main_dttm_col=order_date. Select filter trỏ cả bốn dataset để lọc đồng nhất các ô tổng.',
        'PDF có scroll/viewport ở chart category. Bản chuyển đổi giữ mọi category và dùng zoom/scroll khi cần; không cố định số liệu/giá trị từ ảnh. Khối kết luận trang 5 là văn bản tĩnh, được ghi nhãn rõ không cập nhật theo bộ lọc.',
        'Bố cục giữ thứ tự KPI và nhóm chart; Superset chuyển vùng lọc sang thanh ngang. Kích thước và tooltip là bản tương đương, không pixel-perfect. Kiểm tra ảnh trong `migration/evidence/screenshots/` và ghi nhận giới hạn ở `docs/browser-QA.md`.',
    ]
    (ROOT/'docs/visual-mapping.md').write_text('\n'.join(lines)+'\n')
    save('migration/evidence/visual-inventory.json',mapping)
    print('Wrote 28 visual mappings and metric crosswalk')


if __name__=='__main__':main()
