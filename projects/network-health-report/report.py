import csv
import sys
from pathlib import Path
path = Path(sys.argv[1] if len(sys.argv) > 1 else "sample.csv")
with path.open(newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))
if not rows:
    raise SystemExit("CSV contains no device rows")
print(f"{'Device':<22} {'Availability':>12} {'Avg loss':>10}")
for row in rows:
    checks, failures = int(row["checks"]), int(row["failures"])
    if checks <= 0 or failures < 0 or failures > checks:
        raise SystemExit(f"Invalid check counts for {row['device']}")
    availability = 100 * (checks - failures) / checks
    loss = float(row["avg_packet_loss_pct"])
    print(f"{row['device']:<22} {availability:>11.3f}% {loss:>9.3f}%")
