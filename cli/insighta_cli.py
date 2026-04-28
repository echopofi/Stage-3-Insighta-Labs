#!/usr/bin/env python3
import os
import sys
import json
import time
import secrets
import hashlib
import base64
import shutil
import pathlib
import webbrowser
import http.server
import socketserver
import urllib.parse
import urllib.request
import ssl
from typing import Optional, Dict, Any, List

import click
import httpx


CREDENTIALS_FILE = pathlib.Path.home() / ".insighta" / "credentials.json"
DEFAULT_API_URL = "http://localhost:8000"
PORT = 8765


def load_credentials() -> Optional[Dict[str, Any]]:
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE) as f:
            return json.load(f)
    return None


def save_credentials(credentials: Dict[str, Any]):
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f, indent=2)


def clear_credentials():
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()


def generate_code_verifier(length: int = 128) -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).rstrip(b"=").decode()


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def get_access_token() -> Optional[str]:
    creds = load_credentials()
    if creds:
        return creds.get("access_token")
    return None


def is_token_expired(expires_at: str) -> bool:
    try:
        exp_time = int(expires_at)
        return time.time() >= exp_time
    except:
        return True


def refresh_token(api_url: str, refresh_token: str) -> Optional[Dict[str, Any]]:
    try:
        response = httpx.get(
            f"{api_url}/api/v1/auth/refresh",
            params={"refresh_token": refresh_token},
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        click.echo(f"Error refreshing token: {e}", err=True)
    return None


def ensure_valid_token(api_url: str) -> bool:
    creds = load_credentials()
    if not creds:
        return False
    
    refresh_token_str = creds.get("refresh_token")
    exp_at = creds.get("expires_at")
    
    if exp_at and is_token_expired(exp_at):
        if refresh_token_str:
            new_creds = refresh_token(api_url, refresh_token_str)
            if new_creds and new_creds.get("status") == "success":
                save_credentials({
                    "access_token": new_creds["access_token"],
                    "refresh_token": new_creds["refresh_token"],
                    "expires_at": str(int(time.time()) + new_creds.get("expires_in", 900)),
                    "username": creds.get("username"),
                    "role": creds.get("role")
                })
                return True
        clear_credentials()
        return False
    
    return True


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        if "code" in query and "state" in query:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication Successful!</h1><p>You can close this window and return to the CLI.</p></body></html>")
            
            self.server.oauth_code = query["code"][0]
            self.server.oauth_state = query["state"][0]
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication Failed</h1><p>No authorization code received.</p></body></html>")
            self.server.oauth_code = None
            self.server.oauth_state = None
    
    def log_message(self, format, *args):
        pass


@click.group()
@click.option("--api-url", default=DEFAULT_API_URL, help="API base URL")
@click.pass_context
def cli(ctx, api_url):
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url


@cli.command()
@click.pass_context
def login(ctx):
    api_url = ctx.obj["api_url"]
    
    if get_access_token() and ensure_valid_token(api_url):
        click.echo("Already logged in. Use 'logout' first to login again.")
        return
    
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)
    
    callback_url = f"http://127.0.0.1:{PORT}/callback"
    
    try:
        response = httpx.get(
            f"{api_url}/api/v1/auth/github/login",
            params={"redirect_uri": callback_url},
            timeout=30.0
        )
        if response.status_code != 200:
            click.echo(f"Error starting auth: {response.text}", err=True)
            return
        
        auth_data = response.json()
        auth_url = auth_data.get("authorization_url")
        
        click.echo("Opening GitHub OAuth in your browser...")
        webbrowser.open(auth_url)
        
        click.echo(f"Waiting for callback at http://127.0.0.1:{PORT}...")
        
        with socketserver.TCPServer(("127.0.0.1", PORT), OAuthCallbackHandler) as httpd:
            httpd.handle_request()
            
            if not hasattr(httpd, "oauth_code") or not httpd.oauth_code:
                click.echo("No authorization code received.", err=True)
                return
            
            code = httpd.oauth_code
            
            token_response = httpx.get(
                f"{api_url}/api/v1/auth/github/callback",
                params={"code": code, "state": state},
                timeout=30.0
            )
            
            if token_response.status_code != 200:
                click.echo(f"Error exchanging code: {token_response.text}", err=True)
                return
            
            token_data = token_response.json()
            
            if token_data.get("status") == "success":
                save_credentials({
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data["refresh_token"],
                    "expires_at": str(int(time.time()) + token_data.get("expires_in", 900)),
                    "username": "CLI User",
                    "role": "analyst"
                })
                click.echo("Login successful!")
            else:
                click.echo(f"Login failed: {token_data}", err=True)
                
    except Exception as e:
        click.echo(f"Error during login: {e}", err=True)


@cli.command()
@click.pass_context
def logout(ctx):
    api_url = ctx.obj["api_url"]
    
    creds = load_credentials()
    if creds:
        refresh_t = creds.get("refresh_token")
        if refresh_t:
            try:
                httpx.get(
                    f"{api_url}/api/v1/auth/logout",
                    params={"refresh_token": refresh_t},
                    timeout=10.0
                )
            except:
                pass
    
    clear_credentials()
    click.echo("Logged out successfully.")


@cli.command()
@click.pass_context
def whoami(ctx):
    creds = load_credentials()
    if creds:
        click.echo(f"Username: {creds.get('username', 'N/A')}")
        click.echo(f"Role: {creds.get('role', 'N/A')}")
    else:
        click.echo("Not logged in.")


@cli.command()
@click.option("--gender", help="Filter by gender")
@click.option("--country-id", help="Filter by country code")
@click.option("--age-group", help="Filter by age group (child/teenager/adult/senior)")
@click.option("--min-age", type=int, help="Minimum age")
@click.option("--max-age", type=int, help="Maximum age")
@click.option("--sort-by", type=click.Choice(["age", "created_at", "gender_probability"]), help="Sort field")
@click.option("--order", type=click.Choice(["asc", "desc"]), default="asc")
@click.option("--page", type=int, default=1)
@click.option("--limit", type=int, default=10)
@click.pass_context
def list_profiles(ctx, gender, country_id, age_group, min_age, max_age, sort_by, order, page, limit):
    api_url = ctx.obj["api_url"]
    
    if not ensure_valid_token(api_url):
        click.echo("Not logged in. Use 'login' first.", err=True)
        return
    
    creds = load_credentials()
    headers = {"Authorization": f"Bearer {creds['access_token']}"}
    
    params = {"page": page, "limit": limit}
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
    if sort_by:
        params["sort_by"] = sort_by
        params["order"] = order
    
    try:
        response = httpx.get(
            f"{api_url}/api/v1/profiles",
            headers=headers,
            params=params,
            timeout=30.0
        )
        
        if response.status_code == 401:
            clear_credentials()
            click.echo("Session expired. Please login again.", err=True)
            return
        
        if response.status_code != 200:
            click.echo(f"Error: {response.text}", err=True)
            return
        
        data = response.json()
        
        if data.get("status") == "success":
            profiles = data.get("data", [])
            total = data.get("total", 0)
            total_pages = data.get("total_pages", 0)
            
            click.echo(f"\nTotal profiles: {total} | Page {page}/{total_pages}\n")
            click.echo("-" * 80)
            
            for p in profiles:
                click.echo(f"{p['name']} | {p['gender']} | Age {p['age']} ({p['age_group']}) | {p['country_name']}")
        else:
            click.echo(f"Error: {data}", err=True)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("query")
@click.option("--page", type=int, default=1)
@click.option("--limit", type=int, default=10)
@click.pass_context
def search(ctx, query, page, limit):
    api_url = ctx.obj["api_url"]
    
    if not ensure_valid_token(api_url):
        click.echo("Not logged in. Use 'login' first.", err=True)
        return
    
    creds = load_credentials()
    headers = {"Authorization": f"Bearer {creds['access_token']}"}
    
    try:
        response = httpx.get(
            f"{api_url}/api/v1/profiles/search",
            headers=headers,
            params={"q": query, "page": page, "limit": limit},
            timeout=30.0
        )
        
        if response.status_code == 401:
            clear_credentials()
            click.echo("Session expired. Please login again.", err=True)
            return
        
        if response.status_code != 200:
            click.echo(f"Error: {response.text}", err=True)
            return
        
        data = response.json()
        
        if data.get("status") == "success":
            profiles = data.get("data", [])
            total = data.get("total", 0)
            
            click.echo(f"\nFound {total} profiles matching '{query}'\n")
            
            for p in profiles:
                click.echo(f"{p['name']} | {p['gender']} | Age {p['age']} ({p['age_group']}) | {p['country_name']}")
        else:
            click.echo(f"Error: {data}", err=True)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("name")
@click.pass_context
def get_profile(ctx, name):
    api_url = ctx.obj["api_url"]
    
    if not ensure_valid_token(api_url):
        click.echo("Not logged in. Use 'login' first.", err=True)
        return
    
    creds = load_credentials()
    headers = {"Authorization": f"Bearer {creds['access_token']}"}
    
    try:
        response = httpx.get(
            f"{api_url}/api/v1/profiles",
            headers=headers,
            params={"name": name, "limit": 1},
            timeout=30.0
        )
        
        if response.status_code != 200:
            click.echo(f"Error: {response.text}", err=True)
            return
        
        data = response.json()
        
        if data.get("status") == "success" and data.get("data"):
            p = data["data"][0]
            click.echo(f"\nProfile: {p['name']}")
            click.echo(f"Gender: {p['gender']} ({p['gender_probability']})")
            click.echo(f"Age: {p['age']} ({p['age_group']})")
            click.echo(f"Country: {p['country_name']} ({p['country_probability']})")
            click.echo(f"Created: {p['created_at']}")
        else:
            click.echo("Profile not found.")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option("--gender", help="Filter by gender")
@click.option("--country-id", help="Filter by country code")
@click.option("--age-group", help="Filter by age group")
@click.option("--min-age", type=int)
@click.option("--max-age", type=int)
@click.pass_context
def export_csv(ctx, gender, country_id, age_group, min_age, max_age):
    api_url = ctx.obj["api_url"]
    
    if not ensure_valid_token(api_url):
        click.echo("Not logged in. Use 'login' first.", err=True)
        return
    
    creds = load_credentials()
    headers = {"Authorization": f"Bearer {creds['access_token']}"}
    
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
            f"{api_url}/api/v1/profiles/export",
            headers=headers,
            params=params,
            timeout=60.0
        )
        
        if response.status_code == 401:
            clear_credentials()
            click.echo("Session expired. Please login again.", err=True)
            return
        
        if response.status_code != 200:
            click.echo(f"Error: {response.text}", err=True)
            return
        
        with open("profiles_export.csv", "w") as f:
            f.write(response.text)
        
        click.echo("Exported to profiles_export.csv")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.pass_context
def list_users(ctx):
    api_url = ctx.obj["api_url"]
    
    if not ensure_valid_token(api_url):
        click.echo("Not logged in. Use 'login' first.", err=True)
        return
    
    creds = load_credentials()
    headers = {"Authorization": f"Bearer {creds['access_token']}"}
    
    try:
        response = httpx.get(
            f"{api_url}/api/v1/admin/users",
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code == 403:
            click.echo("Admin access required.", err=True)
            return
        
        if response.status_code != 200:
            click.echo(f"Error: {response.text}", err=True)
            return
        
        data = response.json()
        
        if data.get("status") == "success":
            users = data.get("data", [])
            
            click.echo(f"\nTotal users: {len(users)}\n")
            click.echo("-" * 60)
            
            for u in users:
                status = "active" if u.get("is_active") else "inactive"
                click.echo(f"{u['username']} | {u['role']} | {u['email']} | {status}")
        else:
            click.echo(f"Error: {data}", err=True)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.pass_context
def list_logs(ctx):
    api_url = ctx.obj["api_url"]
    
    if not ensure_valid_token(api_url):
        click.echo("Not logged in. Use 'login' first.", err=True)
        return
    
    creds = load_credentials()
    headers = {"Authorization": f"Bearer {creds['access_token']}"}
    
    try:
        response = httpx.get(
            f"{api_url}/api/v1/admin/logs",
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code == 403:
            click.echo("Admin access required.", err=True)
            return
        
        if response.status_code != 200:
            click.echo(f"Error: {response.text}", err=True)
            return
        
        data = response.json()
        
        if data.get("status") == "success":
            logs = data.get("data", [])
            
            click.echo("\nRecent Request Logs:\n")
            click.echo("-" * 80)
            
            for log in logs[:50]:
                click.echo(f"{log['timestamp']} | {log['method']} | {log['path']} | {log['status_code']} | {log['ip_address']}")
        else:
            click.echo(f"Error: {data}", err=True)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    cli()