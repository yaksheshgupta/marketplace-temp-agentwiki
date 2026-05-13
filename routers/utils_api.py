import hashlib
import random
import re
import string
import uuid

from fastapi import APIRouter, HTTPException, Query, Request

from models.schemas import TextInput, HashRequest, RandomStringRequest, RandomNumberRequest

router = APIRouter(prefix="/utils", tags=["Utils"])

QUOTES = [
    {"quote": "The best way to predict the future is to invent it.", "author": "Alan Kay"},
    {"quote": "Code is like humor. When you have to explain it, it's bad.", "author": "Cory House"},
    {"quote": "Simplicity is the soul of efficiency.", "author": "Austin Freeman"},
    {"quote": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
    {"quote": "Experience is the name everyone gives to their mistakes.", "author": "Oscar Wilde"},
    {"quote": "Make it work, make it right, make it fast.", "author": "Kent Beck"},
    {"quote": "Programs must be written for people to read.", "author": "Harold Abelson"},
    {"quote": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "author": "Martin Fowler"},
]


@router.get("/uuid")
def get_uuid(version: int = Query(default=4, ge=1, le=4)):
    """
    Generate a random UUID (Universally Unique Identifier).

    - `version=4` (default) — fully random, most common
    - `version=1` — based on current time and MAC address
    - Useful for generating unique IDs for records, sessions, or tokens
    """
    generators = {
        1: str(uuid.uuid1()),
        4: str(uuid.uuid4()),
    }
    generated = generators.get(version, str(uuid.uuid4()))
    return {"uuid": generated, "version": version}


@router.post("/random/number")
def random_number(body: RandomNumberRequest):
    """
    Generate a random floating-point number within a given range.

    - `min` defaults to 0, `max` defaults to 100
    - Returns both the float result and a truncated integer version
    - `min` must be strictly less than `max`
    """
    if body.min >= body.max:
        raise HTTPException(status_code=400, detail="min must be less than max")
    result = random.uniform(body.min, body.max)
    return {"min": body.min, "max": body.max, "result": result, "result_int": int(result)}


@router.post("/random/string")
def random_string(body: RandomStringRequest):
    """
    Generate a random string of a given length.

    - Default charset: letters + digits (alphanumeric)
    - Set `include_symbols: true` to also include punctuation characters
    - `length` range: 1 to 256 characters
    """
    charset = string.ascii_letters + string.digits
    if body.include_symbols:
        charset += string.punctuation
    result = "".join(random.choices(charset, k=body.length))
    return {"length": body.length, "result": result, "include_symbols": body.include_symbols}


@router.get("/random/color")
def random_color():
    """
    Generate a random color in HEX, RGB, and HSL formats.

    Useful for UI prototyping, data visualization, or testing color pickers.
    Each call returns a different color.
    """
    r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    hex_color = f"#{r:02X}{g:02X}{b:02X}"
    return {
        "hex": hex_color,
        "rgb": {"r": r, "g": g, "b": b},
        "hsl": _rgb_to_hsl(r, g, b),
    }


@router.get("/random/quote")
def random_quote():
    """
    Return a random inspirational or programming-related quote.

    Each call picks randomly from a curated list of quotes with attribution.
    """
    return random.choice(QUOTES)


@router.post("/text/word-count")
def word_count(body: TextInput):
    """
    Analyze a block of text and return detailed statistics.

    Returns character count (with and without spaces), word count, sentence count,
    paragraph count, and average word length.
    """
    words = body.text.split()
    sentences = re.split(r'[.!?]+', body.text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return {
        "characters": len(body.text),
        "characters_no_spaces": len(body.text.replace(" ", "")),
        "words": len(words),
        "sentences": len(sentences),
        "paragraphs": len([p for p in body.text.split("\n\n") if p.strip()]),
        "average_word_length": round(sum(len(w) for w in words) / len(words), 2) if words else 0,
    }


@router.post("/text/reverse")
def reverse_text(body: TextInput):
    """
    Reverse the characters in a string.

    Works on any Unicode text including emojis and multi-byte characters.
    """
    return {"input": body.text, "reversed": body.text[::-1]}


@router.post("/text/palindrome")
def check_palindrome(body: TextInput):
    """
    Check whether a string is a palindrome.

    Strips punctuation and spaces before comparing, so `"A man, a plan, a canal: Panama"`
    correctly evaluates as a palindrome. The cleaned comparison string is included in the response.
    """
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', body.text).lower()
    return {
        "input": body.text,
        "is_palindrome": cleaned == cleaned[::-1],
        "cleaned": cleaned,
    }


@router.post("/text/case")
def transform_case(body: TextInput, transform: str = Query(default="upper", pattern="^(upper|lower|title|snake|camel|kebab)$")):
    """
    Convert a string to a specific case format.

    Supported transforms:
    - `upper` — ALL CAPS
    - `lower` — all lowercase
    - `title` — Title Case
    - `snake` — snake_case
    - `camel` — camelCase
    - `kebab` — kebab-case
    """
    text = body.text
    transforms = {
        "upper": text.upper(),
        "lower": text.lower(),
        "title": text.title(),
        "snake": "_".join(text.lower().split()),
        "camel": text.split()[0].lower() + "".join(w.title() for w in text.split()[1:]) if text.split() else "",
        "kebab": "-".join(text.lower().split()),
    }
    return {"input": text, "transform": transform, "result": transforms[transform]}


@router.post("/hash")
def hash_text(body: HashRequest):
    """
    Hash a string using a cryptographic algorithm.

    Supported algorithms: `md5`, `sha1`, `sha256` (default), `sha512`.
    Note: MD5 and SHA1 are not collision-resistant — use SHA256 or SHA512 for security purposes.
    """
    hashers = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }
    hasher = hashers[body.algorithm]
    result = hasher(body.text.encode()).hexdigest()
    return {"input": body.text, "algorithm": body.algorithm, "hash": result}


@router.get("/ip")
def get_ip(request: Request):
    """
    Return the IP address of the caller and their User-Agent string.

    Respects the `X-Forwarded-For` header for clients behind proxies or load balancers.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0] if forwarded_for else request.client.host
    return {"ip": ip, "user_agent": request.headers.get("user-agent", "unknown")}


@router.get("/coin-flip")
def coin_flip(flips: int = Query(default=1, ge=1, le=100)):
    """
    Simulate one or more coin flips.

    - `flips` controls how many times the coin is tossed (1 to 100)
    - Returns each individual result plus a summary count of heads vs tails
    """
    results = [random.choice(["heads", "tails"]) for _ in range(flips)]
    return {
        "flips": flips,
        "results": results,
        "heads": results.count("heads"),
        "tails": results.count("tails"),
    }


@router.get("/dice")
def roll_dice(
    sides: int = Query(default=6, ge=2, le=100),
    count: int = Query(default=1, ge=1, le=20),
):
    """
    Roll one or more dice with a configurable number of sides.

    - `sides` — number of faces on each die (default: 6, max: 100)
    - `count` — how many dice to roll at once (default: 1, max: 20)
    - Returns individual roll results and the total sum
    """
    rolls = [random.randint(1, sides) for _ in range(count)]
    return {"sides": sides, "count": count, "rolls": rolls, "total": sum(rolls)}


def _rgb_to_hsl(r: int, g: int, b: int) -> dict:
    r_, g_, b_ = r / 255, g / 255, b / 255
    cmax, cmin = max(r_, g_, b_), min(r_, g_, b_)
    delta = cmax - cmin
    l = (cmax + cmin) / 2
    s = 0 if delta == 0 else delta / (1 - abs(2 * l - 1))
    if delta == 0:
        h = 0
    elif cmax == r_:
        h = 60 * (((g_ - b_) / delta) % 6)
    elif cmax == g_:
        h = 60 * ((b_ - r_) / delta + 2)
    else:
        h = 60 * ((r_ - g_) / delta + 4)
    return {"h": round(h, 1), "s": round(s * 100, 1), "l": round(l * 100, 1)}
