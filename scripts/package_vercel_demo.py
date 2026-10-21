"""Build an allowlisted, credential-free demo bundle after the Vite demo build."""
from pathlib import Path
import shutil
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from recomendacao_imobiliaria.case_demos import demo_inputs
from recomendacao_imobiliaria.decision_cases import KINDS, TITLES

def examples():
    target = ROOT / 'frontend/src/demo/examples.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps({kind: dict(title=TITLES[kind], inputs=demo_inputs(kind)) for kind in KINDS}, ensure_ascii=False), encoding='utf-8')

def package():
    target = ROOT / 'tmp/vercel-imobiliario'
    target.mkdir(parents=True, exist_ok=True)
    # Only generated frontend assets and explicitly selected Python modules are uploaded.
    shutil.copytree(ROOT / 'frontend/dist', target / 'public', dirs_exist_ok=True)
    (target / 'api').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'deploy/vercel-demo/api.py', target / 'api/demo.py')
    engine = target / 'demo_engine'
    engine.mkdir(exist_ok=True)
    for name in ['__init__', 'case_demos', 'decision_cases', 'case_reports', 'financial_study', 'technical_study', 'business_study', 'public_services']:
        shutil.copyfile(ROOT / f'src/recomendacao_imobiliaria/{name}.py', engine / f'{name}.py')
    shutil.copyfile(ROOT / 'api/routes/concept.py', engine / 'concept.py')
    (target / 'requirements.txt').write_text('fastapi==0.136.1\npydantic==2.13.3\n', encoding='utf-8')
    (target / '.vercelignore').write_text('.env*\n**/__pycache__/**\n**/*.pyc\n.vercel\n', encoding='utf-8')
    (target / 'vercel.json').write_text(json.dumps(dict(framework=None, buildCommand='', installCommand='', outputDirectory='public',
        functions={'api/demo.py': dict(maxDuration=30, includeFiles='demo_engine/**')},
        rewrites=[dict(source='/app/:path*', destination='/index.html'), dict(source='/login', destination='/index.html'), dict(source='/register', destination='/index.html')],
        headers=[dict(source='/(.*)', headers=[dict(key='X-Content-Type-Options', value='nosniff')])]), indent=2), encoding='utf-8')
    print(target)

if __name__ == '__main__':
    if '--examples' in sys.argv:
        examples()
    else:
        package()
