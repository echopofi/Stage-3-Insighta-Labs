import os
import json
import secrets
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
try:
    load_dotenv(BASE_DIR / ".env")
except:
    pass

from fastapi import FastAPI, Request

app = FastAPI(title="Insighta Labs+ Portal", version="2.0.0")

@app.get("/")
def home(request: Request):
    return {"status": "ok", "message": "Insighta Labs+ Web Portal"}