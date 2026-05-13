from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader

from core.security import (
    users_db, api_keys_db,
    hash_password, verify_password,
    create_access_token, decode_token,
    generate_api_key, hash_api_key,
)
from models.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse, ApiKeyResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    api_key: str = Security(api_key_header),
) -> str:
    # Try JWT first
    if token:
        payload = decode_token(token)
        if payload:
            return payload.get("sub")

    # Try API key
    if api_key:
        hashed = hash_api_key(api_key)
        username = api_keys_db.get(hashed)
        if username:
            return username

    raise HTTPException(status_code=401, detail="Invalid or missing credentials")


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest):
    """
    Create a new user account.

    - `username` must be unique (3–50 characters)
    - `password` must be at least 6 characters (stored as a bcrypt hash)
    - Returns the created user profile — no sensitive data included
    """
    if body.username in users_db:
        raise HTTPException(status_code=409, detail="Username already taken")
    users_db[body.username] = {
        "username": body.username,
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "api_keys": [],
    }
    return UserResponse(username=body.username, email=body.email)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """
    Authenticate and receive a JWT access token.

    - Token expires after 30 minutes (configurable via `JWT_EXPIRE_MINUTES`)
    - Use the returned token in the `Authorization: Bearer <token>` header on protected endpoints
    """
    user = users_db.get(body.username)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": body.username})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(username: str = Depends(get_current_user)):
    """
    Return the profile of the currently authenticated user.

    Accepts either auth method:
    - `Authorization: Bearer <jwt>` — JWT from `/auth/login`
    - `X-API-Key: <key>` — API key from `/auth/api-key/generate`
    """
    user = users_db[username]
    return UserResponse(username=user["username"], email=user["email"])


@router.post("/api-key/generate", response_model=ApiKeyResponse)
def generate_key(username: str = Depends(get_current_user)):
    """
    Generate a new API key for the authenticated user.

    - Keys are prefixed with `sk-` and are 44 characters long
    - The raw key is only shown once — store it immediately
    - Only the SHA-256 hash is persisted server-side
    - Requires a valid JWT or existing API key to call
    """
    key = generate_api_key()
    hashed = hash_api_key(key)
    api_keys_db[hashed] = username
    users_db[username]["api_keys"].append(hashed)
    return ApiKeyResponse(api_key=key)


@router.delete("/api-key/revoke", status_code=204)
def revoke_key(api_key: str, username: str = Depends(get_current_user)):
    """
    Permanently revoke an API key.

    - Pass the raw key (starting with `sk-`) as the `api_key` query parameter
    - You can only revoke keys that belong to your account
    - Returns 204 No Content on success
    """
    hashed = hash_api_key(api_key)
    if api_keys_db.get(hashed) != username:
        raise HTTPException(status_code=404, detail="API key not found")
    del api_keys_db[hashed]
    users_db[username]["api_keys"].remove(hashed)
