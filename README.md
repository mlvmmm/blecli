# blecli

A command-line tool for Bluetooth Low Energy recon on Kali Linux. It uses
[bleak](https://github.com/hbldh/bleak) for everything you can do with a normal
Bluetooth adapter — discovering advertisers, enumerating GATT, reading/writing
characteristics, streaming notifications — and shells out to published passive
sniffers (btmon, Sniffle, btlejack) for over-the-air capture, which a standard
adapter cannot do.

> Only scan, connect to, or capture traffic from devices you own or are
> explicitly authorised to test.

## Install

```bash
sudo apt install bluez python3-venv       # BlueZ provides the stack + btmon
git clone <this repo> blecli && cd blecli
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
```

BLE scanning needs permission to use the adapter. Either run as root, or grant
the capability once:

```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
```

## Usage

```bash
blecli scan                      # 10s advertisement sweep
blecli scan -t 0 -v --json out.json   # run until Ctrl+C, log everything
blecli scan -n Fitbit -r -70     # only "Fitbit"-ish devices stronger than -70 dBm

blecli enum AA:BB:CC:DD:EE:FF --read-all      # list services + read readables
blecli read AA:BB:CC:DD:EE:FF 2a19            # read Battery Level (short UUID)
blecli write AA:BB:CC:DD:EE:FF 0xffe1 01ff    # write bytes to a handle/UUID
blecli notify AA:BB:CC:DD:EE:FF 2a37 --log hr.jsonl   # stream notifications
```

Characteristics can be given as a full 128-bit UUID, a 16-bit short UUID
(`2a19`), or a handle (`0x0012`). A value that could be either, such as `0xffe1`,
is tried as a handle first and then as a short UUID.

`scan` is an active scan: the adapter sends scan requests to the devices it hears,
so they can detect it. It is not silent. `--adapter` only applies on BlueZ.

## Passive sniffing

A normal adapter cannot follow a live connection's frequency hopping, so these
subcommands drive dedicated tools. blecli just assembles their command lines.

```bash
# Local HCI trace of this host's own BLE traffic (BlueZ, no extra hardware):
blecli sniff btmon -w capture.btsnoop

# Over-the-air, nRF52840 dongle flashed with Sniffle firmware:
#   pip install sniffle-ble  (provides sniff_receiver.py)
blecli sniff sniffle -s /dev/ttyACM0 -o capture.pcap

# Over-the-air, BBC micro:bit flashed with btlejack firmware:
#   pip install btlejack
blecli sniff btlejack -s            # list connections on the air
blecli sniff btlejack -x capture.pcap
```

Open the resulting `.pcap`/`.btsnoop` files in Wireshark for analysis.

## Commands

| Command        | What it does                                             |
|----------------|----------------------------------------------------------|
| `scan`         | Actively collect advertisements: name, RSSI, vendor, service data |
| `enum`         | Connect and list services, characteristics, descriptors  |
| `read`         | Read a single characteristic                             |
| `write`        | Write bytes to a characteristic (with or without response)|
| `notify`       | Subscribe to notify/indicate characteristics             |
| `sniff btmon`  | Local HCI trace via BlueZ                                 |
| `sniff sniffle`| Over-the-air capture via nRF52840 + Sniffle              |
| `sniff btlejack`| Over-the-air capture via micro:bit + btlejack           |
