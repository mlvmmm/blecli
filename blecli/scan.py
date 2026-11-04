"""Advertisement scanning."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.uuids import uuidstr_to_str

from blecli.util import JsonlWriter, adapter_kwargs, company_name, hexdump, now_iso


@dataclass
class Seen:
    address: str
    name: str | None = None
    rssi: int = -127
    rssi_max: int = -127
    tx_power: int | None = None
    count: int = 0
    manufacturer: dict[str, str] = field(default_factory=dict)
    services: set[str] = field(default_factory=set)
    service_data: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "name": self.name,
            "rssi": self.rssi,
            "rssi_max": self.rssi_max,
            "tx_power": self.tx_power,
            "adv_count": self.count,
            "manufacturer": self.manufacturer,
            "services": sorted(self.services),
            "service_data": self.service_data,
        }


def _describe_services(uuids: set[str]) -> str:
    names = []
    for u in sorted(uuids):
        desc = uuidstr_to_str(u)
        names.append(desc if desc != "Unknown" else u)
    return ", ".join(names)


async def run_scan(args) -> int:
    seen: dict[str, Seen] = {}
    log = JsonlWriter(args.log)

    def on_adv(device: BLEDevice, adv: AdvertisementData) -> None:
        if args.min_rssi is not None and adv.rssi < args.min_rssi:
            return
        name = adv.local_name or device.name
        if args.name and (not name or args.name.lower() not in name.lower()):
            return
        if args.address and device.address.lower() != args.address.lower():
            return

        entry = seen.get(device.address)
        is_new = entry is None
        if is_new:
            entry = seen[device.address] = Seen(device.address)
        entry.name = name or entry.name
        entry.rssi = adv.rssi
        entry.rssi_max = max(entry.rssi_max, adv.rssi)
        entry.count += 1
        if adv.tx_power is not None:
            entry.tx_power = adv.tx_power
        for cid, data in adv.manufacturer_data.items():
            entry.manufacturer[company_name(cid)] = hexdump(data)
        entry.services.update(adv.service_uuids)
        for uuid, data in adv.service_data.items():
            entry.service_data[uuid] = hexdump(bytes(data))

        log.write({"ts": now_iso(), **entry.to_dict()})
        if is_new or args.verbose:
            mfr = ", ".join(entry.manufacturer) or "-"
            print(f"[{now_iso()}] {'NEW ' if is_new else '    '}{device.address}  "
                  f"{adv.rssi:4d} dBm  {name or '<unnamed>'}  mfr={mfr}")

    scanner = BleakScanner(detection_callback=on_adv, **adapter_kwargs(args))
    print(f"Scanning{' until Ctrl+C' if args.timeout <= 0 else f' for {args.timeout:g}s'}...")
    await scanner.start()
    try:
        if args.timeout > 0:
            await asyncio.sleep(args.timeout)
        else:
            await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await scanner.stop()
        log.close()

    _print_summary(seen)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([s.to_dict() for s in seen.values()], fh, indent=2)
        print(f"\nWrote {len(seen)} devices to {args.json}")
    return 0


def _print_summary(seen: dict[str, Seen]) -> None:
    print(f"\n{len(seen)} device(s), strongest first:\n")
    print(f"{'ADDRESS':<38} {'RSSI':>5} {'MAX':>5} {'ADVS':>5}  NAME / DETAILS")
    for s in sorted(seen.values(), key=lambda s: s.rssi_max, reverse=True):
        print(f"{s.address:<38} {s.rssi:>5} {s.rssi_max:>5} {s.count:>5}  {s.name or '<unnamed>'}")
        for company, data in s.manufacturer.items():
            print(f"{'':<58}mfr {company}: {data}")
        if s.services:
            print(f"{'':<58}svc {_describe_services(s.services)}")
        for uuid, data in s.service_data.items():
            print(f"{'':<58}svcdata {uuid}: {data}")
        if s.tx_power is not None:
            print(f"{'':<58}tx_power {s.tx_power} dBm")

