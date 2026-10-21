"""Small REST/psql clients. Never print request credentials, URIs or response bodies."""
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
import requests

ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = uuid.UUID('f114501e-2921-4d3a-9f01-a4ee1bde59c4')
MARKER = 'amazon-delivery-intelligence:superset-migration:v1'


def uid(key):
    return str(uuid.uuid5(NAMESPACE, key))


def save(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sql(query):
    """Use existing local container, or psql with standard PG* environment vars.

    Passwords belong in PGPASSFILE/PGPASSWORD, never in command arguments.
    """
    db = os.environ.get('AMAZON_DATABASE', 'tunglocaldb')
    container = os.environ.get('AMAZON_PG_CONTAINER', 'postgres-local')
    if container:
        args = ['docker', 'exec', '-i', container, 'sh', '-c',
                'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -At', 'sh', db]
    else:
        args = ['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-d', db, '-At']
    result = subprocess.run(args, input=query, text=True, capture_output=True)
    if result.returncode:
        # Do not propagate connection strings or credentials from subprocess errors.
        raise RuntimeError('PostgreSQL command failed; check target, access, and SQL file')
    return result.stdout.strip()


def sql_json(query):
    return json.loads(sql('SELECT coalesce(json_agg(t),\'[]\'::json) FROM (' + query.rstrip(';') + ') t;'))


class API:
    def __init__(self):
        self.base = os.environ.get('SUPERSET_URL', 'http://localhost:8088').rstrip('/')
        self.s = requests.Session()
        self._lists = {}
        self.refresh_token = os.environ.get('SUPERSET_REFRESH_TOKEN')
        token = os.environ.get('SUPERSET_ACCESS_TOKEN')
        if not token:
            user = os.environ.get('SUPERSET_USERNAME')
            password = os.environ.get('SUPERSET_PASSWORD')
            if user and password:
                r = self.s.post(self.base + '/api/v1/security/login', json={
                    'username': user, 'password': password, 'provider': 'db', 'refresh': True}, timeout=30)
                if not r.ok:
                    raise RuntimeError('Superset sign-in failed; credentials are not logged')
                auth=r.json();token=auth['access_token'];self.refresh_token=auth.get('refresh_token')
            elif (ROOT / 'migration/.auth.json').exists():
                auth=json.loads((ROOT / 'migration/.auth.json').read_text())
                token=auth['access_token'];self.refresh_token=auth.get('refresh_token')
            else:
                raise RuntimeError('Set SUPERSET_USERNAME/SUPERSET_PASSWORD or SUPERSET_ACCESS_TOKEN')
        self.s.headers['Authorization'] = 'Bearer ' + token
        self.s.headers['X-CSRFToken'] = self.request('GET', 'security/csrf_token/')['result']
        self.s.headers['Referer'] = self.base + '/'

    def request(self, method, path, **kwargs):
        # A stale pooled HTTP connection may be closed by gunicorn. Retry only
        # reads, including the SELECT-only chart-data endpoint; never mutations.
        tries=3 if method=='GET' or (method=='POST' and path=='chart/data') else 1
        for attempt in range(tries):
            try:
                r=self.s.request(method,self.base+'/api/v1/'+path,timeout=120,**kwargs)
                break
            except requests.RequestException:
                if attempt+1==tries:raise RuntimeError(f'Superset {method} {path}: connection failed') from None
                time.sleep(attempt+1)
        if r.status_code==401 and self.refresh_token:
            refreshed=self.s.post(self.base+'/api/v1/security/refresh',
                headers={'Authorization':'Bearer '+self.refresh_token},timeout=30)
            if refreshed.ok:
                self.s.headers['Authorization']='Bearer '+refreshed.json()['access_token']
                r=self.s.request(method,self.base+'/api/v1/'+path,timeout=120,**kwargs)
        if not r.ok:
            # Whitelist validation field names only; bodies can contain SQL/data/credentials.
            try:
                data = r.json()
                fields = list(data.get('message', {})) if isinstance(data.get('message'), dict) else []
            except ValueError:
                fields = []
            raise RuntimeError(f'Superset {method} {path}: HTTP {r.status_code}; fields={fields}')
        if r.headers.get('Content-Type', '').startswith('application/zip'):
            return r.content
        return r.json()

    def all(self, kind):
        if kind in self._lists:return self._lists[kind]
        result, page = [], 0
        while True:
            d = self.request('GET', kind + '/', params={'q': f'(page:{page},page_size:100)'})
            result.extend(d['result'])
            if len(result) >= d['count']:
                self._lists[kind]=result
                return result
            page += 1

    def upsert(self, kind, key, body):
        """Deterministic UUIDs survive missing state files and failed partial runs."""
        expected = uid(kind + ':' + key)
        found = [x for x in self.all(kind) if x.get('uuid') == expected]
        if len(found) > 1:
            raise RuntimeError('Duplicate project UUID; refusing ambiguous update')
        if found:
            ident = found[0]['id']
            d = self.request('GET', f'{kind}/{ident}')['result']
            if d.get('description') and not d['description'].startswith(MARKER):
                raise RuntimeError('Project ownership marker mismatch')
            self.request('PUT', f'{kind}/{ident}', json={**body, 'uuid': expected})
        else:
            ident = self.request('POST', kind + '/', json={**body, 'uuid': expected})['id']
            self._lists[kind].append({'id':ident,'uuid':expected})
        return ident
