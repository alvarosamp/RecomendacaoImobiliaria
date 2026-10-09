"""Verify anonymous access to the exact release manifests and all layers."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

repos = ['alvarocareli/ri-hostinger-a10dda-' + name for name in ('api', 'frontend', 'db', 'mlflow', 'minio')]
accept = ', '.join(['application/vnd.oci.image.index.v1+json', 'application/vnd.docker.distribution.manifest.list.v2+json', 'application/vnd.oci.image.manifest.v1+json', 'application/vnd.docker.distribution.manifest.v2+json'])
results = []

for repo in repos:
    tag = '20261005-v1'
    query = urllib.parse.urlencode({'service': 'registry.docker.io', 'scope': f'repository:{repo}:pull'})
    with urllib.request.urlopen('https://auth.docker.io/token?' + query, timeout=60) as response:
        token = json.load(response)['token']
    headers = {'Authorization': 'Bearer ' + token, 'Accept': accept}
    registry = 'https://registry-1.docker.io/v2/' + repo

    def manifest(ref):
        request = urllib.request.Request(registry + '/manifests/' + ref, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response), response.headers['Docker-Content-Digest']

    index, digest = manifest(tag)
    if 'manifests' in index:
        platform = next(m for m in index['manifests'] if m.get('platform', {}).get('os') == 'linux' and m.get('platform', {}).get('architecture') == 'amd64')
        document, platform_digest = manifest(platform['digest'])
    else:
        document, platform_digest = index, digest
    for blob in [document['config'], *document['layers']]:
        request = urllib.request.Request(registry + '/blobs/' + blob['digest'], headers=headers, method='HEAD')
        with urllib.request.urlopen(request, timeout=60) as response:
            assert response.status == 200
    request = urllib.request.Request(registry + '/blobs/' + document['config']['digest'], headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        config = json.load(response)
    assert config['os'] == 'linux' and config['architecture'] == 'amd64'
    item = {'image': repo + ':' + tag, 'digest': digest, 'platform_digest': platform_digest, 'architecture': 'linux/amd64', 'anonymous_manifest_and_all_layers': True}
    results.append(item)
    print(json.dumps(item), flush=True)

Path('deploy/hostinger/published-images.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
