import argparse
import json
from pathlib import Path
import re
import secrets
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument('--app-image',required=True)
parser.add_argument('--model-image',required=True)
parser.add_argument('--corpus',type=Path,required=True)
parser.add_argument('--cloud-key-file',type=Path)
args=parser.parse_args()
for image in (args.app_image,args.model_image):
    if not re.fullmatch(r'docker\.io/ndreuu/oleinikov-iris@sha256:[0-9a-f]{64}',image):
        raise SystemExit('Use a verified immutable digest from the existing repository')
base=['kubectl','--context=itmo-student-13','-n','itmo-student-13']


def apply(value):
    result=subprocess.run(base+['apply','--server-side','--field-manager=oleinikov-lab3','-f','-'],
        input=value if isinstance(value,str) else json.dumps(value),text=True,capture_output=True)
    if result.returncode:
        # Do not echo kubectl diagnostics that might include submitted Secret/ConfigMap data.
        raise SystemExit('Kubernetes apply failed; resource content suppressed')
    print(result.stdout,end='')


existing=subprocess.run(base+['get','secret','oleinikov-lab3-mcp','-o','name'],text=True,capture_output=True)
if existing.returncode:
    apply({'apiVersion':'v1','kind':'Secret','metadata':{'name':'oleinikov-lab3-mcp'},
           'type':'Opaque','stringData':{'MCP_TOKEN':secrets.token_urlsafe(40)}})
if args.cloud_key_file:
    key=args.cloud_key_file.read_text().strip()
    if not key or '\n' in key:
        raise SystemExit('Expected one API key in the file')
    apply({'apiVersion':'v1','kind':'Secret','metadata':{'name':'oleinikov-lab3-llm7'},
           'type':'Opaque','stringData':{'LLM7_API_KEY':key}})
corpus=args.corpus.read_text()
json.loads(corpus)
apply({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'oleinikov-lab3-corpus'},'data':{'kb.json':corpus}})
root=Path(__file__).resolve().parents[1]
manifest=(root/'k8s/app.yaml').read_text().replace('${APP_IMAGE}',args.app_image).replace('${MODEL_IMAGE}',args.model_image)
apply(manifest)
if args.cloud_key_file:
    subprocess.run(base+['rollout','restart','deployment/oleinikov-lab3-portal'],check=True)
allowed=subprocess.run(base+['auth','can-i','create','networkpolicies'],capture_output=True,text=True)
if allowed.stdout.strip()=='yes':
    apply((root/'k8s/network-policy.yaml').read_text())
else:
    print('NetworkPolicy unavailable in assigned RBAC; MCP bearer authentication remains required')
for deployment in ('ollama','kb-mcp','portal','cloud-mock'):
    subprocess.run(base+['rollout','status','deployment/oleinikov-lab3-'+deployment,'--timeout=600s'],check=True)
