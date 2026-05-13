import math
import statistics

from fastapi import APIRouter, HTTPException, Path, Query

from models.schemas import TwoNumberInput, NumberListInput, StatsResponse

router = APIRouter(prefix="/math", tags=["Math"])


@router.post("/add")
def add(body: TwoNumberInput):
    """Add two numbers together and return the result."""
    return {"a": body.a, "b": body.b, "result": body.a + body.b, "operation": "addition"}


@router.post("/subtract")
def subtract(body: TwoNumberInput):
    """Subtract `b` from `a` and return the result."""
    return {"a": body.a, "b": body.b, "result": body.a - body.b, "operation": "subtraction"}


@router.post("/multiply")
def multiply(body: TwoNumberInput):
    """Multiply two numbers and return the product."""
    return {"a": body.a, "b": body.b, "result": body.a * body.b, "operation": "multiplication"}


@router.post("/divide")
def divide(body: TwoNumberInput):
    """
    Divide `a` by `b` and return the quotient.

    Returns a `400` error if `b` is zero.
    """
    if body.b == 0:
        raise HTTPException(status_code=400, detail="Division by zero")
    return {"a": body.a, "b": body.b, "result": body.a / body.b, "operation": "division"}


@router.post("/power")
def power(body: TwoNumberInput):
    """
    Raise `a` to the power of `b` (a^b).

    Returns a `400` error if the result overflows float range.
    """
    try:
        result = body.a ** body.b
    except OverflowError:
        raise HTTPException(status_code=400, detail="Result too large to compute")
    return {"base": body.a, "exponent": body.b, "result": result}


@router.post("/modulo")
def modulo(body: TwoNumberInput):
    """
    Return the remainder of `a` divided by `b` (a % b).

    Returns a `400` error if `b` is zero.
    """
    if body.b == 0:
        raise HTTPException(status_code=400, detail="Modulo by zero")
    return {"a": body.a, "b": body.b, "result": body.a % body.b}


@router.get("/sqrt/{n}")
def sqrt(n: float = Path(..., description="Number to take square root of")):
    """
    Compute the square root of a number.

    Returns a `400` error if the input is negative (complex results not supported).
    """
    if n < 0:
        raise HTTPException(status_code=400, detail="Cannot take sqrt of a negative number")
    return {"input": n, "result": math.sqrt(n)}


@router.get("/factorial/{n}")
def factorial(n: int = Path(..., ge=0, le=20)):
    """
    Compute the factorial of a non-negative integer (n!).

    - Input range: 0 to 20 (0! = 1, 20! = 2,432,902,008,176,640,000)
    - Values above 20 would exceed safe integer bounds
    """
    return {"input": n, "result": math.factorial(n)}


@router.get("/fibonacci/{n}")
def fibonacci(n: int = Path(..., ge=1, le=50)):
    """
    Generate the first `n` numbers of the Fibonacci sequence.

    - Sequence starts at 0: `0, 1, 1, 2, 3, 5, 8, 13, ...`
    - Input range: 1 to 50
    - Returns the full sequence and the nth value
    """
    seq = [0, 1]
    for _ in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return {"n": n, "sequence": seq[:n], "nth_value": seq[n - 1]}


@router.get("/primes")
def primes(limit: int = Query(default=50, ge=2, le=10000)):
    """
    Return all prime numbers up to a given limit using the Sieve of Eratosthenes.

    - `limit` controls the upper bound (default: 50, max: 10,000)
    - Returns the list of primes and a count
    """
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i * i, limit + 1, i):
                sieve[j] = False
    result = [i for i, v in enumerate(sieve) if v]
    return {"limit": limit, "count": len(result), "primes": result}


@router.post("/statistics", response_model=StatsResponse)
def compute_statistics(body: NumberListInput):
    """
    Compute descriptive statistics for a list of numbers.

    Returns mean, median, mode (if unique), population standard deviation, min, and max.
    Send at least one number; mode returns `null` when no unique mode exists.
    """
    nums = body.numbers
    try:
        mode_val = statistics.mode(nums)
    except statistics.StatisticsError:
        mode_val = None
    return StatsResponse(
        mean=statistics.mean(nums),
        median=statistics.median(nums),
        mode=mode_val,
        std_dev=statistics.pstdev(nums),
        min=min(nums),
        max=max(nums),
    )


@router.get("/gcd")
def gcd(a: int = Query(...), b: int = Query(...)):
    """
    Compute the Greatest Common Divisor (GCD) and Least Common Multiple (LCM) of two integers.

    Useful for simplifying fractions or finding shared factors between numbers.
    """
    return {"a": a, "b": b, "gcd": math.gcd(a, b), "lcm": abs(a * b) // math.gcd(a, b) if math.gcd(a, b) else 0}


@router.get("/is-prime/{n}")
def is_prime(n: int = Path(..., ge=2)):
    """
    Check whether a given integer is a prime number.

    - If not prime, the response includes the smallest divisor found
    - Uses trial division up to √n for efficiency
    - Minimum input: 2 (the smallest prime)
    """
    if n < 2:
        return {"number": n, "is_prime": False}
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return {"number": n, "is_prime": False, "divisor": i}
    return {"number": n, "is_prime": True}
