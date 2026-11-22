import asyncio
from contextlib import asynccontextmanager
from html import escape
import json
import logging
import os
from pathlib import Path
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.gateway import Gateway, MCPFailure, mcp_call

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('mcp').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app):
    app.state.gateway=Gateway()
    yield
    await app.state.gateway.http.aclose()


app=FastAPI(title='ЛираТех · Поиск по базе знаний',lifespan=lifespan)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1,max_length=1000)
    path: list[str] | None = None
    statuses: list[str] = Field(default_factory=lambda:['Действует'])
    version: str | None = None
    private: bool = False
    fault: str = 'live'

    @field_validator('query')
    @classmethod
    def nonempty(cls,value):
        if not value.strip():
            raise ValueError('Введите вопрос')
        return value.strip()

    @field_validator('statuses')
    @classmethod
    def valid_statuses(cls,value):
        if not value or not set(value)<={'Действует','Архив','Черновик'}:
            raise ValueError('Неизвестный статус')
        return value

    @field_validator('path')
    @classmethod
    def valid_path(cls,value):
        if value is not None and (len(value)>2 or not all(isinstance(v,str) and 0<len(v)<100 for v in value)):
            raise ValueError('Неверный путь')
        return value

    @field_validator('version')
    @classmethod
    def valid_version(cls,value):
        if value is not None and (len(value)>20 or not value.replace('.','').isdigit()):
            raise ValueError('Неверная версия')
        return value

    @field_validator('fault')
    @classmethod
    def valid_fault(cls,value):
        if value not in {'live','ok','429','quota','503','timeout','invalid_citations','both_down'}:
            raise ValueError('Неизвестный сценарий')
        return value

    def filters(self):
        return {key:getattr(self,key) for key in ('path','statuses','version') if getattr(self,key) is not None}


@app.get('/',response_class=HTMLResponse)
async def home():
    return (Path(__file__).parent/'static/index.html').read_text()


@app.get('/health')
async def health():
    return {'status':'ready','cloud_configured':bool(os.getenv('LLM7_API_KEY')),
            'local_model':app.state.gateway.model,'synthetic_tests':os.getenv('ENABLE_TEST_SCENARIOS')=='true'}


@app.get('/api/sections')
async def sections():
    try:
        return await mcp_call('list_sections',{})
    except (MCPFailure,TimeoutError):
        raise HTTPException(503,'База знаний временно недоступна')


@app.post('/api/search')
async def search(body:SearchRequest):
    try:
        return await mcp_call('search_docs',{'query':body.query,'limit':5,**body.filters()})
    except (MCPFailure,TimeoutError):
        raise HTTPException(503,'База знаний временно недоступна')


@app.post('/api/ask')
async def ask(body:SearchRequest,request:Request):
    if body.fault!='live' and os.getenv('ENABLE_TEST_SCENARIOS')!='true':
        raise HTTPException(403,'Имитатор выключен')
    request_id=str(uuid.uuid4())
    task=asyncio.create_task(app.state.gateway.answer(body.query,body.filters(),body.private,body.fault))
    try:
        async with asyncio.timeout(90):
            while not task.done():
                if await request.is_disconnected():
                    task.cancel()
                    raise HTTPException(499,'Запрос отменён')
                await asyncio.sleep(.1)
            result=await task
        result['request_id']=request_id
        print(json.dumps({'event':'request','request_id':request_id,'route':result['route'],'reason':result['reason'],
                          'calls':result['calls'],'timings_ms':result['timings_ms']},ensure_ascii=False),flush=True)
        return result
    except (MCPFailure,TimeoutError):
        raise HTTPException(503,'Сервис не успел обработать запрос')
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task,return_exceptions=True)


@app.get('/docs/{doc_id}/{version}',response_class=HTMLResponse)
async def document(doc_id:str,version:str):
    try:
        response=await mcp_call('get_doc',{'doc_id':doc_id,'version':version})
        doc=response['document']
    except (MCPFailure,TimeoutError,KeyError):
        raise HTTPException(404,'Редакция документа не найдена')
    content=''.join('<section id="'+escape(s['anchor'],quote=True)+'"><h2>'+escape(s['title'])+'</h2>'+''.join('<p>'+escape(p)+'</p>' for p in s['body'])+'</section>' for s in doc['sections'])
    return '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+escape(doc['title'])+'</title><style>body{font:17px/1.65 system-ui;max-width:820px;margin:48px auto;padding:0 24px;color:#20352e}p{white-space:pre-wrap}section{scroll-margin-top:20px}a{color:#147355}</style><a href="/">← База знаний</a><h1>'+escape(doc['title'])+'</h1><p>'+escape(doc_id+'@'+version+' · '+doc['status']+' · '+' / '.join(doc['path']))+'</p>'+content+'</html>'


@app.get('/api/state')
async def state():
    gateway=app.state.gateway
    return {'circuits':{k:v.snapshot() for k,v in gateway.circuits.items()},'local_active_and_waiting':gateway.slots.count}
