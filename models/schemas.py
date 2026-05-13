from typing import Optional, Any
from pydantic import BaseModel, Field


# --- Auth ---
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str
    email: str


class ApiKeyResponse(BaseModel):
    api_key: str
    message: str = "Store this key safely — it won't be shown again."


# --- Math ---
class TwoNumberInput(BaseModel):
    a: float
    b: float


class NumberListInput(BaseModel):
    numbers: list[float] = Field(..., min_length=1)


class StatsResponse(BaseModel):
    mean: float
    median: float
    mode: Optional[float]
    std_dev: float
    min: float
    max: float


# --- Utils ---
class TextInput(BaseModel):
    text: str


class HashRequest(BaseModel):
    text: str
    algorithm: str = Field(default="sha256", pattern="^(md5|sha1|sha256|sha512)$")


class RandomStringRequest(BaseModel):
    length: int = Field(default=16, ge=1, le=256)
    include_symbols: bool = False


class RandomNumberRequest(BaseModel):
    min: float = 0
    max: float = 100


# --- Finance ---
class CreateAccountRequest(BaseModel):
    owner_name: str = Field(..., min_length=2, max_length=100)
    account_type: str = Field(default="checking", pattern="^(checking|savings|business)$")
    initial_deposit: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")


class AccountResponse(BaseModel):
    account_id: str
    account_number: str
    owner_name: str
    account_type: str
    balance: float
    currency: str
    created_at: str
    status: str


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description: str = Field(default="Deposit")


class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description: str = Field(default="Withdrawal")


class TransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: float = Field(..., gt=0)
    description: str = Field(default="Transfer")


class TransactionResponse(BaseModel):
    transaction_id: str
    account_id: str
    type: str
    amount: float
    balance_after: float
    description: str
    currency: str
    timestamp: str
    status: str


# --- Marketplace: Products ---

class ProductResponse(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    original_price: float
    currency: str
    category: str
    brand: str
    sku: str
    stock: int
    rating: float
    review_count: int
    images: list[str]
    tags: list[str]
    in_stock: bool
    created_at: str


class PaginatedProducts(BaseModel):
    total: int
    limit: int
    offset: int
    products: list[ProductResponse]


class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: str = Field(..., min_length=3, max_length=120)
    body: str = Field(..., min_length=10, max_length=2000)


class ReviewResponse(BaseModel):
    review_id: str
    product_id: str
    username: str
    rating: int
    title: str
    body: str
    verified_purchase: bool
    created_at: str


# --- Marketplace: Cart ---

class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=99)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=0, le=99)


class CartItemResponse(BaseModel):
    product_id: str
    name: str
    brand: str
    price: float
    quantity: int
    line_total: float
    in_stock: bool
    stock_available: int


class CartResponse(BaseModel):
    username: str
    item_count: int
    items: list[CartItemResponse]
    subtotal: float
    tax: float
    total: float
    currency: str


# --- Marketplace: Orders ---

class OrderLineItem(BaseModel):
    product_id: str
    name: str
    brand: str
    sku: str
    quantity: int
    unit_price: float
    line_total: float


class OrderResponse(BaseModel):
    order_id: str
    username: str
    status: str
    items: list[OrderLineItem]
    item_count: int
    subtotal: float
    tax: float
    shipping: float
    total: float
    currency: str
    shipping_address: Optional[Any]
    estimated_delivery: Optional[str]
    placed_at: str
    updated_at: str


class OrderSummaryResponse(BaseModel):
    order_id: str
    status: str
    item_count: int
    total: float
    currency: str
    placed_at: str
