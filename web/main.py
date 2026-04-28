import os
import json
import secrets
from pathlib import Path
import hashlib
import base64

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except:
    pass

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Insighta Labs+ Portal", version="2.0.0")
templates = Jinja2Templates(directory="templates")

CSRF_TOKEN_COOKIE = "csrf_token"
SESSION_COOKIE = "session"

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get_user(request: Request):
    user = None
    session = request.cookies.get(SESSION_COOKIE)
    if session:
        try:
            payload = json.loads(base64.b64decode(session.split('.')[1] + '==').decode())
            user = {"username": payload.get("login"), "role": payload.get("role")}
        except:
            pass
    return user


@app.get("/")
def home(request: Request):
    user = get_user(request)
    return templates.TemplateResponse(request, "index.html", {"request": request, "user": user})


@app.get("/login")
def login_page(request: Request):
    csrf_token = secrets.token_urlsafe(32)
    response = templates.TemplateResponse(request, "login.html", {"request": request, "csrf_token": csrf_token})
    response.set_cookie(key=CSRF_TOKEN_COOKIE, value=csrf_token, httponly=True, max_age=600)
    return response


@app.get("/github/login")
def github_login(request: Request):
    if not GITHUB_CLIENT_ID:
        return RedirectResponse(url="/")
    
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    
    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={GITHUB_CALLBACK_URI}&"
        f"scope=read:user%20user:email&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )
    
    return RedirectResponse(url=github_auth_url)