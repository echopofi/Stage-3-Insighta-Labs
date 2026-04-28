# Insighta Labs+ Web Portal

## Overview

A web-based UI for the Profile Intelligence System with secure authentication via HTTP-only cookies and CSRF protection.

## Features

- **GitHub OAuth Login**: Secure authentication with PKCE
- **HTTP-Only Cookies**: Access and refresh tokens stored securely
- **CSRF Protection**: Token-based CSRF validation on state-changing operations
- **Role-Based UI**: Admin and analyst views

## Pages

| Route | Description |
|-------|------------|
| `/` | Home page |
| `/login` | Login page |
| `/github/login` | GitHub OAuth redirect |
| `/github/callback` | OAuth callback handler |
| `/logout` | Logout and clear session |
| `/dashboard` | User dashboard |
| `/profiles` | Profile list with filtering |
| `/profiles/search` | Natural language search |
| `/export` | CSV export |
| `/admin` | Admin panel (admin only) |

## Security

### HTTP-Only Cookies
- `session`: JWT with 15-minute expiry
- `refresh_token`: Long-lived refresh token
- `csrf_token`: CSRF protection token

### CSRF Protection
- CSRF token generated on login page load
- Validated on form submissions
- Token passed as hidden field or header

### Rate Limiting
- 100 requests per minute per IP on backend
- Sameorigin enforced on API calls

## Running Locally

```bash
cd web
pip install -r requirements.txt
python3 main.py
```

The portal runs on `http://localhost:3000`.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| GITHUB_CLIENT_ID | GitHub OAuth App ID | (required) |
| GITHUB_CLIENT_SECRET | GitHub OAuth App Secret | (required) |
| GITHUB_CALLBACK_URI | OAuth callback | http://localhost:3000/github/callback |
| BACKEND_URL | Backend API URL | http://localhost:8000 |

## Integration with Backend

The web portal proxies requests to the backend API:

1. User authenticates via GitHub (portal handles OAuth)
2. Portal stores session cookie
3. API requests include session cookie
4. Backend validates and processes requests
5. Responses returned to portal

### API Endpoints Used

- `GET /api/v1/profiles` - List profiles
- `GET /api/v1/profiles/search` - Natural language search
- `GET /api/v1/profiles/export` - CSV export
- `GET /api/v1/admin/users` - List users (admin)
- `GET /api/v1/admin/logs` - View logs (admin)