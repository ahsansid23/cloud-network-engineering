"""Parse a conservative subset of Junos 'show bgp neighbor' text."""
import re

PEER = re.compile(r"^\s*Peer:\s*(\S+?)(?:\+\d+)?\s+AS\s+(\d+)", re.M)
STATE = re.compile(r"^\s*Type:\s*\S+\s+State:\s*(\S+)", re.M)
STATE_ONLY = re.compile(r"^\s*State:\s*(\S+)", re.M)
PREFIX = re.compile(r"^\s*Received prefixes:\s*(\d+)\s*$", re.M)


def parse(text, device_name):
    """Return normalized {'devices': [...]} data; raise ValueError on unsupported text."""
    matches = list(PEER.finditer(text))
    if not matches:
        raise ValueError("No supported Junos 'Peer: ... AS ...' blocks found")
    peers = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.start():end]
        state_match = STATE.search(block) or STATE_ONLY.search(block)
        if not state_match:
            raise ValueError(f"Could not find session State for peer {match.group(1)}")
        prefix_match = PREFIX.search(block)
        peer = {"address": match.group(1), "remote_as": int(match.group(2)),
                "state": state_match.group(1)}
        if prefix_match:
            peer["prefixes_received"] = int(prefix_match.group(1))
        peers.append(peer)
    return {"devices": [{"name": device_name, "vendor": "juniper_junos", "peers": peers}]}
