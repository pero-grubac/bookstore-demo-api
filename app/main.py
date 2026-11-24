from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401  (registers all models)
from app.core import cache
from app.core.config import settings
from app.core.database import DbSession
from app.core.exceptions import AppError, app_error_handler
from app.features.auth.router import router as auth_router
from app.features.authors.router import router as authors_router
from app.features.books.router import router as books_router
from app.features.categories.router import router as categories_router
from app.features.customers.router import router as customers_router
from app.features.orders.router import router as orders_router

DESCRIPTION = """
A small demo REST API for an online bookstore.

**How to try it:** register via `POST /auth/register` (or use a seeded account),
then click **Authorize** and log in with your email and password.
All endpoints except `/auth` require a token; changing the catalog requires an
admin account.
"""

TAGS_METADATA = [
    {"name": "Auth", "description": "Registration and JWT login."},
    {"name": "Authors", "description": "Book authors."},
    {"name": "Books", "description": "The book catalog (details cached in Redis)."},
    {"name": "Categories", "description": "Book genres / categories."},
    {"name": "Customers", "description": "Customer profiles."},
    {"name": "Orders", "description": "Placing and managing orders."},
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    swagger_ui_parameters={"persistAuthorization": True},
)
app.add_exception_handler(AppError, app_error_handler)

for router in (
    auth_router,
    authors_router,
    books_router,
    categories_router,
    customers_router,
    orders_router,
):
    app.include_router(router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health", include_in_schema=False)
def health(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "unavailable"
    return {
        "status": "ok",
        "database": database,
        "redis": "ok" if cache.ping() else "unavailable",
    }
