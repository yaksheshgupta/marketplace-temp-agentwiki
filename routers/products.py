import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from routers.auth import get_current_user
from models.schemas import (
    ProductResponse, ReviewRequest, ReviewResponse,
    PaginatedProducts,
)

router = APIRouter(prefix="/products", tags=["Products"])

# ── Seed data ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


PRODUCTS: dict[str, dict] = {p["product_id"]: p for p in [
    {
        "product_id": "prod-001",
        "name": "Wireless Noise-Cancelling Headphones",
        "description": "Premium over-ear headphones with 30-hour battery life and active noise cancellation. Foldable design for easy portability.",
        "price": 199.99,
        "original_price": 249.99,
        "currency": "USD",
        "category": "electronics",
        "brand": "SoundWave",
        "sku": "SW-ANC-001",
        "stock": 45,
        "rating": 4.6,
        "review_count": 312,
        "images": ["https://example.com/images/headphones-1.jpg", "https://example.com/images/headphones-2.jpg"],
        "tags": ["audio", "wireless", "noise-cancelling"],
        "in_stock": True,
        "created_at": "2025-01-15T10:00:00+00:00",
    },
    {
        "product_id": "prod-002",
        "name": "Mechanical Gaming Keyboard",
        "description": "Tenkeyless mechanical keyboard with Cherry MX Red switches, RGB backlighting, and USB-C detachable cable.",
        "price": 89.99,
        "original_price": 89.99,
        "currency": "USD",
        "category": "electronics",
        "brand": "KeyForge",
        "sku": "KF-MKB-TKL",
        "stock": 120,
        "rating": 4.4,
        "review_count": 178,
        "images": ["https://example.com/images/keyboard-1.jpg"],
        "tags": ["gaming", "keyboard", "mechanical", "rgb"],
        "in_stock": True,
        "created_at": "2025-01-20T08:30:00+00:00",
    },
    {
        "product_id": "prod-003",
        "name": "4K Ultra-Slim Monitor 27\"",
        "description": "27-inch 4K IPS display with 99% sRGB coverage, USB-C 65W power delivery, and height-adjustable stand.",
        "price": 449.00,
        "original_price": 549.00,
        "currency": "USD",
        "category": "electronics",
        "brand": "ViewMax",
        "sku": "VM-4K-27",
        "stock": 18,
        "rating": 4.7,
        "review_count": 95,
        "images": ["https://example.com/images/monitor-1.jpg"],
        "tags": ["monitor", "4k", "usb-c", "ips"],
        "in_stock": True,
        "created_at": "2025-02-01T09:00:00+00:00",
    },
    {
        "product_id": "prod-004",
        "name": "Classic Fit Oxford Shirt",
        "description": "100% cotton Oxford weave shirt with button-down collar. Available in multiple colours. Machine washable.",
        "price": 39.99,
        "original_price": 39.99,
        "currency": "USD",
        "category": "clothing",
        "brand": "DailyWear",
        "sku": "DW-OXF-BLU-M",
        "stock": 200,
        "rating": 4.2,
        "review_count": 540,
        "images": ["https://example.com/images/shirt-1.jpg", "https://example.com/images/shirt-2.jpg"],
        "tags": ["shirt", "cotton", "formal", "casual"],
        "in_stock": True,
        "created_at": "2025-01-05T07:00:00+00:00",
    },
    {
        "product_id": "prod-005",
        "name": "Running Shoes Pro",
        "description": "Lightweight mesh running shoes with responsive foam midsole and reflective heel tab for night visibility.",
        "price": 119.95,
        "original_price": 139.95,
        "currency": "USD",
        "category": "clothing",
        "brand": "StrideTech",
        "sku": "ST-RUN-BLK-10",
        "stock": 75,
        "rating": 4.5,
        "review_count": 290,
        "images": ["https://example.com/images/shoes-1.jpg"],
        "tags": ["shoes", "running", "sports", "lightweight"],
        "in_stock": True,
        "created_at": "2025-01-28T11:00:00+00:00",
    },
    {
        "product_id": "prod-006",
        "name": "The Art of Clean Code",
        "description": "A comprehensive guide to writing readable, maintainable, and testable software. Covers SOLID principles, refactoring, and TDD.",
        "price": 29.99,
        "original_price": 34.99,
        "currency": "USD",
        "category": "books",
        "brand": "TechPress",
        "sku": "TP-BOOK-CLEAN",
        "stock": 500,
        "rating": 4.8,
        "review_count": 1243,
        "images": ["https://example.com/images/book-cleancode.jpg"],
        "tags": ["programming", "software", "best-practices", "refactoring"],
        "in_stock": True,
        "created_at": "2024-11-10T00:00:00+00:00",
    },
    {
        "product_id": "prod-007",
        "name": "Designing Data-Intensive Applications",
        "description": "Deep dive into the principles behind reliable, scalable, and maintainable data systems. Covers databases, streams, and distributed systems.",
        "price": 44.99,
        "original_price": 59.99,
        "currency": "USD",
        "category": "books",
        "brand": "O'Reilly",
        "sku": "OR-BOOK-DDIA",
        "stock": 350,
        "rating": 4.9,
        "review_count": 2876,
        "images": ["https://example.com/images/book-ddia.jpg"],
        "tags": ["databases", "distributed-systems", "architecture", "engineering"],
        "in_stock": True,
        "created_at": "2024-09-01T00:00:00+00:00",
    },
    {
        "product_id": "prod-008",
        "name": "Ergonomic Office Chair",
        "description": "Fully adjustable mesh office chair with lumbar support, 4D armrests, and breathable backrest. Certified for 8-hour use.",
        "price": 349.00,
        "original_price": 399.00,
        "currency": "USD",
        "category": "home",
        "brand": "ErgoSit",
        "sku": "ES-CHAIR-PRO",
        "stock": 30,
        "rating": 4.6,
        "review_count": 187,
        "images": ["https://example.com/images/chair-1.jpg"],
        "tags": ["chair", "ergonomic", "office", "furniture"],
        "in_stock": True,
        "created_at": "2025-02-10T12:00:00+00:00",
    },
    {
        "product_id": "prod-009",
        "name": "Pour-Over Coffee Maker Set",
        "description": "Borosilicate glass pour-over dripper with stainless steel filter, walnut stand, and 600ml carafe. Brew café-quality coffee at home.",
        "price": 54.99,
        "original_price": 54.99,
        "currency": "USD",
        "category": "home",
        "brand": "BrewCraft",
        "sku": "BC-POUR-001",
        "stock": 90,
        "rating": 4.7,
        "review_count": 423,
        "images": ["https://example.com/images/coffee-1.jpg", "https://example.com/images/coffee-2.jpg"],
        "tags": ["coffee", "kitchen", "brewing", "pour-over"],
        "in_stock": True,
        "created_at": "2025-01-12T09:00:00+00:00",
    },
    {
        "product_id": "prod-010",
        "name": "Yoga Mat Premium",
        "description": "6mm thick non-slip TPE yoga mat with alignment lines, carrying strap, and sweat-resistant surface. 183 × 61 cm.",
        "price": 49.95,
        "original_price": 64.95,
        "currency": "USD",
        "category": "sports",
        "brand": "FlexFlow",
        "sku": "FF-YOGA-PRM",
        "stock": 160,
        "rating": 4.5,
        "review_count": 814,
        "images": ["https://example.com/images/yogamat-1.jpg"],
        "tags": ["yoga", "fitness", "mat", "non-slip"],
        "in_stock": True,
        "created_at": "2025-01-08T08:00:00+00:00",
    },
    {
        "product_id": "prod-011",
        "name": "Adjustable Dumbbell Set 5–52 lbs",
        "description": "Dial-select adjustable dumbbells replacing 15 sets of weights. Compact, quick weight change, sold as a pair.",
        "price": 299.00,
        "original_price": 329.00,
        "currency": "USD",
        "category": "sports",
        "brand": "IronEdge",
        "sku": "IE-DUMB-ADJ",
        "stock": 0,
        "rating": 4.8,
        "review_count": 632,
        "images": ["https://example.com/images/dumbbells-1.jpg"],
        "tags": ["weights", "dumbbell", "gym", "strength"],
        "in_stock": False,
        "created_at": "2024-12-20T10:00:00+00:00",
    },
    {
        "product_id": "prod-012",
        "name": "Portable Bluetooth Speaker",
        "description": "IP67 waterproof speaker with 360° sound, 20-hour playtime, and built-in powerbank for charging your phone.",
        "price": 79.99,
        "original_price": 99.99,
        "currency": "USD",
        "category": "electronics",
        "brand": "SoundWave",
        "sku": "SW-BTS-360",
        "stock": 55,
        "rating": 4.3,
        "review_count": 501,
        "images": ["https://example.com/images/speaker-1.jpg"],
        "tags": ["audio", "bluetooth", "waterproof", "portable"],
        "in_stock": True,
        "created_at": "2025-02-05T10:00:00+00:00",
    },
]}

REVIEWS: dict[str, list[dict]] = {pid: [] for pid in PRODUCTS}

CATEGORIES = [
    {"slug": "electronics", "name": "Electronics", "description": "Gadgets, devices, and accessories", "product_count": 4},
    {"slug": "clothing", "name": "Clothing & Footwear", "description": "Apparel and shoes for every occasion", "product_count": 2},
    {"slug": "books", "name": "Books", "description": "Technical and non-fiction titles", "product_count": 2},
    {"slug": "home", "name": "Home & Kitchen", "description": "Furniture, appliances, and cookware", "product_count": 2},
    {"slug": "sports", "name": "Sports & Fitness", "description": "Equipment and gear for an active life", "product_count": 2},
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(p: dict) -> ProductResponse:
    return ProductResponse(**p)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedProducts)
def list_products(
    category: Optional[str] = Query(default=None, description="Filter by category slug"),
    brand: Optional[str] = Query(default=None, description="Filter by brand name"),
    min_price: Optional[float] = Query(default=None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(default=None, ge=0, description="Maximum price"),
    in_stock: Optional[bool] = Query(default=None, description="Only show in-stock items"),
    sort_by: str = Query(default="created_at", pattern="^(price|rating|review_count|created_at|name)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Browse the product catalogue with optional filters, sorting, and pagination.

    **Filters:**
    - `category` — one of `electronics`, `clothing`, `books`, `home`, `sports`
    - `brand` — partial, case-insensitive match
    - `min_price` / `max_price` — price range in USD
    - `in_stock` — `true` to hide out-of-stock items

    **Sorting:** `price`, `rating`, `review_count`, `created_at` (default), `name`

    **Pagination:** `limit` (max 100) and `offset`.
    """
    items = list(PRODUCTS.values())

    if category:
        items = [p for p in items if p["category"] == category.lower()]
    if brand:
        items = [p for p in items if brand.lower() in p["brand"].lower()]
    if min_price is not None:
        items = [p for p in items if p["price"] >= min_price]
    if max_price is not None:
        items = [p for p in items if p["price"] <= max_price]
    if in_stock is not None:
        items = [p for p in items if p["in_stock"] == in_stock]

    reverse = order == "desc"
    items.sort(key=lambda p: p[sort_by], reverse=reverse)

    total = len(items)
    page = items[offset: offset + limit]

    return PaginatedProducts(
        total=total,
        limit=limit,
        offset=offset,
        products=[_to_response(p) for p in page],
    )


@router.get("/search", response_model=PaginatedProducts)
def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Full-text search across product names, descriptions, brands, and tags.

    - Matches are scored by the number of query terms found (most relevant first)
    - Results are paginated via `limit` / `offset`
    """
    terms = q.lower().split()
    scored = []
    for p in PRODUCTS.values():
        haystack = " ".join([
            p["name"], p["description"], p["brand"],
            p["category"], " ".join(p["tags"])
        ]).lower()
        score = sum(1 for t in terms if t in haystack)
        if score:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    items = [p for _, p in scored]
    total = len(items)

    return PaginatedProducts(
        total=total,
        limit=limit,
        offset=offset,
        products=[_to_response(p) for p in items[offset: offset + limit]],
    )


@router.get("/categories")
def list_categories():
    """Return all available product categories with their product counts."""
    return {"categories": CATEGORIES}


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str):
    """
    Retrieve full details for a single product by its ID.

    Returns `404` if the product does not exist.
    """
    p = PRODUCTS.get(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_response(p)


@router.get("/{product_id}/reviews", response_model=list[ReviewResponse])
def get_reviews(
    product_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List customer reviews for a product, newest first.

    Returns `404` if the product does not exist.
    """
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    reviews = list(reversed(REVIEWS[product_id]))
    return [ReviewResponse(**r) for r in reviews[offset: offset + limit]]


@router.post("/{product_id}/reviews", response_model=ReviewResponse, status_code=201)
def add_review(
    product_id: str,
    body: ReviewRequest,
    username: str = Depends(get_current_user),
):
    """
    Submit a review for a product.

    - `rating` must be between 1 and 5
    - `title` and `body` are required
    - Auth required — one review per user per product is allowed

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")

    existing = [r for r in REVIEWS[product_id] if r["username"] == username]
    if existing:
        raise HTTPException(status_code=409, detail="You have already reviewed this product")

    review = {
        "review_id": "rev-" + str(uuid.uuid4())[:8],
        "product_id": product_id,
        "username": username,
        "rating": body.rating,
        "title": body.title,
        "body": body.body,
        "verified_purchase": False,
        "created_at": _now(),
    }
    REVIEWS[product_id].append(review)

    # Update product aggregate rating
    all_ratings = [r["rating"] for r in REVIEWS[product_id]]
    p = PRODUCTS[product_id]
    p["review_count"] = len(all_ratings)
    p["rating"] = round(sum(all_ratings) / len(all_ratings), 1)

    return ReviewResponse(**review)
