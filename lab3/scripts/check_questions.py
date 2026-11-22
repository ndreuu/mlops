import argparse
import json
from pathlib import Path
import re
import time

import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:18083')
parser.add_argument('--output',type=Path,default=Path('reports/questions.json'))
parser.add_argument('--search-only',action='store_true')
args=parser.parse_args()
cases=json.loads((Path(__file__).resolve().parents[1]/'checks/questions.json').read_text())
report={'cloud_real_verified':False,'mode':'search' if args.search_only else 'ordinary_local_fallback','cases':[]}
with httpx.Client(timeout=95) as client:
    for case in cases:
        payload={'query':case['query'],**{k:case[k] for k in ('path','statuses') if k in case}}
        start=time.monotonic()
        response=client.post(args.base_url+('/api/search' if args.search_only else '/api/ask'),json=payload)
        response.raise_for_status()
        value=response.json()
        if any(c['visibility']!='cloud_ok' for c in value['cards']):
            raise SystemExit('Private response must not be written into a public report')
        found=[c['id']+'@'+c['version'] for c in value['cards']]
        retrieved=all(x in found for x in case.get('expected',[])) and (not case.get('expected_any') or any(x in found for x in case['expected_any']))
        row={'id':case['id'],'top5':found,'retrieval_passed':retrieved,'seconds':round(time.monotonic()-start,2)}
        if not args.search_only:
            answer=re.sub(r'(?<=\d)[\s\u00a0\u202f]+(?=\d)','',value['answer'].lower().replace('ё','е'))
            row.update(route=value['route'],reason=value['reason'],answer=value['answer'],
                       fact_checks={fact:bool(re.search(fact,answer)) for fact in case['facts']},
                       sources=[{k:s[k] for k in ('number','doc_id','version','anchor','url','status')} for s in value['sources']],
                       calls=value['calls'],prompt_tokens=value['prompt_tokens'],model_metrics=value['model_metrics'])
            row['answer_passed']=all(row['fact_checks'].values())
            row['generated_answer_passed']=row['answer_passed'] and value['route'] in ('local','cloud')
        report['cases'].append(row)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:row[k] for k in ('id','retrieval_passed','route','answer_passed','generated_answer_passed','seconds') if k in row},ensure_ascii=False),flush=True)
report['retrieval_passed']=sum(r['retrieval_passed'] for r in report['cases'])
if not args.search_only:
    report['answers_passed']=sum(r['answer_passed'] for r in report['cases'])
    report['generated_answers_passed']=sum(r['generated_answer_passed'] for r in report['cases'])
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Retrieval:',report['retrieval_passed'],'/',len(cases),flush=True)
if not args.search_only:
    print('Generated answers:',report['generated_answers_passed'],'/',len(cases),flush=True)
