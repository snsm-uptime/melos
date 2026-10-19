# Auth API Contract (Reused from finance-dashboard)

**Status:** Stable (no modifications)  
**Source:** `finance-dashboard/api/routes/auth.py`  
**Changes for Melos:** None—direct copy with zero adaptations

---

## Overview

Session-based authentication with httpOnly cookies. All auth flows go through POST endpoints that return session cookies. Clients maintain sessions via browser cookie jar; API validates via session table.

---

## Endpoints

### POST /auth/register

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123",
  "alias": "John Doe"
}
```

**Response (201 Created):**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "alias": "John Doe",
  "email_verified": false
}
```

**Set-Cookie:** `session_id=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=<30 days>`

**Error (400 Bad Request):**
```json
{
  "detail": "Email already registered"
}
```

**Error (429 Too Many Requests):**
- Rate limit: 5 registrations per IP per hour (ENV: `AUTH_RATE_LIMIT_REGISTER_MAX`, `AUTH_RATE_LIMIT_REGISTER_WINDOW_SECONDS`)

---

### POST /auth/sign-in

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**Response (200 OK):**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "alias": "John Doe",
  "email_verified": true,
  "theme": "dark",
  "locale": "en"
}
```

**Set-Cookie:** `session_id=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=<30 days>`

**Error (401 Unauthorized):**
```json
{
  "detail": "Invalid email or password"
}
```

**Error (429 Too Many Requests):**
- Rate limit: 10 sign-in attempts per IP per 15 minutes (ENV: `AUTH_RATE_LIMIT_SIGN_IN_MAX`, `AUTH_RATE_LIMIT_SIGN_IN_WINDOW_SECONDS`)

---

### POST /auth/sign-out

**Request:** (no body; uses session cookie)

**Response (200 OK):**
```json
{
  "detail": "Signed out successfully"
}
```

**Set-Cookie:** `session_id=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0` (clears cookie)

---

### GET /auth/session

**Request:** (uses session cookie)

**Response (200 OK):**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "alias": "John Doe",
  "email_verified": true,
  "theme": "dark",
  "locale": "en"
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "No active session"
}
```

---

### GET /auth/me

**Request:** (uses session cookie)

**Response (200 OK):**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "alias": "John Doe",
  "email_verified": true,
  "theme": "dark",
  "locale": "en"
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "No active session"
}
```

---

### POST /auth/password-reset/request

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "detail": "Password reset email sent (if email exists)"
}
```

**Note:** Always returns 200 even if email not found (security: no email enumeration)

**Error (429 Too Many Requests):**
- Rate limit: 3 reset requests per IP per hour

---

### POST /auth/password-reset/confirm

**Request:**
```json
{
  "token": "<reset_token_from_email>",
  "new_password": "new_secure_password_123"
}
```

**Response (200 OK):**
```json
{
  "detail": "Password reset successfully"
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Token expired or invalid"
}
```

**Token Expiry:** 1 hour (ENV: not configurable, hardcoded in application/password_reset.py)

---

### POST /auth/verify/request

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "detail": "Verification email sent (if email verification is required)"
}
```

**Gated by:** `EMAIL_VERIFICATION_REQUIRED` environment variable (default: false)

---

### POST /auth/verify/confirm

**Request:**
```json
{
  "token": "<verification_token_from_email>"
}
```

**Response (200 OK):**
```json
{
  "detail": "Email verified successfully"
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Token expired or invalid"
}
```

**Token Expiry:** 1 hour

---

## Session Storage

**Database Table:** `session`

| Column | Type | Notes |
|--------|------|-------|
| `session_id` | UUID | Primary key, generated at sign-in |
| `user_id` | UUID | Foreign key to user |
| `token_hash` | String | Hashed session token (for validation) |
| `created_at` | Timestamp | Session creation time |
| `expires_at` | Timestamp | Session expiry (30 days from creation) |
| `ip_address` | String | IP of session creator (for security audit) |

**Validation:** On each request, session middleware validates session_id from cookie against token_hash in DB.

---

## Error Handling

All auth errors return standard HTTP status codes:
- **400 Bad Request:** Missing fields, invalid email, password too weak
- **401 Unauthorized:** Invalid credentials, expired token, no session
- **429 Too Many Requests:** Rate limit exceeded (per IP, per endpoint)
- **500 Internal Server Error:** SMTP misconfiguration (fails loudly), database errors

Rate limit headers (per RFC 6585):
- `RateLimit-Limit: <max_requests>`
- `RateLimit-Remaining: <requests_left>`
- `RateLimit-Reset: <unix_timestamp>`

**Rate Limit Detection:** IP extracted from `AUTH_CLIENT_IP_HEADER` (default: `X-Forwarded-For`), validated against `TRUSTED_PROXY_IPS`.

---

## Security Notes

1. **Password Hashing:** Argon2 (via argon2-cffi, no configuration)
2. **Session Lifetime:** 30 days (hardcoded in adapters/persistence/sessions.py)
3. **Cookie Flags:**
   - `HttpOnly=true` (JavaScript cannot access)
   - `Secure=true` in production (HTTPS only)
   - `SameSite=Lax` (CSRF protection)
4. **Rate Limiting:** Per IP and per user (see rate limit tables in env vars)
5. **Email Validation:** Basic regex; no external verification on registration
6. **Email Verification:** Gated by `EMAIL_VERIFICATION_REQUIRED`; not required for Melos v1

---

## BFF Proxy (Next.js)

All auth endpoints are proxied through Next.js BFF routes under `ui/app/api/auth/`.

| Route | Proxy To | Cookie Handling |
|-------|----------|-----------------|
| `POST /api/auth/sign-in` | `POST /auth/sign-in` (api:8000) | Forwards Set-Cookie header to client |
| `POST /api/auth/register` | `POST /auth/register` | Forwards Set-Cookie header to client |
| `POST /api/auth/sign-out` | `POST /auth/sign-out` | Forwards Set-Cookie header (clear) |
| `GET /api/auth/session` | `GET /auth/session` | Reads session cookie from request |
| `GET /api/auth/me` | `GET /auth/me` | Reads session cookie from request |

---

## Configuration (via .env)

```bash
# Session
SESSION_SECRET=<random_string_64_chars>
SESSION_COOKIE_NAME=session_id
SESSION_COOKIE_SECURE=true  # false in dev, true in prod
SESSION_COOKIE_SAMESITE=Lax

# Rate Limits
AUTH_RATE_LIMIT_REGISTER_MAX=5
AUTH_RATE_LIMIT_REGISTER_WINDOW_SECONDS=3600
AUTH_RATE_LIMIT_SIGN_IN_MAX=10
AUTH_RATE_LIMIT_SIGN_IN_WINDOW_SECONDS=900
AUTH_RATE_LIMIT_PASSWORD_RESET_REQUEST_MAX=3
AUTH_RATE_LIMIT_PASSWORD_RESET_REQUEST_WINDOW_SECONDS=3600
AUTH_RATE_LIMIT_VERIFY_REQUEST_MAX=5
AUTH_RATE_LIMIT_VERIFY_REQUEST_WINDOW_SECONDS=3600

# Email Verification
EMAIL_VERIFICATION_REQUIRED=false  # Not required for Melos v1

# Network
TRUSTED_PROXY_IPS=172.16.0.0/12,127.0.0.1  # Compose network + localhost
AUTH_CLIENT_IP_HEADER=X-Forwarded-For

# SMTP (Required for email flows)
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SMTP_USER=<username>
SMTP_PASSWORD=<password>
SMTP_FROM=noreply@melos.example.com
SMTP_USE_TLS=false
SMTP_STARTTLS=true
SMTP_TIMEOUT_SECONDS=10

# App URL (for reset links, invites)
PUBLIC_APP_URL=http://localhost:3000  # dev; https://melos.example.com in prod
```

---

## Testing

Auth layer is tested via:
1. **Unit tests** (domain/): Password hashing, token generation
2. **Integration tests** (api/tests/test_auth.py): Register, sign-in, sign-out, session, password reset, email verification
3. **BFF tests** (ui/__tests__/api/auth/): Cookie forwarding, error propagation

Test database: Uses `docker-compose.test.yml` with isolated Postgres.

