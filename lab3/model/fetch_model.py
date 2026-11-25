import hashlib
import json
import os
from pathlib import Path
import urllib.request

root=Path(os.getenv('MODEL_ROOT','/models'))
root.mkdir(parents=True,exist_ok=True)
base='https://registry.ollama.ai/v2/library/qwen3'
with urllib.request.urlopen(base+'/manifests/0.6b',timeout=30) as response:
    raw=response.read()
manifest=json.loads(raw)
if hashlib.sha256(raw).hexdigest()!='7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435':
    raise ValueError('Ollama manifest changed; review before updating the pinned model')
weights=[x for x in manifest['layers'] if x['mediaType']=='application/vnd.ollama.image.model']
assert len(weights)==1 and weights[0]['digest']=='sha256:7f4030143c1c477224c5434f8272c662a8b042079a0a584f0a27a1684fe2e1fa'
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
destination=root/'manifests/registry.ollama.ai/library/qwen3/0.6b'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_bytes(raw)
destination.chmod(0o444)
print(json.dumps({'model':'qwen3:0.6b','weights_sha256':weights[0]['digest'],
                  'weights_bytes':weights[0]['size'],'manifest_sha256':hashlib.sha256(raw).hexdigest()}),flush=True)
