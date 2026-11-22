import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlparse

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:18084/mcp')
parser.add_argument('--from-kubernetes',action='store_true')
parser.add_argument('--output',type=Path,default=Path('reports/mcp.json'))
args=parser.parse_args()
if urlparse(args.url).hostname not in ('localhost','127.0.0.1','oleinikov-lab3-kb-mcp'):
    raise SystemExit('MCP token is restricted to the local tunnel / assigned service')
if args.from_kubernetes:
    result=subprocess.run(['kubectl','--context=itmo-student-13','-n','itmo-student-13',
        'get','secret','oleinikov-lab3-mcp','-o','jsonpath={.data.MCP_TOKEN}'],capture_output=True,check=True)
    token=base64.b64decode(result.stdout).decode()
else:
    token=os.environ['MCP_TOKEN']


async def main():
    report={}
    async with httpx.AsyncClient(headers={'Authorization':'Bearer '+token},timeout=5) as client:
        async with streamable_http_client(args.url,http_client=client) as (reader,writer,_):
            async with ClientSession(reader,writer) as session:
                initialized=await session.initialize()
                report['protocol_version']=initialized.protocolVersion
                tools=await session.list_tools()
                report['tools']=[{'name':t.name,'inputSchema':t.inputSchema,'outputSchema':t.outputSchema} for t in tools.tools]
                assert {t.name for t in tools.tools}=={'search_docs','get_doc','list_sections'}
                tree=await session.call_tool('list_sections',{})
                assert not tree.isError
                report.update(tree.structuredContent['counts'])
                report['generation']=tree.structuredContent['generation']
                result=await session.call_tool('search_docs',{'query':'Сколько активных подписчиков помещается в закрытый канал?','limit':5})
                assert not result.isError
                report['top5']=[c['id']+'@'+c['version'] for c in result.structuredContent['cards']]
                assert 'M-05@2.0' in report['top5'] and 'M-05@1.1' not in report['top5']
                report['versions']=[]
                for version in ('1.1','2.0'):
                    result=await session.call_tool('get_doc',{'doc_id':'M-05','version':version})
                    assert not result.isError
                    doc=result.structuredContent['document']
                    report['versions'].append({k:doc[k] for k in ('id','version','status','url')})
                bad=await session.call_tool('get_doc',{'doc_id':'M-05','version':'9.9'})
                report['missing_version_is_error']=bad.isError
                assert bad.isError
    async with httpx.AsyncClient(timeout=5) as client:
        response=await client.post(args.url,json={})
        report['without_token_status']=response.status_code
        assert response.status_code==401
        response=await client.post(args.url,json={},headers={'Authorization':'Bearer '+token,'Origin':'https://not-allowed.invalid'})
        report['forbidden_origin_status']=response.status_code
        assert response.status_code==403
    report['passed']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='tools'},ensure_ascii=False,indent=2))
    print('tools/list:',', '.join(t['name'] for t in report['tools']))


asyncio.run(main())
