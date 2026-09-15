#!/usr/bin/env python3
"""Track D: Cost-frontier simulation and threshold optimization model."""

from __future__ import annotations

import pathlib
import datetime as dt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from baseline_3sigma import load, VISITS_PER_WEEK

COST_VISIT = 380.0
COST_PENALTY_WEEK = 600.0
METRICS = ["offline_duration_sec", "disconnection_cnt", "reboot_cnt"]


def load_meter_proxy_ground_truth(data_dir: pathlib.Path) -> pd.DataFrame:
    """Computes proxy ground truth failure state (< 80% collection rate)."""
    meter_file = data_dir / "meter_read_success.csv"
    if not meter_file.exists():
        raise FileNotFoundError(f"Missing {meter_file}")

    df = pd.read_csv(meter_file)
    df["week_start"] = pd.to_datetime(df["week_start"]).dt.strftime("%Y-%m-%d")
    expected = df["meters_expected"].replace(0, np.nan)
    df["collection_rate"] = df["meters_read"] / expected
    df["is_faulty"] = (df["collection_rate"] < 0.80).astype(int)
    return df[["week_start", "gateway_id", "is_faulty"]].drop_duplicates()


def simulate_fleet_cost(predictions: pd.DataFrame, ground_truth: pd.DataFrame, target_weeks: list[str]) -> dict:
    """Evaluates €380 visit costs against compounding €600 weekly penalties."""
    gt_eval = ground_truth[ground_truth["week_start"].isin(target_weeks)].copy()
    gt_sorted = gt_eval.sort_values(["gateway_id", "week_start"])

    pred_visits = predictions.groupby("gateway_id")["week_start"].apply(set).to_dict()
    total_visit_cost = len(predictions) * COST_VISIT

    episodes = []
    for gid, group in gt_sorted.groupby("gateway_id"):
        curr = []
        for row in group.itertuples():
            if row.is_faulty:
                curr.append(row.week_start)
            else:
                if curr:
                    episodes.append((gid, curr))
                    curr = []
        if curr:
            episodes.append((gid, curr))

    penalty_cost = 0.0
    caught = 0
    delays = []

    for gid, ep_weeks in episodes:
        visits = pred_visits.get(gid, set())
        hits = [w for w in ep_weeks if w in visits]
        if hits:
            earliest_hit = min(hits)
            unresolved = ep_weeks.index(earliest_hit) + 1
            delays.append(unresolved)
            penalty_cost += unresolved * COST_PENALTY_WEEK
            caught += 1
        else:
            delays.append(len(ep_weeks))
            penalty_cost += len(ep_weeks) * COST_PENALTY_WEEK

    total_episodes = len(episodes)
    return {
        "total_cost": total_visit_cost + penalty_cost,
        "visit_cost": total_visit_cost,
        "penalty_cost": penalty_cost,
        "episodes_caught": caught,
        "total_episodes": total_episodes,
        "capture_rate": (caught / total_episodes) if total_episodes else 0.0,
        "mean_delay": float(np.mean(delays)) if delays else 0.0,
    }


def rank_week_custom_sigma(frame: pd.DataFrame, target_monday: dt.date, sigma: float) -> pd.DataFrame:
    """Score gateways using customizable sigma multiplier with flattened columns."""
    if hasattr(frame["ts"].dt, "tz") and frame["ts"].dt.tz is not None:
        t_end = pd.Timestamp(target_monday, tz="UTC")
    else:
        t_end = pd.Timestamp(target_monday)

    t_start_7d = t_end - pd.Timedelta(days=7)
    t_start_28d = t_end - pd.Timedelta(days=35)

    baseline_mask = (frame["ts"] >= t_start_28d) & (frame["ts"] < t_start_7d)
    recent_mask = (frame["ts"] >= t_start_7d) & (frame["ts"] < t_end)

    base_df = frame[baseline_mask]
    recent_df = frame[recent_mask]

    base_stats = base_df.groupby("gateway_id")[METRICS].agg(["mean", "std"])

    if base_stats.empty or recent_df.empty:
        return pd.DataFrame(columns=["gateway_id", "flagged_hours"])

    # Flatten MultiIndex columns: e.g. offline_duration_sec_mean, offline_duration_sec_std
    base_stats.columns = [f"{col}_{stat}" for col, stat in base_stats.columns]
    base_stats = base_stats.reset_index()

    recent_merged = recent_df.merge(base_stats, on="gateway_id", how="left")

    anomalies = pd.Series(False, index=recent_merged.index)
    for m in METRICS:
        col_mean = recent_merged[f"{m}_mean"]
        col_std = recent_merged[f"{m}_std"].fillna(0)
        cutoff = col_mean + (sigma * col_std)
        anomalies |= (recent_merged[m] > cutoff) & (col_std > 0)

    recent_merged["is_anom"] = anomalies.astype(int)
    scores = recent_merged.groupby("gateway_id")["is_anom"].sum().reset_index()
    scores.rename(columns={"is_anom": "flagged_hours"}, inplace=True)
    return scores.sort_values("flagged_hours", ascending=False)


def get_validation_mondays(gt: pd.DataFrame, n_weeks: int = 8) -> list[dt.date]:
    mondays = sorted(pd.to_datetime(gt["week_start"].unique()).date)
    return mondays[-n_weeks:]


def run_threshold_sweep(data_dir: pathlib.Path, thresholds: list[float]) -> pd.DataFrame:
    print("Loading telemetry for threshold sensitivity modeling...")
    frame = load(data_dir)
    gt = load_meter_proxy_ground_truth(data_dir)
    val_mondays = get_validation_mondays(gt, n_weeks=8)
    target_weeks = [w.isoformat() for w in val_mondays]
    print(f"Validation weeks ({len(target_weeks)}): {target_weeks}")

    results = []
    for thresh in thresholds:
        rows = []
        for monday in val_mondays:
            ranked = rank_week_custom_sigma(frame, monday, thresh)
            for rank, row in enumerate(ranked.head(VISITS_PER_WEEK).itertuples(index=False), 1):
                rows.append({
                    "week_start": monday.isoformat(),
                    "rank": rank,
                    "gateway_id": row.gateway_id,
                    "score": float(row.flagged_hours),
                })
        preds = pd.DataFrame(rows)
        metrics = simulate_fleet_cost(preds, gt, target_weeks)
        metrics["threshold"] = thresh
        results.append(metrics)
        print(
            f"Threshold {thresh:.1f}σ -> Total: €{metrics['total_cost']:,.0f} | "
            f"Visits: €{metrics['visit_cost']:,.0f} | Penalty: €{metrics['penalty_cost']:,.0f} | "
            f"Caught: {metrics['episodes_caught']}/{metrics['total_episodes']} ({metrics['capture_rate']:.1%})"
        )

    return pd.DataFrame(results)


if __name__ == "__main__":
    threshold_range = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    res_df = run_threshold_sweep(pathlib.Path("data"), threshold_range)

    plots_dir = pathlib.Path("plots")
    plots_dir.mkdir(exist_ok=True)

    plt.figure(figsize=(8, 4.5))
    plt.plot(res_df["threshold"], res_df["total_cost"], marker="o", linewidth=2, color="#1f77b4", label="Total Fleet Loss")
    plt.plot(res_df["threshold"], res_df["penalty_cost"], marker="s", linestyle=":", color="#ff7f0e", label="Unresolved Penalty (€600/wk)")
    plt.axvline(3.0, color="#d62728", linestyle="--", label="Operational Baseline (3.0σ)")
    plt.title("Threshold Sensitivity vs. Portfolio Loss (€380 vs €600)")
    plt.xlabel("Anomaly Sigma Threshold (σ)")
    plt.ylabel("Simulated 8-Week Fleet Loss (€)")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / "cost_frontier.png", dpi=150)
    plt.close()
    print("Saved cost frontier plot to plots/cost_frontier.png")
