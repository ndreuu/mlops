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
report['passed']=True
out=args.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

scratch.cleanup()
