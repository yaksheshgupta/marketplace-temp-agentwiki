import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from routers.auth import get_current_user
from routers.products import PRODUCTS
from routers.cart import CARTS, _get_cart
from models.schemas import OrderResponse, OrderSummaryResponse

router = APIRouter(prefix="/orders", tags=["Orders"])

ORDERS: dict[str, dict] = {}  # order_id -> order


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_order_response(order: dict) -> OrderResponse:
    return OrderResponse(**order)


@router.post("/checkout", response_model=OrderResponse, status_code=201)
def checkout(username: str = Depends(get_current_user)):
    """
    Place an order for everything currently in the cart.

    - Validates stock for all items before committing
    - Deducts stock from each product
    - Clears the cart on success
    - Returns the created order with a unique `ORD-` prefixed ID

    Returns `400` if the cart is empty or any item is out of stock.

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    cart = _get_cart(username)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Validate all items first
    line_items = []
    for product_id, entry in cart.items():
        p = PRODUCTS.get(product_id)
        if not p:
            raise HTTPException(status_code=400, detail=f"Product {product_id} no longer exists")
        if not p["in_stock"] or p["stock"] < entry["quantity"]:
            raise HTTPException(
                status_code=400,
                detail=f"'{p['name']}' only has {p['stock']} units in stock (requested {entry['quantity']})"
            )
        line_items.append({
            "product_id": product_id,
            "name": p["name"],
            "brand": p["brand"],
            "sku": p["sku"],
            "quantity": entry["quantity"],
            "unit_price": p["price"],
            "line_total": round(p["price"] * entry["quantity"], 2),
        })

    # Commit: deduct stock
    for item in line_items:
        p = PRODUCTS[item["product_id"]]
        p["stock"] -= item["quantity"]
        if p["stock"] == 0:
            p["in_stock"] = False

    subtotal = round(sum(i["line_total"] for i in line_items), 2)
    tax = round(subtotal * 0.08, 2)
    shipping = 0.00 if subtotal >= 50 else 4.99
    total = round(subtotal + tax + shipping, 2)

    order_id = "ORD-" + str(uuid.uuid4()).upper()[:10]
    order = {
        "order_id": order_id,
        "username": username,
        "status": "confirmed",
        "items": line_items,
        "item_count": len(line_items),
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "currency": "USD",
        "shipping_address": None,
        "estimated_delivery": None,
        "placed_at": _now(),
        "updated_at": _now(),
    }
    ORDERS[order_id] = order

    # Clear cart
    CARTS[username] = {}

    return _build_order_response(order)


@router.get("", response_model=list[OrderSummaryResponse])
def list_orders(
    status: str = Query(default=None, description="Filter by status: confirmed, shipped, delivered, cancelled"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    username: str = Depends(get_current_user),
):
    """
    List all orders placed by the authenticated user, newest first.

    **Filters:** `status` — `confirmed`, `shipped`, `delivered`, `cancelled`

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    orders = [o for o in ORDERS.values() if o["username"] == username]
    if status:
        orders = [o for o in orders if o["status"] == status]

    orders.sort(key=lambda o: o["placed_at"], reverse=True)
    page = orders[offset: offset + limit]

    return [
        OrderSummaryResponse(
            order_id=o["order_id"],
            status=o["status"],
            item_count=o["item_count"],
            total=o["total"],
            currency=o["currency"],
            placed_at=o["placed_at"],
        )
        for o in page
    ]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, username: str = Depends(get_current_user)):
    """
    Retrieve full details for a specific order.

    Returns `404` if the order does not exist or does not belong to the authenticated user.

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    order = ORDERS.get(order_id)
    if not order or order["username"] != username:
        raise HTTPException(status_code=404, detail="Order not found")
    return _build_order_response(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: str, username: str = Depends(get_current_user)):
    """
    Cancel a confirmed order.

    - Only orders with status `confirmed` can be cancelled
    - Restores stock for all items in the order
    - Returns `409` if the order is already shipped, delivered, or cancelled

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    order = ORDERS.get(order_id)
    if not order or order["username"] != username:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] != "confirmed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel an order with status '{order['status']}'"
        )

    # Restore stock
    for item in order["items"]:
        p = PRODUCTS.get(item["product_id"])
        if p:
            p["stock"] += item["quantity"]
            p["in_stock"] = True

    order["status"] = "cancelled"
    order["updated_at"] = _now()
    return _build_order_response(order)
