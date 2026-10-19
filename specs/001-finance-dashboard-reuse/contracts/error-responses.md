# Error Response Contract

**Status:** Standard across all Melos endpoints  
**Basis:** FastAPI/Pydantic conventions

---

## Standard Error Response Format

All API errors return JSON with this structure:

```json
{
  "detail": "Human-readable error message"
}
```

---

## HTTP Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| **400** | Bad Request | Missing required field, invalid email, weak password |
| **401** | Unauthorized | No session, invalid credentials, expired token |
| **403** | Forbidden | Only owner can perform this action |
| **404** | Not Found | Kitchen not found, recipe not found, user not found |
| **409** | Conflict | Email already registered, ingredient already exists |
| **422** | Unprocessable Entity | Invalid request body (Pydantic validation error) |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | SMTP misconfigured, database connection lost |

---

## Rate Limit Response (429)

When a rate limit is exceeded, the response includes headers:

```
HTTP/1.1 429 Too Many Requests

RateLimit-Limit: 5
RateLimit-Remaining: 0
RateLimit-Reset: 1634682900

{
  "detail": "Too many requests. Try again in 60 seconds."
}
```

**Headers:**
- `RateLimit-Limit`: Max requests in the window
- `RateLimit-Remaining`: Requests left before limit
- `RateLimit-Reset`: Unix timestamp when limit resets

---

## Domain Error → HTTP Mapping

Melos domain errors are mapped to user-facing HTTP responses by adapters:

| Domain Error | HTTP Status | Message |
|--------------|-------------|---------|
| `ValidationError` | 400 | "Invalid input: {reason}" |
| `NotFoundError` | 404 | "Resource not found" |
| `UnauthorizedError` | 401 | "Not authenticated" |
| `PermissionError` | 403 | "Permission denied" |
| `DuplicateError` | 409 | "Resource already exists" |
| `AIUnavailable` | 503 | "AI service unavailable" |
| `PageFetchFailed` | 502 | "Could not fetch recipe from URL" |
| `RecipeParsingFailed` | 400 | "Could not parse recipe text" |
| `EmbeddingFailed` | 500 | "Could not generate embeddings" |

---

## Pydantic Validation Error (422)

If the request body fails Pydantic validation, FastAPI returns:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "invalid email format",
      "type": "value_error.email"
    }
  ]
}
```

**In Melos:** Use clear, simple Pydantic models to minimize validation errors. Error messages in schemas should guide users (e.g., `description="Email address (e.g., user@example.com)"`).

---

## Health Check Endpoint

### GET /health

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-10-19T12:00:00Z",
  "version": "1.0.0"
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "reason": "Database connection failed",
  "timestamp": "2026-10-19T12:00:00Z"
}
```

**Checks:**
- Database connectivity (Postgres)
- API runtime (FastAPI app)
- External service availability (Gemini API optional; warn if unavailable)

---

## SMTP Misconfiguration (Fails Loudly)

If SMTP is misconfigured (missing host, wrong port, auth failure), the API **does not silently fail**. Instead:

1. API startup fails with a clear error message
2. No email is sent without visibility
3. Logs include the SMTP error details

**Environment variables checked at startup:**
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- If any are missing, API fails on boot with error message

---

## External Service Errors

### Gemini API Unavailable

If Gemini API is unavailable (quota exceeded, service down):

```json
{
  "detail": "AI service temporarily unavailable. Try again later."
}
```

**Status:** 503 Service Unavailable

**Retry:** Client may retry with exponential backoff.

---

### Page Fetch Failed

If URL fetching fails (SSRF violation, timeout, invalid URL):

```json
{
  "detail": "Could not fetch recipe from URL: Connection timeout"
}
```

**Status:** 400 Bad Request (user can retry with different URL)

**SSRF Prevention:**
- No private/loopback IPs: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `fc00::/7`
- Max 3 redirects
- 10-second timeout
- 2MB response size limit

---

## Testing Error Handling

Error responses are tested via:
1. **Unit tests** (domain/): Business logic errors (e.g., ValidationError)
2. **Integration tests** (api/tests/): HTTP status codes, response bodies, rate limits
3. **Manual testing:** Trigger SMTP misconfiguration, API downtime, Gemini quota exceeded

Test fixtures include error scenarios:
- Missing fields in request body
- Invalid email format
- Rate limit exceeded
- Kitchen not found (404 vs 403)

