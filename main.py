from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth
from routers import products, cart, orders

app = FastAPI(
    title="Dummy Marketplace API",
    description="""
## Dummy Marketplace API

A realistic e-commerce API you can explore, test against, and build integrations with.

### Auth Methods
- **JWT Bearer Token** — obtained via `/auth/login`
- **API Key** — pass as `X-API-Key` header, generated via `/auth/api-key/generate`

Endpoints marked with a lock icon require one of the above.

### Modules
| Module | Prefix | Auth |
|---|---|---|
| Auth | `/auth` | — |
| Products | `/products` | Public (reviews need auth) |
| Cart | `/cart` | Required |
| Orders | `/orders` | Required |
    """,
    version="2.0.0",
    contact={"name": "Dummy Marketplace", "email": "admin@example.com"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to the Dummy Marketplace API",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi_json": "/openapi.json",
        "version": "2.0.0",
        "routes": {
            "auth": "/auth — register, login, JWT tokens, API keys",
            "products": "/products — browse, search, filter, reviews",
            "categories": "/products/categories — list all categories",
            "cart": "/cart — add/update/remove items, view totals",
            "orders": "/orders — checkout, order history, cancel",
        },
    }


@app.get("/health", tags=["Root"])
def health():
    return {"status": "ok"}
