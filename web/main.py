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

from fastapi import FastAPI, Request, Query, Form, Cookie
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Insighta Labs+ Portal", version="2.0.0")
templates = Jinja2Templates(directory="templates")

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
CSRF_TOKEN_COOKIE = "csrf_token"
SESSION_COOKIE = "session"

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "Ov23liplaceholderclientid")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "placeholderclientsecret")
GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI", "http://localhost:3000/github/callback")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "user": None})


@app.get("/login")
def login_page(request: Request):
    csrf_token = secrets.token_urlsafe(32)
    response = templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})
    response.set_cookie(key=CSRF_TOKEN_COOKIE, value=csrf_token, httponly=True, max_age=600)
    return response


@app.get("/github/login")
def github_login(request: Request):
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    
    import hashlib
    import base64
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


@app.get("/github/callback")
def github_callback(request: Request, code: str = Query(...), state: str = Query(...)):
    import httpx
    
    token_url = "https://github.com/login/oauth/access_token"
    token_data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_CALLBACK_URI
    }
    
    try:
        response = httpx.post(token_url, json=token_data, timeout=10)
        if response.status_code == 200:
            token_response = response.json()
            access_token = token_response.get("access_token")
            
            if access_token:
                user_response = httpx.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if user_response.status_code == 200:
                    github_user = user_response.json()
                    
                    session_payload = {
                        "sub": github_user.get("id"),
                        "login": github_user.get("login"),
                        "role": "analyst"
                    }
                    import base64
                    session_b64 = base64.b64encode(json.dumps(session_payload).encode()).decode()
                    session_token = f"eyJ.{session_b64}."
                    
                    response = RedirectResponse(url="/dashboard")
                    response.set_cookie(key=SESSION_COOKIE, value=session_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60)
                    return response
    
    except Exception as e:
        pass
    
    return RedirectResponse(url="/login")


@app.get("/logout")
def logout(request: Request):
    response = RedirectResponse(url="/")
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_TOKEN_COOKIE)
    return response


@app.get("/dashboard")
def dashboard(request: Request):
    session = request.cookies.get(SESSION_COOKIE)
    user = None
    
    if session:
        try:
            import base64
            payload = json.loads(base64.b64decode(session.split('.')[1] + '==').decode())
            user = {"username": payload.get("login"), "role": payload.get("role")}
        except:
            pass
    
    if not user:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


@app.get("/profiles")
def profiles_page(request: Request, page: int = Query(1), limit: int = Query(10)):
    import httpx
    
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/profiles",
            params={"page": page, "limit": min(limit, 50)},
            timeout=10
        )
        data = response.json() if response.status_code == 200 else {}
    except:
        data = {"data": [], "total": 0}
    
    profiles = data.get("data", []) if data.get("status") == "success" else []
    total = data.get("total", 0)
    total_pages = data.get("total_pages", 1)
    
    return templates.TemplateResponse("profiles.html", {
        "request": request, 
        "user": None,
        "profiles": profiles,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages
    })


@app.get("/profiles/search")
def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request, "user": None})


@app.post("/api/search")
def api_search(request: Request, q: str = Form(...), page: int = Form(1), limit: int = Form(10)):
    import httpx
    
    csrf_token = request.cookies.get(CSRF_TOKEN_COOKIE)
    form_csrf = request.form.get("csrf_token")
    
    if csrf_token != form_csrf:
        return JSONResponse(status_code=403, content={"status": "error", "message": "CSRF validation failed"})
    
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/profiles/search",
            params={"q": q, "page": page, "limit": limit},
            timeout=10
        )
        return JSONResponse(content=response.json() if response.status_code == 200 else {"status": "error"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/export")
def export_page(request: Request):
    return templates.TemplateResponse("export.html", {"request": request, "user": None})


@app.post("/api/export")
def api_export(request: Request):
    import httpx
    
    params = {}
    response = httpx.get(f"{BACKEND_URL}/api/v1/profiles/export", params=params, timeout=30)
    
    if response.status_code == 200:
        from fastapi.responses import StreamingResponse
        import io
        return StreamingResponse(
            iter([response.text]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=profiles_export.csv"}
        )
    
    return JSONResponse(status_code=500, content={"status": "error"})