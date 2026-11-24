<div align="center">

# 📚 Bookstore API

[![CI](https://github.com/pero-grubac/BookstoreAPI/actions/workflows/ci.yml/badge.svg)](https://github.com/pero-grubac/BookstoreAPI/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.165-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.1-D71F00?logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-FF4438?logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.7-37814A?logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/tests-23_passing-2EA44F?logo=pytest&logoColor=white)

**A REST API for an online bookstore: catalog, JWT accounts, orders that reserve stock, and confirmation emails sent by a background worker.**

<img src="screenshots/demo.gif" alt="Bookstore API demo: logging in through Swagger's Authorize dialog, listing books, placing an order for two books and getting 201, then opening the order confirmation email in Mailpit" width="900">

</div>

---

## 📌 Project Overview

**Bookstore API** is a small, clean FastAPI project built as a portfolio demo. Customers register, browse the catalog and place orders. The API checks and reserves stock in one transaction, answers right away, and leaves the confirmation email to a **Celery worker**. Everything runs with one `docker compose up`: the API, the worker, PostgreSQL, Redis, and Mailpit to catch the emails.

The code is split by feature. Each entity has its own folder with the same four files: `models.py`, `schemas.py`, `service.py` and `router.py`.

| Role | Signs in as | What they do |
|------|-------------|--------------|
| 🛍️ **Customer** | any registered account | Browse authors, books and categories; place orders; see and cancel their own pending orders; edit their profile |
| 🛡️ **Administrator** | `admin@bookstore.dev` | Everything a customer can do, plus managing the catalog, seeing all customers and orders, and moving orders through `pending → paid → shipped` |

Every endpoint except `/auth/register` and `/auth/login` requires a JWT.

---

## 🎬 Use Cases

### 🔎 Explore the API

Swagger UI groups the endpoints by tag. **Authorize** logs in with an email and password, and a padlock marks every endpoint that needs a token.

<img src="screenshots/swagger-overview.png" alt="Swagger UI: title, the Authorize button and the Auth, Authors and Books tags" width="900">

### 🛍️ Customer: browse the catalog

After logging in, `GET /books` returns the catalog with authors and categories. Books can be filtered by author, by category, or by a search in the title. A single book is served from the Redis cache.

<img src="screenshots/swagger-get-books.png" alt="GET /books in Swagger: server response 200 and the JSON list of books" width="900">

### 📧 Customer: place an order and get an email

`POST /orders` takes the prices from the catalog, reserves stock and answers `201` straight away. The confirmation email goes onto the Celery queue. The worker picks it up and sends it, and it shows up in Mailpit a moment later.

<img src="screenshots/mailpit-order-email.png" alt="Mailpit showing the order confirmation email with the ordered books, quantities, prices and total" width="900">

🎬 The full flow is also available as a video: [`screenshots/demo.mp4`](screenshots/demo.mp4) (44 s).

---

## ✨ Features

- 📚 **Catalog**: create, read, update and delete authors, books and categories. Books can be filtered by author, category or title, and a book can have several categories
- 🔐 **JWT authentication**: `POST /auth/register` and `POST /auth/login` use the OAuth2 password flow. Passwords are hashed with Argon2, and the **Authorize** button in Swagger works without any setup
- 🛡️ **Roles**: customers read the catalog and manage their own orders. Admins change the catalog and see everything
- 🧾 **Orders**: prices come from the catalog, never from the client. Stock is checked and reserved while the book rows are locked (`SELECT … FOR UPDATE`), so two orders can't sell the same last copy
- 🔁 **Order statuses**: `pending → paid → shipped`, or `cancelled`. Invalid transitions are rejected, and cancelling returns the books to stock
- 📨 **Background email**: `POST /orders` only queues a task. The Celery worker sends the confirmation (text and HTML) and retries with backoff if SMTP fails
- ⚡ **Caching**: `GET /books/{id}` is cached in Redis and cleared when the book or its stock changes. If Redis is down, the API keeps working without the cache
- ✅ **Validation and clear errors**: Pydantic checks every request (ISBN format, positive prices, quantities). Business errors come back as `404` or `409` with a readable `detail`
- 🌱 **Demo data**: one command seeds 5 authors, 4 categories, 10 books, 3 customers, and 5 orders in different statuses

### 📖 Endpoints

| Tag | Endpoints | Access |
|-----|-----------|--------|
| **Auth** | `POST /auth/register`, `POST /auth/login` | public |
| **Authors** | `GET /authors`, `GET /authors/{id}` | logged in |
| | `POST`, `PATCH`, `DELETE /authors/{id}` | admin |
| **Books** | `GET /books?author_id=&category_id=&search=`, `GET /books/{id}` | logged in |
| | `POST`, `PATCH`, `DELETE /books/{id}` | admin |
| **Categories** | `GET /categories`, `GET /categories/{id}` | logged in |
| | `POST`, `PATCH`, `DELETE /categories/{id}` | admin |
| **Customers** | `GET /customers/me`, `PATCH /customers/me` | logged in |
| | `GET /customers`, `GET /customers/{id}` | admin |
| **Orders** | `POST /orders`, `GET /orders`, `GET /orders/{id}`, `POST /orders/{id}/cancel` | logged in (own orders) |
| | `PATCH /orders/{id}/status` | admin |

`GET /health` reports the database and Redis status. It is left out of Swagger.

---

## 🗄️ Database

PostgreSQL 17, with SQLAlchemy 2.0 models and Alembic migrations in [`alembic/versions/`](alembic/versions/).

| Table | Contains |
|-------|----------|
| `authors` | Name, bio, creation time |
| `categories` | Unique category names |
| `books` | Title, unique ISBN, description, `NUMERIC(10,2)` price, stock, year, author (`RESTRICT` on delete) |
| `book_categories` | Many-to-many link between books and categories (`CASCADE` on delete) |
| `customers` | Unique email, full name, Argon2 password hash, `is_admin` |
| `orders` | Customer, `order_status` enum (`pending`, `paid`, `shipped`, `cancelled`), total, creation time |
| `order_items` | Book, quantity, and the unit price at the time of the order |

Constraint names follow a fixed naming convention, so migrations stay stable. The API container runs the migrations every time it starts.

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

---

## 🛠️ Tech Stack

| Technology | Usage |
|------------|-------|
| Python 3.12 + FastAPI | REST API, dependency injection, OpenAPI and Swagger UI |
| Pydantic v2 + pydantic-settings | Request and response models, configuration from the environment |
| SQLAlchemy 2.0 + psycopg 3 | ORM models and queries on PostgreSQL |
| Alembic | Database migrations |
| PostgreSQL 17 | Data |
| Redis 7 | Book cache and Celery broker (separate databases) |
| Celery 5 | Background worker for the confirmation emails |
| Mailpit | SMTP server and web UI for emails in development |
| PyJWT + pwdlib (Argon2) | Tokens and password hashing |
| Docker Compose | API, worker, PostgreSQL, Redis and Mailpit in one command |
| pytest + httpx | Unit and API tests |
| Playwright + ffmpeg | Screenshots and the demo video |
| black, isort, flake8, pre-commit | Formatting and linting |
| GitHub Actions | CI (lint, tests, Docker smoke test) and releases |

---

## 📁 Repository Structure

```
BookstoreAPI/
├── app/
│   ├── core/                     config, database, security (JWT, Argon2), cache, email, errors, pagination
│   ├── features/
│   │   ├── auth/                 /auth/register, /auth/login, current-user dependencies
│   │   ├── authors/              models.py · schemas.py · service.py · router.py
│   │   ├── books/
│   │   ├── categories/
│   │   ├── customers/
│   │   └── orders/               + tasks.py: the confirmation email (Celery task)
│   ├── models.py                 imports every model (used by Alembic)
│   ├── seed.py                   demo accounts, catalog and orders
│   ├── worker.py                 Celery app
│   └── main.py                   FastAPI app, tags, routers, /health
├── alembic/                      migrations
├── tests/                        pytest suite (SQLite in memory, no Docker needed)
├── scripts/
│   ├── smoke_test.sh             end-to-end check of the Docker stack (used by CI)
│   ├── take_screenshots.py       Playwright screenshots
│   └── record_demo.py            Playwright demo video → MP4 + GIF
├── screenshots/                  images and the demo video used in this README
├── Dockerfile                    one image for both the API and the worker
├── docker-compose.yml            api, worker, db, redis, mailpit
└── .github/workflows/ci.yml      CI/CD
```

---

## 🚀 Setup & Run

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.12 (only for running the tests, or the API outside Docker)

### 1. Clone the repository
```bash
git clone https://github.com/pero-grubac/BookstoreAPI.git
cd BookstoreAPI
```

### 2. Start everything
```bash
docker compose up --build -d
docker compose exec api python -m app.seed
```

<img src="screenshots/docker-compose-ps.png" alt="docker compose ps: api, db, mailpit, redis and worker all up" width="700">

| Service | What it does | URL |
|---------|--------------|-----|
| `api` | FastAPI app; runs the migrations on start | http://localhost:8000/docs |
| `worker` | Celery worker (same image as `api`) that sends the emails | `docker compose logs -f worker` |
| `db` | PostgreSQL | `localhost:5432` |
| `redis` | Cache and Celery broker | `localhost:6379` |
| `mailpit` | Catches every outgoing email | http://localhost:8025 |

### 3. Try it
1. Open **http://localhost:8000/docs** and click **Authorize**. Enter the email as *username*, plus the password.
2. Place an order with `POST /orders`:
   ```json
   { "items": [{ "book_id": 1, "quantity": 2 }] }
   ```
3. Open **http://localhost:8025**. The confirmation email is there within a second or two.

### 🔑 Demo accounts

| Role | Email | Password |
|------|-------|----------|
| Administrator | `admin@bookstore.dev` | `admin12345` |
| Customer | `ana.petrovic@example.com` | `password123` |
| Customer | `marko.jovanovic@example.com` | `password123` |
| Customer | `jelena.nikolic@example.com` | `password123` |

### ⚙️ Configuration

Each setting is taken from the first of these that has it: an environment variable, the git-ignored `.env` file (copy [`.env.example`](.env.example)), or the default in [`app/core/config.py`](app/core/config.py). Docker Compose sets the container hostnames itself.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+psycopg://bookstore:bookstore@localhost:5432/bookstore` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache; leave empty to disable caching |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker |
| `SMTP_HOST`, `SMTP_PORT` | `localhost`, `1025` | Where the worker sends email (Mailpit) |
| `MAIL_FROM` | `Bookstore <orders@bookstore.dev>` | Sender of the emails |
| `SECRET_KEY` | `change-me` | JWT signing key; **set your own** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `CACHE_TTL_SECONDS` | `60` | How long a book stays cached |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | `admin@bookstore.dev`, `admin12345` | Admin account created by the seed |

### 💻 Run the API and worker outside Docker

```bash
docker compose up -d db redis mailpit

python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows (source .venv/bin/activate on Linux/macOS)
pip install -r requirements-dev.txt
cp .env.example .env                # then set SECRET_KEY

alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

In a second terminal, start the worker:

```bash
celery -A app.worker:celery_app worker --loglevel=info
# Windows: add --pool=solo (Celery's default process pool doesn't run on Windows)
```

Orders still work without a running worker. Their emails wait in Redis and go out once a worker starts.

### Reset the demo data
```bash
docker compose down -v
docker compose up -d
docker compose exec api python -m app.seed
```

---

## 🧪 Tests

```bash
# unit and API tests (no Docker needed)
pytest

# end-to-end check of the running Docker stack
bash scripts/smoke_test.sh

# formatting and linting
black . && isort . && flake8
pre-commit install   # run them on every commit
```

| Suite | Tests | What it covers |
|-------|------:|----------------|
| Auth | 5 | Register and read the profile, duplicate email, wrong password, missing or invalid token, customers can't list customers |
| Catalog | 10 | Login required, a book with its author and categories, customers can't change the catalog, filters, duplicate ISBN, partial updates, required fields can't be set to null, an author with books can't be deleted, `PATCH` for categories, `404` |
| Orders | 5 | Stock reserved and total computed, an order that is out of stock leaves stock unchanged, cancelling returns stock, status flow enforced, customers only see their own orders |
| Order emails | 3 | `POST /orders` queues the task with the order id; the task, run eagerly with `apply()`, sends the right email to a mocked SMTP server; a missing order sends nothing |
| Smoke test | – | On the real stack: health, `alembic check` on PostgreSQL, seed, `401` without a token, login, books, a new order, and its email arriving in Mailpit through the worker |

The unit tests run on SQLite in memory, with Redis disabled and the Celery queue mocked, so they need no services. The smoke test covers everything those mocks replace.

### Screenshots and the demo video

With the stack running and seeded:

```bash
playwright install chromium
python scripts/take_screenshots.py   # 1000x750 at 2x scale
python scripts/record_demo.py        # 1280x720 MP4 + GIF, needs ffmpeg on PATH
```

Both scripts place a real order as the demo customer.

---

## ⚙️ CI/CD

[`ci.yml`](.github/workflows/ci.yml) runs on pushes and pull requests to `main`, **but only when something that affects the build changes**: Python code, requirements, lint config, migrations, scripts, the Dockerfile, `docker-compose.yml`, or the workflow itself. README edits and screenshots do not start a run. It can also be started by hand.

| Job | Runner | Steps |
|-----|--------|-------|
| **Lint & unit tests** | `ubuntu-latest` | black, isort and flake8 checks, pytest, test report as an artifact |
| **Docker stack smoke test** | `ubuntu-latest` | `docker compose up --build`, then [`smoke_test.sh`](scripts/smoke_test.sh): migrations, seed, login, an order, and the worker's email in Mailpit. Prints the service logs on failure |
| **Release** | `ubuntu-latest` | Only for tags `v*`, after both jobs pass: builds the image, pushes it to GitHub Container Registry (`ghcr.io`), and creates a GitHub release with generated notes |

A newer push to the same branch cancels the run still in progress.

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## 🏗️ Architecture

```mermaid
flowchart LR
    CLIENT[Client<br/>Swagger UI · curl]
    subgraph API["api (FastAPI)"]
        R[Routers<br/>HTTP only]
        S[Services<br/>business rules]
        D[Dependencies<br/>JWT · roles · DB session]
    end
    subgraph WORKER["worker (Celery)"]
        T[send_order_confirmation]
    end
    PG[(PostgreSQL)]
    subgraph REDIS["Redis"]
        C[(db 0: cache)]
        Q[(db 1: task queue)]
    end
    MAIL[Mailpit<br/>SMTP · web UI]

    CLIENT --> R
    R --> D
    R --> S
    S --> PG
    S <-.-> C
    R -- "delay(order_id)" --> Q
    Q --> T
    T --> PG
    T -- SMTP --> MAIL
```

Routers only deal with HTTP: they read the request, call a service and return the result. Services hold the rules and the queries. They raise `NotFoundError` or `ConflictError`, and a single handler turns those into `404` or `409`. The worker uses the same models and database as the API.

### Data model

```mermaid
erDiagram
    AUTHORS ||--o{ BOOKS : writes
    BOOKS }o--o{ CATEGORIES : "book_categories"
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains
    BOOKS ||--o{ ORDER_ITEMS : "ordered as"

    AUTHORS {
        int id PK
        varchar name
        text bio
        timestamptz created_at
    }
    BOOKS {
        int id PK
        varchar title
        varchar isbn "unique"
        numeric price
        int stock
        int published_year
        int author_id FK
    }
    CATEGORIES {
        int id PK
        varchar name "unique"
    }
    CUSTOMERS {
        int id PK
        varchar email "unique"
        varchar full_name
        varchar hashed_password "Argon2"
        bool is_admin
    }
    ORDERS {
        int id PK
        int customer_id FK
        enum status "pending, paid, shipped, cancelled"
        numeric total
        timestamptz created_at
    }
    ORDER_ITEMS {
        int id PK
        int order_id FK
        int book_id FK
        int quantity
        numeric unit_price "price at order time"
    }
```

### Placing an order

```mermaid
sequenceDiagram
    autonumber
    actor C as Customer
    participant API as POST /orders
    participant S as orders.service
    participant DB as PostgreSQL
    participant R as Redis
    participant W as Celery worker
    participant M as Mailpit

    C->>API: items [{book_id, quantity}], Bearer token
    API->>S: create_order(customer, items)
    S->>DB: SELECT books … FOR UPDATE
    alt not enough stock
        S-->>API: ConflictError
        API-->>C: 409 "Not enough stock for …"
    end
    S->>DB: stock − quantity, INSERT order + items, COMMIT
    S->>R: clear cached books
    API->>R: send_order_confirmation.delay(order_id)
    API-->>C: 201 order
    R-->>W: task
    W->>DB: load order, items, customer
    W->>M: SMTP: "Order #… confirmed"
```

---

## 🧭 Design Decisions

- **One folder per feature, four files each.** `models`, `schemas`, `service` and `router`, with no repository layer or other abstractions on top. Things are easy to find, and a new feature is easy to add.
- **Services raise domain errors, not HTTP errors.** `NotFoundError` and `ConflictError` are mapped to `404` and `409` in one place, so the business rules don't depend on FastAPI.
- **The server decides prices and stock.** The client only sends book ids and quantities. Rows are locked during the order, so orders placed at the same time can't oversell.
- **Money is `NUMERIC(10,2)` and `Decimal`.** There are no floating-point totals, and JSON returns prices as strings (`"14.90"`).
- **Email never slows down or breaks an order.** The API only queues the task. If Redis is unreachable, the order is still saved and the error is logged. The worker retries SMTP failures with backoff.
- **The cache is best-effort.** If Redis fails, the API stops using the cache for a short while and reads from PostgreSQL.
- **Partial updates use `PATCH`.** Fields you leave out stay the same, and required fields can't be set to `null`.
- **Login uses the OAuth2 form.** That is what lets Swagger's **Authorize** button work without extra setup.
- **Configuration is not code.** Everything comes from environment variables or a git-ignored `.env`. The committed defaults only point at the local Docker services.
- **Fast tests locally, the real stack in CI.** The unit tests need nothing but Python. The smoke test runs the same `docker-compose.yml` you use and checks the whole path, including the worker and the email.
- **CI only runs when it matters.** Path filters keep README and screenshot edits from using runner minutes.
