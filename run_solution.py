#!/usr/bin/env python3
"""Main execution runner for generating weekly gateway maintenance predictions."""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys
import pandas as pd
import numpy as np

from baseline_3sigma import load, rank_week, VISITS_PER_WEEK, SCORED_WEEKS

# Actionable technician guidance keyed by primary telemetry anomaly
METRIC_ACTIONS = {
    "offline_duration_sec": "Check backhaul cellular connection, SIM status, and main power supply.",
    "disconnection_cnt": "Inspect local RF antenna impedance, connector corrosion, and line noise.",
    "reboot_cnt": "Inspect power capacitor stability, watchdog timer logs, and power drops.",
    "rx_bytes": "Investigate mesh routing loops, packet flooding, and corrupted buffer queues.",
    "tx_bytes": "Verify radio transmitter health, antenna VSWR, and carrier packet loss.",
}


def get_target_mondays(frame: pd.DataFrame, dynamic: bool = False) -> list[dt.date]:
    """Return the official 8 evaluation weeks, or infer Mondays dynamically from telemetry."""
    if not dynamic:
        return SCORED_WEEKS

    max_ts = frame["ts"].max()
    latest_monday = max_ts.date() - dt.timedelta(days=max_ts.weekday())
    min_monday = frame["ts"].min().date()

    mondays = []
    curr = latest_monday
    while curr >= min_monday and len(mondays) < 8:
        mondays.append(curr)
        curr -= dt.timedelta(days=7)
    return sorted(mondays)


def format_reason(row, sigma: float) -> str:
    """Build concise, actionable technician triage text under 300 characters."""
    hours = int(row.flagged_hours)
    worst = row.worst_metric or "composite drift"
    action = METRIC_ACTIONS.get(worst, "Run full diagnostics and check antenna connections.")

    reason = (
        f"Alert: {hours}h cumulative breach >{sigma}σ baseline in trailing 7d. "
        f"Primary indicator: {worst}. Recommended action: {action}"
    )
    return reason[:290]


def build_predictions(frame: pd.DataFrame, weeks: list[dt.date], sigma: float = 3.0) -> pd.DataFrame:
    rows = []
    for monday in weeks:
        ranked = rank_week(frame, monday)
        if len(ranked) < VISITS_PER_WEEK:
            raise SystemExit(f"only {len(ranked)} gateways found before {monday}")

        for rank, row in enumerate(ranked.head(VISITS_PER_WEEK).itertuples(index=False), 1):
            rows.append(
                {
                    "week_start": monday.isoformat(),
                    "rank": rank,
                    "gateway_id": row.gateway_id,
                    "score": float(row.flagged_hours),
                    "reason": format_reason(row, sigma),
                }
            )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Part 1 predictions.csv")
    parser.add_argument("--data", type=pathlib.Path, default=pathlib.Path("data"))
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("predictions.csv"))
    parser.add_argument("--threshold", type=float, default=3.0, help="Sigma threshold multiplier")
    parser.add_argument("--dynamic-dates", action="store_true", help="Infer Mondays from data")
    args = parser.parse_args(argv)

    if not args.data.exists():
        print(f"Error: Data directory '{args.data}' does not exist.", file=sys.stderr)
        return 1

    print(f"Loading telemetry from {args.data}...")
    frame = load(args.data)
    weeks = get_target_mondays(frame, dynamic=args.dynamic_dates)
    print(f"Processing {len(weeks)} target weeks at {args.threshold} sigma...")

    preds = build_predictions(frame, weeks, sigma=args.threshold)
    preds.to_csv(args.out, index=False)
    print(f"Done. Wrote {len(preds)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
