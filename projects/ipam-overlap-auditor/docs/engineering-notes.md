# Engineering notes: IPAM overlap auditing

This guide explains the networking concepts behind the auditor, implementation decisions, and how to interpret results without confusing a syntactic overlap with a production routing fault.

## 1. CIDR refresher

Classless Inter-Domain Routing (CIDR) represents an address block as an address and prefix length. The prefix length is the number of significant leading bits. For IPv4, `10.20.0.0/16` contains 65,536 addresses; `10.20.8.0/24` contains 256. IPv6 uses the same prefix concept with a 128-bit address space.

A prefix is canonical when all host bits are zero. `10.20.8.0/24` is canonical; `10.20.8.7/24` is an interface address expression, not the canonical network prefix. The tool uses Python `ipaddress.ip_network(..., strict=True)` to reject host bits instead of quietly rewriting an operator's input. This makes source-data errors visible. See the [Python ipaddress documentation](https://docs.python.org/3/library/ipaddress.html).

## 2. What does overlap mean?

Two prefixes overlap if they share any address space. For canonical CIDR blocks of the same address family, overlap means one block is equal to or contained within the other.

- `192.0.2.0/24` and `192.0.2.0/24`: duplicate allocation.
- `192.0.2.0/24` and `192.0.2.128/25`: nested overlap.
- `192.0.2.0/24` and `192.0.3.0/24`: disjoint.
- An IPv4 prefix and IPv6 prefix are not compared as overlapping networks.

The `overlaps()` method handles address arithmetic; the tool distinguishes exact equality from a non-identical overlap to make reports more actionable.

## 3. Why site and VRF are part of the key

An IP address is not globally unique across every private network. Two disconnected sites or isolated VRFs can legitimately reuse RFC 1918 space. Comparing every prefix in a file without context would produce false positives.

This implementation only compares records where both `site` and `vrf` match exactly. Real environments may also need tenant, environment, cloud account, VPC/VNet, network type, or explicit address-space-sharing policy. If route leaking, VPNs, peering, or mergers connect address spaces, separate VRF labels do not guarantee there is no conflict. Model those relationships separately.

## 4. Aggregate versus allocation

Route aggregation and hierarchical IPAM commonly represent a parent block and child prefixes at the same time. An organization may own `10.40.0.0/16` and allocate `10.40.8.0/24` to an application subnet. That relationship can be intentional.

The auditor flags it because a CSV alone does not say whether the parent is a summary, reserved pool, or simultaneously allocated subnet. Suppressing all parent/child overlaps can hide genuine double allocation. A more mature implementation could add a record type such as `aggregate`, `pool`, or `allocation` and enforce documented type-aware rules. Until then, treat each finding as a review prompt, not an automatic declaration of an outage.

## 5. Complexity and scale

The current implementation compares each valid entry with every other entry. With n valid rows, the number of candidate pairs is n(n-1)/2, so runtime grows quadratically. This is useful in a teaching project because the logic is compact and easy to audit.

For large datasets, sort networks by address family, site, VRF, and integer start/end address, then use an interval structure to avoid checking all pairs. Any optimization should preserve deterministic findings and be tested against a simple reference implementation. Benchmark synthetic inventories before claiming a scale limit.

## 6. Input and report contract

The CSV is untrusted input. The tool validates required headers and per-row values, rejects malformed CIDRs, preserves source row numbers, and returns structured findings. Invalid rows are not included in overlap comparison because their network boundaries are unknown.

Text output is intended for a human reviewing a change. JSON output is more appropriate for CI artifacts or a future report consumer. Exit codes distinguish a clean inventory, findings, and an input/header error. Consumers should not assume every non-zero code means a crash.

## 7. How this fits a change process

1. Generate a sanitized inventory snapshot.
2. Run static validation and save JSON output.
3. Have an engineer review every finding and confirm the intended scope model.
4. Compare against cloud and routing constraints relevant to the change.
5. Obtain approval, plan rollback, and execute through the normal change process.
6. Re-run validation after the source inventory changes.

This tool does not check whether a route is advertised, and does not prove that two networks are connected. It reports consistency issues only in the records it receives.

## 8. Potential extensions

- Validate duplicate names and whitespace-only headers.
- Add explicit record classes so parent pools and child allocations can follow policy-defined rules.
- Emit summary counts by severity and finding code.
- Add allow-list rules that require a reason and owner; never silently suppress findings.
- Add a versioned input contract or JSON Schema for integrations.
- Add CI that runs unit tests and a known-clean fixture separately from the intentionally failing sample.
- Add a performance fixture before replacing pairwise comparison.

Each extension should preserve safe defaults, explain false-positive/false-negative trade-offs, and include synthetic tests.
