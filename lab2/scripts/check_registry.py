"""Wait for anonymous registry pull; never log registry tokens."""
import argparse
import json
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('repository')
parser.add_argument('digest')
parser.add_argument('--timeout', type=int, default=300)
args = parser.parse_args()
if args.repository.startswith('docker.io/'):
    name = args.repository.removeprefix('docker.io/')
    registry = 'registry-1.docker.io'
    token_url = f'https://auth.docker.io/token?service=registry.docker.io&scope=repository:{name}:pull'
else:
    name = args.repository.removeprefix('ghcr.io/')
    registry = 'ghcr.io'
    token_url = f'https://ghcr.io/token?service=ghcr.io&scope=repository:{name}:pull'
deadline = time.monotonic() + args.timeout
while True:
    try:
        with urllib.request.urlopen(token_url, timeout=15) as response:
            token = json.load(response)['token']
        request = urllib.request.Request(f'https://{registry}/v2/{name}/manifests/{args.digest}', method='HEAD',
            headers={'Authorization': f'Bearer {token}',
                     'Accept': 'application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json'})
        with urllib.request.urlopen(request, timeout=15) as response:
            actual = response.headers['Docker-Content-Digest']
        if actual != args.digest:
            raise SystemExit('Registry digest mismatch')
        print(json.dumps({'repository': args.repository, 'digest': actual, 'anonymous_pull': True}))
        break
    except (OSError, KeyError):
        if time.monotonic() >= deadline:
            raise SystemExit('Image is not anonymously pullable; check repository visibility')
        print('Waiting for anonymous registry access...', flush=True)
        time.sleep(10)
