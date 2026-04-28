# Insighta Labs+ - Stage 3 Task

## Overview

Insighta Labs+ is a secure, multi-interface Profile Intelligence System built on top of the Stage 2 profile management system.

## Architecture

### Three Repos

1. **Backend** (`/backend`) - FastAPI REST API
2. **CLI** (`/cli`) - Command-line interface tool
3. **Web Portal** (`/web`) - Web-based UI

### System Diagram

```
┌─────────────────┐     ┌─────────────────┐
│   CLI Tool      │────▶│   Backend API   │
│ (Python/Click) │     │  (FastAPI)      │
└─────────────────┘     └────────┬────────┘
                                  │
┌─────────────────┐              │
│  Web Portal     │────────────────┘
│  (FastAPI)     │◀───────────────
└─────────────────┘     ┌────────┴────────┐
                        │     SQLite       │
                        │   Database      │
                        └─────────────────┘
```

## Authentication Flow

### GitHub OAuth with PKCE

1. **CLI/Web** generates code_verifier and code_challenge
2. Redirects to GitHub authorize URL with code_challenge
3. User authorizes on GitHub
4. GitHub redirects with authorization code
5. **Backend** exchanges code for access_token using code_verifier
6. Access token + refresh token issued to client

### Token Management

- **Access Token**: 15-minute expiry, Bearer token in Authorization header
- **Refresh Token**: 30-day expiry, used to obtain new access tokens
- Tokens automatically refreshed on expiry

### Web Portal Cookies

- `session`: HTTP-only cookie with JWT (15 min)
- `refresh_token`: HTTP-only cookie (30 days)
- `csrf_token`: HTTP-only cookie for CSRF protection

## Role Enforcement Logic

### Roles

- **admin**: Full system access, user management, logs
- **analyst**: Read profiles, search, export CSV

### Implementation

```python
def require_role(required_role: str):
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role != "admin" and required_role not in [user.role, "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker
```

- `/api/v1/profiles` - analyst+ required
- `/api/v1/profiles/{id}` - analyst+ required
- `/api/v1/profiles/export` - analyst+ required
- `/api/v1/profiles` (POST) - admin only
- `/api/v1/profiles/{id}` (DELETE) - admin only
- `/api/v1/admin/users` - admin only
- `/api/v1/admin/logs` - admin only
- `/api/v1/users/{id}/role` - admin only

## Natural Language Parsing Approach

### Supported Queries

```
males from <country>
females from <country>
<age_group> from <country>
<age_group> above <age>
<age_group> below <age>
young (16-24)
```

### Implementation

1. Parse query into keywords
2. Match country codes/names from COUNTRY_MAP
3. Extract gender, age_group, min_age, max_age
4. Build SQLAlchemy filters
5. Apply filters and return results

### Validation

- Keywords validated against allowed set
- Returns 400 if no valid keywords found

## Live URLs

- **Backend**: http://localhost:8000
- **Web Portal**: http://localhost:3000

## CLI Usage

```bash
# Login
python3 insighta_cli.py login

# List profiles
python3 insighta_cli.py list-profiles --gender male --limit 10

# Search
python3 insighta_cli.py search "males from Nigeria over 25"

# Export
python3 insighta_cli.py export-csv --gender female
```

## CSV Export

Endpoint: `GET /api/v1/profiles/export`

Parameters:
- `gender`, `country_id`, `age_group`, `min_age`, `max_age`

Returns CSV with headers:
- id, name, gender, gender_probability, age, age_group, country_id, country_name, country_probability, created_at

## API Versioning

All endpoints under `/api/v1/` prefix.

## Pagination

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "total_pages": 203,
  "data": [...]
}
```

## Rate Limiting

- 100 requests per minute per IP
- Returns 429 when exceeded
- Applies to all endpoints

## Request Logging

- All requests logged to database
- Admin can view via `/api/v1/admin/logs`
- Fields: user_id, method, path, status_code, ip_address, timestamp

## Running the System

### Backend

```bash
cd backend
python3 main.py
```

### CLI

```bash
cd cli
pip install -e .
insighta login
```

### Web Portal

```bash
cd web
python3 main.py
```

## GitHub OAuth Setup

1. Create GitHub OAuth App
2. Set callback URL to `http://localhost:8000/api/v1/auth/github/callback` (backend) or `http://localhost:3000/github/callback` (web)
3. Set environment variables:
   ```
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```