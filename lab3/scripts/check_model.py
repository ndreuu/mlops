import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:18086')
parser.add_argument('--health-url',default='http://127.0.0.1:18087/health')
parser.add_argument('--output',type=Path,default=Path('reports/cpu.json'))
args=parser.parse_args()
base=['kubectl','--context=itmo-student-13','-n','itmo-student-13']
report={}
with httpx.Client(timeout=80) as client:
 response=client.get(args.health_url);response.raise_for_status();report['health']=response.json()
 payload={'model':'qwen2.5:0.5b','messages':[{'role':'user','content':'Ответь одним словом по-русски. Какого цвета снег?'}],
          'stream':False,'keep_alive':-1,'options':{'num_gpu':0,'num_thread':1,'num_ctx':2048,'num_predict':48,'temperature':0}}
 report['idle_metrics']=subprocess.check_output(base+['top','pods','-l','app=oleinikov-lab3-ollama'],text=True)
 started=time.monotonic()
 response=client.post(args.base_url+'/api/chat',json=payload);response.raise_for_status();value=response.json()
 report.update(request=payload,answer=value['message']['content'],seconds=round(time.monotonic()-started,2),
               model_metrics={k:value[k] for k in ('prompt_eval_count','eval_count','total_duration','load_duration')})
 response=client.get(args.base_url+'/api/ps');response.raise_for_status()
 report['loaded_models']=[{k:m[k] for k in ('name','size','size_vram','context_length','details')} for m in response.json()['models']]
 assert report['answer'].strip() and report['loaded_models'] and all(m['size_vram']==0 for m in report['loaded_models'])
code="import hashlib,json,pathlib; p=pathlib.Path('/tmp/ollama-models/blobs/sha256-c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515'); print(json.dumps({'weights_sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),'weights_bytes':p.stat().st_size,'memory_peak_bytes':int(pathlib.Path('/sys/fs/cgroup/memory.peak').read_text()),'memory_current_bytes':int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())}))"
report.update(json.loads(subprocess.check_output(base+['exec','deployment/oleinikov-lab3-ollama','--','python','-c',code],text=True)))
assert report['weights_sha256']=='c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515'
report['passed']=True
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
