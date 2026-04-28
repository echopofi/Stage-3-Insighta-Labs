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

@app.get("/")
def home(request: Request):
    return {"status": "ok", "message": "Insighta Labs+ Web Portal"}

@app.get("/test")
def test(request: Request):
    return {"status": "success"}