from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import urllib.request

# Ollama migrates catalog metadata on first start. The immutable blobs stay in
# the image in small layers; startup reconstructs them on an ephemeral disk volume.
catalog=Path('/tmp/ollama-models')
catalog.mkdir(exist_ok=True)
shutil.copytree('/models/blobs',catalog/'blobs',dirs_exist_ok=True)
weight_hash='c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515'
weight_path=catalog/'blobs'/('sha256-'+weight_hash)
if not weight_path.exists() or hashlib.file_digest(weight_path.open('rb'),'sha256').hexdigest()!=weight_hash:
    weight_path.unlink(missing_ok=True)
    checksum=hashlib.sha256()
    with weight_path.open('wb') as output:
        for part in sorted(Path('/model-parts').glob('part*')):
            with part.open('rb') as source:
                while block:=source.read(1024*1024):
                    checksum.update(block)
                    output.write(block)
    if checksum.hexdigest()!=weight_hash:
        raise ValueError('Packaged weights checksum mismatch')
    weight_path.chmod(0o444)
shutil.copytree('/models/manifests',catalog/'manifests',dirs_exist_ok=True)
os.environ['OLLAMA_MODELS']=str(catalog)
process=subprocess.Popen(['/usr/bin/ollama','serve'])
ready=False


def warmup():
    global ready
    payload=json.dumps({'model':'qwen2.5:0.5b','prompt':'','stream':False,'keep_alive':-1,
                       'options':{'num_gpu':0,'num_ctx':2048,'num_thread':1}}).encode()
    while process.poll() is None:
        try:
            request=urllib.request.Request('http://127.0.0.1:11434/api/generate',data=payload,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=90) as response:
                result=json.load(response)
            if result.get('done'):
                ready=True
                return
        except (OSError,ValueError):
            time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/health','/livez'):
            self.send_error(404)
            return
        healthy=process.poll() is None and (ready or self.path=='/livez')
        body=json.dumps({'status':'ready' if healthy else 'loading','model':'qwen2.5:0.5b','compute':'cpu'}).encode()
        self.send_response(200 if healthy else 503)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self,*args):
        pass


threading.Thread(target=warmup,daemon=True).start()
ThreadingHTTPServer(('0.0.0.0',11435),Handler).serve_forever()
