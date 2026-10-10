"""Parse NSE index-constituent CSVs (Nifty 50/100/200/500 share one layout).

The parser is strict: an unexpected header, duplicate symbol or ISIN, blank
field or invalid ISIN check digit rejects the whole file. Nothing is guessed.
"""

import csv
import io
import re
from datetime import UTC, datetime
from urllib.request import Request, urlopen

HEADER = ["Company Name", "Industry", "Symbol", "Series", "ISIN Code"]
FIELDS = ("name", "industry", "symbol", "series", "isin")
SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9&_-]{0,19}")
ISIN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")

# NSE's published list location; it may change or block automated clients.
NSE_ARCHIVE = "https://nsearchives.nseindia.com/content/indices/{file}"
INDEX_FILES = {
    "NIFTY50": "ind_nifty50list.csv",
    "NIFTY100": "ind_nifty100list.csv",
    "NIFTY200": "ind_nifty200list.csv",
    "NIFTY500": "ind_nifty500list.csv",
}


def isin_valid(code):
    """ISO 6166 check: letters become 10-35, then a Luhn check on the digits."""
    if not isinstance(code, str) or not ISIN.fullmatch(code):
        return False
    digits = "".join(str(int(ch, 36)) for ch in code[:-1])
    total = 0
    # The check digit is appended to the right, so double from the rightmost.
    for position, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if position % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return (10 - total % 10) % 10 == int(code[-1])


def parse_constituents(raw):
    """Return validated members, in file order, from the CSV bytes."""
    if not isinstance(raw, bytes | bytearray):
        raise TypeError("Constituent input must be bytes")
    try:
        text = bytes(raw).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Constituent file is not UTF-8 text") from exc
    rows = list(csv.reader(io.StringIO(text)))
    while rows and not any(cell.strip() for cell in rows[-1]):
        rows.pop()
    if not rows or [c.strip() for c in rows[0]] != HEADER:
        raise ValueError(f"Unexpected header; expected: {', '.join(HEADER)}")
    members, symbols, isins = [], set(), set()
    for line, row in enumerate(rows[1:], start=2):
        if len(row) != len(HEADER):
            raise ValueError(f"Line {line}: expected {len(HEADER)} columns")
        m = dict(zip(FIELDS, (c.strip() for c in row), strict=True))
        if not all(m.values()):
            raise ValueError(f"Line {line}: blank field")
        if not SYMBOL.fullmatch(m["symbol"]):
            raise ValueError(f"Line {line}: invalid symbol {m['symbol']!r}")
        if not isin_valid(m["isin"]):
            raise ValueError(f"Line {line}: invalid ISIN {m['isin']!r}")
        if m["symbol"] in symbols or m["isin"] in isins:
            raise ValueError(f"Line {line}: duplicate symbol or ISIN")
        symbols.add(m["symbol"])
        isins.add(m["isin"])
        members.append(m)
    if not members:
        raise ValueError("Constituent file has no members")
    return members


def download_constituents(universe_id, *, opener=urlopen, timeout=30):
    """Fetch the current list. Returns raw bytes, URL and UTC retrieval time.

    The download is a convenience: if NSE blocks it, download the CSV in a
    browser and import the saved file instead.
    """
    if universe_id not in INDEX_FILES:
        raise ValueError(f"No known NSE file for {universe_id}")
    url = NSE_ARCHIVE.format(file=INDEX_FILES[universe_id])
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (research data loader)", "Accept": "*/*"},
    )
    with opener(request, timeout=timeout) as response:
        raw = response.read()
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
    parse_constituents(raw)  # fail before anything is saved
    return {"raw": raw, "url": url, "retrieved_at": retrieved_at}
