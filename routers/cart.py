from fastapi import APIRouter, Depends, HTTPException

from routers.auth import get_current_user
from routers.products import PRODUCTS
from models.schemas import CartResponse, AddToCartRequest, UpdateCartItemRequest

router = APIRouter(prefix="/cart", tags=["Cart"])

# user -> {product_id: {quantity, ...}}
CARTS: dict[str, dict[str, dict]] = {}


def _get_cart(username: str) -> dict[str, dict]:
    return CARTS.setdefault(username, {})


def _build_response(username: str) -> CartResponse:
    cart = _get_cart(username)
    items = []
    subtotal = 0.0

    for product_id, entry in cart.items():
        p = PRODUCTS.get(product_id)
        if not p:
            continue
        line_total = round(p["price"] * entry["quantity"], 2)
        subtotal += line_total
        items.append({
            "product_id": product_id,
            "name": p["name"],
            "brand": p["brand"],
            "price": p["price"],
            "quantity": entry["quantity"],
            "line_total": line_total,
            "in_stock": p["in_stock"],
            "stock_available": p["stock"],
        })

    subtotal = round(subtotal, 2)
    tax = round(subtotal * 0.08, 2)  # 8% tax
    return CartResponse(
        username=username,
        item_count=len(items),
        items=items,
        subtotal=subtotal,
        tax=tax,
        total=round(subtotal + tax, 2),
        currency="USD",
    )


@router.get("", response_model=CartResponse)
def view_cart(username: str = Depends(get_current_user)):
    """
    Return the current user's cart including line items, subtotal, tax (8%), and total.

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    return _build_response(username)


@router.post("/items", response_model=CartResponse, status_code=201)
def add_to_cart(body: AddToCartRequest, username: str = Depends(get_current_user)):
    """
    Add a product to the cart or increase its quantity if already present.

    - Returns `404` if the product does not exist
    - Returns `400` if the requested quantity exceeds available stock
    - Returns the updated cart

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    p = PRODUCTS.get(body.product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    if not p["in_stock"] or p["stock"] == 0:
        raise HTTPException(status_code=400, detail="Product is out of stock")

    cart = _get_cart(username)
    current_qty = cart.get(body.product_id, {}).get("quantity", 0)
    new_qty = current_qty + body.quantity

    if new_qty > p["stock"]:
        raise HTTPException(
            status_code=400,
            detail=f"Only {p['stock']} units available (you already have {current_qty} in cart)"
        )

    cart[body.product_id] = {"quantity": new_qty}
    return _build_response(username)


@router.patch("/items/{product_id}", response_model=CartResponse)
def update_cart_item(
    product_id: str,
    body: UpdateCartItemRequest,
    username: str = Depends(get_current_user),
):
    """
    Set the quantity of a cart item to an exact value.

    - Use `quantity: 0` to remove the item (equivalent to DELETE)
    - Returns `404` if the item is not in the cart
    - Returns `400` if quantity exceeds available stock

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    cart = _get_cart(username)
    if product_id not in cart:
        raise HTTPException(status_code=404, detail="Item not in cart")

    if body.quantity == 0:
        del cart[product_id]
        return _build_response(username)

    p = PRODUCTS.get(product_id)
    if p and body.quantity > p["stock"]:
        raise HTTPException(status_code=400, detail=f"Only {p['stock']} units available")

    cart[product_id]["quantity"] = body.quantity
    return _build_response(username)


@router.delete("/items/{product_id}", response_model=CartResponse)
def remove_from_cart(product_id: str, username: str = Depends(get_current_user)):
    """
    Remove a specific product from the cart entirely.

    Returns `404` if the item is not currently in the cart.

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    cart = _get_cart(username)
    if product_id not in cart:
        raise HTTPException(status_code=404, detail="Item not in cart")
    del cart[product_id]
    return _build_response(username)


@router.delete("", status_code=204)
def clear_cart(username: str = Depends(get_current_user)):
    """
    Remove all items from the cart.

    Returns 204 No Content.

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    CARTS[username] = {}
