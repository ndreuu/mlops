import hashlib
import json
import os
from pathlib import Path
import urllib.request

root=Path(os.getenv('MODEL_ROOT','/models'))
root.mkdir(parents=True,exist_ok=True)
base='https://registry.ollama.ai/v2/library/qwen2.5'
with urllib.request.urlopen(base+'/manifests/0.5b',timeout=30) as response:
    raw=response.read()
manifest=json.loads(raw)
if hashlib.sha256(raw).hexdigest()!='a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67':
    raise ValueError('Ollama manifest changed; review before updating the pinned model')
weights=[x for x in manifest['layers'] if x['mediaType']=='application/vnd.ollama.image.model']
assert len(weights)==1 and weights[0]['digest']=='sha256:c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515'
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
destination=root/'manifests/registry.ollama.ai/library/qwen2.5/0.5b'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_bytes(raw)
destination.chmod(0o444)
print(json.dumps({'model':'qwen2.5:0.5b','weights_sha256':weights[0]['digest'],
                  'weights_bytes':weights[0]['size'],'manifest_sha256':hashlib.sha256(raw).hexdigest()}),flush=True)
