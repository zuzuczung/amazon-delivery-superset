"""Create five linked drill-down dashboards in the local Superset workspace."""
import argparse
import json
from pathlib import Path

from child_spec import DASHBOARDS, FILTERS, visuals
from common import API, MARKER, ROOT, save, uid
from migrate import dataset_metrics, form, query
from spec import COLUMN_LABELS


CHILD_DATASET_SQL = """SELECT b.*,
CASE
  WHEN pickup_delay_min < 5 THEN '01 · 0–5 phút'
  WHEN pickup_delay_min < 10 THEN '02 · 5–10 phút'
  WHEN pickup_delay_min < 15 THEN '03 · 10–15 phút'
  ELSE '04 · Trên 15 phút'
END AS pickup_delay_band
FROM amazon_bi.delivery_orders b"""


def page_visuals(dashboard, page):
    return [v for row in page['rows'] for v in row]


def chart_key(dashboard, page, visual):
    return f"{dashboard['key']}-{page['key']}-{visual['key']}"


def dashboard_layout(dashboard, chart_ids):
    tabs = 'TABS-' + dashboard['key'].upper()
    pos = {
        'DASHBOARD_VERSION_KEY': 'v2',
        'ROOT_ID': dict(type='ROOT', id='ROOT_ID', children=['GRID_ID']),
        'GRID_ID': dict(type='GRID', id='GRID_ID', children=['ROW-BACK', tabs], parents=['ROOT_ID']),
        'ROW-BACK': dict(type='ROW', id='ROW-BACK', children=['MARKDOWN-BACK'],
                         parents=['ROOT_ID', 'GRID_ID'], meta={'background': 'BACKGROUND_TRANSPARENT'}),
        'MARKDOWN-BACK': dict(type='MARKDOWN', id='MARKDOWN-BACK', children=[],
                              parents=['ROOT_ID', 'GRID_ID', 'ROW-BACK'],
                              meta={'width': 12, 'height': 8,
                                    'code': '[← Về dashboard chính](/superset/dashboard/amazon-delivery-intelligence/)'}),
        tabs: dict(type='TABS', id=tabs, children=[], parents=['ROOT_ID', 'GRID_ID'], meta={}),
    }
    base_parents = ['ROOT_ID', 'GRID_ID', tabs]
    for page_index, page in enumerate(dashboard['pages'], 1):
        tab = f"TAB-{dashboard['key'].upper()}-{page_index}"
        pos[tabs]['children'].append(tab)
        pos[tab] = dict(type='TAB', id=tab, children=[], parents=base_parents,
                        meta={'text': page['name']})
        for row_index, row in enumerate(page['rows']):
            row_id = f"ROW-{dashboard['key'].upper()}-{page_index}-{row_index}"
            pos[tab]['children'].append(row_id)
            pos[row_id] = dict(type='ROW', id=row_id, children=[],
                               parents=base_parents + [tab],
                               meta={'background': 'BACKGROUND_TRANSPARENT'})
            for v in row:
                key = chart_key(dashboard, page, v)
                chart_id = chart_ids[key]
                node = f'CHART-{chart_id}'
                pos[row_id]['children'].append(node)
                pos[node] = dict(type='CHART', id=node, children=[],
                                 parents=base_parents + [tab, row_id],
                                 meta={'chartId': chart_id, 'uuid': uid('chart:' + key),
                                       'width': 12 // len(row),
                                       'height': 22 if v['kind'] == 'kpi' else 50,
                                       'sliceName': v['title']})
    return pos


def native_filters(dashboard, dataset_id, chart_ids):
    all_ids = [chart_ids[chart_key(dashboard, p, v)]
               for p in dashboard['pages'] for v in page_visuals(dashboard, p)]
    tabs = [f"TAB-{dashboard['key'].upper()}-{i}"
            for i in range(1, len(dashboard['pages']) + 1)]
    configs = []
    for col in FILTERS:
        is_time = col == 'order_date'
        default = ({'extraFormData': {'time_range': '2022-02-11 : 2022-04-07'},
                    'filterState': {'value': '2022-02-11 : 2022-04-07'}, 'ownState': {}}
                   if is_time else {'extraFormData': {}, 'filterState': {}, 'ownState': {}})
        configs.append(dict(
            id=f"NATIVE_FILTER-{dashboard['key'].upper()}-{col}", type='NATIVE_FILTER',
            name=COLUMN_LABELS[col], filterType='filter_time' if is_time else 'filter_select',
            targets=[{}] if is_time else [{'datasetId': dataset_id, 'column': {'name': col}}],
            defaultDataMask=default, cascadeParentIds=[],
            controlValues={'enableEmptyFilter': False, 'multiSelect': True, 'searchAllOptions': True},
            scope={'rootPath': ['ROOT_ID'], 'excluded': []},
            chartsInScope=all_ids, tabsInScope=tabs))
    return configs


def metadata(dashboard, dataset_id, chart_ids):
    return dict(
        native_filter_configuration=native_filters(dashboard, dataset_id, chart_ids),
        filter_bar_orientation='HORIZONTAL', cross_filters_enabled=False,
        chart_configuration={}, color_scheme='supersetColors',
        label_colors={'Jam': '#D64550', 'High': '#E66C37', 'Medium': '#FBE34D',
                      'Low': '#118DFF', 'motorcycle': '#118DFF',
                      'scooter': '#6B007B', 'van': '#E66C37'},
        refresh_frequency=0, expanded_slices={}, timed_refresh_immune_slices=[],
        map_label_colors={}, shared_label_colors=[], color_scheme_domain=[])


def upsert_dataset(api, database_id):
    expected = uid('dataset:children')
    existing = [x for x in api.all('dataset') if x.get('uuid') == expected]
    table = 'amazon_delivery_children'
    if existing:
        dataset_id = existing[0]['id']
        current = api.request('GET', f'dataset/{dataset_id}')['result']
        if not (current.get('description') or '').startswith(MARKER):
            raise RuntimeError('Child dataset ownership mismatch')
        api.request('PUT', f'dataset/{dataset_id}', json={'sql': CHILD_DATASET_SQL})
    else:
        collisions = [x for x in api.all('dataset')
                      if x.get('table_name') == table and x.get('schema') == 'amazon_bi']
        if collisions:
            raise RuntimeError('Unowned child dataset name collision')
        dataset_id = api.request('POST', 'dataset/', json={
            'database': database_id, 'schema': 'amazon_bi', 'table_name': table,
            'sql': CHILD_DATASET_SQL, 'uuid': expected})['id']
    current = api.request('GET', f'dataset/{dataset_id}')['result']
    metric_ids = {m['metric_name']: m['id'] for m in current['metrics']}
    metrics = [{**m, **({'id': metric_ids[m['metric_name']]}
                        if m['metric_name'] in metric_ids else {})}
               for m in dataset_metrics('base')]
    columns = [dict(id=c['id'], column_name=c['column_name'],
                    verbose_name=COLUMN_LABELS.get(c['column_name'], c.get('verbose_name')))
               for c in current['columns']]
    api.request('PUT', f'dataset/{dataset_id}', json={
        'description': MARKER + '; child dashboards; grain=one order',
        'main_dttm_col': 'order_date', 'filter_select_enabled': True,
        'metrics': metrics, 'columns': columns})
    return dataset_id


def add_main_navigation(api, child_urls):
    state = json.loads((ROOT / 'migration/.state.json').read_text())
    dashboard = api.request('GET', f"dashboard/{state['dashboard_id']}")['result']
    if dashboard.get('uuid') != uid('dashboard:main'):
        raise RuntimeError('Main dashboard ownership mismatch')
    pos = json.loads(dashboard['position_json'])
    row_id, markdown_id = 'ROW-CHILD-DASHBOARDS-NAV', 'MARKDOWN-CHILD-DASHBOARDS-NAV'
    if row_id not in pos:
        backup = ROOT / 'migration/evidence/child-dashboards-main-before.json'
        if not backup.exists():
            save('migration/evidence/child-dashboards-main-before.json', {
                'dashboard_id': state['dashboard_id'],
                'position_json': dashboard['position_json'],
                'json_metadata': dashboard['json_metadata']})
        tab = 'TAB-P1'
        if tab not in pos:
            raise RuntimeError('Main dashboard first tab is missing')
        pos[tab]['children'].insert(0, row_id)
        parents = ['ROOT_ID', 'GRID_ID', 'TABS-AMAZON', tab]
        pos[row_id] = dict(type='ROW', id=row_id, children=[markdown_id], parents=parents,
                           meta={'background': 'BACKGROUND_TRANSPARENT'})
        links = ' · '.join(f"[{title}]({url})" for title, url in child_urls)
        pos[markdown_id] = dict(type='MARKDOWN', id=markdown_id, children=[],
                                parents=parents + [row_id],
                                meta={'width': 12, 'height': 12,
                                      'code': '**Dashboard phân tích chuyên sâu:**  ' + links})
    else:
        links = ' · '.join(f"[{title}]({url})" for title, url in child_urls)
        pos[markdown_id]['meta']['code'] = '**Dashboard phân tích chuyên sâu:**  ' + links
    api.request('PUT', f"dashboard/{state['dashboard_id']}",
                json={'position_json': json.dumps(pos, ensure_ascii=False)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    page_count = sum(len(d['pages']) for d in DASHBOARDS)
    chart_count = sum(len(visuals(d)) for d in DASHBOARDS)
    if not args.apply:
        print(json.dumps({'dashboards': len(DASHBOARDS), 'pages': page_count,
                          'charts': chart_count, 'apply': False}, ensure_ascii=False))
        return

    api = API()
    main_state = json.loads((ROOT / 'migration/.state.json').read_text())
    dataset_id = upsert_dataset(api, main_state['database_id'])
    themes = api.all('theme')
    light = [t for t in themes if t.get('is_system') and t.get('theme_name') == 'THEME_DEFAULT']
    css = ('.dashboard-content{background:#fff}.dashboard-chart{border:1px solid #118DFF;'
           'border-radius:4px}.dashboard-component-tabs-content{background:#fff}'
           '.header-title a{font-size:14px;line-height:18px}')
    result = {'dataset_id': dataset_id, 'dashboards': {}, 'charts': {}}
    child_urls = []

    for dashboard in DASHBOARDS:
        chart_ids = {}
        for page in dashboard['pages']:
            for v in page_visuals(dashboard, page):
                key = chart_key(dashboard, page, v)
                f = form(v, dataset_id)
                chart_ids[key] = api.upsert('chart', key, dict(
                    slice_name=v['title'],
                    description=MARKER + '; child dashboard; ' + key,
                    datasource_id=dataset_id, datasource_type='table', viz_type=f['viz_type'],
                    params=json.dumps(f, ensure_ascii=False),
                    query_context=json.dumps(query(v, dataset_id), ensure_ascii=False)))
        body = dict(dashboard_title=dashboard['title'], slug=dashboard['slug'], published=True,
                    position_json=json.dumps(dashboard_layout(dashboard, chart_ids), ensure_ascii=False),
                    json_metadata=json.dumps(metadata(dashboard, dataset_id, chart_ids), ensure_ascii=False),
                    css=css)
        if light:
            body['theme_id'] = light[0]['id']
        for existing in api.all('dashboard'):
            if existing.get('slug') == dashboard['slug'] and existing.get('uuid') != uid('dashboard:' + dashboard['key']):
                raise RuntimeError('Dashboard slug belongs to another resource: ' + dashboard['slug'])
        dashboard_id = api.upsert('dashboard', dashboard['key'], body)
        for page in dashboard['pages']:
            for v in page_visuals(dashboard, page):
                key = chart_key(dashboard, page, v)
                chart_id = chart_ids[key]
                f = form(v, dataset_id)
                f.update(slice_id=chart_id, dashboards=[dashboard_id])
                context = query(v, dataset_id)
                context['form_data'] = f
                api.request('PUT', f'chart/{chart_id}', json={
                    'dashboards': [dashboard_id],
                    'params': json.dumps(f, ensure_ascii=False),
                    'query_context': json.dumps(context, ensure_ascii=False)})
        url = api.base + '/superset/dashboard/' + dashboard['slug'] + '/'
        child_urls.append((dashboard['title'].split('·', 1)[1].strip(), url))
        result['dashboards'][dashboard['key']] = {
            'id': dashboard_id, 'uuid': uid('dashboard:' + dashboard['key']),
            'title': dashboard['title'], 'slug': dashboard['slug'], 'url': url,
            'pages': [p['name'] for p in dashboard['pages']], 'charts': len(chart_ids)}
        result['charts'].update(chart_ids)

    add_main_navigation(api, child_urls)

    failures = []
    main_dashboard = api.request('GET', f"dashboard/{main_state['dashboard_id']}")['result']
    main_positions = json.loads(main_dashboard['position_json'])
    main_tabs = sum(isinstance(n, dict) and n.get('type') == 'TAB'
                    for n in main_positions.values())
    main_linked = api.request('GET', f"dashboard/{main_state['dashboard_id']}/charts")['result']
    if main_tabs != 5:
        failures.append(['main', 'tab_count', main_tabs])
    if len(main_linked) != 28:
        failures.append(['main', 'linked_charts', len(main_linked)])
    if 'ROW-CHILD-DASHBOARDS-NAV' not in main_positions:
        failures.append(['main', 'child_navigation_missing'])
    for dashboard in DASHBOARDS:
        item = result['dashboards'][dashboard['key']]
        persisted = api.request('GET', f"dashboard/{item['id']}")['result']
        positions = json.loads(persisted['position_json'])
        tab_count = sum(isinstance(n, dict) and n.get('type') == 'TAB' for n in positions.values())
        linked = api.request('GET', f"dashboard/{item['id']}/charts")['result']
        if tab_count != len(dashboard['pages']):
            failures.append([dashboard['key'], 'tab_count', tab_count])
        if len(linked) != len(visuals(dashboard)):
            failures.append([dashboard['key'], 'linked_charts', len(linked)])
        for page in dashboard['pages']:
            for v in page_visuals(dashboard, page):
                response = api.request('POST', 'chart/data', json=query(v, dataset_id))
                status = response['result'][0].get('status')
                if status != 'success':
                    failures.append([chart_key(dashboard, page, v), 'query', status])

    result.update(pages=page_count, chart_count=chart_count,
                  main_dashboard_id=main_state['dashboard_id'], failures=failures)
    save('migration/child-dashboards.state.json', result)
    save('migration/evidence/child-dashboards.json', result)
    if failures:
        raise SystemExit(f'FAILED: {len(failures)} child dashboard checks')
    print(json.dumps({'dashboards': len(DASHBOARDS), 'pages': page_count,
                      'charts': chart_count, 'dataset_id': dataset_id,
                      'failures': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
