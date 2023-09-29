# Copyright 2023 iiPython

# Modules
import os
import logging
from typing import List
from pathlib import Path
from hashlib import sha256
from json import dumps, loads

from blacksheep import (
    json, redirect, bad_request, unauthorized,
    Application, Request, Response
)
from blacksheep.server.templating import use_templates
from jinja2 import FileSystemLoader

# Initialization
base_dir = Path(__file__).parent
logging.basicConfig(
    format = "[%(levelname)s] %(message)s",
    level = logging.INFO
)

app = Application()
app.use_sessions(os.urandom(128))
app.serve_files(base_dir / "static", root_path = "static")

view = use_templates(app, loader = FileSystemLoader(base_dir / "templates"))

# Handle access token
access_token = os.environ.get("ACCESS_TOKEN", "").strip()
if not access_token:
    logging.warn("No access token present! It it highly recommended that you add one.")
    access_token = None

# Setup data recording
data_path = base_dir / "data"
tokens_file = data_path / "tokens.json"
os.makedirs(data_path, exist_ok = True)

def get_tokens() -> List[str]:
    if not tokens_file.is_file():
        return []

    with open(tokens_file, "r") as fh:
        return loads(fh.read())

def add_token(token: str) -> None:
    tokens = get_tokens()
    tokens.append(token)
    with open(tokens_file, "w+") as fh:
        fh.write(dumps(tokens))

@app.route("/api/upload", methods = ["POST"])
async def api_upload(request: Request) -> Response:
    data = await request.json()
    if data.get("token") not in get_tokens():
        return unauthorized("Invalid client token.")

    path, logs = data_path / (data["hostname"] + ".json"), []
    del data["hostname"], data["token"]
    if path.is_file():
        with open(path, "r") as fh:
            logs = loads(fh.read())

    logs.append(data)
    with open(path, "w+") as fh:
        fh.write(dumps(logs[-144:]))

    return json({"success": True})

@app.route("/api/logs", methods = ["GET"])
async def api_logs(request: Request) -> Response:
    if "logged_in" not in request.session:
        return json({"success": False, "error": "You are not logged in."})

    log_data = {}
    for file in os.listdir(data_path):
        if file == "tokens.json":
            continue

        with open(data_path / file, "r") as fh:
            log_data[file.removesuffix(".json")] = loads(fh.read())

    return json(log_data)

# Public routing
@app.route("/", methods = ["GET"])
async def route_index(request: Request) -> Response:
    if "logged_in" in request.session:
        return redirect("/dashboard")

    return redirect("/login")

@app.route("/logout", methods = ["GET"])
async def route_logout(request: Request) -> Response:
    if "logged_in" in request.session:
        del request.session["logged_in"]

    return redirect("/login")

@app.route("/login", methods = ["GET", "POST"])
async def route_login(request: Request) -> Response:
    if access_token is None:
        request.session["logged_in"] = True
        return redirect("/dashboard")

    elif "logged_in" in request.session:
        return redirect("/dashboard")

    # Handle posting
    elif request.method == "POST":
        data = await request.form()
        if "token" not in data:
            return bad_request("Missing token!")

        elif sha256(data["token"].encode()).hexdigest() != access_token:
            return unauthorized("Invalid token!")

        request.session["logged_in"] = True
        return redirect("/dashboard")

    return view("login", {})

@app.route("/dashboard", methods = ["GET"])
async def route_dashboard(request: Request) -> Response:
    if "logged_in" not in request.session:
        return redirect("/login")

    return view("dashboard", {})

