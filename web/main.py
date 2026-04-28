import os
import json
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except:
    pass

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="Insighta Labs+ Portal", version="2.0.0")

try:
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
except Exception as e:
    templates = None
    print(f"Templates error: {e}")

ACCESS_TOKEN_EXPIRE_MINUTES = 15
CSRF_TOKEN_COOKIE = "csrf_token"
SESSION_COOKIE = "session"

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "Ov23liplaceholderclientid")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "placeholderclientsecret")
GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI", "http://localhost:3000/github/callback")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@app.get("/")
def home(request: Request):
    try:
        if templates:
            return templates.TemplateResponse("index.html", {"request": request, "user": None})
    except Exception as e:
        return {"status": "error", "message": str(e), "templates_loaded": True}
    return {"status": "ok", "message": "Home"}


@app.get("/test")
def test(request: Request):
    return {
        "status": "success",
        "templates_loaded": templates is not None,
        "templates_dir": str(BASE_DIR / "templates") if templates else None,
        "backend": BACKEND_URL
    }