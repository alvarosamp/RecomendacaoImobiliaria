"""Create a static allowlist for Vercel. No collection, credentials or network."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'public'
SNAPSHOTS = ('simulation.json', 'roads.json', 'radar.json', 'territory.json', 'regulations.json', 'market.json')
STATIC_SUFFIXES = {'.html', '.js', '.css', '.svg', '.png'}


def build():
    inventory = json.loads((ROOT / 'data' / 'simulation.json').read_text())
    if inventory.get('meta', {}).get('synthetic') is not True:
        raise ValueError('Only the synthetic ISP demonstration may be packaged.')
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)  # Generated output only; never the source web/data folders.
    OUTPUT.mkdir()
    for source in (ROOT / 'web').rglob('*'):
        if not source.is_file():
            continue
        if source.suffix not in STATIC_SUFFIXES and source.name != 'LEAFLET-LICENSE':
            continue
        if source.is_symlink():
            raise ValueError(f'Symlinks are not allowed in the static bundle: {source.name}')
        destination = OUTPUT / source.relative_to(ROOT / 'web')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    snapshots = OUTPUT / 'snapshots'
    snapshots.mkdir()
    for name in SNAPSHOTS:
        source = ROOT / 'data' / name
        json.loads(source.read_text())
        shutil.copyfile(source, snapshots / name)
    (OUTPUT / 'health.json').write_text(json.dumps({'status':'ok', 'mode':'synthetic-demo'}))
    files = [p for p in OUTPUT.rglob('*') if p.is_file()]
    print(f'ISP static build: {len(files)} files, {sum(p.stat().st_size for p in files):,} bytes; planning uses api/plan.py.')


if __name__ == '__main__':
    build()
