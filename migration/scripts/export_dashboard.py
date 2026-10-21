"""Export only this project's dashboard via official REST; strip credentials."""
import io
import json
import re
import urllib.parse
import zipfile
import yaml
from common import API, ROOT, save, uid


def main():
    state=json.loads((ROOT/'migration/.state.json').read_text());api=API()
    ident=state['dashboard_id']
    d=api.request('GET',f'dashboard/{ident}')['result']
    if d['uuid']!=uid('dashboard:main'):raise RuntimeError('Dashboard ownership mismatch')
    payload=api.request('GET','dashboard/export/',params={'q':f'!({ident})'})
    if not isinstance(payload,bytes):raise RuntimeError('Expected official ZIP export')
    dest=ROOT/'migration/exports/amazon_delivery_superset_6.zip'
    counts={'dashboards':0,'charts':0,'datasets':0,'databases':0}
    with zipfile.ZipFile(io.BytesIO(payload)) as source,zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as out:
        for name in source.namelist():
            if name.endswith('/'):continue
            content=source.read(name)
            if '/databases/' in name and name.endswith('.yaml'):
                obj=yaml.safe_load(content)
                u=urllib.parse.urlsplit(obj['sqlalchemy_uri'])
                # Export has a masked password. Replace it regardless, and drop
                # any secret-bearing extras/certificates. Username is omitted.
                host=u.hostname or 'host.docker.internal'
                host=f'[{host}]' if ':' in host else host
                port=f':{u.port}' if u.port else ''
                obj['sqlalchemy_uri']=urllib.parse.urlunsplit((u.scheme,
                    'REPLACE_USER:XXXXXXXXXX@'+host+port,u.path,'',''))
                for key in ['password','encrypted_extra','server_cert','ssh_tunnel','ssh_tunnel_id']:
                    obj.pop(key,None)
                if 'extra' in obj:obj['extra']='{}'
                content=yaml.safe_dump(obj,sort_keys=False,allow_unicode=True).encode()
            for kind in counts:
                if f'/{kind}/' in name:counts[kind]+=1
            out.writestr(name,content)
    if counts!={'dashboards':1,'charts':28,'datasets':4,'databases':1}:
        raise RuntimeError('Unexpected export inventory; inspect before delivery')
    save('migration/evidence/export.json',dict(file=str(dest.relative_to(ROOT)),inventory=counts,
        format='official Superset dashboard export, version 1.0.0, from running Superset 6.0.0',
        credentials='database URI user/password replaced; configure existing DB or provide credentials at import',
        import_status='not reimported into live instance to avoid overwriting other shared database configuration'))
    print(json.dumps(counts))


if __name__=='__main__':main()
