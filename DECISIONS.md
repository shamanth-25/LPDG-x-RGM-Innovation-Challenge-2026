# Engineering Decisions & Track Selection

Here is a rundown of the five main engineering decisions I made while building this pipeline, what else I considered, and why I ended up going this route.

---

## 1. The Five Core Choices

### Choice 1: Track Selection — Track D (Data Science & Decision Modeling)
* **What I chose:** I went with Track D. 
* **What else I considered:** Track A (Data Engineering) or Track B (DevOps).
* **Why I went this route:** The primary constraint in this problem isn't shuffling parquet files around or setting up infrastructure; it’s figuring out how to spend a limited technician budget to stop revenue bleed. Framing this natively as an asymmetric economic loss problem made the most sense for the business.

### Choice 2: Anomaly Scoring — 3-Sigma Deviations over Machine Learning
* **What I chose:** I stuck to a straightforward 3-sigma statistical deviation baseline across the 3 core metrics (`offline_duration_sec`, `disconnection_cnt`, `reboot_cnt`).
* **What else I considered:** Training a gradient-boosted tree (like XGBoost) or an RNN on the telemetry features.
* **Why I went this route:** The telemetry dataset doesn't actually have verified failure labels. Training a heavy ML classifier on proxy heuristics is a great way to overfit and leak data. The 3-sigma approach is deterministic, audit-friendly, and field engineers can actually understand it.

### Choice 3: Temporal Partitioning — Rolling 28-Day Baseline
* **What I chose:** I built the historical baselines (mean and standard deviation) strictly from the preceding 28 days $[T - 35\text{d}, T - 7\text{d})$, and aggregated the anomalies over the trailing 7 days $[T - 7\text{d}, T)$.
* **What else I considered:** Using the entire historical dataset or expanding windows.
* **Why I went this route:** Expanding windows slowly drown out recent hardware degradation, and using global distributions accidentally looks into the future. A strict 28-day sliding window adapts to local operating conditions safely.

### Choice 4: Ground-Truth Failure Definition — Unsupervised K-Means Clustering
* **What I chose:** I established our failure boundary by applying 1-D K-Means clustering to the historical meter collection rates. This let the math find the clear cutoff between healthy noise and physical breakdown (~65.6%), instead of just guessing. I then ranked whatever breached that boundary by cumulative failure hours.
* **What else I considered:** Just assuming a flat `<80%` collection rate meant a gateway was broken, or solely relying on 3-sigma telemetry spikes.
* **Why I went this route:** If I just made up an 80% threshold, my €600 penalty simulation would be completely circular—it would only prove that my model is good at guessing my own made-up rules. K-Means clustering forces the pipeline to test against genuine, statistically validated hardware states.

### Choice 5: Execution Architecture — Containerized CLI Wrapper
* **What I chose:** I wrote `run_solution.py` and wrapped the whole thing in Docker Compose.
* **What else I considered:** Modifying the provided `baseline_3sigma.py` script directly, or just throwing up a Makefile for host environments.
* **Why I went this route:** Editing the reference baseline script is an easy way to introduce regressions. Wrapping it cleanly in Docker ensures that regardless of who runs this code or heavily customized Python environments they use on their laptop, it just works out of the box.

---

## 2. Where the System Falls Over

* **Silent Gateways:** If a gateway loses total power or its backhaul totally severs, it completely stops emitting telemetry. Right now, this script just aggregates existing rows. Prolonged zero-row intervals really ought to be explicitly penalized as missing data rather than just assuming the unit is healthy.
* **Cold Starts:** Gateways that were just installed won't have a 28-day baseline yet. They fall back to whatever partial span is available, which makes their standard deviations pretty volatile.
* **Weather vs. Hardware:** The pipeline looks at units in isolation. It doesn't check if there's a localized thunderstorm or carrier blackout. This means we might accidentally dispatch a technician for an antenna drop when it’s really just a passing storm.

---

## 3. What Another Two Weeks Would Buy

1. **Geospatial Dispatching:** If we grabbed the GPS coordinates for these gateways and ran them through a Vehicle Routing solver, we could cluster dispatches by zip code. That would easily drop average truck roll costs from €380 down to maybe €240.
2. **Survival Modeling:** We could fit Weibull survival curves against the installation age and reboot stress to start predicting failures *before* they actually happen.
3. **Automated Feedback Loops:** If we had real technician work logs (`field_visits.csv`), we could ingest them and re-weight our metrics based on which parts were *actually* replaced in the field.
