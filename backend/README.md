# Insighta Labs+ Backend

## System Architecture

### Overview
The backend is a FastAPI-based REST API that provides secure access to the Profile Intelligence System. It enforces authentication, authorization, and rate limiting on all endpoints.

### Components
- **API Server**: FastAPI with Uvicorn
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: GitHub OAuth with PKCE
- **Rate Limiting**: In-memory token bucket (100 requests/minute)

### API Versioning
All endpoints are prefixed with `/api/v1/` to support future versions.

### Endpoints

#### Authentication
- `GET /api/v1/auth/github/login` - Initiates GitHub OAuth flow
- `GET /api/v1/auth/github/callback` - Handles OAuth callback
- `GET /api/v1/auth/refresh` - Refreshes access token
- `POST /api/v1/auth/logout` - Revokes tokens and logs out
- `GET /api/v1/auth/me` - Returns current user info

#### Profiles
- `POST /api/v1/profiles` - Create profile (admin only)
- `GET /api/v1/profiles` - List profiles with filtering, sorting, pagination
- `GET /api/v1/profiles/search` - Natural language search
- `GET /api/v1/profiles/export` - Export profiles as CSV
- `GET /api/v1/profiles/{id}` - Get single profile
- `DELETE /api/v1/profiles/{id}` - Delete profile (admin only)

#### Admin
- `GET /api/v1/admin/users` - List all users (admin only)
- `GET /api/v1/admin/logs` - View request logs (admin only)
- `PUT /api/v1/users/{id}/role` - Update user role (admin only)

### Database Schema

#### Users
| Field | Type | Description |
|-------|------|------------|
| id | String | Primary key |
| github_id | String | GitHub user ID |
| username | String | GitHub username |
| email | String | User email |
| role | String | admin or analyst |
| is_active | Boolean | Account status |
| created_at | DateTime | Creation timestamp |

#### RefreshTokens
| Field | Type | Description |
|-------|------|------------|
| id | String | Primary key |
| user_id | String | Foreign key to users |
| token | String | Unique token |
| code_verifier | String | PKCE verifier |
| expires_at | DateTime | Expiration |
| revoked | Boolean | Revocation status |

#### OAuthStates
| Field | Type | Description |
|-------|------|------------|
| state | String | OAuth state |
| code_verifier | String | PKCE verifier |
| redirect_uri | String | Callback URI |
| client_type | String | cli or web |
| expires_at | DateTime | Expiration |

### Running Locally

```bash
cd backend
pip install -r requirements.txt
python3 main.py
```

The API runs on `http://localhost:8000`.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| GITHUB_CLIENT_ID | GitHub OAuth App ID | (required) |
| GITHUB_CLIENT_SECRET | GitHub OAuth App Secret | (required) |
| GITHUB_CALLBACK_URI | OAuth callback | http://localhost:8000/api/v1/auth/github/callback |
| BACKEND_URL | Backend URL | http://localhost:8000 |
| WEB_PORTAL_URL | Web portal URL | http://localhost:3000 |