# Network health report

An offline Python script that reads a CSV snapshot of synthetic device check counts and average packet loss, then prints a simple availability summary. It demonstrates turning monitoring exports into a repeatable report.

## Metrics

- **Availability estimate:** `(checks - failures) / checks * 100`.
- **Average packet loss:** taken directly from the input's `avg_packet_loss_pct` field and displayed as a percentage.

Availability is only as meaningful as the check method, sampling interval, timeout, and denominator. This formula does not calculate service-level availability over time, distinguish planned maintenance, or infer end-user experience. Average packet loss is not a substitute for latency, jitter, per-flow loss, or time-series analysis.

## Input format

`sample.csv` contains:

```csv
device,checks,failures,avg_packet_loss_pct
edge-router-1,1000,2,0.03
core-switch-1,1000,0,0.00
lab-firewall-1,1000,8,0.25
```

All values are synthetic. The current script requires a row per device, positive check counts, and failure counts between zero and checks. It expects numeric packet-loss percentages; validate input ranges before using output in an operational report.

## Run

```bash
python report.py sample.csv
```

If no argument is supplied, the script reads `sample.csv` relative to the current working directory. Pass a path explicitly when running from elsewhere.

## Interpretation and limitations

- A 99.8% result from 1,000 probes means 2 probes failed; it does not necessarily mean 99.8% monthly service availability.
- Averages can hide short outages and bursts. Preserve timestamps and raw observations for incident analysis.
- The report has no time window, device identity validation, alert thresholds, confidence intervals, or historical storage.
- It does not perform probes, query SNMP/streaming telemetry, or contact network devices.
- No monitoring platform integration or production SLO validation is included.

Before operational use, add strict CSV schema/range checks, timestamped samples, explicit measurement windows, tests, and a clear definition of how failures and maintenance are counted.
