# Insighta Labs+ CLI

## Installation

```bash
pip install -e .
```

Or run directly:

```bash
python3 insighta_cli.py
```

## Configuration

Configure the API URL:

```bash
export INSIGHTA_API_URL=http://localhost:8000
```

## Authentication Flow

### GitHub OAuth with PKCE

The CLI uses GitHub OAuth with PKCE (Proof Key for Code Exchange) for secure authentication:

1. User initiates login with `insighta login`
2. CLI generates a code verifier and challenge
3. Browser opens GitHub authorization page
4. User authorizes the app
5. CLI exchanges the code for tokens
6. Tokens are stored securely in `~/.insighta/credentials.json`

### Token Handling

- **Access Token**: 15-minute expiry, used for API requests
- **Refresh Token**: 30-day expiry, used to obtain new access tokens
- Tokens are automatically refreshed when expired
- On logout, refresh token is revoked

## Commands

### Authentication

```bash
insighta login      # Login with GitHub
insighta logout    # Logout and clear credentials
insighta whoami     # Show current user
```

### Profiles

```bash
insighta profiles list                    # List profiles
insighta profiles list --gender male  # Filter by gender
insighta profiles list --country-id NG # Filter by country
insighta profiles list --age-group adult    # Filter by age group
insighta profiles list --min-age 25      # Minimum age
insighta profiles list --max-age 40     # Maximum age
insighta profiles list --sort-by age --order desc  # Sort
insighta profiles list --page 2 --limit 20        # Pagination

insighta profiles search "males from Nigeria over 25"  # Natural language search
insighta profiles get "John Smith"                    # Get profile by name
insighta profiles export                           # Export to CSV
```

### Admin

```bash
insighta admin users   # List all users (admin only)
insighta admin logs   # View request logs (admin only)
```

## Credential Storage

Credentials are stored in `~/.insighta/credentials.json`:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "...",
  "expires_at": "1234567890",
  "username": "user",
  "role": "analyst"
}
```

## Role-Based Access

- **admin**: Full access to all endpoints, including user management and logs
- **analyst**: Read access to profiles, can export CSV

## Natural Language Search

The CLI supports natural language queries:

```
males from Nigeria
females from US above 25
teenagers from UK
seniors
adults from Canada
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| INSIGHTA_API_URL | API base URL | http://localhost:8000 |