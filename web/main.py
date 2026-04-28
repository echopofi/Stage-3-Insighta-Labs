import os
import json
import secrets
import hashlib
import base64
import time
import datetime
from pathlib import Path
from typing import Optional
from functools import wraps
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from fastapi import FastAPI, Request, HTTPException, Query, Header, Form, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Insighta Labs+ Portal", version="2.0.0")

@app.get("/")
def home(request: Request):
    return {"status": "ok", "message": "Insighta Labs+ Web Portal"}

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
CSRF_TOKEN_COOKIE = "csrf_token"
SESSION_COOKIE = "session"

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "Ov23liplaceholderclientid")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "placeholderclientsecret")
GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI", "http://localhost:3000/github/callback")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    session = request.cookies.get(SESSION_COOKIE)
    if not session:
        return None
    
    try:
        payload = json.loads(base64.b64decode(session.split('.')[1] + '==').decode())
        user_id = payload.get("sub")
        if user_id:
            return db.query(User).filter(User.id == user_id, User.is_active == True).first()
    except:
        pass
    return None


def require_auth(user: Optional[User] = None):
    def auth_checker(r: Request = None, user: User = None):
        if not user:
            raise HTTPException(status_code=401, detail={"status": "error", "message": "Authentication required"})
        return user
    return auth_checker


def require_role(required_role: str):
    def role_checker(user: User = None):
        if not user:
            raise HTTPException(status_code=401, detail={"status": "error", "message": "Authentication required"})
        if user.role != "admin" and required_role not in [user.role, "admin"]:
            raise HTTPException(status_code=403, detail={"status": "error", "message": "Insufficient permissions"})
        return user
    return role_checker


@app.get("/test")
def test():
    return {"status": "ok", "message": "test endpoint"}


@app.get("/")
def home(request: Request):
    return {"status": "ok", "message": "Insighta Labs+ Web Portal"}


@app.get("/login")
def login_page(request: Request):
    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})
    response.set_cookie(
        key=CSRF_TOKEN_COOKIE,
        value=csrf_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600
    )
    response.set_cookie(
        key="oauth_state",
        value=secrets.token_urlsafe(32),
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600
    )
    return response


@app.get("/github/login")
def github_login(request: Request):
    state = request.cookies.get("oauth_state") or secrets.token_urlsafe(32)
    code_verifier = services.generate_code_verifier()
    code_challenge = services.generate_code_challenge(code_verifier)
    
    db = SessionLocal()
    oauth_state = OAuthState(
        state=state,
        code_verifier=code_verifier,
        redirect_uri=GITHUB_CALLBACK_URI,
        client_type="web",
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    )
    db.add(oauth_state)
    db.commit()
    db.close()
    
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
def github_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    oauth_state = db.query(OAuthState).filter(OAuthState.state == state).first()
    
    if not oauth_state:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Invalid state"})
    
    if oauth_state.expires_at < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail={"status": "error", "message": "State expired"})
    
    code_verifier = oauth_state.code_verifier
    db.delete(oauth_state)
    db.commit()
    
    token_url = "https://github.com/login/oauth/access_token"
    token_data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_CALLBACK_URI,
        "code_verifier": code_verifier
    }
    
    response = httpx.post(token_url, json=token_data)
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Failed to exchange code for token"})
    
    token_response = response.json()
    access_token = token_response.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "No access token received"})
    
    user_response = httpx.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    github_user = user_response.json()
    
    email_response = httpx.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    emails = email_response.json()
    primary_email = next((e["email"] for e in emails if e.get("primary")), emails[0]["email"] if emails else None)
    
    user = db.query(User).filter(User.github_id == str(github_user["id"])).first()
    
    if not user:
        user = User(
            github_id=str(github_user["id"]),
            username=github_user["login"],
            email=primary_email or github_user.get("email"),
            role="analyst"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    session_payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "exp": int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())
    }
    session_b64 = base64.b64encode(json.dumps(session_payload).encode()).decode()
    session_token = f"eyJ.{session_b64}."
    
    refresh_token_str = secrets.token_urlsafe(32)
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_token)
    db.commit()
    db.close()
    
    response = RedirectResponse(url="/dashboard")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    return response


@app.get("/logout")
def logout(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    db = SessionLocal()
    if refresh_token:
        stored_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        if stored_token:
            stored_token.revoked = True
            db.commit()
    db.close()
    
    response = RedirectResponse(url="/")
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie("refresh_token")
    response.delete_cookie(CSRF_TOKEN_COOKIE)
    response.delete_cookie("oauth_state")
    return response


@app.get("/dashboard")
def dashboard(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


@app.get("/profiles")
def profiles_page(
    request: Request,
    page: int = Query(1),
    limit: int = Query(10),
    gender: str = None,
    country_id: str = None,
    age_group: str = None,
    min_age: int = None,
    max_age: int = None,
    user: User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/login")
    
    params = {"page": page, "limit": min(limit, 50)}
    if gender:
        params["gender"] = gender
    if country_id:
        params["country_id"] = country_id
    if age_group:
        params["age_group"] = age_group
    if min_age is not None:
        params["min_age"] = min_age
    if max_age is not None:
        params["max_age"] = max_age
    
    session = request.cookies.get(SESSION_COOKIE)
    
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/profiles",
            params=params,
            timeout=30.0
        )
        
        if response.status_code == 401:
            return RedirectResponse(url="/login")
        
        data = response.json() if response.status_code == 200 else {}
    except:
        data = {"status": "error", "data": []}
    
    profiles = data.get("data", []) if data.get("status") == "success" else []
    total = data.get("total", 0)
    total_pages = data.get("total_pages", 1)
    
    return templates.TemplateResponse(
        "profiles.html",
        {
            "request": request,
            "user": user,
            "profiles": profiles,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "filters": {
                "gender": gender,
                "country_id": country_id,
                "age_group": age_group,
                "min_age": min_age,
                "max_age": max_age
            }
        }
    )


@app.get("/profiles/search")
def search_page(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("search.html", {"request": request, "user": user})


@app.post("/api/search")
def api_search(
    request: Request,
    q: str = Form(...),
    page: int = Form(1),
    limit: int = Form(10),
    user: User = Depends(get_current_user)
):
    if not user:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Authentication required"})
    
    csrf_token = request.cookies.get(CSRF_TOKEN_COOKIE)
    form_csrf = request.form.get("csrf_token")
    
    if csrf_token != form_csrf:
        return JSONResponse(status_code=403, content={"status": "error", "message": "CSRF validation failed"})
    
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/profiles/search",
            params={"q": q, "page": page, "limit": limit},
            timeout=30.0
        )
        
        if response.status_code == 401:
            return RedirectResponse(url="/login")
        
        return JSONResponse(content=response.json() if response.status_code == 200 else {"status": "error"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/export")
def export_page(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("export.html", {"request": request, "user": user})


@app.post("/api/export")
def api_export(
    request: Request,
    gender: str = Form(None),
    country_id: str = Form(None),
    age_group: str = Form(None),
    min_age: int = Form(None),
    max_age: int = Form(None),
    user: User = Depends(get_current_user)
):
    if not user:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Authentication required"})
    
    csrf_token = request.cookies.get(CSRF_TOKEN_COOKIE)
    form_csrf = request.form.get("csrf_token")
    
    if csrf_token != form_csrf:
        return JSONResponse(status_code=403, content={"status": "error", "message": "CSRF validation failed"})
    
    params = {}
    if gender:
        params["gender"] = gender
    if country_id:
        params["country_id"] = country_id
    if age_group:
        params["age_group"] = age_group
    if min_age is not None:
        params["min_age"] = min_age
    if max_age is not None:
        params["max_age"] = max_age
    
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/profiles/export",
            params=params,
            timeout=60.0
        )
        
        if response.status_code == 401:
            return RedirectResponse(url="/login")
        
        from fastapi.responses import StreamingResponse
        import io
        
        return StreamingResponse(
            iter([response.text]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=profiles_export.csv"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/admin")
def admin_page(request: Request, user: User = Depends(get_current_user)):
    if not user or user.role != "admin":
        return RedirectResponse(url="/dashboard")
    
    db = SessionLocal()
    users = db.query(User).all()
    logs = db.query(RequestLog).order_by(desc(RequestLog.timestamp)).limit(100).all()
    db.close()
    
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "logs": logs
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)


def handler(request):
    return app(request)