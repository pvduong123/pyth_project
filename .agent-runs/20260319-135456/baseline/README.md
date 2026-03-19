# Python SaaS Starter

Production-ready SaaS starter built with Python, FastAPI, server-rendered Jinja templates, and PostgreSQL. Authentication is implemented with JWT stored in an HTTP-only cookie.

## Features

- Email/password authentication pages
- Auth API endpoints for register, login, logout, and current user
- Forgot password pages and reset APIs
- Protected dashboard route
- User profile page
- Billing settings UI backed by PostgreSQL
- Clean architecture split into domain, application, infrastructure, and presentation layers
- Reusable template components and shared styling

## Architecture

```text
app/
  domain/          Core business entities and repository contracts
  application/     Use-case services and validation rules
  infrastructure/  SQLAlchemy, PostgreSQL, hashing, session token implementations
  presentation/    FastAPI routers, dependencies, and API schemas
templates/         Reusable Jinja components and page templates
static/            Shared CSS assets
```

## Requirements

- Python 3.11+
- Docker and Docker Compose

## Local Setup

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -e .
   ```

4. Start PostgreSQL:

   ```bash
   docker compose up -d db
   ```

5. Run database migrations:

   ```bash
   alembic upgrade head
   ```

6. Run the app:

   ```bash
   uvicorn app.main:app --reload
   ```

7. Open the app at `http://127.0.0.1:8000`.

## Environment Variables

| Variable | Required | Description | Example |
| --- | --- | --- | --- |
| `APP_NAME` | No | App title used in templates and FastAPI metadata. | `Python SaaS Starter` |
| `APP_ENV` | No | Runtime environment label. | `development` |
| `SECRET_KEY` | Yes | JWT signing key. Use a random value with at least 32 bytes in production. | `change-this-in-production-with-at-least-32-bytes` |
| `DATABASE_URL` | Yes | SQLAlchemy connection string for PostgreSQL. | `postgresql+psycopg://postgres:postgres@localhost:5432/saas_starter` |
| `COOKIE_NAME` | No | Name of the authentication cookie containing the JWT. | `saas_session` |
| `COOKIE_SECURE` | No | Set to `true` behind HTTPS in production. | `false` |
| `JWT_ALGORITHM` | No | JWT signing algorithm. | `HS256` |
| `JWT_EXPIRE_MINUTES` | No | JWT lifetime in minutes. | `10080` |
| `RESET_TOKEN_EXPIRE_MINUTES` | No | Single-use reset token lifetime in minutes. | `30` |
| `HOST` | No | Documented local bind host. | `127.0.0.1` |
| `PORT` | No | Documented local bind port. | `8000` |

## Auth API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`

### Example register payload

```json
{
  "full_name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "supersecret123"
}
```

## Protected Routes

- `/dashboard`
- `/profile`
- `/settings/billing`

Unauthenticated requests to those pages are redirected to `/login`.

## Notes for Production

- Set `COOKIE_SECURE=true` and run behind HTTPS.
- If you need immediate logout/revocation, add refresh tokens or JWT denylisting in a later step.
- Password reset links are logged locally through the development email service.
- The legacy `sessions` table may still exist in existing databases until you remove it with a migration.
- Back the billing settings page with a real billing provider such as Stripe when moving past starter mode.

## Migration Workflow

For a legacy database that was created before Alembic was introduced:

```bash
alembic stamp 0001_baseline_legacy_schema
alembic upgrade head
```

For a fresh database:

```bash
alembic upgrade head
```
