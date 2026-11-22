# Room

Local UI and agent for TVs and other devices on **this computer’s Wi-Fi**.

This cloud agent cannot see your home network. Run the hub on your Mac (or any machine on the same LAN as the TV).

## Run

```bash
cd home-control
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m home_control --demo          # sample devices, no LAN required
python -m home_control                 # real scan of this Mac's Wi-Fi
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787) **on that Mac**. This Cursor Cloud chat cannot press buttons on your TV.

- **Scan Wi-Fi** uses mDNS, SSDP, and a unicast probe of TV/speaker ports (Roku 8060, Samsung 8001, Chromecast, Sonos, LG, Sony). That still works when the router filters multicast.
- **Deep scan** also probes plugs, Home Assistant, printers, and media servers on your `/24`. Use that only on a network you own.
- The agent understands phrases like `what's on my wifi`, `turn off the living room tv`, `mute the roku`, `turn on the bedroom plug`.

## Your `tv.py`

If you have a script at `~/Downloads/tv.py`, point the hub at it:

```bash
python -m home_control --plugin /Users/viswanathsekar/Downloads/tv.py
```

The plugin can expose `discover()` (list of dicts with `name`, `address`, `protocol`) and `command(device, action, value)`.

## What it can press today

| Protocol | Control |
| --- | --- |
| Roku | Full remote, app launch |
| TP-Link Kasa | On / off |
| Shelly / Tasmota | On / off |
| Sonos | Play, pause, volume |
| Sony Bravia | IRCC (set `HOME_CONTROL_SONY_PSK`) |
| Samsung | Remote keys over websocket (accept the pairing prompt on the TV once) |
| LG, Chromecast, Apple TV | Discovered; control needs pairing or `tv.py` |

The hub only talks to private addresses (`10/8`, `172.16/12`, `192.168/16`, loopback).

## Agent (Cursor playground)

The hub UI already has a built-in command agent. There is also a Cursor Agent SDK project in `../room` that talks to the same hub:

```bash
# terminal 1
python -m home_control --demo   # or omit --demo on your home Wi-Fi

# terminal 2
cd ../room
npx @grok/agent-sdk login       # once, on your machine
npx @grok/agent-sdk dev         # playground
```

Set `HOME_HUB_URL` if the hub is not on `http://127.0.0.1:8787`.

## Tests

```bash
cd home-control
python -m pytest
```
