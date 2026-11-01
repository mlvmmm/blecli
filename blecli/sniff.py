"""Thin wrappers around published passive BLE sniffers.

blecli does not sniff on its own; standard Bluetooth adapters cannot follow the
frequency-hopping of a live connection. These helpers build and run the command
lines for the usual tools so you don't have to remember each one's flags. Capture
only traffic you are authorised to capture.
"""

from __future__ import annotations

import shutil
import subprocess
import sys


def _run(cmd: list[str]) -> int:
    exe = shutil.which(cmd[0])
    if exe is None:
        print(f"error: '{cmd[0]}' not found on PATH.\n"
              f"  See the README for how to install it.", file=sys.stderr)
        return 127
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 0


def run_btmon(args) -> int:
    """Host-controller trace via BlueZ btmon (local adapter traffic only)."""
    cmd = ["btmon"]
    if args.write:
        cmd += ["-w", args.write]
    return _run(cmd)


def run_sniffle(args) -> int:
    """Over-the-air capture with an nRF52840 dongle running the Sniffle firmware."""
    cmd = ["sniff_receiver.py", "-s", args.serial]
    if args.channel is not None:
        cmd += ["-c", str(args.channel)]
    if args.rssi is not None:
        cmd += ["-r", str(args.rssi)]
    if args.mac:
        cmd += ["-m", args.mac]
    if args.advonly:
        cmd += ["-a"]
    if args.output:
        cmd += ["-o", args.output]
    return _run(cmd)


def run_btlejack(args) -> int:
    """Over-the-air capture with a micro:bit running btlejack firmware."""
    cmd = ["btlejack"]
    if args.scan_connections:
        cmd += ["-s"]
    elif args.follow:
        cmd += ["-f", args.follow]
    else:
        cmd += ["-c", "any"]
    if args.output:
        cmd += ["-x", args.output]
    return _run(cmd)
