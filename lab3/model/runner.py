from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import tempfile
import time
import urllib.request

# Ollama migrates catalog metadata on first start. The immutable blobs stay in
# the image; only the small writable catalog and generated server key use tmpfs.
catalog=Path(tempfile.mkdtemp(prefix='ollama-models-',dir='/tmp'))
(catalog/'blobs').symlink_to('/models/blobs',target_is_directory=True)
shutil.copytree('/models/manifests',catalog/'manifests',dirs_exist_ok=True)
os.environ['OLLAMA_MODELS']=str(catalog)
process=subprocess.Popen(['/usr/bin/ollama','serve'])
ready=False


def warmup():
    global ready
    payload=json.dumps({'model':'deepseek-r1:1.5b','prompt':'','stream':False,'keep_alive':-1,
                       'options':{'num_gpu':0,'num_ctx':2048,'num_thread':2}}).encode()
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
        body=json.dumps({'status':'ready' if healthy else 'loading','model':'deepseek-r1:1.5b','compute':'cpu'}).encode()
        self.send_response(200 if healthy else 503)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self,*args):
        pass


threading.Thread(target=warmup,daemon=True).start()
ThreadingHTTPServer(('0.0.0.0',11435),Handler).serve_forever()
