"""Detect local secret values in the source selected for publication."""
from pathlib import Path
from dotenv import dotenv_values

secrets = []
for file in ('.env', 'hostinger.env'):
    for key, value in dotenv_values(file).items():
        if value and len(value) >= 12 and any(word in key.upper() for word in ('PASS', 'SECRET', 'TOKEN', 'KEY')):
            secrets.append(value.encode())
roots = ['src', 'api', 'config', 'frontend/src', 'frontend/public', 'Infra/initdb']
found = []
for root in roots:
    for file in Path(root).rglob('*'):
        if file.is_file() and file.suffix in ('.py', '.json', '.js', '.jsx', '.css', '.html', '.sql', '.svg'):
            content = file.read_bytes()
            if any(secret in content for secret in secrets):
                found.append(str(file))
assert not found, 'Local secret value detected in: ' + ', '.join(found)
print('PASS: no local or deployment secret values in selected application source')
