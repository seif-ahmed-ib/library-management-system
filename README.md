# Library Management System

A complete Library Management System built with FastAPI for the DSC 306 R and Python Programming Language course. Librarians manage books and review all borrowing activity, while members borrow, return, and review their own history.

## Features

- JWT registration, login, token validation, and protected routes
- Role-based authorization for `admin` and `member`
- Full book CRUD with Pydantic validation and correct HTTP status codes
- Borrowing, returning, availability tracking, personal history, and admin history
- Maximum of three active books per member and duplicate-borrow protection
- Redis Cache-Aside for book lists and individual books
- Cache invalidation after create, update, delete, borrow, and return operations
- Structured JSON logs for requests, authentication, errors, and data changes
- Live monitoring dashboard with request counts, timings, error rate, recent errors, cache metrics, and system health
- Responsive frontend for registration, login, book management, borrowing, and returning
- Automated API, business-rule, cache, monitoring, and frontend tests
- Docker Compose stack with FastAPI, PostgreSQL, and Redis

## Technology Stack

- Python 3.11
- FastAPI and Pydantic v2
- SQLAlchemy 2.0
- PostgreSQL with psycopg (SQLite is supported for quick local development)
- Redis
- PyJWT and pwdlib/Argon2
- Pytest and FastAPI TestClient
- Docker and Docker Compose

## Architecture

```text
app/
├── api/v1/routes/       # HTTP endpoints
├── auth/                # JWT and role dependencies
├── cache/               # Redis adapter and book Cache-Aside logic
├── core/                # Settings, security, and logging
├── db/                  # SQLAlchemy base, engine, and sessions
├── frontend/            # Course bonus frontend
├── middleware/          # Request logging and metrics
├── models/              # SQLAlchemy entities
├── monitoring/          # Metrics registry and live dashboard
├── schemas/             # Pydantic request/response models
├── scripts/             # Admin maintenance command
└── services/            # Business rules and database operations
tests/                   # Automated test suite
```

The request flow is:

```text
Client -> FastAPI route -> authentication/authorization -> service -> SQLAlchemy -> database
                                                |-> Redis Cache-Aside for book reads
Every request -> logging middleware -> JSON logs + monitoring metrics
```

## Recommended Setup: Docker

Docker runs the complete stack, including PostgreSQL and Redis.

1. Clone the repository and open its directory.
2. Copy the environment template:

   Windows CMD:

   ```cmd
   copy .env.example .env
   ```

   PowerShell/Linux/macOS:

   ```bash
   cp .env.example .env
   ```

3. Generate a secret and place it in `.env` as `SECRET_KEY`:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Build and start the stack:

   ```bash
   docker compose up --build -d
   ```

5. Create the first admin interactively:

   ```bash
   docker compose exec app python -m app.scripts.create_admin --name "Library Admin" --email admin@example.com
   ```

6. Open:

   - Frontend: <http://127.0.0.1:8000/app>
   - Swagger API docs: <http://127.0.0.1:8000/docs>
   - Monitoring dashboard: <http://127.0.0.1:8000/monitoring>
   - Health endpoint: <http://127.0.0.1:8000/health>

Stop the services without deleting data:

```bash
docker compose down
```

## Local Setup on Windows

1. Create and activate a Python 3.11 environment:

   ```cmd
   py -3.11 -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:

   ```cmd
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Create `.env`:

   ```cmd
   copy .env.example .env
   ```

4. For the fastest local start, change `DATABASE_URL` in `.env` to:

   ```env
   DATABASE_URL=sqlite:///./library.db
   ```

   Keep the PostgreSQL URL when PostgreSQL is installed locally. Redis should be running at the configured `REDIS_URL`; if Redis is temporarily unavailable, requests safely fall back to the database and return `X-Cache: BYPASS`.

5. Create an admin and run the API:

   ```cmd
   python -m app.scripts.create_admin --name "Library Admin" --email admin@example.com
   uvicorn app.main:app --reload
   ```

Tables are created automatically when the application starts.

## Main API Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Public | Register a member |
| POST | `/api/v1/auth/login` | Public | Receive a JWT |
| GET | `/api/v1/auth/me` | Authenticated | Current user |
| GET | `/api/v1/books` | Authenticated | List books (cached) |
| GET | `/api/v1/books/{id}` | Authenticated | Get one book (cached) |
| POST | `/api/v1/books` | Admin | Create a book |
| PUT | `/api/v1/books/{id}` | Admin | Update a book |
| DELETE | `/api/v1/books/{id}` | Admin | Delete a book |
| POST | `/api/v1/borrows` | Member | Borrow a book |
| POST | `/api/v1/borrows/{id}/return` | Member | Return a book |
| GET | `/api/v1/borrows/me/history` | Member | Personal history |
| GET | `/api/v1/borrows` | Admin | All borrowing records |
| GET | `/health` | Public | Application, DB, and Redis health |
| GET | `/monitoring/data` | Public | Monitoring data for the dashboard |

## Demonstrating Redis Cache-Aside

1. Log in through `/docs` or `/app` and copy the JWT.
2. Request the same book twice:

   ```bash
   curl -i -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:8000/api/v1/books/1
   curl -i -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:8000/api/v1/books/1
   ```

3. Compare the response headers:

   - First request: `X-Cache: MISS`
   - Second request: `X-Cache: HIT`
   - `X-Response-Time-ms` provides the measured request time

4. Update, delete, borrow, or return the book. The next read returns `MISS`, proving invalidation occurred, then later reads return `HIT` again.

Cache hit/miss totals and hit rate also appear at `/monitoring`.

## Logging and Monitoring

Logs use one JSON object per line and are written to the console and `logs/library-api.log`. Recorded events include:

- Request method, route, status code, request ID, and response time
- Login attempts, failures, successful authentication, and token validation failures
- Book CRUD and borrowing/return operations
- Cache hits, misses, failures, and invalidation-related activity
- Database health errors and unhandled exceptions

The dashboard at `/monitoring` refreshes every three seconds and displays:

- Total request count and count by route
- Average and maximum response time
- Error count and error rate
- Recent warning/error log events
- Cache hit rate
- Application, PostgreSQL/SQLite, and Redis health

## Testing

Run the full test suite:

```bash
python -m compileall -q app tests
python -m pytest -q
```

The suite covers authentication, authorization, CRUD, validation, borrowing rules, history access, cache hits, invalidation, health, monitoring, and frontend availability.

## Git Workflow

- `main`: stable submission-ready code
- `develop`: integrated development code
- `feature/*`: isolated feature work

Commits should be focused and traceable. The current project owner and primary backend contributor is Seif Ahmed. Any additional team member must make genuine commits/branches that reflect their real work before submission.

## Security Notes

- Never commit `.env` or real secrets.
- Replace the example `SECRET_KEY` before use.
- Passwords are stored as Argon2 hashes, never as plaintext.
- Login logs never include passwords or JWT values.
- Admin accounts are created through the interactive maintenance command, not public registration.

## Project Status

Core requirements and both optional bonus integrations are implemented. See [DISCUSSION_GUIDE.md](docs/DISCUSSION_GUIDE.md) for a concise walkthrough of the design and likely project discussion questions.
