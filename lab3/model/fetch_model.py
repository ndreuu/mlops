import hashlib
import json
import os
from pathlib import Path
import urllib.request

root=Path(os.getenv('MODEL_ROOT','/models'))
root.mkdir(parents=True,exist_ok=True)
base='https://registry.ollama.ai/v2/library/deepseek-r1'
with urllib.request.urlopen(base+'/manifests/1.5b',timeout=30) as response:
    raw=response.read()
manifest=json.loads(raw)
if hashlib.sha256(raw).hexdigest()!='e0979632db5a88d1a53884cb2a941772d10ff5d055aabaa6801c4e36f3a6c2d7':
    raise ValueError('Ollama manifest changed; review before updating the pinned model')
weights=[x for x in manifest['layers'] if x['mediaType']=='application/vnd.ollama.image.model']
assert len(weights)==1 and weights[0]['digest']=='sha256:aabd4debf0c8f08881923f2c25fc0fdeed24435271c2b3e92c4af36704040dbc'
for layer in [manifest['config']]+manifest['layers']:
    digest=layer['digest'].split(':')[1]
    destination=root/'blobs'/('sha256-'+digest)
    destination.parent.mkdir(exist_ok=True)
    if not destination.exists():
        print('Downloading verified model blob:',layer['size'],'bytes',flush=True)
        with urllib.request.urlopen(base+'/blobs/'+layer['digest'],timeout=180) as response, destination.open('wb') as output:
            while block:=response.read(1024*1024):
                output.write(block)
    checksum=hashlib.file_digest(destination.open('rb'),'sha256').hexdigest()
    if checksum!=digest or destination.stat().st_size!=layer['size']:
        raise ValueError('Model blob checksum/size mismatch')
    destination.chmod(0o444)
destination=root/'manifests/registry.ollama.ai/library/deepseek-r1/1.5b'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_bytes(raw)
destination.chmod(0o444)
print(json.dumps({'model':'deepseek-r1:1.5b','weights_sha256':weights[0]['digest'],
                  'weights_bytes':weights[0]['size'],'manifest_sha256':hashlib.sha256(raw).hexdigest()}),flush=True)
