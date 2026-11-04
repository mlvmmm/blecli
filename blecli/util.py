"""Formatting helpers shared by the commands."""

from __future__ import annotations

import json
import time
from typing import IO, Any

# Small subset of Bluetooth SIG company identifiers, enough to label common devices.
COMPANY_IDS = {
    0x0006: "Microsoft",
    0x000D: "Texas Instruments",
    0x004C: "Apple",
    0x0059: "Nordic Semiconductor",
    0x0075: "Samsung",
    0x0087: "Garmin",
    0x00E0: "Google",
    0x0171: "Amazon",
    0x02E5: "Espressif",
    0x038F: "Xiaomi",
}


def adapter_kwargs(args) -> dict:
    """Build the bleak arguments that select an adapter (BlueZ only)."""
    adapter = getattr(args, "adapter", None)
    return {"bluez": {"adapter": adapter}} if adapter else {}


def company_name(cid: int) -> str:
    return COMPANY_IDS.get(cid, f"0x{cid:04X}")


def hexdump(data: bytes) -> str:
    return data.hex(" ")


def printable(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def parse_hex(value: str) -> bytes:
    cleaned = value.replace(" ", "").replace(":", "")
    if cleaned.lower().startswith("0x"):
        cleaned = cleaned[2:]
    return bytes.fromhex(cleaned)


def now_iso() -> str:
    t = time.time()
    return time.strftime("%H:%M:%S", time.localtime(t)) + f".{int(t * 1000) % 1000:03d}"


class JsonlWriter:
    """Append one JSON object per line; a no-op when no path is given."""

    def __init__(self, path: str | None):
        self._fh: IO[str] | None = open(path, "a", encoding="utf-8") if path else None

    def write(self, record: dict[str, Any]) -> None:
        if self._fh:
            self._fh.write(json.dumps(record) + "\n")
            self._fh.flush()

    def close(self) -> None:
        if self._fh:
            self._fh.close()
