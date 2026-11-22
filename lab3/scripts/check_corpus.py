import asyncio
import argparse
import tempfile
import copy
import json
import os
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--corpus',type=Path,required=True)
parser.add_argument('--tokenizer',type=Path,default=Path('assets/tokenizer.json'))
parser.add_argument('--output',type=Path,default=Path('reports/corpus.json'))
args=parser.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.kb import KnowledgeBase,validate_corpus
scratch=tempfile.TemporaryDirectory()
kb=KnowledgeBase(args.corpus,Path(scratch.name)/'kb.sqlite',args.tokenizer)
report={'generation':kb.generation,**kb.counts}
bad=copy.deepcopy(kb.data)
del bad['sections'][0]['subsections'][0]['documents'][0]['visibility']
try:
 validate_corpus(bad)
 raise RuntimeError('Missing label accepted')
except ValueError:
 report['missing_visibility_rejected']=True
max_tokens=max(kb.tokens(chunk) for d in kb.documents for section in d['sections'] for chunk in kb.chunks(' '.join(section['body'])))
report['maximum_chunk_tokens']=max_tokens
assert max_tokens<=175
injected=[d for d in kb.documents if any('CANARY-' in p for s in d['sections'] for p in s['body'])]
report['original_injection_quote_preserved']=False
report['unsafe_excerpt_excluded']=False
for doc in injected:
 raw=kb.get_doc(doc['id'],doc['version'])['document']
 assert raw==doc or raw['sections']==doc['sections']
 result=kb.search_docs(doc['id'],statuses=[doc['status']])
 snippets=[s for c in result['cards'] for s in c['snippets']]
 report['original_injection_quote_preserved']=True
 report['unsafe_excerpt_excluded']=not any('CANARY-' in s['text'] for s in snippets)
assert report['original_injection_quote_preserved'] and report['unsafe_excerpt_excluded']
for query in ['" OR 1=1 --','* : ( ) NOT NEAR',"'; DROP TABLE docs; --"]:
 kb.search_docs(query)
report['query_escaping_passed']=True
from app.gateway import valid_answer
samples=[{'number':1,'text':'Лимит канала — 7 участников. Приглашения место не занимают.'},
         {'number':2,'text':'Удержание ниже порога. Расширение отложено.'}]
assert valid_answer('«Лимит канала — 7 участников.» [1]',samples)
assert not valid_answer('[1] [2]',samples)
assert not valid_answer('Лимит канала — 8 участников. [1]',samples)
assert not valid_answer('Расширение отложено, потому что приглашения занимают место. [2]',samples)
assert not valid_answer('Лимит канала — 7 участников. [2]',samples)
assert not valid_answer('Лимит канала — 7 участников. [999]',samples)
report['grounded_quote_checks_passed']=True
from app.gateway import Circuit,retry_after
async def check_circuit():
    circuit=Circuit()
    await circuit.fail('synthetic',.001)
    await asyncio.sleep(.01)
    first,second=await asyncio.gather(circuit.acquire(),circuit.acquire())
    assert first is True and second is False
    await circuit.success()
    assert await circuit.acquire() is True
asyncio.run(check_circuit())
assert retry_after('3',60)==3 and retry_after('bad',60)==60
from datetime import datetime,timedelta,timezone
from email.utils import format_datetime
assert 8<=retry_after(format_datetime(datetime.now(timezone.utc)+timedelta(seconds=10)),60)<=10
report['half_open_one_probe_passed']=True
report['retry_after_seconds_and_date_passed']=True


report['passed']=True
out=args.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

scratch.cleanup()
