# Agent instructions

blecli targets Kali Linux with BlueZ, but I also work on it on a Mac, where bleak
uses CoreBluetooth. Say which platform you checked, because passing on one doesn't
prove it works on the other.

## Real devices and radios

- Don't run `scan`, `enum`, `read`, `write`, `notify` or `sniff` unless I ask in
  this conversation. They use the radio or start capture tools.
- Only target devices I name. `write` can change how a device behaves, so never
  choose a target or payload yourself.
- Scan and capture output describes other people's devices. `*.pcap`, `*.btsnoop`
  and `*.jsonl` are gitignored, but `scan --json` output isn't, so never commit it.

## Platform differences

On macOS:

- Device addresses are UUIDs, not MAC addresses.
- `--adapter` has no effect, because it's BlueZ-only.
- Passive scanning isn't supported. On BlueZ it needs `or_patterns`.
- `btmon` isn't available.

## Code rules

- `sniff` only assembles and runs the external tools' commands. A normal adapter
  can't follow a live connection, so don't add over-the-air capture to blecli.
- `pyproject.toml` allows Python 3.10 and `bleak>=3.0`, while `.venv` has Python 3.15
  and bleak 3.0.2. Avoid syntax newer than 3.10, and check bleak calls against both
  ends of that range. Selecting an adapter needs bleak 3: older releases silently
  ignore `bluez={"adapter": ...}`.
- Scripts may read the output of `read` and `notify`, so keep data on stdout and
  status messages on stderr.

## Checking changes

There's no test suite and no linter is set up. These don't touch the radio:

```bash
.venv/bin/python -B -m blecli --help
.venv/bin/python -B -m blecli scan --help
```

To test logic, use stand-ins for bleak objects and `subprocess.call`. Tell me what
still needs checking on real hardware.
