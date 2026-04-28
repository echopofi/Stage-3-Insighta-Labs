import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except:
    pass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "Ov23liplaceholderclientid")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "placeholderclientsecret")
GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI", "http://localhost:3000/github/callback")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

@app.get("/")
def home(request: Request):
    return {"status": "ok", "message": "Insighta Labs+ Web Portal"}

@app.get("/test")
def test(request: Request):
    return {
        "status": "success", 
        "client_id_set": bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_ID != "Ov23liplaceholderclientid"),
        "callback": GITHUB_CALLBACK_URI,
        "backend": BACKEND_URL
    }