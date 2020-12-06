import asyncio
import json
from os import environ as env
from types import ClassMethodDescriptorType

from aiohttp import client, web, ClientSession, WSMsgType
import aiohttp_jinja2
from dotenv import find_dotenv, load_dotenv
import jinja2

import if_debug
from code_server_manager import CodeServerManager

load_dotenv(find_dotenv())
if_debug.attach_debugger_if_dev()
code_server_manager = CodeServerManager()

@aiohttp_jinja2.template("home.html")
async def does_work(req: web.Request) -> web.Response:
    return {}


async def proxy_handler(req: web.Request) -> web.Response:
    await code_server_manager.find_or_create_container(f"github_percyodi")
    
    reqH = req.headers.copy()
    base_url = "http://github_percyodi:8080"
    # Do web socket Stuff
    if reqH["connection"] == "Upgrade" and reqH["upgrade"] == "websocket" and req.method == "GET":
        ws_server = web.WebSocketResponse()
        await ws_server.prepare(req)
        print(f'##### WS_SERVER {ws_server}')

        client_session = ClientSession(cookies=req.cookies)

        path_qs_cleaned = req.path_qs.removeprefix("/devenv")
        async with client_session.ws_connect(base_url+path_qs_cleaned) as ws_client:
            print(f'##### WS_CLIENT {ws_client}')

            async def wsforward(ws_from,ws_to):
                async for msg in ws_from:
                    print(f'>>> msg: {msg}')
                    mt = msg.type
                    md = msg.data
                    if mt == WSMsgType.TEXT:
                        await ws_to.send_str(md)
                    elif mt == WSMsgType.BINARY:
                        await ws_to.send_bytes(md)
                    elif mt == WSMsgType.PING:
                        await ws_to.ping()
                    elif mt == WSMsgType.PONG:
                        await ws_to.pong()
                    elif ws_to.closed:
                        await ws_to.close(code=ws_to.close_code,message=msg.extra)
                    else:
                        raise ValueError(f'unexpected message type: {msg}')

            finished,unfinished = await asyncio.wait([wsforward(ws_server,ws_client),wsforward(ws_client,ws_server)],return_when=asyncio.FIRST_COMPLETED)

            return ws_server
    else: # Do http proxy
        # proxyPath = req.match_info.get("proxyPath", "")
        proxyPath = req.path_qs
        if proxyPath != "":
            proxyPath = proxyPath.removeprefix("/devenv").removeprefix("devenv").removeprefix("/")
            proxyPath = "/" + proxyPath
        async with client.request(
            req.method,
            base_url + proxyPath,
            allow_redirects=False,
            data = await req.read()
        ) as res:
            headers = res.headers.copy()
            headers["service-worker-allowed"] = "/"
            body = await res.read()
            return web.Response(
                headers=headers,
                status = res.status,
                body = body
            )

app = web.Application()
app.add_routes([web.get("/", does_work)])
app.add_routes([web.get(r'/devenv', proxy_handler)])
app.add_routes([web.get(r'/{proxyPath:.*}', proxy_handler)])
# app.add_routes([web.get(r'/{proxyPath:.*}', proxy_handler)])

aiohttp_jinja2.setup(app,loader=jinja2.FileSystemLoader("./templates") )



web.run_app(app, port=5000)