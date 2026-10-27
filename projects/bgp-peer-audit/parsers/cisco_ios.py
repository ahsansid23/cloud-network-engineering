"""Parse a conservative subset of Cisco IOS 'show ip bgp neighbors' text."""
import re

HEADER = re.compile(
    r"^BGP neighbor is (\S+),\s*(?:vrf\s+\S+,\s*)?remote AS (\d+)", re.M)
STATE = re.compile(r"^\s*BGP state = ([^,\r\n]+)", re.M)
PREFIX = re.compile(r"^\s*(\d+) accepted prefixes\b", re.M)


def parse(text, device_name):
    """Return normalized {'devices': [...]} data; raise ValueError on unsupported text."""
    matches = list(HEADER.finditer(text))
    if not matches:
        raise ValueError("No supported Cisco IOS 'BGP neighbor is ... remote AS ...' blocks found")
    peers = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.start():end]
        state_match = STATE.search(block)
        if not state_match:
            raise ValueError(f"Could not find BGP state for peer {match.group(1)}")
        peer = {"address": match.group(1), "remote_as": int(match.group(2)),
                "state": state_match.group(1).strip()}
        prefix_match = PREFIX.search(block)
        if prefix_match:
            peer["prefixes_received"] = int(prefix_match.group(1))
        peers.append(peer)
    return {"devices": [{"name": device_name, "vendor": "cisco_ios", "peers": peers}]}
