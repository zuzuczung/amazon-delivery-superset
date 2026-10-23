"""Apply Vietnamese presentation labels without rebuilding charts or their queries."""
import argparse
import copy
import json

from common import API, ROOT, save, uid
from migrate import dataset_metrics
from spec import COLUMN_LABELS, METRICS, title, visuals


def chart_labels(params, visual):
    result = copy.deepcopy(params)
    if 'subheader' in result and visual['kind'] == 'kpi':
        result['subheader'] = METRICS[visual['metric']][0]
    if result.get('x_axis_title'):
        result['x_axis_title'] = COLUMN_LABELS.get(visual['dimension'], result['x_axis_title'])
    if result.get('y_axis_title'):
        result['y_axis_title'] = METRICS[visual['metric']][0]
    if 'slice_name' in result:
        result['slice_name'] = title(visual)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    state = json.loads((ROOT / 'migration/evidence/deployment.json').read_text())
    api = API()
    dashboard = api.request('GET', f"dashboard/{state['dashboard_id']}")['result']
    assert dashboard['uuid'] == uid('dashboard:main'), 'Dashboard ownership mismatch'
    backup = {'dashboard': {}, 'charts': {}, 'datasets': {}}
    chart_updates, dataset_updates = {}, {}
    translations, expected_titles = {}, {}
    for visual in visuals():
        ident = state['charts'][visual['key']]
        chart = api.request('GET', f'chart/{ident}')['result']
        assert chart['uuid'] == uid('chart:' + visual['key']), 'Chart ownership mismatch'
        expected_titles[ident] = title(visual)
        translations[chart['slice_name']] = title(visual)
        old = {key: chart[key] for key in ['slice_name', 'params', 'query_context']}
        new = copy.deepcopy(old)
        new['slice_name'] = title(visual)
        new['params'] = json.dumps(chart_labels(json.loads(old['params']), visual), ensure_ascii=False)
        if old['query_context']:
            context = json.loads(old['query_context'])
            context['form_data'] = chart_labels(context.get('form_data', {}), visual)
            new['query_context'] = json.dumps(context, ensure_ascii=False)
        backup['charts'][str(ident)] = old
        chart_updates[ident] = new
    for key, ident in state['datasets'].items():
        dataset = api.request('GET', f'dataset/{ident}')['result']
        assert dataset['uuid'] == uid('dataset:' + key), 'Dataset ownership mismatch'
        old = {
            'metrics': [{k: m[k] for k in ['id', 'metric_name', 'verbose_name', 'expression', 'd3format', 'description'] if k in m}
                        for m in dataset['metrics']],
            'columns': [{k: c[k] for k in ['id', 'column_name', 'verbose_name'] if k in c}
                        for c in dataset['columns']],
        }
        new = copy.deepcopy(old)
        labels = {m['metric_name']: m['verbose_name'] for m in dataset_metrics(key)}
        for metric in new['metrics']:
            if metric['metric_name'] in labels:
                translations[metric.get('verbose_name') or metric['metric_name']] = labels[metric['metric_name']]
                metric['verbose_name'] = labels[metric['metric_name']]
        for column in new['columns']:
            if column['column_name'] in COLUMN_LABELS:
                column['verbose_name'] = COLUMN_LABELS[column['column_name']]
        backup['datasets'][str(ident)] = old
        dataset_updates[ident] = new
    old_dashboard = {key: dashboard[key] for key in ['position_json', 'json_metadata']}
    backup['dashboard'] = old_dashboard
    position = json.loads(old_dashboard['position_json'])
    for node in position.values():
        if not isinstance(node, dict) or node.get('type') != 'CHART':
            continue
        meta = node['meta']
        if meta.get('chartId') in expected_titles:
            meta['sliceName'] = expected_titles[meta['chartId']]
            if 'chartTitle' in meta:
                meta['chartTitle'] = meta['sliceName']
    metadata = json.loads(old_dashboard['json_metadata'])
    for name in ['label_colors', 'map_label_colors']:
        if isinstance(metadata.get(name), dict):
            metadata[name] = {translations.get(k, k): value for k, value in metadata[name].items()}
    for name in ['shared_label_colors', 'color_scheme_domain']:
        if isinstance(metadata.get(name), list):
            metadata[name] = [translations.get(value, value) if isinstance(value, str) else value
                              for value in metadata[name]]
    for config in metadata.get('native_filter_configuration', []):
        column = config['id'].removeprefix('NATIVE_FILTER-AMAZON-')
        if column in COLUMN_LABELS:
            config['name'] = COLUMN_LABELS[column]
    new_dashboard = {'position_json': json.dumps(position, ensure_ascii=False),
                     'json_metadata': json.dumps(metadata, ensure_ascii=False)}
    if not args.apply:
        print(json.dumps({'dashboard_id': state['dashboard_id'], 'charts': expected_titles,
                          'datasets': list(dataset_updates), 'mode': 'preview'}, ensure_ascii=False))
        return
    backup_path = ROOT / 'migration/evidence/localization-before.json'
    # Keep the first pre-change snapshot for rollback, including after a partial run.
    if not backup_path.exists():
        save('migration/evidence/localization-before.json', backup)
    for ident, body in dataset_updates.items():
        api.request('PUT', f'dataset/{ident}', json=body)
    for ident, body in chart_updates.items():
        api.request('PUT', f'chart/{ident}', json=body)
    api.request('PUT', f"dashboard/{state['dashboard_id']}", json=new_dashboard)
    checks = []
    for ident, body in chart_updates.items():
        actual = api.request('GET', f'chart/{ident}')['result']
        assert actual['slice_name'] == expected_titles[ident]
        assert json.loads(actual['params']) == json.loads(body['params'])
        old_context = json.loads(backup['charts'][str(ident)]['query_context'])
        new_context = json.loads(actual['query_context'])
        assert old_context['queries'] == new_context['queries'], 'Analytical query changed'
        checks.append({'id': ident, 'title': actual['slice_name'], 'queries_unchanged': True})
    for ident in dataset_updates:
        actual = api.request('GET', f'dataset/{ident}')['result']
        before = backup['datasets'][str(ident)]['metrics']
        assert {m['metric_name']: m['expression'] for m in before} == {
            m['metric_name']: m['expression'] for m in actual['metrics']}, 'SQL expression changed'
        assert {m['metric_name']: m.get('d3format') for m in before} == {
            m['metric_name']: m.get('d3format') for m in actual['metrics']}, 'Number format changed'
        assert {m['metric_name']: m.get('verbose_name') for m in actual['metrics']} == {
            m['metric_name']: m.get('verbose_name') for m in dataset_updates[ident]['metrics']}
    actual = api.request('GET', f"dashboard/{state['dashboard_id']}")['result']
    assert json.loads(actual['position_json']) == position
    assert json.loads(actual['json_metadata']) == metadata
    save('migration/evidence/localization.json', {
        'language': 'vi', 'dashboard_id': state['dashboard_id'], 'charts': checks,
        'sql_and_queries_unchanged': True, 'dataset_ids': list(dataset_updates),
        'backup': 'migration/evidence/localization-before.json',
    })
    print(json.dumps({'localized_charts': len(checks), 'queries_unchanged': True, 'datasets': len(dataset_updates)}))


if __name__ == '__main__':
    main()
