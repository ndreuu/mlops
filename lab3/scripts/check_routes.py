"""Acceptance checks against real CPU inference plus explicitly synthetic cloud."""
import argparse
import asyncio
import json
from pathlib import Path
import time

import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:18083')
parser.add_argument('--mock-url',default='http://127.0.0.1:18085')
parser.add_argument('--corpus',type=Path,required=True)
parser.add_argument('--output',type=Path,default=Path('reports/routes.json'))
args=parser.parse_args()
question='Сколько активных подписчиков помещается в закрытый канал сейчас? Влияют ли непринятые приглашения?'
report={'cloud_real_verified':False,'cloud_provider':'synthetic-cloud-mock','local_provider':'real Ollama CPU','cases':[]}


def save(name,value,passed,**extra):
    row={'case':name,**{k:value[k] for k in ('route','reason','provider','calls','context_id','timings_ms') if k in value},'passed':bool(passed),**extra}
    report['cases'].append(row)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(row,ensure_ascii=False),flush=True)
    if not passed:
        raise RuntimeError('Acceptance failed: '+name)


async def main():
    async with httpx.AsyncClient(timeout=95) as client:
        async def ask(fault='live',**extra):
            response=await client.post(args.base_url+'/api/ask',json={'query':question,'fault':fault,**extra})
            response.raise_for_status()
            return response.json()
        async def state():
            return (await client.get(args.base_url+'/api/state')).json()
        async def recover():
            retry=(await state())['circuits']['mock']['retry_in_seconds']
            if retry>0:
                await asyncio.sleep(retry+.1)
            return await ask('ok')
        async def wait_count(count):
            for _ in range(100):
                value=await state()
                if value['local_active_and_waiting']==count:
                    return value
                await asyncio.sleep(.1)
            raise RuntimeError('Local queue did not reach expected occupancy')
        value=await ask('ok')
        save('synthetic_cloud_success',value,value['route']=='cloud' and value['provider']=='cloud-mock' and value['calls']=={'mcp':1,'cloud':1,'local':0})
        # Observe open circuit while the first fallback is still generating.
        first=asyncio.create_task(ask('429'))
        for _ in range(40):
            if (await state())['circuits']['mock']['state']=='open':
                break
            await asyncio.sleep(.05)
        second=asyncio.create_task(ask('ok'))
        a,b=await asyncio.gather(first,second)
        save('429_to_cpu',a,a['route']=='local' and a['reason']=='cloud_429' and a['calls']=={'mcp':1,'cloud':1,'local':1})
        save('open_circuit_skips_cloud',b,b['route']=='local' and b['reason'].startswith('circuit_open:') and b['calls']['cloud']==0)
        recovered=await recover()
        save('cloud_recovery',recovered,recovered['route']=='cloud' and recovered['circuit']['state']=='closed')
        for fault,reason in [('quota','cloud_quota'),('503','cloud_503'),('timeout','cloud_timeout'),('invalid_citations','cloud_invalid_answer')]:
            value=await ask(fault)
            save(fault+'_to_cpu',value,value['route']=='local' and value['reason']==reason and value['calls']=={'mcp':1,'cloud':1,'local':1})
            value=await recover()
            save(fault+'_recovery',value,value['route']=='cloud' and value['circuit']['state']=='closed')
        value=await ask('both_down')
        save('both_unavailable',value,value['route']=='search_only' and bool(value['cards']) and value['calls']=={'mcp':1,'cloud':1,'local':1})
        await asyncio.sleep(1.1)  # Synthetic circuit only; real Retry-After is not shortened.
        data=json.loads(args.corpus.read_text())
        docs=[d for section in data['sections'] for sub in section['subsections'] for d in sub['documents']]
        private=next(d for d in docs if d['visibility']=='local_only')
        before=(await client.get(args.mock_url+'/stats')).json()['calls']
        for label,overrides in [('private_mode',{'private':True}),('local_only',{'query':private['id']}),('copied_private_query',{'query':private['sections'][0]['body'][0][:800]})]:
            value=await ask('ok',**overrides)
            after=(await client.get(args.mock_url+'/stats')).json()['calls']
            save(label,value,value['calls']['cloud']==0 and after==before and value['route'] in ('local','search_only'),cloud_requests_delta=after-before)
        stats=(await client.get(args.mock_url+'/stats')).json()
        save('no_private_markers_in_mock',{},not stats['private_marker_seen'],private_marker_seen=stats['private_marker_seen'])
        # One real generation, one waiting request, then overload rejection.
        a=asyncio.create_task(ask(private=True))
        await wait_count(1)
        b=asyncio.create_task(ask(private=True))
        await wait_count(2)
        value=await ask(private=True)
        save('queue_full',value,value['route']=='search_only' and 'local_queue_full' in value['reason'] and value['calls']['local']==0)
        one,two=await asyncio.gather(a,b)
        save('one_active_one_waiting',two,one['route']=='local' and two['route']=='local' and (await state())['local_active_and_waiting']==0)
        task=asyncio.create_task(ask(private=True))
        await wait_count(1)
        started=time.monotonic()
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        await wait_count(0)
        save('disconnect_releases_slot',{},True,release_seconds=round(time.monotonic()-started,3))
        value=await ask(private=True)
        save('generation_after_cancel',value,value['route']=='local' and value['calls']['local']==1)
    report['passed']=all(c['passed'] for c in report['cases'])
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


asyncio.run(main())
