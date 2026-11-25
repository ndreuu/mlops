import hmac
import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
import uvicorn

from app.kb import KnowledgeBase

kb = KnowledgeBase()
token = os.environ['MCP_TOKEN']
if len(token) < 24:
    raise ValueError('MCP_TOKEN must contain at least 24 characters')
allowed_origins = os.getenv('MCP_ALLOWED_ORIGINS', 'http://localhost:18083,http://127.0.0.1:18083').split(',')
server = FastMCP('line-knowledge-base', host='0.0.0.0', port=8000, stateless_http=True, json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
        allowed_hosts=['127.0.0.1:*','localhost:*','oleinikov-lab3-kb-mcp:*','oleinikov-lab3-kb-mcp.itmo-student-13.svc:*'],
        allowed_origins=allowed_origins))


@server.tool()
def list_sections() -> dict[str, Any]:
    """Get the section/subsection tree, exact document versions and index generation."""
    return kb.list_sections()


@server.tool()
def search_docs(query: str, limit: int = 5, path: list[str] | None = None,
                statuses: list[str] | None = None, version: str | None = None) -> dict[str, Any]:
    """Search sections after path/status/version filtering; return unique document cards."""
    return kb.search_docs(query, limit, path, statuses, version)


@server.tool()
def get_doc(doc_id: str, version: str) -> dict[str, Any]:
    """Read one exact document version, including original sections and links."""
    return kb.get_doc(doc_id, version)


@server.custom_route('/health', methods=['GET'])
async def health(request):
    return JSONResponse({'status':'ready','generation':kb.generation, **kb.counts})


class Authenticate:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'] != '/health':
            headers = dict(scope['headers'])
            supplied = headers.get(b'authorization', b'')
            if not hmac.compare_digest(supplied, ('Bearer ' + token).encode()):
                await JSONResponse({'error':'MCP authentication required'}, status_code=401)(scope, receive, send)
                return
            origin = headers.get(b'origin', b'').decode(errors='replace')
            if origin and origin not in allowed_origins:
                await JSONResponse({'error':'Origin not allowed'}, status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


app = Authenticate(server.streamable_http_app())
if __name__ == '__main__':
    logging.getLogger('mcp').setLevel(logging.WARNING)
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT','8000')), access_log=False, log_level='warning')
