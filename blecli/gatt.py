"""GATT connections: enumerate, read, write and stream notifications."""

from __future__ import annotations

import asyncio
import sys

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.uuids import uuidstr_to_str

from blecli.util import JsonlWriter, hexdump, now_iso, parse_hex, printable


def _adapter_kwargs(args) -> dict:
    return {"adapter": args.adapter} if getattr(args, "adapter", None) else {}


async def _connect(args) -> BleakClient:
    """Resolve the target first so a missing device fails fast with a clear message."""
    print(f"Looking for {args.address}...", file=sys.stderr)
    device = await BleakScanner.find_device_by_address(
        args.address, timeout=args.scan_timeout, **_adapter_kwargs(args)
    )
    if device is None:
        raise SystemExit(f"error: {args.address} not found within {args.scan_timeout:g}s")
    client = BleakClient(device, timeout=args.connect_timeout, **_adapter_kwargs(args))
    await client.connect()
    print(f"Connected to {device.address} ({device.name or 'unnamed'}), MTU {client.mtu_size}",
          file=sys.stderr)
    return client


def _full_uuid(ref: str) -> str:
    """Expand a 16-bit short UUID into its full 128-bit form."""
    ref = ref.lower()
    return f"0000{ref}-0000-1000-8000-00805f9b34fb" if len(ref) == 4 else ref


def _resolve_char(client: BleakClient, ref: str) -> BleakGATTCharacteristic:
    """Accept a characteristic UUID, a 16-bit short UUID, or a decimal/0x handle."""
    services = client.services
    if ref.lower().startswith("0x") or ref.isdigit():
        char = services.get_characteristic(int(ref, 0))
        if char:
            return char
    char = services.get_characteristic(_full_uuid(ref))
    if char is None:
        raise SystemExit(f"error: no characteristic matching {ref!r}")
    return char


def _label(uuid: str) -> str:
    desc = uuidstr_to_str(uuid)
    return f"{uuid} ({desc})" if desc != "Unknown" else uuid


async def run_enum(args) -> int:
    client = await _connect(args)
    try:
        for service in client.services:
            print(f"\nservice {_label(service.uuid)}")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  char handle=0x{char.handle:04x} {_label(char.uuid)}  [{props}]")
                if args.read_all and "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char)
                        print(f"       = {hexdump(value)}  |{printable(value)}|")
                    except Exception as exc:  # noqa: BLE001 - surface, keep going
                        print(f"       ! read failed: {exc}")
                for desc in char.descriptors:
                    print(f"    desc handle=0x{desc.handle:04x} {_label(desc.uuid)}")
    finally:
        await client.disconnect()
    return 0


async def run_read(args) -> int:
    client = await _connect(args)
    try:
        char = _resolve_char(client, args.char)
        value = await client.read_gatt_char(char)
        print(f"{hexdump(value)}")
        print(f"ascii: |{printable(value)}|", file=sys.stderr)
    finally:
        await client.disconnect()
    return 0


async def run_write(args) -> int:
    client = await _connect(args)
    try:
        char = _resolve_char(client, args.char)
        payload = parse_hex(args.data)
        await client.write_gatt_char(char, payload, response=not args.no_response)
        print(f"wrote {len(payload)} byte(s) to {char.uuid}", file=sys.stderr)
    finally:
        await client.disconnect()
    return 0


async def run_notify(args) -> int:
    client = await _connect(args)
    log = JsonlWriter(args.log)
    chars = [_resolve_char(client, ref) for ref in args.char]
    count = 0

    def on_notify(char: BleakGATTCharacteristic, data: bytearray) -> None:
        nonlocal count
        count += 1
        data = bytes(data)
        print(f"[{now_iso()}] {char.uuid}  {hexdump(data)}  |{printable(data)}|")
        log.write({"ts": now_iso(), "char": char.uuid, "hex": data.hex(),
                   "ascii": printable(data)})

    try:
        for char in chars:
            await client.start_notify(char, on_notify)
        print(f"Subscribed to {len(chars)} characteristic(s); Ctrl+C to stop.",
              file=sys.stderr)
        if args.timeout > 0:
            await asyncio.sleep(args.timeout)
        else:
            await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        for char in chars:
            try:
                await client.stop_notify(char)
            except Exception:  # noqa: BLE001 - best effort during teardown
                pass
        await client.disconnect()
        log.close()
        print(f"\n{count} notification(s) received.", file=sys.stderr)
    return 0
