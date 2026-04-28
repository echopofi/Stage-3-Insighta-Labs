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

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

@app.get("/")
def home(request: Request):
    return {"status": "ok", "message": "Insighta Labs+ Web Portal"}

@app.get("/test")
def test(request: Request):
    return {"status": "success", "client_id": GITHUB_CLIENT_ID[:10] if GITHUB_CLIENT_ID else "not set"}