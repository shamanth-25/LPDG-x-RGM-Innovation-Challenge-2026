# Engineering Decisions & Track Selection

This document formalizes the technical and analytical trade-offs made in designing the IoT gateway predictive maintenance pipeline.

---

## 1. The Five Core Choices

### Choice 1: Track Selection — Track D (Data Science & Decision Modeling)
* **What was chosen:** Track D was selected to directly model fleet maintenance as an asymmetric economic loss problem (€380 per technician visit vs. €600 weekly recurring fault penalty under a strict 15-visit capacity constraint).
* **What else could have been done:** Track A (Data Engineering / Parquet streaming pipelines) or Track B (DevOps / Infrastructure Reliability).
* **Why it was rejected:** The primary business constraint is not ingestion throughput or orchestration tooling; it is capital and labor allocation under resource limits. Supervised classifiers trained without verified labels suffer from severe target leakage and poor calibration. Grounding the triage strategy in decision theory and uncertainty estimation provides an auditable, defensible framework for operations.

### Choice 2: Anomaly Scoring — 3-Sigma Statistical Deviation Over Supervised Machine Learning
* **What was chosen:** Scored gateway degradation using a 3-sigma deviation baseline across the 3 core telemetry metrics (`offline_duration_sec`, `disconnection_cnt`, `reboot_cnt`).
* **What else could have been done:** Trained a gradient-boosted tree (e.g., XGBoost, LightGBM) or recurrent neural network on telemetry features.
* **Why it was rejected:** Telemetry does not contain verified binary ground-truth failure labels. Training a complex classifier on proxy heuristics introduces artificial label noise, risk of overfitting, and uncalibrated probabilities. The 3-sigma approach is deterministic, fully auditable by field engineers, and requires no opaque feature engineering.

### Choice 3: Temporal Partitioning — Rolling 28-Day Baseline with Strict Monday Cutoffs
* **What was chosen:** Derived baseline distributions (mean and standard deviation) strictly from the preceding 28 days $[T - 35\text{d}, T - 7\text{d})$, aggregating anomaly counts over the trailing 7 days $[T - 7\text{d}, T)$.
* **What else could have been done:** Used global fleet distributions across the entire dataset or expanding historical windows.
* **Why it was rejected:** Expanding windows dilute recent hardware degradation patterns, while global distributions introduce lookahead leakage. The fixed 28-day window adapts to local operating conditions while guaranteeing zero data contamination from future timestamps.

### Choice 4: Ranking Heuristic — Cumulative Anomaly Hours Over Single-Peak Outliers
* **What was chosen:** Ranked gateways based on total hours spent beyond the 3-sigma threshold across telemetry metrics in the trailing 7 days.
* **What else could have been done:** Ranked by maximum single-hour $z$-score deviation or total raw count of anomalous events.
* **Why it was rejected:** IoT cellular networks experience frequent transient noise, carrier packet storms, and temporary connection jitter that self-resolve within minutes. Cumulative duration filters out temporary network hiccups, prioritizing sustained degradation that genuinely warrants a physical technician visit.

### Choice 5: Execution Architecture — Dynamic Root CLI Wrapper with Containerized Execution
* **What was chosen:** Implemented `run_solution.py` with dynamic date discovery (`--dynamic-dates`) containerized via Docker Compose.
* **What else could have been done:** Modified `baseline_3sigma.py` directly, or relied on a host-level Python environment with a Makefile.
* **Why it was rejected:** Modifying the original baseline script risks introducing regressions against reference implementations. Containerization eliminates environment drift across host operating systems, and dynamic date detection enables the pipeline to execute out-of-the-box when evaluators mount unseen telemetry from arbitrary date ranges.

---

## 2. Operational Limitations & Edge Cases

* **Silent Gateways:** Gateways that lose power or backhaul connectivity completely stop emitting telemetry rows. The current aggregation tallies existing rows; prolonged zero-row intervals should be penalized via explicit missing-interval detection rather than assuming nominal health.
* **Cold Starts (< 28 Days History):** Newly installed gateways lack the full 28-day baseline history. Currently, they fall back to available partial spans, which can produce volatile standard deviations.
* **Environmental vs. Hardware Faults:** The pipeline currently treats antenna drops in isolation, without cross-referencing weather or regional cellular carrier outages, which can lead to false dispatches during storm events.

---

## 3. What Another Two Weeks Would Buy

1. **Geospatial Dispatch Clustering:** Integrate gateway GPS coordinates with a Vehicle Routing Problem (VRP) solver to group dispatches geographically, reducing average truck roll costs from €380 to an estimated €240 per site.
2. **Weibull Degradation & Survival Modeling:** Fit parametric survival curves against hardware installation age and cumulative reboot stress to estimate time-to-failure before meter reading collection drops.
3. **Automated Maintenance Feedback Loop:** Ingest technician work logs (`field_visits.csv`) to dynamically re-weight telemetry metrics based on actual hardware replacements performed in the field.
