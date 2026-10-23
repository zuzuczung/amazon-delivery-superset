"""One local entry point; credentials are prompted without echo, never saved."""
import getpass
import os
import subprocess
import sys
from common import ROOT


def main():
    if not os.environ.get('SUPERSET_ACCESS_TOKEN'):
        if not os.environ.get('SUPERSET_USERNAME'):
            os.environ['SUPERSET_USERNAME']=input('Superset username: ')
        if not os.environ.get('SUPERSET_PASSWORD'):
            os.environ['SUPERSET_PASSWORD']=getpass.getpass('Superset password: ')
    try:
        for script,args in [('profile.py',[]),('migrate.py',['--apply-sql']),
                            ('build_risk_dashboard.py',['--apply']),('verify_risk_dashboard.py',[]),
                            ('build_vehicle_dashboard.py',['--apply']),('verify_vehicle_dashboard.py',[]),
                            ('verify.py',[]),('export_dashboard.py',[]),('document.py',[])]:
            subprocess.run([sys.executable,str(ROOT/'migration/scripts'/script),*args],check=True,cwd=ROOT)
    finally:
        os.environ.pop('SUPERSET_PASSWORD',None)


if __name__=='__main__':main()
