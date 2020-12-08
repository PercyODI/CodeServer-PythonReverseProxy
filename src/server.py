import asyncio
import base64
import json
import ssl
from os import environ as env

import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import ClientSession, WSMsgType, client, web
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from dotenv import find_dotenv, load_dotenv
from oauthlib.oauth2 import WebApplicationClient

import if_debug
from code_server_manager import CodeServerManager

load_dotenv(find_dotenv())
if_debug.attach_debugger_if_dev()
code_server_manager = CodeServerManager()

oath_client = WebApplicationClient(env["GITHUB_CLIENT_ID"])


async def login(req: web.Request) -> web.Response:
    request_uri = oath_client.prepare_request_uri(
        env["GITHUB_URL"],
        redirect_uri=str(req.url.parent) + "/callback",
        scope=["openid", "email", "profile"],
    )

    raise web.HTTPFound(request_uri)


@aiohttp_jinja2.template("home.html")
async def callback(req: web.Request) -> web.Response:
    code = req.query["code"]
    token_url, headers, body = oath_client.prepare_token_request(
        env["GITHUB_ACCESS_TOKEN"],
        # authorization_response=str(req.url),
        # redirect_url=str(req.url.parent),
        code=code,
    )
    headers["Accept"] = "application/json"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            token_url,
            headers=headers,
            data=body,
            params=[
                ("client_id", env["GITHUB_CLIENT_ID"]),
                ("client_secret", env["GITHUB_CLIENT_SECRET"]),
                ("code", code),
            ]
            # auth=(env["GITHUB_CLIENT_ID"], env["GITHUB_CLIENT_SECRET"])
        ) as token_response:
            data = await token_response.read()
            print(data)
            tokens = oath_client.parse_request_body_response(data)
            print(tokens)
            new_headers = {"Authorization": "token " +
                           tokens.get("access_token")}
            async with session.get(
                "https://api.github.com/user", headers=new_headers
            ) as user_response:
                user_data_str = await user_response.read()
                user_data = json.loads(user_data_str)
                print(user_data)
                session = await get_session(req)
                session["container_name"] = (
                    user_data["login"] + "_" + str(user_data["id"])
                )
                return {"is_logged_in": True}


@aiohttp_jinja2.template("home.html")
async def logout(req: web.Request) -> web.Response:
    session = await get_session(req)
    session.invalidate()
    return {"is_logged_in": False}


@aiohttp_jinja2.template("home.html")
async def does_work(req: web.Request) -> web.Response:
    sess = await get_session(req)
    return {"is_logged_in": "container_name" in sess.keys()}


async def proxy_handler(req: web.Request) -> web.Response:
    sess = await get_session(req)
    if "container_name" not in sess.keys():
        raise web.HTTPFound("/login")
    else:
        container_name = sess["container_name"]
    await code_server_manager.find_or_create_container(container_name)
    reqH = req.headers.copy()
    base_url = f"http://{container_name}:8080"
    # Do web socket Stuff
    if (
        reqH["connection"] == "Upgrade"
        and reqH["upgrade"] == "websocket"
        and req.method == "GET"
    ):
        ws_server = web.WebSocketResponse()
        await ws_server.prepare(req)
        print(f"##### WS_SERVER {ws_server}")

        client_session = ClientSession(cookies=req.cookies)

        path_qs_cleaned = req.path_qs.removeprefix("/devenv")
        async with client_session.ws_connect(base_url + path_qs_cleaned) as ws_client:
            print(f"##### WS_CLIENT {ws_client}")

            async def wsforward(ws_from, ws_to):
                async for msg in ws_from:
                    print(f">>> msg: {msg}")
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
                        await ws_to.close(code=ws_to.close_code, message=msg.extra)
                    else:
                        raise ValueError(f"unexpected message type: {msg}")

            finished, unfinished = await asyncio.wait(
                [wsforward(ws_server, ws_client),
                 wsforward(ws_client, ws_server)],
                return_when=asyncio.FIRST_COMPLETED,
            )

            return ws_server
    else:  # Do http proxy
        # proxyPath = req.match_info.get("proxyPath", "")
        proxyPath = req.path_qs
        if proxyPath != "":
            proxyPath = (
                proxyPath.removeprefix("/devenv")
                .removeprefix("devenv")
                .removeprefix("/")
            )
            proxyPath = "/" + proxyPath
        async with client.request(
            req.method,
            base_url + proxyPath,
            allow_redirects=False,
            data=await req.read(),
        ) as res:
            headers = res.headers.copy()
            headers["service-worker-allowed"] = "/"
            body = await res.read()
            return web.Response(headers=headers, status=res.status, body=body)


app = web.Application()

# Set up sessions
secret_key = base64.urlsafe_b64decode(env["FERNET_KEY"])
setup(app, EncryptedCookieStorage(secret_key))

# Set up routes
app.add_routes([web.get("/", does_work)])
app.add_routes([web.get("/login", login)])
app.add_routes([web.get("/callback", callback)])
app.add_routes([web.get("/logout", logout)])
app.add_routes([web.get(r"/devenv", proxy_handler)])
app.add_routes([web.get(r"/{proxyPath:.*}", proxy_handler)])
# app.add_routes([web.get(r'/{proxyPath:.*}', proxy_handler)])

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("./templates"))

if "SSL_CRT_FILE" in env.keys() and "SSL_KEY_FILE" in env.keys():
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(env["SSL_CRT_FILE"], env["SSL_KEY_FILE"])
    web.run_app(app, port=5000, ssl_context=ssl_context)
else:
    web.run_app(app, port=5000)
