# Admin Login Gate Design

## Goal

Add a real login gate for the WC2026 app so public visitors see a login screen first, while protected API data is unavailable without a valid session.

## Approach

- Store the administrator password in environment variable `ADMIN_PASSWORD`.
- Add backend auth endpoints under `/api/v1/auth`:
  - `GET /status` reports whether auth is enabled and whether the current request is authenticated.
  - `POST /login` validates the password and sets an HttpOnly session cookie.
  - `POST /logout` clears the cookie.
- Protect all other `/api/v1/*` routes with FastAPI middleware when `ADMIN_PASSWORD` is configured.
- Sign session cookies with HMAC SHA256 using `AUTH_SESSION_SECRET` when present, otherwise the admin password.
- Render a dedicated glass-style login page in the React app before loading the normal application routes.

## Frontend

The React app checks `/api/v1/auth/status` on startup. If auth is enabled and the session is missing or expired, it renders only the login page. After login succeeds, the app renders the existing routes.

## Deployment

Docker and NAS/Unraid env examples expose:

- `ADMIN_PASSWORD`
- `AUTH_SESSION_SECRET`
- `AUTH_SESSION_MAX_AGE_SECONDS`

Leaving `ADMIN_PASSWORD` empty disables the login gate for local development.

## Testing

Backend tests cover:

- login status before and after authentication
- wrong-password rejection
- protected API denial without a cookie
- protected API access with a valid cookie
