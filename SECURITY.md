# Security Policy

This document explains how LinkedIn Post Bot handles security, authentication, and sensitive data.

---

## Table of Contents

- [Secrets Handling](#secrets-handling)
- [OAuth Flow](#oauth-flow)
- [API Key Storage](#api-key-storage)
- [Rate Limiting](#rate-limiting)
- [Responsible Usage](#responsible-usage)
- [Reporting Vulnerabilities](#reporting-vulnerabilities)

---

## Secrets Handling

### What We Store

| Data | Storage | Encryption |
|------|---------|------------|
| LinkedIn OAuth tokens | PostgreSQL / SQLite | Fernet (AES-128-CBC + HMAC-SHA256) |
| GitHub OAuth tokens | PostgreSQL / SQLite | Fernet (AES-128-CBC + HMAC-SHA256) |
| User preferences | PostgreSQL / SQLite | No (non-sensitive) |
| Post content & history | PostgreSQL / SQLite | No |

### What We NEVER Do

- **Never log secrets** — Access tokens, API keys, and client secrets are never printed to console or logs
- **Never expose secrets via API** — Settings endpoint returns masked versions (e.g., `gsk_xxxx...xxxx`)
- **Never transmit secrets unnecessarily** — Tokens are only sent to their respective API providers
- **Never store passwords** — We use OAuth; users authenticate directly with LinkedIn

### Environment Variables

All sensitive configuration is loaded from environment variables:

```bash
# Backend (.env)
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
GROQ_API_KEY=...
UNSPLASH_ACCESS_KEY=...

# Frontend (web/.env.local)
CLERK_SECRET_KEY=...
```

> **Important**: Never commit `.env` files. The `.gitignore` excludes all environment files and database files.

---

## Authentication & Middleware

### Clerk JWT Authentication

All API data endpoints require a valid Clerk JWT token:

- **`require_auth`**: Dependency that raises HTTP 401 if no valid token is present. Used on all settings, publish, and scheduling endpoints.
- **`get_current_user`**: Optional dependency that returns the authenticated user or `None`. Used on endpoints that work with or without auth.
- **User Ownership**: A `_verify_user_ownership()` helper raises HTTP 403 if the authenticated user doesn't match the requested `user_id`.

### Request Tracing

Every request includes an `X-Request-ID` header (generated or forwarded from client) for distributed tracing and debugging.

---

## OAuth Flow

### LinkedIn OAuth 2.0

The application uses LinkedIn's official OAuth 2.0 authorization code flow:

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  User    │         │  App     │         │ LinkedIn │
└────┬─────┘         └────┬─────┘         └────┬─────┘
     │                    │                     │
     │ 1. Click "Connect" │                     │
     │───────────────────>│                     │
     │                    │                     │
     │                    │ 2. Redirect to      │
     │                    │    LinkedIn OAuth   │
     │<───────────────────│────────────────────>│
     │                    │                     │
     │ 3. User grants     │                     │
     │    permission      │                     │
     │───────────────────────────────────────-->│
     │                    │                     │
     │                    │ 4. LinkedIn sends   │
     │                    │    auth code        │
     │<─────────────────────────────────────────│
     │                    │                     │
     │ 5. Callback to app │                     │
     │───────────────────>│                     │
     │                    │ 6. Exchange code    │
     │                    │    for token        │
     │                    │<───────────────────>│
     │                    │                     │
     │                    │ 7. Store token      │
     │                    │    securely         │
     │                    │                     │
```

### Required OAuth Scopes

| Scope | Purpose | Required |
|-------|---------|----------|
| `openid` | OpenID Connect user info | ✅ Yes |
| `profile` | Basic profile information | ✅ Yes |
| `email` | Email address | Optional |
| `w_member_social` | Create posts on behalf of user | ✅ Yes |

### Token Lifecycle

1. **Acquisition**: Token obtained via OAuth callback
2. **Storage**: Encrypted in SQLite with expiration timestamp
3. **Refresh**: Automatic refresh before expiry (60-second buffer)
4. **Revocation**: Users can disconnect via LinkedIn settings

### Per-User Credentials

Each user stores their own:
- LinkedIn Client ID & Secret (from their own LinkedIn Developer App)
- Groq API Key
- Unsplash Access Key

This ensures:
- Multi-tenant isolation
- No shared API quotas
- Users control their own credentials

---

## Multi-Tenant Isolation Guarantees

### Design Principle

```
┌───────────────────────────────────────────────────────────────────┐
│             MULTI-TENANT ISOLATION GUARANTEES                      │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ✅ User A can ONLY access:          ❌ User A can NEVER access:  │
│  - Their own OAuth tokens            - User B's tokens            │
│  - Their own GitHub activity         - User B's activity          │
│  - Their own LinkedIn posts          - User B's posts             │
│  - Their own settings                - User B's settings          │
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
```

### Implementation Details

**Database Level:**
- Every query includes `WHERE user_id = ?`
- User ID is the Clerk authentication ID
- No admin endpoints return all users' data

**API Level:**
- User ID extracted from JWT claims
- All endpoints scoped to authenticated user
- Cross-user access returns 404/403

**Service Level:**
- GitHub activity: Scoped by username/token
- AI generation: Receives only user's activity
- LinkedIn posting: Uses only user's OAuth token

### Token Validation

Before any operation that requires an OAuth token:

```python
# 1. Verify user is authenticated (Clerk JWT)
# 2. Retrieve token by user_id (tenant isolation)
# 3. Check token exists
# 4. Check token not expired
# 5. Proceed or return error
```

**Graceful Failure Handling:**
- Missing token → "Please connect your account"
- Expired token → "Please reconnect your account"
- Invalid token → "Authentication failed, please reconnect"
- Rate limited → "Too many requests, please wait"

### Cross-User Prevention

1. **No token enumeration** — Tokens keyed by user_id, not sequential IDs
2. **No URN guessing** — LinkedIn URN not exposed externally
3. **Parameterized queries** — SQL injection prevented
4. **JWT validation** — User identity verified on every request

### In-Transit

- All API calls use HTTPS
- JWT tokens verified on each request (Clerk authentication)
- CORS restricts origins to authorized frontends

### At-Rest

- SQLite databases stored locally
- Database files excluded from Git
- Production: Use encrypted volumes or managed databases

### Masking in UI

The settings endpoint returns masked API keys:

```json
{
  "groq_api_key": "gsk_xxxx...xxxx",
  "linkedin_client_secret": "••••••••"
}
```

Full keys are never sent back to the client after initial save.

---

## Rate Limiting

The application implements rate limiting to prevent abuse:

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Post Generation (`/api/post/generate-preview`) | 10 requests | 1 hour |
| Publishing (`/api/publish/full`) | 5 requests | 1 hour |
| Publishing (`/api/post/publish`) | 5 requests | 1 hour |
| General API | 100 requests | 1 hour |

Rate limits are enforced per-user (by Clerk user ID). Exceeded limits return **HTTP 429** responses.

### Implementation

See `services/rate_limiter.py` for the `RateLimiter` class:

```python
from services.middleware import post_generation_limiter, rate_limit

@rate_limit(post_generation_limiter)
async def generate_preview(user_id: str, ...):
    ...
```

---

## Responsible Usage

### What This Tool Is For

✅ Generating LinkedIn posts from your own GitHub activity  
✅ Publishing content to your own LinkedIn profile  
✅ Saving time on content creation  

### What This Tool Is NOT For

❌ Automated mass posting or spam  
❌ Posting on behalf of others without consent  
❌ Scraping LinkedIn data  
❌ Bypassing LinkedIn rate limits  
❌ Any activity that violates LinkedIn's Terms of Service  

### LinkedIn Terms Compliance

This application:
- Uses only LinkedIn's official APIs
- Requires explicit user authorization (OAuth)
- Does not automate engagement (likes, comments)
- Does not use browser automation or scraping
- Respects LinkedIn's API rate limits

> **Warning**: Excessive posting or suspicious activity may result in LinkedIn restricting your account. Use responsibly.

---

## Reporting Vulnerabilities

If you discover a security vulnerability, please:

1. **Do NOT open a public issue**
2. Email the maintainer directly with details
3. Include steps to reproduce if possible
4. Allow reasonable time for a fix before disclosure

We take security seriously and will respond promptly.

---

## Security Checklist for Contributors

When contributing code, ensure:

- [ ] No secrets logged to console (use masked versions if needed)
- [ ] No secrets returned in API responses (mask or omit)
- [ ] Input validation on all user-provided data
- [ ] Rate limiting on resource-intensive endpoints
- [ ] CORS configuration restricts to known origins
- [ ] SQL queries use parameterization (no string concatenation)
- [ ] OAuth tokens stored with expiration handling

---

**Last updated**: February 2026
