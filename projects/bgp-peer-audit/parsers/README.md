# Offline vendor parsers

These small parsers convert sanitized text captures into the existing normalized JSON shape accepted by `report.py`. They make no network connections and do not execute device commands.

## Use

Run from `projects/bgp-peer-audit`:

```sh
python -c "from pathlib import Path; from parsers.junos import parse; import json; print(json.dumps(parse(Path('fixtures/junos-neighbors.txt').read_text(), 'edge-r1'), indent=2))"
python -c "from pathlib import Path; from parsers.cisco_ios import parse; import json; print(json.dumps(parse(Path('fixtures/cisco-ios-neighbors.txt').read_text(), 'edge-r1'), indent=2))"
```

Save the JSON output to a file, then pass that file to `python report.py normalized.json`.

## Supported subset and limitations

- Juniper Junos: text blocks beginning `Peer: ADDRESS[+PORT] AS ASN`, with a `State:` field and optionally `Received prefixes: N` within each peer block. Both the `Type: ... State: ...` line and a standalone `State:` line are supported.
- Cisco IOS: blocks beginning `BGP neighbor is ADDRESS, ... remote AS ASN`, with `BGP state = STATE` and optionally `N accepted prefixes`.
- Missing prefix counts are omitted, not guessed. The downstream audit will warn if thresholds are configured.
- Output contains only address, remote AS, state, and received-prefix count when recognized. Device name is caller-supplied. Configure thresholds separately in normalized JSON if required.
- These are intentionally narrow regex parsers, not complete grammars. IOS XE/NX-OS/IOS XR variants, VRF-specific header variations beyond the optional single VRF token, IPv6 address formats with unexpected punctuation, localized output, alternate prefixes terminology, wrapped/multi-line fields, summary/table output, Junos XML/JSON, logical-system-specific output, and vendor/software-version differences may not parse. Treat failure as unsupported rather than trusting partial data.
- Junos may show several routing tables per peer; this parser captures the first matching `Received prefixes` line in that peer block. For multi-family/multi-RIB environments this is not a total across address families.
- Always sanitize captures first. Fixtures use documentation-only addresses and private-use ASNs. No live-device validation is claimed.
