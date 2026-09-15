# ⚡ IoT Gateway Predictive Maintenance
### Track D: Decision Modeling & Asymmetric Cost Optimization

*An automated predictive maintenance triage pipeline for smart meter IoT gateways. Identifies and ranks the top 15 gateways requiring field technician visits each week under an asymmetric cost structure (€380 visit cost vs. €600 weekly recurring penalty for missed meter readings).*

---

## 📌 Executive Summary

Field dispatch operations face a steep economic imbalance:
* **Cost of Action (Technician Visit):** Fixed at **€380**.
* **Cost of Inaction (Unaddressed Gateway Degradation):** Compounds at **€600 / week** in lost meter collection and SLA billing penalties.
* **Operational Constraint:** Fixed budget of **15 physical dispatches per calendar week**.

This system implements a **rolling 28-day statistical anomaly model** across telemetry metrics (`offline_duration_sec`, `disconnection_cnt`, `reboot_cnt`) paired with an **asymmetric decision frontier** to rank candidate gateways each week without lookahead leakage.

---

## 📊 Key Modeling Results (Track D)

| Metric | Empirical Value | Operational Interpretation |
| :--- | :--- | :--- |
| **Optimal Anomaly Cutoff** | **3.0σ** | Minimizes portfolio loss (€182,400 across 8 weeks) vs. 1.5σ (€194,400) |
| **Total 8-Week Loss (95% CI)** | **€94,818 – €133,706** | 300-iteration non-parametric bootstrap resampling over 299 gateways |
| **Median Expected Loss** | **€116,060** | Baseline financial exposure under realistic failure variance |
| **Failure Episode Capture Rate** | **48.2%** (40.0% – 55.5% CI) | Captures 54/112 historical fault episodes within the 15-visit/wk cap |
| **Mean Resolution Latency** | **2.01 weeks** (1.83 – 2.26 CI) | Average duration from fault onset to technician intervention |

---

## 🖼️ Visual Performance & Decision Frontiers

* **Threshold Sensitivity Cost Frontier:** See `plots/cost_frontier.png` for portfolio loss evaluated from 1.5σ to 4.0σ cutoffs.
* **Fleet Uncertainty Bootstrap Distribution:** See `plots/bootstrap_uncertainty.png` for the empirical 95% confidence interval distribution.

---

## 🚀 Quick Start (Submission Reproduction)

### 1. Generate Submission Predictions (Part 1 Gate)
Ensure the telemetry dataset is mounted in `./data`. Run the containerized pipeline:

```bash
docker compose up --build
