import json
from os import environ as env

import requests
from dotenv import load_dotenv, find_dotenv
from flask import Flask, jsonify, redirect, render_template, session, url_for, request, Response
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from functools import wraps
from werkzeug.routing import PathConverter
import docker
import time

load_dotenv(find_dotenv())

app = Flask(__name__, static_url_path="/notstatic")
app.secret_key = env["SESSION_KEY"]
# port = env["PORT"]

oauth = OAuth(app)

auth0 = oauth.register(
    "auth0",
    client_id=env["CLIENT_ID"],
    client_secret=env["CLIENT_SECRET"],
    api_base_url=env["AUTH0_BASE"],
    access_token_url=f"{env['AUTH0_BASE']}/oauth/token",
    authorize_url=f"{env['AUTH0_BASE']}/authorize",
    client_kwargs={
        "scope": "openid profile email read:roles"
    }
)

client = docker.from_env()


@app.route("/callback")
def callback_handling():
    req = request
    auth0.authorize_access_token()
    resp = auth0.get("userinfo")
    userinfo = resp.json()

    session["jwt_payload"] = userinfo
    session["profile"] = {
        "user_id": userinfo["sub"],
        "name": userinfo["name"],
        "picture": userinfo["picture"]
    }

    return redirect("/home")


@app.route("/login")
def login():
    return auth0.authorize_redirect(redirect_uri=url_for("callback_handling", _external=True))
    # return auth0.authorize_redirect(redirect_uri=f"http://localhost:{ port }/callback")


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "profile" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


@app.route("/notloggedin")
def not_logged_in():
    return render_template("notLoggedIn.html")


@app.route("/home")
@requires_auth
def home():
    return render_template("home.html")


@app.route("/logout")
def logout():
    session.clear()
    params = {"returnTo": url_for(
        'not_logged_in', _external=True), 'client_id': env["CLIENT_ID"]}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@app.route("/<path:subpath>")
@app.route("/devenv", defaults={"subpath": None})
@requires_auth
def devenv(subpath):
    container_name = session["profile"]["user_id"].replace("|", "_")
    try:
        client.containers.get(container_name)
    except docker.errors.NotFound:
        client.containers.run("codercom/code-server:latest", "--auth none", detach=True, name=container_name, ports={8080:8080}, network="my_network")
        time.sleep(5)
    
    if subpath is not None:
        resp = requests.get(f"http://{container_name}:8080/{subpath}")
    else:
        resp = requests.get(f"http://{container_name}:8080")
    headers = [(name, value) for (name, value) in resp.raw.headers.items()]
    response = Response(resp.content, resp.status_code, headers)
    return response
    return redirect("http://localhost:8080")


# @app.route("/<path:subpath>")
# def wot(subpath):
#     print(subpath)
#     return jsonify({})