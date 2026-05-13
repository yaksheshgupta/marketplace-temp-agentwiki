import random
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from routers.auth import get_current_user
from models.schemas import (
    CreateAccountRequest, AccountResponse,
    DepositRequest, WithdrawRequest, TransferRequest,
    TransactionResponse,
)

router = APIRouter(prefix="/finance", tags=["Finance"], dependencies=[Depends(get_current_user)])

# In-memory stores
accounts_db: dict[str, dict] = {}
transactions_db: dict[str, dict] = {}  # transaction_id -> transaction


def _generate_account_number() -> str:
    return "ACC" + "".join([str(random.randint(0, 9)) for _ in range(10)])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_transaction(account_id: str, txn_type: str, amount: float, balance_after: float, description: str, currency: str) -> dict:
    txn = {
        "transaction_id": "TXN-" + str(uuid.uuid4()).upper()[:12],
        "account_id": account_id,
        "type": txn_type,
        "amount": round(amount, 2),
        "balance_after": round(balance_after, 2),
        "description": description,
        "currency": currency,
        "timestamp": _now(),
        "status": "completed",
    }
    transactions_db[txn["transaction_id"]] = txn
    accounts_db[account_id]["transactions"].append(txn["transaction_id"])
    return txn


# ── Accounts ──────────────────────────────────────────────────────────────────

@router.post("/accounts", response_model=AccountResponse, status_code=201)
def create_account(body: CreateAccountRequest):
    """
    Open a new dummy bank account.

    - `account_type`: `checking`, `savings`, or `business`
    - `currency`: any 3-letter ISO 4217 code (e.g. `USD`, `EUR`, `INR`)
    - `initial_deposit`: optional opening balance (defaults to 0)
    - Returns the new account with a generated account number and unique ID

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    account_id = str(uuid.uuid4())
    account = {
        "account_id": account_id,
        "account_number": _generate_account_number(),
        "owner_name": body.owner_name,
        "account_type": body.account_type,
        "balance": round(body.initial_deposit, 2),
        "currency": body.currency,
        "created_at": _now(),
        "status": "active",
        "transactions": [],
    }
    accounts_db[account_id] = account

    if body.initial_deposit > 0:
        _make_transaction(account_id, "credit", body.initial_deposit, body.initial_deposit, "Opening deposit", body.currency)

    return AccountResponse(**{k: v for k, v in account.items() if k != "transactions"})


@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts():
    """
    Return a list of all accounts.

    Useful for browsing the current state of the dummy bank.
    Each account shows its balance, type, currency, and status.

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    return [
        AccountResponse(**{k: v for k, v in acc.items() if k != "transactions"})
        for acc in accounts_db.values()
    ]


@router.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: str):
    """
    Retrieve details for a specific account by its ID.

    Returns balance, owner, account number, type, currency, and status.
    Returns `404` if the account does not exist.

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    acc = accounts_db.get(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountResponse(**{k: v for k, v in acc.items() if k != "transactions"})


@router.delete("/accounts/{account_id}", status_code=204)
def close_account(account_id: str):
    """
    Close an account by marking its status as `closed`.

    - The account record is retained for audit purposes
    - Closed accounts cannot receive deposits or initiate withdrawals/transfers
    - Returns `404` if the account does not exist

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    acc = accounts_db.get(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    if acc["status"] == "closed":
        raise HTTPException(status_code=409, detail="Account is already closed")
    accounts_db[account_id]["status"] = "closed"


# ── Transactions ──────────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/deposit", response_model=TransactionResponse)
def deposit(account_id: str, body: DepositRequest):
    """
    Deposit funds into an account.

    - `amount` must be greater than 0
    - Updates the account balance immediately
    - Records the transaction with a unique `TXN-` prefixed ID
    - Returns `404` if the account does not exist, `409` if it is closed

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    acc = accounts_db.get(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    if acc["status"] == "closed":
        raise HTTPException(status_code=409, detail="Cannot deposit into a closed account")

    acc["balance"] = round(acc["balance"] + body.amount, 2)
    return TransactionResponse(**_make_transaction(account_id, "credit", body.amount, acc["balance"], body.description, acc["currency"]))


@router.post("/accounts/{account_id}/withdraw", response_model=TransactionResponse)
def withdraw(account_id: str, body: WithdrawRequest):
    """
    Withdraw funds from an account.

    - `amount` must be greater than 0 and cannot exceed the current balance
    - Returns `400` if insufficient funds
    - Returns `404` if the account does not exist, `409` if it is closed

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    acc = accounts_db.get(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    if acc["status"] == "closed":
        raise HTTPException(status_code=409, detail="Cannot withdraw from a closed account")
    if body.amount > acc["balance"]:
        raise HTTPException(status_code=400, detail=f"Insufficient funds — balance is {acc['balance']} {acc['currency']}")

    acc["balance"] = round(acc["balance"] - body.amount, 2)
    return TransactionResponse(**_make_transaction(account_id, "debit", body.amount, acc["balance"], body.description, acc["currency"]))


@router.post("/transfer", response_model=dict)
def transfer(body: TransferRequest):
    """
    Transfer funds between two accounts.

    - Both accounts must exist and be active
    - The source account must have sufficient balance
    - Generates two linked transactions: a debit on the sender and a credit on the receiver
    - Returns both transaction records in a single response

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    src = accounts_db.get(body.from_account_id)
    dst = accounts_db.get(body.to_account_id)

    if not src:
        raise HTTPException(status_code=404, detail="Source account not found")
    if not dst:
        raise HTTPException(status_code=404, detail="Destination account not found")
    if src["status"] == "closed":
        raise HTTPException(status_code=409, detail="Source account is closed")
    if dst["status"] == "closed":
        raise HTTPException(status_code=409, detail="Destination account is closed")
    if body.from_account_id == body.to_account_id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")
    if body.amount > src["balance"]:
        raise HTTPException(status_code=400, detail=f"Insufficient funds — balance is {src['balance']} {src['currency']}")

    src["balance"] = round(src["balance"] - body.amount, 2)
    dst["balance"] = round(dst["balance"] + body.amount, 2)

    debit_txn = _make_transaction(body.from_account_id, "debit", body.amount, src["balance"], f"Transfer to {dst['account_number']}: {body.description}", src["currency"])
    credit_txn = _make_transaction(body.to_account_id, "credit", body.amount, dst["balance"], f"Transfer from {src['account_number']}: {body.description}", dst["currency"])

    return {
        "status": "success",
        "debit": TransactionResponse(**debit_txn),
        "credit": TransactionResponse(**credit_txn),
    }


@router.get("/accounts/{account_id}/transactions", response_model=list[TransactionResponse])
def get_transactions(
    account_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    txn_type: str = Query(default=None, pattern="^(credit|debit)$"),
):
    """
    List transaction history for an account.

    - Results are sorted newest-first
    - Use `limit` and `offset` for pagination
    - Filter by `txn_type`: `credit` (money in) or `debit` (money out)
    - Returns `404` if the account does not exist

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    acc = accounts_db.get(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    txns = [transactions_db[tid] for tid in reversed(acc["transactions"]) if tid in transactions_db]

    if txn_type:
        txns = [t for t in txns if t["type"] == txn_type]

    return [TransactionResponse(**t) for t in txns[offset: offset + limit]]


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: str):
    """
    Retrieve a single transaction by its ID.

    Transaction IDs are prefixed with `TXN-` and returned from deposit, withdraw, and transfer calls.
    Returns `404` if the transaction does not exist.

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    txn = transactions_db.get(transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse(**txn)


@router.get("/accounts/{account_id}/statement")
def get_statement(
    account_id: str,
    from_date: str = Query(default=None, description="Start date YYYY-MM-DD"),
    to_date: str = Query(default=None, description="End date YYYY-MM-DD"),
):
    """
    Generate a mini account statement with optional date filtering.

    - `from_date` and `to_date` are both optional and must be in `YYYY-MM-DD` format
    - Returns a summary (opening balance, total credits, total debits, closing balance)
      alongside the matching transactions sorted oldest-first

    **Auth required** — pass `Authorization: Bearer <token>` or `X-API-Key: <key>`.
    """
    acc = accounts_db.get(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    txns = [transactions_db[tid] for tid in acc["transactions"] if tid in transactions_db]

    try:
        if from_date:
            txns = [t for t in txns if t["timestamp"][:10] >= from_date]
        if to_date:
            txns = [t for t in txns if t["timestamp"][:10] <= to_date]
    except Exception:
        raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")

    total_credits = sum(t["amount"] for t in txns if t["type"] == "credit")
    total_debits = sum(t["amount"] for t in txns if t["type"] == "debit")

    return {
        "account_id": account_id,
        "account_number": acc["account_number"],
        "owner_name": acc["owner_name"],
        "currency": acc["currency"],
        "current_balance": acc["balance"],
        "period": {"from": from_date, "to": to_date},
        "summary": {
            "total_credits": round(total_credits, 2),
            "total_debits": round(total_debits, 2),
            "net": round(total_credits - total_debits, 2),
            "transaction_count": len(txns),
        },
        "transactions": [TransactionResponse(**t) for t in txns],
    }
