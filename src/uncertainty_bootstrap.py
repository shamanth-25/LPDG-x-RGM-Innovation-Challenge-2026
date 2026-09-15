#!/usr/bin/env python3
"""Track D: Bootstrap resampling model for fleet uncertainty quantification."""

from __future__ import annotations

import pathlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from baseline_3sigma import load, VISITS_PER_WEEK
from src.cost_optimization import (
    load_meter_proxy_ground_truth,
    simulate_fleet_cost,
    get_validation_mondays,
    rank_week_custom_sigma,
)


def run_bootstrap_simulation(
    data_dir: pathlib.Path,
    iterations: int = 300,
    seed: int = 42,
) -> dict:
    gt = load_meter_proxy_ground_truth(data_dir)
    val_mondays = get_validation_mondays(gt, n_weeks=8)
    target_weeks = [w.isoformat() for w in val_mondays]

    print("Generating validation period predictions (3.0σ baseline)...")
    frame = load(data_dir)
    rows = []
    for monday in val_mondays:
        ranked = rank_week_custom_sigma(frame, monday, sigma=3.0)
        for rank, row in enumerate(ranked.head(VISITS_PER_WEEK).itertuples(index=False), 1):
            rows.append({
                "week_start": monday.isoformat(),
                "rank": rank,
                "gateway_id": row.gateway_id,
                "score": float(row.flagged_hours),
            })
    preds = pd.DataFrame(rows)

    unique_gids = gt["gateway_id"].unique()
    rng = np.random.default_rng(seed)

    boot_costs = []
    boot_capture_rates = []
    boot_delays = []

    print(f"Running {iterations} bootstrap resamples over {len(unique_gids)} gateways...")
    for _ in range(iterations):
        sample_gids = rng.choice(unique_gids, size=len(unique_gids), replace=True)
        sub_gt = gt[gt["gateway_id"].isin(sample_gids)]
        sub_preds = preds[preds["gateway_id"].isin(sample_gids)]

        metrics = simulate_fleet_cost(sub_preds, sub_gt, target_weeks)
        boot_costs.append(metrics["total_cost"])
        boot_capture_rates.append(metrics["capture_rate"])
        boot_delays.append(metrics["mean_delay"])

    cost_ci = np.percentile(boot_costs, [2.5, 50.0, 97.5])
    capture_ci = np.percentile(boot_capture_rates, [2.5, 50.0, 97.5])
    delay_ci = np.percentile(boot_delays, [2.5, 50.0, 97.5])

    plots_dir = pathlib.Path("plots")
    plots_dir.mkdir(exist_ok=True)

    plt.figure(figsize=(8, 4.5))
    plt.hist(boot_costs, bins=25, color="#2ca02c", edgecolor="black", alpha=0.75)
    plt.axvline(cost_ci[0], color="red", linestyle="--", label=f"2.5% CI: €{cost_ci[0]:,.0f}")
    plt.axvline(cost_ci[1], color="black", linestyle="-", label=f"Median: €{cost_ci[1]:,.0f}")
    plt.axvline(cost_ci[2], color="red", linestyle="--", label=f"97.5% CI: €{cost_ci[2]:,.0f}")
    plt.title("Fleet Uncertainty: Bootstrap Cost Distribution (€)")
    plt.xlabel("Simulated 8-Week Fleet Loss (€)")
    plt.ylabel("Bootstrap Frequency")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / "bootstrap_uncertainty.png", dpi=150)
    plt.close()
    print("Saved bootstrap uncertainty plot to plots/bootstrap_uncertainty.png")

    return {
        "cost_95_ci": (cost_ci[0], cost_ci[2]),
        "cost_median": cost_ci[1],
        "capture_rate_95_ci": (capture_ci[0], capture_ci[2]),
        "mean_delay_95_ci": (delay_ci[0], delay_ci[2]),
    }


if __name__ == "__main__":
    summary = run_bootstrap_simulation(pathlib.Path("data"))
    print("\n--- Empirical Modeling Results ---")
    print(f"Total 8-Week Fleet Loss 95% Range: €{summary['cost_95_ci'][0]:,.0f} to €{summary['cost_95_ci'][1]:,.0f}")
    print(f"Median Fleet Loss: €{summary['cost_median']:,.0f}")
    print(f"Capture Rate 95% Range: {summary['capture_rate_95_ci'][0]:.1%} to {summary['capture_rate_95_ci'][1]:.1%}")
    print(f"Mean Resolution Delay 95% Range: {summary['mean_delay_95_ci'][0]:.2f} to {summary['mean_delay_95_ci'][1]:.2f} weeks")
