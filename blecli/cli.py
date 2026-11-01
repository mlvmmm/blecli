"""Argument parsing and dispatch for the blecli command."""

from __future__ import annotations

import argparse
import asyncio
import sys

from blecli import __version__
from blecli import gatt, scan, sniff


def _add_adapter(p: argparse.ArgumentParser) -> None:
    p.add_argument("-i", "--adapter", metavar="hciX",
                   help="HCI adapter to use (e.g. hci0). Default: system default.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blecli",
        description="Scan BLE advertisers, enumerate GATT, stream notifications, "
                    "and drive passive sniffers.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    s = sub.add_parser("scan", help="Passively collect BLE advertisements.")
    _add_adapter(s)
    s.add_argument("-t", "--timeout", type=float, default=10,
                   help="Seconds to scan; <=0 runs until Ctrl+C. Default 10.")
    s.add_argument("-n", "--name", help="Only show devices whose name contains this.")
    s.add_argument("-a", "--address", help="Only show this address.")
    s.add_argument("-r", "--min-rssi", type=int, help="Drop adverts weaker than this dBm.")
    s.add_argument("-v", "--verbose", action="store_true",
                   help="Print every advert, not just first sighting.")
    s.add_argument("--json", help="Write the final device list to this JSON file.")
    s.add_argument("--log", help="Append every advert as JSONL to this file.")
    s.set_defaults(func=lambda a: asyncio.run(scan.run_scan(a)))

    # enum
    e = sub.add_parser("enum", help="Connect and list services/characteristics.")
    _add_adapter(e)
    e.add_argument("address", help="Target device address.")
    e.add_argument("--read-all", action="store_true",
                   help="Also read every readable characteristic.")
    e.add_argument("--scan-timeout", type=float, default=10)
    e.add_argument("--connect-timeout", type=float, default=20)
    e.set_defaults(func=lambda a: asyncio.run(gatt.run_enum(a)))

    # read
    r = sub.add_parser("read", help="Read one characteristic.")
    _add_adapter(r)
    r.add_argument("address")
    r.add_argument("char", help="Characteristic UUID, 16-bit short UUID, or handle.")
    r.add_argument("--scan-timeout", type=float, default=10)
    r.add_argument("--connect-timeout", type=float, default=20)
    r.set_defaults(func=lambda a: asyncio.run(gatt.run_read(a)))

    # write
    w = sub.add_parser("write", help="Write bytes to one characteristic.")
    _add_adapter(w)
    w.add_argument("address")
    w.add_argument("char", help="Characteristic UUID, 16-bit short UUID, or handle.")
    w.add_argument("data", help="Hex payload, e.g. 01ff or 01:ff.")
    w.add_argument("--no-response", action="store_true",
                   help="Write without a response (write command).")
    w.add_argument("--scan-timeout", type=float, default=10)
    w.add_argument("--connect-timeout", type=float, default=20)
    w.set_defaults(func=lambda a: asyncio.run(gatt.run_write(a)))

    # notify
    n = sub.add_parser("notify", help="Subscribe to notify/indicate characteristics.")
    _add_adapter(n)
    n.add_argument("address")
    n.add_argument("char", nargs="+", help="One or more characteristics to subscribe to.")
    n.add_argument("-t", "--timeout", type=float, default=0,
                   help="Seconds to listen; <=0 runs until Ctrl+C. Default: forever.")
    n.add_argument("--log", help="Append each notification as JSONL to this file.")
    n.add_argument("--scan-timeout", type=float, default=10)
    n.add_argument("--connect-timeout", type=float, default=20)
    n.set_defaults(func=lambda a: asyncio.run(gatt.run_notify(a)))

    # sniff
    sn = sub.add_parser("sniff", help="Drive an external passive sniffer.")
    sn_sub = sn.add_subparsers(dest="sniffer", required=True)

    bt = sn_sub.add_parser("btmon", help="Local HCI trace via BlueZ btmon.")
    bt.add_argument("-w", "--write", help="Write capture to this .pcap/.btsnoop file.")
    bt.set_defaults(func=sniff.run_btmon)

    sf = sn_sub.add_parser("sniffle", help="Over-the-air capture via nRF52840 + Sniffle.")
    sf.add_argument("-s", "--serial", default="/dev/ttyACM0", help="Dongle serial port.")
    sf.add_argument("-c", "--channel", type=int, help="Advertising channel 37/38/39.")
    sf.add_argument("-r", "--rssi", type=int, help="Minimum RSSI to capture.")
    sf.add_argument("-m", "--mac", help="Only follow this MAC.")
    sf.add_argument("-a", "--advonly", action="store_true", help="Advertisements only.")
    sf.add_argument("-o", "--output", help="Write capture to this PCAP file.")
    sf.set_defaults(func=sniff.run_sniffle)

    bj = sn_sub.add_parser("btlejack", help="Over-the-air capture via micro:bit + btlejack.")
    bj.add_argument("-s", "--scan-connections", action="store_true",
                    help="List existing connections on the air.")
    bj.add_argument("-f", "--follow", help="Follow this access address.")
    bj.add_argument("-x", "--output", help="Write capture to this PCAP file.")
    bj.set_defaults(func=sniff.run_btlejack)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 0
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - top-level friendly error
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
