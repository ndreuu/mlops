"""Wait for anonymous GHCR pull; never log registry tokens."""
import argparse
import json
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('repository')
parser.add_argument('digest')
parser.add_argument('--timeout', type=int, default=300)
args = parser.parse_args()
name = args.repository.removeprefix('ghcr.io/')
deadline = time.monotonic() + args.timeout
while True:
    try:
        with urllib.request.urlopen(f'https://ghcr.io/token?service=ghcr.io&scope=repository:{name}:pull', timeout=15) as response:
            token = json.load(response)['token']
        request = urllib.request.Request(f'https://ghcr.io/v2/{name}/manifests/{args.digest}', method='HEAD',
            headers={'Authorization': f'Bearer {token}',
                     'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
        with urllib.request.urlopen(request, timeout=15) as response:
            actual = response.headers['Docker-Content-Digest']
        if actual != args.digest:
            raise SystemExit('Registry digest mismatch')
        print(json.dumps({'repository': args.repository, 'digest': actual, 'anonymous_pull': True}))
        break
    except (OSError, KeyError):
        if time.monotonic() >= deadline:
            raise SystemExit('Image is not anonymously pullable; set the GHCR package visibility to Public')
        print('Waiting for anonymous registry access...', flush=True)
        time.sleep(10)
