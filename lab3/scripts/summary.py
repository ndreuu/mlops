import argparse
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--evidence',type=Path,default=Path('evidence'))
args=parser.parse_args()
def read(name):return json.loads((args.evidence/name).read_text())
q=read('questions.json');m=read('mcp.json');r=read('routes.json');c=read('cpu-after-restart.json');restart=read('restart.json')
print(f'CPU: {c["health"]["compute"]}, VRAM={c["loaded_models"][0]["size_vram"]}, generation={c["seconds"]}s')
print('MCP: '+', '.join(t['name'] for t in m['tools']))
print(f'Corpus: {m["records"]} records / {m["unique_ids"]} IDs / {m["sections"]} sections / {m["paths"]} paths')
print(f'MCP auth: no token={m["without_token_status"]}, bad Origin={m["forbidden_origin_status"]}')
print(f'Questions: retrieval={q["retrieval_passed"]}/9, facts={q["answers_passed"]}/9, model-selected quotes={q["model_selected_quotes_passed"]}/9, free-form outputs={q["generated_answers_passed"]}')
print(f'Routes: {sum(row["passed"] for row in r["cases"])}/{len(r["cases"])} passed (cloud mock + real CPU)')
private=[row for row in r['cases'] if row['case'] in ('private_mode','local_only','copied_private_query')]
print(f'Privacy: {len(private)} checks, cloud requests='+str(sum(row['cloud_requests_delta'] for row in private)))
print(f'Restart: new Pod={restart["pod_changed"]}, same image={restart["same_image"]}, same weights={restart["same_weights"]}')
print('Real llm7.io: NOT VERIFIED (no API key)')
