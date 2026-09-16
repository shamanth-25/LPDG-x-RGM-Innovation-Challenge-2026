# AI Usage & Attribution

I used a few AI tools to help speed up some of the scaffolding and math for this project, but they definitely weren't perfect. Here’s a quick breakdown of exactly what I used them for and where I had to step in and fix their mistakes.

---

## 1. Tools & Scope

* **The Stacks Used:** OpenAI ChatGPT, Claude, and Gemini.
* **What they helped with:**
  * Setting up the initial scaffolding for the `Dockerfile` and multi-platform build scripts.
  * Formulating the markdown math blocks for the asymmetric financial penalties.
  * Generating shell automation templates for the Docker commands.

---

## 2. Key Prompts I Ran

Here are some of the main prompts I used to guide the tools:

* *"Write a Python script that takes gateway telemetry parquet files and aggregates 3-sigma deviations over rolling 7-day windows without lookahead leakage."*
* *"How do we simulate the trade-off between a fixed €380 truck roll cost and a €600 weekly recurring penalty for missed meter readings under a 15-visit budget cap?"*
* *"Generate a non-parametric bootstrap resampling script in Python to calculate 95% confidence intervals across 300 fleet iterations."*
* *"How should Docker Compose be configured so live evaluators can mount unseen parquet telemetry without crashing on hardcoded date ranges?"*

---

## 3. The Mistakes I Had to Fix

During development, the AI introduced some fairly critical bugs. I caught these and manually corrected them:

### Mistake 1: Schema Hallucination (`KeyError: 'rx_bytes', 'tx_bytes'`)
* **What happened:** When drafting `src/cost_optimization.py`, the AI just assumed standard network telemetry fields and hardcoded `rx_bytes` and `tx_bytes` into the metrics logic.
* **Why it died:** Our dataset only contains `offline_duration_sec`, `disconnection_cnt`, and `reboot_cnt`. Running it immediately crashed inside Docker with a fatal `KeyError`.
* **The fix:** I threw out the hallucinated fields and properly mapped the script strictly to the actual schema.

### Mistake 2: Pandas MultiIndex Merge Crash
* **What happened:** The AI tried to calculate the mean and standard deviation via `base_df.groupby("gateway_id")[metrics].agg(["mean", "std"])` and then carelessly merged it directly onto a flat dataframe.
* **Why it died:** `.agg(["mean", "std"])` generates a 2-level MultiIndex in pandas, which blew up with a `MergeError: Not allowed to merge between different levels` when it hit the single-level dataframe.
* **The fix:** I manually flattened the aggregated column headers into clean, single strings (like `offline_duration_sec_mean`) before executing the merge.

### Mistake 3: Timezone Awareness `InvalidComparison`
* **What happened:** The AI sliced timestamps using a naive `pd.Timestamp(target_monday)` against `frame["ts"]`.
* **Why it died:** The telemetry timestamps in our parquet files are stored as timezone-aware UTC (`datetime64[us, UTC]`). Mixing them threw a `TypeError`.
* **The fix:** Added explicit UTC localization (`tz="UTC"`) to the target limits so the pandas engine could compare them safely.

### Mistake 4: Lookahead Contamination & Date Fragility
* **What happened:** The AI initially chained `validate_submission.py` directly inside `docker-compose.yml` and hardcoded the evaluation dates.
* **Why it died:** If you mount a fresh month of unseen data to test the pipeline, `validate_submission.py` angrily asserts against those static old weeks and crashes the entire container run.
* **The fix:** I decoupled the submission validation from the default Docker entrypoint and implemented a `--dynamic-dates` flag. I also enforced strict rolling baseline windows to mathematically prevent future data leakage.

### Mistake 5: Circular Proxy Validation Assumption
* **What happened:** While drafting the fleet cost simulation, the AI arbitrarily assumed a flat `<80%` meter collection rate was the universal definition of a "broken gateway" and blindly applied the €600 penalty to it.
* **Why it died (logically):** This violated the core instruction to critically *decide* what a failure actually is. Applying a manufactured static threshold meant the simulation was completely circular—our 3-sigma anomaly model was just being benchmarked on how well it agreed with the AI's invented 80% rule, completely detaching the math from the physical world.
* **The fix:** I scrapped the assumption entirely. I implemented a proper 1-D K-Means clustering algorithm to mathematically comb through the entire telemetry distribution and locate the exact empirical cutoff dividing normal RF jitter from physical hardware breakdown.
