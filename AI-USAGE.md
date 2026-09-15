# AI Usage & Attribution

This document details the tools, prompt workflows, and human-in-the-loop verification strategies used throughout this project, explicitly recording real errors introduced by AI suggestions that were caught, debugged, and resolved.

---

## 1. Tools Used & Operational Scope

* **Primary AI Engines:** OpenAI ChatGPT / Claude / Gemini
* **Scope of Assistance:**
  * Initial scaffolding for `Dockerfile` and multi-platform build declarations.
  * Formulating loss equations for asymmetric financial penalties:
    $$\text{Total Loss} = (N_{\text{visits}} \times €380) + \sum_{\text{episodes}} (t_{\text{unresolved}} \times €600)$$
  * Drafting initial structure for markdown documentation and report layouts.
  * Shell automation templates for Docker commands.

---

## 2. Key Prompts Used

* *"Write a Python script that takes gateway telemetry parquet files and aggregates 3-sigma deviations over rolling 7-day windows without lookahead leakage."*
* *"How do we simulate the trade-off between a fixed €380 truck roll cost and a €600 weekly recurring penalty for missed meter readings under a 15-visit budget cap?"*
* *"Generate a non-parametric bootstrap resampling script in Python to calculate 95% confidence intervals across 300 fleet iterations."*
* *"How should Docker Compose be configured so live evaluators can mount unseen parquet telemetry without crashing on hardcoded date ranges?"*

---

## 3. Concrete AI Mistakes Caught and Corrected

During development, the AI introduced several critical bugs that were identified and corrected through manual testing:

### Mistake 1: Schema Hallucination (`KeyError: 'rx_bytes', 'tx_bytes'`)
* **What the AI did:** When generating `src/cost_optimization.py`, the AI assumed standard network telemetry fields and hardcoded `rx_bytes` and `tx_bytes` into the metric list.
* **Why it failed:** The dataset only contained `offline_duration_sec`, `disconnection_cnt`, `reboot_cnt`, and `ts`. Running the script inside Docker crashed with a fatal `KeyError`.
* **Correction:** Inspected `data/telemetry` schema directly and constrained the anomaly detection metrics strictly to the 3 real features.

### Mistake 2: Pandas MultiIndex Merge Crash
* **What the AI did:** To calculate mean and standard deviation, the AI wrote `base_df.groupby("gateway_id")[metrics].agg(["mean", "std"])` and attempted to merge it directly onto `recent_df`.
* **Why it failed:** `.agg(["mean", "std"])` produces a 2-level MultiIndex on columns, whereas `recent_df` has single-level columns. Pandas threw `MergeError: Not allowed to merge between different levels`.
* **Correction:** Explicitly flattened the aggregated column headers into single strings (`f"{col}_{stat}"`) before executing the merge.

### Mistake 3: Timezone Awareness Mismatch (`InvalidComparison`)
* **What the AI did:** Sliced timestamps using naive `pd.Timestamp(target_monday)` against `frame["ts"]`.
* **Why it failed:** Telemetry timestamps in parquet are stored as `datetime64[us, UTC]`. Python raised `TypeError: Cannot compare tz-naive and tz-aware datetime-like objects`.
* **Correction:** Added explicit UTC timezone localization (`pd.Timestamp(target_monday, tz="UTC")`) to ensure clean comparisons.

### Mistake 4: Lookahead Contamination & Hardcoded Date Fragility
* **What the AI did:** The AI initially chained `validate_submission.py` directly inside `docker-compose.yml` and hardcoded the evaluation dates (`2026-02-02` to `2026-03-23`).
* **Why it failed:** When live evaluators mount a new month of unseen data with different calendar dates, `validate_submission.py` asserts against the static 8 weeks, causing the container to crash.
* **Correction:** Decoupled submission validation from the default Docker entrypoint, implemented `--dynamic-dates` to infer Mondays from mounted telemetry, and enforced strict rolling baseline windows $[T - 35\text{d}, T - 7\text{d})$ to prevent data leakage.
