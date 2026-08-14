# LibraDesk — Library Management System

LibraDesk is a complete Library Management System built for the DSC 306 R and Python Programming Language course. The project combines a production-style FastAPI backend with a polished, responsive frontend and realistic demo data.

## Highlights

- JWT registration and login with Admin and Member roles
- Full book CRUD with validation and correct HTTP responses
- Borrow, return, availability tracking, and borrowing history
- Maximum active-borrow limit and duplicate-borrow protection
- Redis Cache-Aside with hit, miss, bypass, and invalidation behavior
- Structured JSON logging and a live monitoring dashboard
- Responsive dashboard with search, filters, modals, toasts, and role-aware actions
- PostgreSQL support, Docker Compose, and an isolated Pytest suite
- Idempotent seed command for a realistic presentation database

## Project Structure

```text
library-management-system/
├── backend/
│   ├── app/
│   │   ├── api/v1/routes/   # FastAPI endpoints
│   │   ├── auth/            # JWT and role dependencies
│   │   ├── cache/           # Redis Cache-Aside
│   │   ├── core/            # Settings, security, and logging
│   │   ├── db/              # SQLAlchemy engine and sessions
│   │   ├── frontend/        # Route that serves the separate frontend
│   │   ├── middleware/      # Request logging and metrics
│   │   ├── models/          # SQLAlchemy entities
│   │   ├── monitoring/      # Metrics and monitoring dashboard
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── scripts/         # Admin and demo-data commands
│   │   └── services/        # Business rules
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   └── assets/
│       ├── css/styles.css
│       └── js/              # API, auth, catalog, circulation, and UI modules
├── docs/
├── docker-compose.yml
└── .env.example
```

The request flow is:

```text
Frontend -> FastAPI route -> authentication/authorization -> service -> SQLAlchemy -> PostgreSQL
                                                     |-> Redis Cache-Aside for book reads
Every request -> logging middleware -> JSON logs + monitoring metrics
```

## Local Setup on Windows

From the project root:

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
copy .env.example .env
```

Keep the PostgreSQL `DATABASE_URL` already configured in your `.env`. Redis can be temporarily unavailable; the application will safely fall back to PostgreSQL and report `X-Cache: BYPASS`.

Create an Admin if one does not already exist:

```cmd
cd backend
python -m app.scripts.create_admin --name "Seif Ahmed" --email admin@library.com
```

Add realistic demo data without deleting anything already in PostgreSQL:

```cmd
python -m app.scripts.seed_demo
```

The seed adds 15 titles, three members, and nine mixed borrowing records. Demo members use the password `Member123!`.

Start the application:

```cmd
python -m uvicorn app.main:app --reload
```

Open:

- Frontend: <http://127.0.0.1:8000/app>
- Swagger: <http://127.0.0.1:8000/docs>
- Monitoring: <http://127.0.0.1:8000/monitoring>
- Health: <http://127.0.0.1:8000/health>

## Docker Setup

From the project root:

```cmd
docker compose up --build -d
docker compose exec app python -m app.scripts.seed_demo
```

Docker starts FastAPI, PostgreSQL, and Redis together. Stop without deleting data using:

```cmd
docker compose down
```

## Main API Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Public | Register a member |
| POST | `/api/v1/auth/login` | Public | Receive a JWT |
| GET | `/api/v1/auth/me` | Authenticated | Read the current user |
| GET | `/api/v1/books` | Authenticated | List books with caching |
| GET | `/api/v1/books/{id}` | Authenticated | Read one cached book |
| POST | `/api/v1/books` | Admin | Create a book |
| PUT | `/api/v1/books/{id}` | Admin | Update a book |
| DELETE | `/api/v1/books/{id}` | Admin | Delete a book |
| POST | `/api/v1/borrows` | Member | Borrow a book |
| POST | `/api/v1/borrows/{id}/return` | Member | Return a book |
| GET | `/api/v1/borrows/me/history` | Member | Personal history |
| GET | `/api/v1/borrows` | Admin | All borrowing records |
| GET | `/health` | Public | Application, database, and Redis health |
| GET | `/monitoring/data` | Public | Monitoring dashboard data |

## Testing

Run from the `backend` folder:

```cmd
python -m compileall -q app tests
python -m pytest -q
```

The tests cover authentication, roles, CRUD, validation, borrowing rules, cache behavior, health, monitoring, the frontend page, and its static assets.

## Redis Demonstration

Request the same book twice through Swagger or curl. The first response returns `X-Cache: MISS`, and the second returns `X-Cache: HIT`. After a create, update, delete, borrow, or return operation, the next book read returns `MISS` again, proving cache invalidation.

## Git Workflow

- `main`: stable submission-ready code
- `develop`: integrated development code
- `feature/*`: isolated work such as `feature/frontend-redesign`

Never commit `.env`, database files, log files, or the virtual environment. Additional team members should contribute genuine work through their own branches and commits.

See [DISCUSSION_GUIDE.md](docs/DISCUSSION_GUIDE.md) for a presentation walkthrough and likely discussion questions.
