import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path


def get_json(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True)
    parser.add_argument('--namespace', default='itmo-student-13')
    parser.add_argument('--port', type=int, default=18090)
    parser.add_argument('--expected-digest', required=True)
    parser.add_argument('--expected-revision', required=True)
    parser.add_argument('--expected-environment', required=True)
    parser.add_argument('--expected-ranking', choices=['normal', 'reverse'], default='normal')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    base_url = f'http://127.0.0.1:{args.port}'
    process = subprocess.Popen([
        'kubectl', '-n', args.namespace, 'port-forward', '--address=127.0.0.1',
        f'service/{args.release}-mlops-search', f'{args.port}:80'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise SystemExit('port-forward terminated before readiness')
            try:
                ready = get_json(base_url + '/readyz')
                if ready.get('status') == 'ready':
                    break
            except (OSError, ValueError):
                pass
            time.sleep(.5)
        else:
            raise SystemExit('readiness timed out')
        meta = get_json(base_url + '/meta')
        request = urllib.request.Request(base_url + '/v1/search',
            data=json.dumps({'query': 'как вернуть предыдущую модель после плохого релиза', 'limit': 3}).encode(),
            headers={'content-type': 'application/json', 'x-request-id': 'release-smoke'})
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.load(response)
        top = result['results'][0]['id']
        checks = {
            'ready': ready.get('status') == 'ready',
            'top_result': top == 'doc-rollback',
            'image_digest': meta.get('image_digest') == args.expected_digest,
            'build_revision': meta.get('build_revision') == args.expected_revision,
            'environment': meta.get('environment') == args.expected_environment,
            'ranking_mode': meta.get('ranking_mode') == args.expected_ranking,
            'index_version': ready.get('index_version') == meta.get('index_version') == result.get('index_version'),
            'request_id': result.get('request_id') == 'release-smoke',
        }
        report = {'release': args.release, 'ready': ready, 'meta': meta, 'expected_top': 'doc-rollback',
                  'actual_top': top, 'checks': checks, 'passed': all(checks.values())}
        output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        print(output, end='')
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output)
        if not report['passed']:
            raise SystemExit('semantic smoke failed')
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == '__main__':
    main()
