"""Synthetic provider: no real API key, prompt or response is logged or persisted."""
import asyncio
import hashlib
import json
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app=FastAPI()
stats={'calls':0,'private_marker_seen':False,'last_context_hash':None}


@app.get('/health')
async def health():
    return {'status':'ready','provider':'synthetic-cloud-mock'}


@app.get('/stats')
async def get_stats():
    return stats


@app.post('/v1/chat/completions')
async def completion(request:Request):
    if request.headers.get('authorization')!='Bearer synthetic-key':
        return JSONResponse({'error':{'code':'invalid_key'}},status_code=401)
    body=await request.json()
    messages=body.get('messages',[])
    text=json.dumps(messages,ensure_ascii=False)
    stats['calls']+=1
    stats['private_marker_seen'] |= bool(re.search(r'\b[A-Z]+-CANARY-[\w-]+',text,re.I))
    stats['last_context_hash']=hashlib.sha256(text.encode()).hexdigest()
    fault=request.headers.get('x-test-scenario','ok')
    if fault in ('429','quota','503','both_down'):
        return JSONResponse({'error':{'code':'insufficient_quota' if fault=='quota' else 'rate_limit' if fault=='429' else 'unavailable'}},
                            status_code=429 if fault in ('429','quota') else 503,headers={'Retry-After':'1'})
    if fault=='timeout':
        await asyncio.sleep(10)
    if fault=='invalid_citations':
        answer='Непроверенный ответ [999].'
    else:
        user=messages[-1]['content']
        match=re.search(r'\[1\][^\n]*\n([^\n]+)',user)
        answer=(match.group(1).split('. ')[0]+'. [1]') if match else 'Нет подтверждений. [1]'
    return {'model':'synthetic-cloud-mock','choices':[{'message':{'role':'assistant','content':answer}}]}
