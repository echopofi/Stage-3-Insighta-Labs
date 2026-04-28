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

from fastapi import FastAPI, Request, Query, Form, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Insighta Labs+ Portal", version="2.0.0")
templates = Jinja2Templates(directory="templates")

ACCESS_TOKEN_EXPIRE_MINUTES = 15
CSRF_TOKEN_COOKIE = "csrf_token"
SESSION_COOKIE = "session"

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "Ov23liplaceholderclientid")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "placeholderclientsecret")
GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI", "http://localhost:3000/github/callback")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@app.get("/")
def home(request: Request):
    user = None
    session = request.cookies.get(SESSION_COOKIE)
    if session:
        try:
            payload = json.loads(base64.b64decode(session.split('.')[1] + '==').decode())
            user = {"username": payload.get("login"), "role": payload.get("role")}
        except:
            pass
    return templates.TemplateResponse(request, "index.html", {"request": request, "user": user})