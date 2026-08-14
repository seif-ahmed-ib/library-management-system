# Project Discussion Guide

Use this guide to explain the project in your own words. Do not memorize sentences without understanding the request flow.

## 1. What does the project do?

It is a Library Management System API. An admin manages books and sees every borrowing record. A member registers, logs in, borrows available books, returns them, and sees only their own history. The system protects invalid states such as borrowing an unavailable book, borrowing the same book twice, or holding more than three active books.

## 2. Explain the request flow

1. A client sends an HTTP request.
2. Request middleware starts a timer and creates a request ID.
3. FastAPI validates inputs with a Pydantic schema.
4. JWT dependencies identify the user and check the required role.
5. The route calls a service.
6. The service enforces business rules and uses SQLAlchemy to access the database.
7. Book GET requests first check Redis; a cache miss reads the database and stores the result.
8. Middleware records the status code, response time, metrics, and a structured log.

## 3. JWT authentication

- Registration hashes the password with Argon2. Plain passwords are never stored.
- Login verifies the hash and creates a signed JWT.
- The token contains the user ID in `sub` and an expiration time in `exp`.
- Protected endpoints read `Authorization: Bearer <token>`, validate the signature and expiration, then load the user.
- A valid token proves integrity and identity; it does not encrypt its payload.

Likely question: Why is `SECRET_KEY` important?

Answer: It signs and verifies tokens. If it leaks, an attacker could create valid tokens. It belongs in `.env`, never Git.

## 4. Role-based authorization

- `require_admin` allows only the admin role.
- `require_member` allows only the member role.
- Admin endpoints: create, update, delete books and view all borrowing records.
- Member endpoints: borrow, return, and personal history.
- Authentication answers "who are you?" Authorization answers "what may you do?"

## 5. Database design

- `users`: identity, password hash, role, and active status.
- `books`: title, author, ISBN, total copies, and available copies.
- `borrow_records`: user ID, book ID, borrow time, and optional return time.
- Foreign keys connect each borrow record to one user and one book.
- A `NULL returned_at` means the borrow is still active.
- ISBN is unique. Check constraints keep copy counts valid.

Likely question: Why keep borrowing history instead of deleting a record on return?

Answer: Setting `returned_at` preserves the full audit/history while clearly distinguishing active and completed borrowing.

## 6. Borrow transaction and rules

The service locks the relevant rows, checks the user and book, checks availability, checks duplicate active borrowing, and counts active books. If all checks pass, it creates a record and decreases `available_copies` in the same commit. Returning sets `returned_at` and increases availability.

Likely question: Why use `with_for_update()`?

Answer: It prevents concurrent requests from reading and changing the same availability state at the same time on databases such as PostgreSQL.

## 7. Redis Cache-Aside

Cache-Aside works as follows:

1. The application asks Redis for the book key.
2. `HIT`: return the cached JSON.
3. `MISS`: query the database, return the result, and store the JSON in Redis with a TTL.
4. Create/update/delete invalidates list keys; update/delete also invalidates the individual item.
5. Borrow/return also invalidate the book because availability changed.
6. If Redis is unavailable, the API uses the database and returns `X-Cache: BYPASS`.

Likely question: Why is invalidation essential?

Answer: Without it, users could see stale titles, deleted books, or incorrect availability until the TTL expires.

## 8. Logging and monitoring

- Logs are structured JSON, so machines and dashboards can parse fields reliably.
- DEBUG records cache detail; INFO records normal success; WARNING records rejected authentication or 4xx responses; ERROR records failures; CRITICAL records an application startup failure.
- Middleware records method, route, status, request ID, and duration.
- `/monitoring` shows request count, average/max response time, error rate, cache hit rate, recent errors, and component health.
- `/health` checks the application, database, and Redis.

## 9. Validation and error handling

- Pydantic rejects invalid request bodies with 422.
- Missing data returns 404.
- Duplicate ISBN or invalid state transitions return 409.
- Missing/invalid authentication returns 401.
- Insufficient role or returning another member's book returns 403.
- Services raise domain errors; routes translate them into HTTP responses.

## 10. Testing

The tests use Pytest, FastAPI TestClient, an isolated SQLite database, and a Redis-compatible fake for deterministic cache tests. They cover happy paths, missing authentication, incorrect roles, duplicates, missing resources, borrowing limits, cache hit/miss, invalidation, health, monitoring, and the frontend route.

Likely question: Why use SQLite in tests if production uses PostgreSQL?

Answer: It makes unit/API tests fast and isolated. PostgreSQL behavior is exercised by the Docker stack; row locking is specifically effective there.

## 11. Docker

Docker Compose runs three services:

- `app`: FastAPI/Uvicorn
- `database`: PostgreSQL with persistent storage
- `redis`: Redis with persistent storage

Health checks ensure the app waits until PostgreSQL and Redis are ready. Environment variables point the app to service names inside the Compose network.

## 12. Demonstration order

1. Open `/health` and `/monitoring`.
2. Register a member and log in.
3. Show that the member cannot create a book.
4. Log in as admin and create/update a book.
5. Read the same book twice and show `MISS`, then `HIT` and response timings.
6. Borrow it as a member; show availability decreased and the next read is a cache `MISS`.
7. Show personal history, return the book, and show availability restored.
8. Show that the admin can see all borrowing records.
9. Open the monitoring dashboard and the JSON log file.
10. From the `backend` folder, run `python -m pytest -q` and show every test passing.
