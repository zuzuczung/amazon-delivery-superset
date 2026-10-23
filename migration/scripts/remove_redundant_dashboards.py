"""Remove only the retired five-dashboard expansion after ownership checks.

Default is a read-only preview. --apply first saves a sanitized official ZIP
and the main layout, then removes the five dashboards, their exclusive charts,
and their unused virtual dataset. No PostgreSQL object is changed.
"""
import argparse
import copy
import io
import json
import shutil
import urllib.parse
import zipfile
from pathlib import Path

import yaml
from common import API, MARKER, ROOT, save, uid


ARCHIVE = 'migration/retired/redundant-children-2026-10-23'
NAV_IDS = {'ROW-CHILD-DASHBOARDS-NAV', 'MARKDOWN-CHILD-DASHBOARDS-NAV'}


def safe_export(api, dashboard_ids):
    payload = api.request('GET', 'dashboard/export/',
                          params={'q': '!(' + ','.join(map(str, sorted(dashboard_ids))) + ')'})
    counts = dict(dashboards=0, charts=0, datasets=0, databases=0)
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(payload)) as src, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as dst:
        for name in src.namelist():
            if name.endswith('/'):
                continue
            content = src.read(name)
            if '/databases/' in name and name.endswith('.yaml'):
                item = yaml.safe_load(content)
                parsed = urllib.parse.urlsplit(item['sqlalchemy_uri'])
                host = parsed.hostname or 'host.docker.internal'
                host = '['+host+']' if ':' in host else host
                port = ':'+str(parsed.port) if parsed.port else ''
                item['sqlalchemy_uri'] = urllib.parse.urlunsplit((
                    parsed.scheme, 'REPLACE_USER:XXXXXXXXXX@'+host+port, parsed.path, '', ''))
                for key in ['password', 'encrypted_extra', 'server_cert', 'ssh_tunnel', 'ssh_tunnel_id']:
                    item.pop(key, None)
                if 'extra' in item:
                    item['extra'] = '{}'
                content = yaml.safe_dump(item, sort_keys=False, allow_unicode=True).encode()
            for kind in counts:
                if '/'+kind+'/' in name:
                    counts[kind] += 1
            dst.writestr(name, content)
    assert counts == dict(dashboards=5, charts=55, datasets=1, databases=1), counts
    destination = ROOT/ARCHIVE/'superset-children-backup.zip'
    if destination.exists():
        raise RuntimeError('A prior backup exists; refusing to overwrite it')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(output.getvalue())
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    state = json.loads((ROOT/'migration/evidence/child-dashboards.json').read_text())
    main_state = json.loads((ROOT/'migration/.state.json').read_text())
    dashboard_ids = {x['id'] for x in state['dashboards'].values()}
    chart_ids = set(state['charts'].values())
    assert len(dashboard_ids) == 5 and len(chart_ids) == 55
    assert not chart_ids.intersection(main_state['charts'].values())
    assert main_state['dashboard_id'] not in dashboard_ids
    api = API()
    main_id = main_state['dashboard_id']
    main_before = api.request('GET', f'dashboard/{main_id}')['result']
    assert main_before['uuid'] == uid('dashboard:main')
    datasets_before = {k: api.request('GET', f'dataset/{ident}')['result']
                       for k, ident in main_state['datasets'].items()}
    charts_before = {str(ident): api.request('GET', f'chart/{ident}')['result']
                     for ident in main_state['charts'].values()}
    for key, expected in state['dashboards'].items():
        item = api.request('GET', f"dashboard/{expected['id']}")['result']
        assert item['uuid'] == uid('dashboard:'+key) == expected['uuid']
        assert item['slug'] == expected['slug']
        linked = api.request('GET', f"dashboard/{expected['id']}/charts")['result']
        assert {c['id'] for c in linked} <= chart_ids
    for key, ident in state['charts'].items():
        item = api.request('GET', f'chart/{ident}')['result']
        assert item['uuid'] == uid('chart:'+key)
        assert (item.get('description') or '').startswith(MARKER)
        assert item['datasource_id'] == state['dataset_id']
        assert {d['id'] for d in item['dashboards']} <= dashboard_ids
    dataset = api.request('GET', f"dataset/{state['dataset_id']}")['result']
    assert dataset['uuid'] == uid('dataset:children')
    assert (dataset.get('description') or '').startswith(MARKER)
    assert dataset['sql'] and dataset['table_name'] == 'amazon_delivery_children'
    all_charts = api.all('chart')
    users = {c['id'] for c in all_charts if c.get('datasource_id') == state['dataset_id']}
    assert users == chart_ids, 'Child dataset is used by unexpected charts'
    dashboard_before_ids = {d['id'] for d in api.all('dashboard')}
    chart_before_ids = {c['id'] for c in all_charts}
    for d in api.all('dashboard'):
        if d['id'] in dashboard_ids or d['id'] == main_id:
            continue
        detail = api.request('GET', f"dashboard/{d['id']}")['result']
        config = json.loads(detail.get('json_metadata') or '{}')
        for filt in config.get('native_filter_configuration', []):
            assert all(t.get('datasetId') != state['dataset_id'] for t in filt.get('targets', []))
    print(json.dumps(dict(dashboard_ids=sorted(dashboard_ids), chart_count=len(chart_ids),
                          dataset_id=state['dataset_id'], apply=args.apply)))
    if not args.apply:
        return
    archive_counts = safe_export(api, dashboard_ids)
    save(ARCHIVE+'/main-before.json', {k: main_before.get(k) for k in
         ['id', 'uuid', 'position_json', 'json_metadata', 'css']})
    for path in ['migration/scripts/build_child_dashboards.py', 'migration/scripts/child_spec.py',
                 'migration/child-dashboards.state.json', 'migration/evidence/child-dashboards.json']:
        shutil.copy2(ROOT/path, ROOT/ARCHIVE/Path(path).name)
    positions = json.loads(main_before['position_json'])
    cleaned = copy.deepcopy(positions)
    for node in NAV_IDS:
        cleaned.pop(node, None)
    for node in cleaned.values():
        if isinstance(node, dict) and 'children' in node:
            node['children'] = [c for c in node['children'] if c not in NAV_IDS]
    api.request('PUT', f'dashboard/{main_id}', json={'position_json': json.dumps(cleaned, ensure_ascii=False)})
    for ident in sorted(dashboard_ids):
        api.request('DELETE', f'dashboard/{ident}')
    for ident in sorted(chart_ids):
        api.request('DELETE', f'chart/{ident}')
    api._lists.clear()
    assert not any(c.get('datasource_id') == state['dataset_id'] for c in api.all('chart'))
    api.request('DELETE', f"dataset/{state['dataset_id']}")
    api._lists.clear()
    assert {d['id'] for d in api.all('dashboard')} == dashboard_before_ids-dashboard_ids
    assert {c['id'] for c in api.all('chart')} == chart_before_ids-chart_ids
    assert state['dataset_id'] not in {d['id'] for d in api.all('dataset')}
    current = api.request('GET', f'dashboard/{main_id}')['result']
    assert json.loads(current['position_json']) == cleaned
    for key in ['json_metadata', 'css', 'uuid']:
        assert current[key] == main_before[key]
    for ident, old in charts_before.items():
        actual = api.request('GET', 'chart/'+ident)['result']
        for key in ['uuid', 'params', 'query_context', 'slice_name', 'datasource_id']:
            assert actual.get(key) == old.get(key), (ident, key)
    for key, ident in main_state['datasets'].items():
        actual = api.request('GET', f'dataset/{ident}')['result']
        assert actual == datasets_before[key], 'Main dataset changed'
    linked = api.request('GET', f'dashboard/{main_id}/charts')['result']
    assert {c['id'] for c in linked} == set(main_state['charts'].values())
    assert sum(isinstance(n, dict) and n.get('type') == 'TAB' for n in cleaned.values()) == 5
    report = dict(status='removed', dashboard_ids=sorted(dashboard_ids), chart_ids=sorted(chart_ids),
                  removed_virtual_dataset_id=state['dataset_id'], backup=ARCHIVE+'/superset-children-backup.zip',
                  backup_inventory=archive_counts, main_dashboard_id=main_id,
                  main_tabs=5, main_charts_unchanged=28, main_datasets_unchanged=4,
                  other_resource_ids_unchanged=True, source_data_changed=False)
    save('migration/evidence/redundant-children-removal.json', report)
    state['status'] = 'removed'
    state['removal_evidence'] = 'migration/evidence/redundant-children-removal.json'
    save('migration/evidence/child-dashboards.json', state)
    save('migration/child-dashboards.state.json', state)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
